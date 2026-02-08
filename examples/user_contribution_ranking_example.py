#!/usr/bin/env python3
"""
Example demonstrating user contribution-based project ranking.

This example shows how to use the new user contribution features
to rank projects based on a specific user's contributions.
"""

import json
from src.project.aggregator import from_git, from_local, merge_local_git
from src.project.top_summary import rank_projects, generate_summaries, generate_summary, to_format

def example_user_contribution_ranking():
    """Demonstrate ranking projects based on user contributions."""
    
    print("=== User Contribution-Based Project Ranking Example ===\n")
    
    # Example git metrics for multiple projects
    projects_data = [
        {
            "name": "web-frontend",
            "repo_path": "/projects/web-frontend",
            "git_metrics": {
                "authors": [
                    {"name": "John Doe", "email": "john@example.com", "commits": 80},
                    {"name": "Jane Smith", "email": "jane@example.com", "commits": 20}
                ],
                "is_collaborative": True,
                "duration": {"first_commit_iso": "2023-01-01", "last_commit_iso": "2023-12-31", "days": 365},
                "commits": 100,
                "files_touched": 25,
                "by_activity": {"code": 70, "test": 20, "doc": 10},
                "languages": [{"ext": ".js"}, {"ext": ".ts"}, {"ext": ".css"}],
                "lines_of_code": 5000,
                "notes": ["React-based web application"]
            }
        },
        {
            "name": "api-backend",
            "repo_path": "/projects/api-backend", 
            "git_metrics": {
                "authors": [
                    {"name": "John Doe", "email": "john@example.com", "commits": 15},
                    {"name": "Bob Wilson", "email": "bob@example.com", "commits": 85}
                ],
                "is_collaborative": True,
                "duration": {"first_commit_iso": "2023-06-01", "last_commit_iso": "2023-12-31", "days": 214},
                "commits": 100,
                "files_touched": 30,
                "by_activity": {"code": 80, "test": 15, "doc": 5},
                "languages": [{"ext": ".py"}],
                "lines_of_code": 8000,
                "notes": ["Python REST API service"]
            }
        },
        {
            "name": "mobile-app",
            "repo_path": "/projects/mobile-app",
            "git_metrics": {
                "authors": [
                    {"name": "John Doe", "email": "john@example.com", "commits": 120}
                ],
                "is_collaborative": False,
                "duration": {"first_commit_iso": "2023-03-01", "last_commit_iso": "2023-11-30", "days": 275},
                "commits": 120,
                "files_touched": 35,
                "by_activity": {"code": 75, "test": 20, "doc": 5},
                "languages": [{"ext": ".dart"}],
                "lines_of_code": 3000,
                "notes": ["Flutter mobile application"]
            }
        },
        {
            "name": "data-analysis",
            "repo_path": "/projects/data-analysis",
            "git_metrics": {
                "authors": [
                    {"name": "Alice Brown", "email": "alice@example.com", "commits": 50},
                    {"name": "Charlie Davis", "email": "charlie@example.com", "commits": 50}
                ],
                "is_collaborative": True,
                "duration": {"first_commit_iso": "2023-09-01", "last_commit_iso": "2023-12-15", "days": 105},
                "commits": 100,
                "files_touched": 20,
                "by_activity": {"code": 60, "test": 25, "doc": 15},
                "languages": [{"ext": ".py"}, {"ext": ".r"}],
                "lines_of_code": 2000,
                "notes": ["Data analysis and visualization scripts"]
            }
        }
    ]
    
    # Create ProjectInfo objects for John Doe
    user_email = "john@example.com"
    projects = []
    
    print(f"Creating project objects for user: {user_email}\n")
    
    for project_data in projects_data:
        pi = from_git(
            project_data["repo_path"], 
            project_data["git_metrics"], 
            user_identifier=user_email
        )
        projects.append(pi)
        
        # Show user contribution info
        user_score = pi.rank_inputs.get("user_contrib_score", 0.0)
        user_share = pi.rank_inputs.get("user_commit_share", 0.0)
        print(f"{project_data['name']}:")
        print(f"  - Total commits: {pi.totals.get('commits', 0)}")
        print(f"  - User contribution: {user_share:.1%} (score: {user_score:.1f})")
        print(f"  - Overall score: {pi.preliminary_score:.4f}")
        print()
    
    # Demonstrate different ranking criteria
    print("=== Ranking Comparisons ===\n")
    
    # 1. Standard score ranking (without user context)
    print("1. Standard Score Ranking (no user context):")
    ranked_by_score = rank_projects(projects, criteria="score", n=4)
    summaries = generate_summaries(ranked_by_score, criteria="score")
    print(to_format(summaries, fmt="text"))
    print()
    
    # 2. User contribution ranking
    print("2. User Contribution Ranking (prioritizes John's involvement):")
    ranked_by_user = rank_projects(projects, criteria="user_contrib", n=4, user_identifier=user_email)
    summaries = generate_summaries(ranked_by_user, criteria="user_contrib", user_identifier=user_email)
    print(to_format(summaries, fmt="text"))
    print()
    
    # 3. Enhanced score ranking (with user context)
    print("3. Enhanced Score Ranking (standard score + user contribution):")
    ranked_enhanced = rank_projects(projects, criteria="score", n=4, user_identifier=user_email)
    summaries = generate_summaries(ranked_enhanced, criteria="score", user_identifier=user_email)
    print(to_format(summaries, fmt="text"))
    print()
    
    # Show detailed comparison
    print("=== Detailed Comparison ===")
    print(f"{'Project':<15} {'Score':<8} {'User%':<8} {'UserScore':<10} {'Rank_std':<9} {'Rank_user':<10} {'Rank_enh':<9}")
    print("-" * 70)
    
    # Get rankings for each project
    std_ranking = {p.name: i+1 for i, p in enumerate(ranked_by_score)}
    user_ranking = {p.name: i+1 for i, p in enumerate(ranked_by_user)}
    enhanced_ranking = {p.name: i+1 for i, p in enumerate(ranked_enhanced)}
    
    for project in projects:
        user_share = project.rank_inputs.get("user_commit_share", 0.0)
        user_score = project.rank_inputs.get("user_contrib_score", 0.0)
        std_rank = std_ranking.get(project.name, 0)
        user_rank = user_ranking.get(project.name, 0)
        enhanced_rank = enhanced_ranking.get(project.name, 0)
        
        print(f"{project.name:<15} {project.preliminary_score:<8.4f} {user_share:<8.1%} {user_score:<10.1f} {std_rank:<9} {user_rank:<10} {enhanced_rank:<9}")

def example_local_project():
    """Example with local projects (no author info)."""
    
    print("\n=== Local Project Example ===\n")
    
    # Local project metrics (no author information)
    local_metrics = {
        "languages": ["Python", "JavaScript"],
        "frameworks": ["Django", "React"],
        "skills": ["web development", "api design", "database design"],
        "lines_of_code": 3500,
        "activity_mix": {"code": 75, "test": 20, "doc": 5},
        "duration": {"start": "2023-01-01", "end": "2023-12-31", "days": 365},
        "totals": {"files": 25},
        "notes": ["Full-stack web application"]
    }
    
    # Create project info with user context
    user_name = "John Doe"
    pi = from_local("/path/to/local-project", local_metrics, user_identifier=user_name)
    
    print(f"Local project for user: {user_name}")
    print(f"User contribution score: {pi.rank_inputs.get('user_contrib_score', 0.0)}")
    print(f"User commit share: {pi.rank_inputs.get('user_commit_share', 0.0)}")
    print(f"Overall score: {pi.preliminary_score:.4f}")
    
    # Generate user-focused summary
    summary = generate_summary(pi, user_identifier=user_name)
    print(f"Summary: {summary}")

if __name__ == "__main__":
    example_user_contribution_ranking()
    example_local_project()
