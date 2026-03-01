from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.deps import get_store
from src.insights.storage import ProjectInsightsStore
from src.pipeline.presentation_pipeline import PresentationPipeline

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillsAddPayload(BaseModel):
    project_id: int
    skills: List[str]


class SkillsRemovePayload(BaseModel):
    project_id: int
    skills: List[str]


class SkillsEditPayload(BaseModel):
    project_id: int
    old: Optional[str] = None
    new: Optional[str] = None
    skills: Optional[List[str]] = None


def _normalize_skills(values: List[Any]) -> List[str]:
    normalized: List[str] = []
    seen: Set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip().casefold()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _load_project_skills_or_404(project_id: int, store: ProjectInsightsStore) -> List[str]:
    load = store.load_project_insight_by_id(project_id)
    if load is None:
        raise HTTPException(status_code=404, detail="Project not found")
    skills = load.get("project_metrics", {}).get("skills", [])
    if not isinstance(skills, list):
        skills = []
    return _normalize_skills(skills)


def _skills_response(project_id: int, skills: List[str]) -> Dict[str, Any]:
    return {"project_id": project_id, "skills": skills}


@router.get("")
def list_skills(
    skills: Optional[str] = Query(None, description="Comma-separated list of skills to filter projects by"),
    store: ProjectInsightsStore = Depends(get_store)
) -> Dict[str, Any]:
    """Get all skills or filter projects by specific skills"""
    pipeline = PresentationPipeline(insights_store=store)
    
    if skills:
        # Parse skills parameter
        skill_list = [skill.strip() for skill in skills.split(",") if skill.strip()]
        
        # If no valid skills after parsing, return all skills
        if not skill_list:
            projects = pipeline.list_available_projects()
            skills_set: Set[str] = set()
            for item in projects:
                pid = item.get("project_id")
                if not isinstance(pid, int):
                    continue
                payload = store.load_project_insight_by_id(pid)
                if not payload:
                    continue
                metrics = payload.get("project_metrics") or {}
                for skill in _normalize_skills(metrics.get("skills", []) or []):
                    skills_set.add(skill)
            return {"skills": sorted(skills_set)}
        
       
        projects = pipeline.list_available_projects()

        filtered_projects = []
        for project in projects:
            project_id = project.get("project_id")
            if not isinstance(project_id, int):
                continue
                
            payload = store.load_project_insight_by_id(project_id)
            if not payload:
                continue
                
            metrics = payload.get("project_metrics") or {}
            project_skills = _normalize_skills(metrics.get("skills", []) or [])
            
            
            project_skills_lower = [skill.lower() for skill in project_skills]
            requested_skills_lower = [skill.lower() for skill in skill_list]
            
            if any(skill in project_skills_lower for skill in requested_skills_lower):
                filtered_projects.append({
                    "project_id": project_id,
                    "project_name": project.get("project_name", "Unknown"),
                    "skills": project_skills,
                    "matching_skills": [skill for skill in project_skills 
                                      if skill.lower() in requested_skills_lower]
                })
        
        return {
            "filter": {
                "requested_skills": skill_list,
                "matching_projects_count": len(filtered_projects)
            },
            "projects": filtered_projects
        }
    else:
        
        projects = pipeline.list_available_projects()
        skills_set: Set[str] = set()
        for item in projects:
            pid = item.get("project_id")
            if not isinstance(pid, int):
                continue
            payload = store.load_project_insight_by_id(pid)
            if not payload:
                continue
            metrics = payload.get("project_metrics") or {}
            for skill in _normalize_skills(metrics.get("skills", []) or []):
                skills_set.add(skill)
        return {"skills": sorted(skills_set)}


@router.get("/year")
def get_skills_by_year(
    year: int = Query(..., ge=1000, le=9999),
    store: ProjectInsightsStore = Depends(get_store),
):
    global_insights = store.load_latest_global_insights() or {}
    chronology = global_insights.get("chronological_skills") or {}
    timeline = chronology.get("timeline") if isinstance(chronology, dict) else []
    if not isinstance(timeline, list):
        timeline = []

    year_str = str(year)
    filtered = [
        entry
        for entry in timeline
        if isinstance(entry, dict)
        and isinstance(entry.get("timestamp"), str)
        and entry["timestamp"][:4] == year_str
    ]
    return {"year": year, "timeline": filtered}


@router.get("/{project_id}")
def get_project_skills(project_id: int, store: ProjectInsightsStore = Depends(get_store)):
    current_skills = _load_project_skills_or_404(project_id, store)
    return _skills_response(project_id, current_skills)


@router.post("/add")
def add_skills(payload: SkillsAddPayload, store: ProjectInsightsStore = Depends(get_store)):
    current_skills = _load_project_skills_or_404(payload.project_id, store)
    updated_skills = _normalize_skills(current_skills + payload.skills)
    store.update_project_skills(payload.project_id, updated_skills)
    return _skills_response(payload.project_id, updated_skills)


@router.post("/remove")
def remove_skills(payload: SkillsRemovePayload, store: ProjectInsightsStore = Depends(get_store)):
    current_skills = _load_project_skills_or_404(payload.project_id, store)
    to_remove = set(_normalize_skills(payload.skills))
    updated_skills = [skill for skill in current_skills if skill not in to_remove]
    store.update_project_skills(payload.project_id, updated_skills)
    return _skills_response(payload.project_id, updated_skills)


@router.post("/edit")
def edit_skills(payload: SkillsEditPayload, store: ProjectInsightsStore = Depends(get_store)):
    current_skills = _load_project_skills_or_404(payload.project_id, store)

    if payload.skills is not None:
        updated_skills = _normalize_skills(payload.skills)
        store.update_project_skills(payload.project_id, updated_skills)
        return _skills_response(payload.project_id, updated_skills)

    if payload.old is None or payload.new is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'skills' for replacement or both 'old' and 'new'.",
        )

    old_norm = _normalize_skills([payload.old])
    new_norm = _normalize_skills([payload.new])
    if not old_norm or not new_norm:
        raise HTTPException(status_code=400, detail="'old' and 'new' must be non-empty strings")

    old_skill = old_norm[0]
    new_skill = new_norm[0]
    if old_skill not in current_skills:
        return _skills_response(payload.project_id, current_skills)

    replaced = [new_skill if skill == old_skill else skill for skill in current_skills]
    updated_skills = _normalize_skills(replaced)
    store.update_project_skills(payload.project_id, updated_skills)
    return _skills_response(payload.project_id, updated_skills)
