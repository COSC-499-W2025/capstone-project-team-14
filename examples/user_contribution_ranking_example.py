#!/usr/bin/env python3
"""Example demonstrating user contribution-based project ranking."""
from src.project.aggregator import from_git
from src.project.top_summary import rank_projects, generate_summaries, to_format

def example_user_contribution_ranking():
    """Demonstrate ranking projects based on user contributions."""
    print("=== User Contribution-Based Project Ranking Example ===\n")
    
    projects_data = [
        {
            "name": "web-frontend",
            "repo_path": "/projects/web-frontend",
            "git_metrics": {
                "authors": [{"name": "John Doe", "email": "john@example.com", "commits": 80},
                           {"name": "Jane Smith", "email": "jane@example.com", "commits": 20}],
                "is_collaborative": True,
                "duration": {"first_commit_iso": "2023-01-01", "last_commit_iso": "2023-12-31", "days": 365},
                "commits": 100, "files_touched": 25,
                "by_activity": {"code": 70, "test": 20, "doc": 10},
                "languages": [{"ext": ".js"}, {"ext": ".ts"}, {"ext": ".css"}],
                "lines_of_code": 5000, "notes": ["React-based web application"]
            }
        },
        {
            "name": "api-backend",
            "repo_path": "/projects/api-backend", 
            "git_metrics": {
                "authors": [{"name": "John Doe", "email": "john@example.com", "commits": 15},
                           {"name": "Bob Wilson", "email": "bob@example.com", "commits": 85}],
                "is_collaborative": True,
                "duration": {"first_commit_iso": "2023-06-01", "last_commit_iso": "2023-12-31", "days": 214},
                "commits": 100, "files_touched": 30,
                "by_activity": {"code": 80, "test": 15, "doc": 5},
                "languages": [{"ext": ".py"}],
                "lines_of_code": 8000, "notes": ["Python REST API service"]
            }
        },
        {
            "name": "mobile-app",
            "repo_path": "/projects/mobile-app",
            "git_metrics": {
                "authors": [{"name": "John Doe", "email": "john@example.com", "commits": 120}],
                "is_collaborative": False,
                "duration": {"first_commit_iso": "2023-03-01", "last_commit_iso": "2023-11-30", "days": 275},
                "commits": 120, "files_touched": 35,
                "by_activity": {"code": 75, "test": 20, "doc": 5},
                "languages": [{"ext": ".dart"}],
                "lines_of_code": 3000, "notes": ["Flutter mobile application"]
            }
        }
    ]
    
    user_email = "john@example.com"
    projects = []
    
    print(f"Creating project objects for user: {user_email}\n")
    
    for project_data in projects_data:
        pi = from_git(project_data["repo_path"], project_data["git_metrics"], user_identifier=user_email)
        projects.append(pi)
        
        user_score = pi.rank_inputs.get("user_contrib_score", 0.0)
        user_share = pi.rank_inputs.get("user_commit_share", 0.0)
