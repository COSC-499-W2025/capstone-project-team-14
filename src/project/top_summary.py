"""Project ranking and summary generation with user contribution support."""
import math
from typing import Iterable, List, Literal, Optional, Tuple
from dataclasses import dataclass

from .aggregator import ProjectInfo, compute_rank_inputs, compute_preliminary_score


RankingCriteria = Literal["score", "recency", "commits", "loc", "impact", "user_contrib"]


@dataclass
class RankedProject:
    """Project with ranking metadata."""
    project: ProjectInfo
    rank: int
    criteria: RankingCriteria
    score: Optional[float] = None


def _ensure_rank(pi: ProjectInfo) -> ProjectInfo:
    """Ensure project has rank_inputs and preliminary_score."""
    if not pi.rank_inputs:
        pi.rank_inputs = compute_rank_inputs(pi)
    if pi.preliminary_score == 0.0 and pi.rank_inputs:
        pi.preliminary_score = compute_preliminary_score(pi.rank_inputs)
    return pi


def _criteria_key(criteria: RankingCriteria, user_identifier: Optional[str] = None):
    """Return key function for ranking by given criteria."""
    if criteria == "score":
        return lambda p: p.preliminary_score
    elif criteria == "recency":
        return lambda p: p.rank_inputs.get("recency_days", float('inf'))
    elif criteria == "commits":
        return lambda p: p.totals.get("commits", 0)
    elif criteria == "loc":
        return lambda p: p.lines_of_code
    elif criteria == "impact":
        return lambda p: _impact_score(p)
    elif criteria == "user_contrib":
        if not user_identifier:
            return lambda p: 0.0
        return lambda p: p.rank_inputs.get("user_contrib_score", 0.0)
    else:
        raise ValueError(f"Unknown criteria: {criteria}")


def _impact_score(pi: ProjectInfo) -> float:
    """Calculate impact score based on commits, LOC, and duration."""
    commits = pi.totals.get("commits", 0)
    loc = pi.lines_of_code
    days = pi.duration.get("days", 1)
    return round(commits * math.log1p(loc) / max(1, days), 2)


def _contribution_summary(pi: ProjectInfo, user_identifier: Optional[str] = None) -> Tuple[str, float]:
    """Generate contribution summary for a project."""
    authors = pi.authors or []
    if not authors:
        if user_identifier and pi.source == "local":
            return (f"{user_identifier} (Local project)", 1.0)
        return ("Individual contributor", 1.0 if not pi.is_collaborative else 0.0)
        
    if user_identifier:
        user_id_lower = user_identifier.lower()
        user_commits = 0
        user_name = None
        
        for author in authors:
            author_email = author.get("email", "").lower()
            author_name = author.get("name", "").lower()
            if user_id_lower in author_email or user_id_lower in author_name:
                user_commits += author.get("commits", 0)
                user_name = author.get("name")
        
        if user_commits > 0:
            total_commits = sum(author.get("commits", 0) for author in authors)
            share = user_commits / total_commits if total_commits > 0 else 0.0
            return (user_name or "User", share)
    
    total_commits = sum(author.get("commits", 0) for author in authors)
    if total_commits <= 0:
        share = 1.0 / max(1, len(authors))
        name = authors[0].get("name") or "Primary contributor"
        return (name, share)
    
    top = max(authors, key=lambda a: a.get("commits", 0))
    top_name = top.get("name") or "Top contributor"
    top_share = top.get("commits", 0) / total_commits
    return (top_name, top_share)


def rank_projects(
    projects: Iterable[ProjectInfo],
    n: int = 5,
    criteria: RankingCriteria = "score",
    user_identifier: Optional[str] = None,
) -> List[ProjectInfo]:
    items = [_ensure_rank(p) for p in projects if isinstance(p, ProjectInfo)]
    if not items:
        return []

    reverse = True if criteria != "recency" else False
    key_fn = _criteria_key(criteria, user_identifier)
    
    ranked = sorted(items, key=key_fn, reverse=reverse)
    n = max(3, min(5, int(n)))
    return ranked[:n]


def generate_summary(
    pi: ProjectInfo,
    max_length: int = 220,
    user_identifier: Optional[str] = None,
) -> str:
    """Generate a concise project summary."""
    if not pi.rank_inputs:
        pi = _ensure_rank(pi)
    
    contributor_name, share = _contribution_summary(pi, user_identifier)
    
    if user_identifier and "Your contribution" not in str(contributor_name):
        user_score = pi.rank_inputs.get("user_contrib_score", 0.0)
        if user_score > 0:
            user_share = pi.rank_inputs.get("user_commit_share", 0.0)
            contributor_part = f"Your contribution: {contributor_name} ({user_share:.0%}), impact {user_score:.1f}"
        else:
            contributor_part = f"Top contributor: {contributor_name} ({share:.0%})"
    elif user_identifier:
        contributor_part = f"Your contribution: {contributor_name} ({share:.0%}), impact {pi.rank_inputs.get('user_contrib_score', 0.0):.1f}"
    else:
        contributor_part = f"Top contributor: {contributor_name} ({share:.0%})"
    
    impact = f"Impact: {pi.totals.get('commits', 0)} commits, {pi.lines_of_code} LOC, {pi.duration.get('days', 0)} days"
    
    langs = ", ".join(pi.languages[:3]) if pi.languages else "Unknown"
    langs_part = f"Langs: {langs}"
    
    recency = pi.rank_inputs.get("recency_days", 0)
    recency_part = f"Recency: {recency}d"
    
    collab_tag = "Collaborative" if pi.is_collaborative else "Solo"
    
    core = f"{pi.name} | {collab_tag} | score {pi.preliminary_score:.4f}. {contributor_part}. {impact}. {langs_part}. {recency_part}."
    
    if len(core) <= max_length:
        return core
    
    parts = core.split(". ")
    result = parts[0]
    for part in parts[1:]:
        if len(result) + len(part) + 2 <= max_length:
            result += ". " + part
        else:
            break
    return result


def generate_summaries(
    projects: Iterable[ProjectInfo],
    n: int = 5,
    criteria: RankingCriteria = "score",
    user_identifier: Optional[str] = None,
    max_length: int = 220,
) -> List[dict]:
    """Generate ranked summaries for multiple projects."""
    ranked = rank_projects(projects, n=n, criteria=criteria, user_identifier=user_identifier)
    summaries = []
    
    for i, pi in enumerate(ranked, 1):
        summary = generate_summary(pi, max_length=max_length, user_identifier=user_identifier)
        summary_dict = {
            "rank": i,
            "id": pi.id,
            "name": pi.name,
            "score": pi.preliminary_score if criteria == "score" else None,
            "criteria": criteria,
            "summary": summary,
            "metrics": {
                "commits": pi.totals.get("commits", 0),
                "loc": pi.lines_of_code,
                "recency_days": pi.rank_inputs.get("recency_days", 0),
                "languages": pi.languages,
                "duration_days": pi.duration.get("days", 0)
            }
        }
        summaries.append(summary_dict)
    
    return summaries


def to_format(
    ranked_projects: List[RankedProject] | List[dict],
    fmt: Literal["text", "markdown", "json"] = "text",
) -> str:
    """Format ranked projects list."""
    if fmt == "text":
        lines = []
        for item in ranked_projects:
            if isinstance(item, dict):
                score_part = f" - score {item['score']}" if item['score'] is not None else ""
                lines.append(f"#{item['rank']}: {item['name']}{score_part}")
                lines.append(f" {item['summary']}")
            else:
                score_part = f" - score {item.score}" if item.score is not None else ""
                lines.append(f"#{item.rank}: {item.project.name}{score_part}")
                lines.append(f" {generate_summary(item.project, user_identifier=None)}")
        return "\n".join(lines)
    
    elif fmt == "markdown":
        lines = []
        for item in ranked_projects:
            if isinstance(item, dict):
                score_part = f" (score: {item['score']})" if item['score'] is not None else ""
                lines.append(f"### #{item['rank']}: {item['name']}{score_part}")
                lines.append(f"{item['summary']}")
            else:
                score_part = f" (score: {item.score})" if item.score is not None else ""
                lines.append(f"### #{item.rank}: {item.project.name}{score_part}")
                lines.append(f"{generate_summary(item.project, user_identifier=None)}")
            lines.append("")
        return "\n".join(lines)
    
    elif fmt == "json":
        import json
        return json.dumps([
            {
                "rank": item['rank'] if isinstance(item, dict) else item.rank,
                "name": item['name'] if isinstance(item, dict) else item.project.name,
                "score": item['score'] if isinstance(item, dict) else item.score,
                "summary": item['summary'] if isinstance(item, dict) else generate_summary(item.project, user_identifier=None)
            }
            for item in ranked_projects
        ], indent=2)
    
    else:
        raise ValueError(f"Unknown format: {fmt}")
