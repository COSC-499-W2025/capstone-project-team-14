"""Tests for user contribution-based ranking functionality."""
import pytest
from src.project.aggregator import ProjectInfo, compute_rank_inputs, compute_preliminary_score, _calculate_user_contribution_score, from_git
from src.project.top_summary import rank_projects, generate_summary


def test_user_contribution_scoring():
    """Test user contribution scoring logic."""
    pi = ProjectInfo("test1", "Test", "git", {"start": "2023-01-01", "end": "2023-12-31", "days": 365}, True,
                   [{"name": "John Doe", "email": "john@example.com", "commits": 80},
                    {"name": "Jane Smith", "email": "jane@example.com", "commits": 20}],
                   ["Python"], [], [], {"code": 80, "test": 15, "doc": 5},
                   1000, {"files": 10, "commits": 100}, [], {}, 0.0)
    
    score, share = _calculate_user_contribution_score(pi, "john@example.com")
    assert score == 1.0 and share == 0.8
    
    score, share = _calculate_user_contribution_score(pi, "unknown@example.com")
    assert score == 0.0 and share == 0.0


def test_rank_inputs_with_user():
    """Test rank inputs with user contribution."""
    pi = ProjectInfo("test2", "Test", "git", {"start": "2023-01-01", "end": "2023-12-31", "days": 365}, True,
                   [{"name": "John Doe", "email": "john@example.com", "commits": 60},
                    {"name": "Jane Smith", "email": "jane@example.com", "commits": 40}],
                   ["Python"], [], [], {"code": 80, "test": 15, "doc": 5},
                   5000, {"files": 50, "commits": 100}, [], {}, 0.0)
    
    rank_inputs = compute_rank_inputs(pi, "john@example.com")
    assert rank_inputs["user_contrib_score"] == 0.8
    assert rank_inputs["user_commit_share"] == 0.6


def test_rank_projects_by_user_contribution():
    """Test ranking projects by user contribution."""
    projects = [
        ProjectInfo("p1", "A", "git", {"start": "2023-01-01", "end": "2023-12-31", "days": 365}, True,
                   [{"name": "John", "email": "john@example.com", "commits": 80}],
                   ["Python"], [], [], {"code": 80, "test": 15, "doc": 5},
                   1000, {"files": 10, "commits": 100}, [], {}, 0.0),
        ProjectInfo("p2", "B", "git", {"start": "2023-01-01", "end": "2023-12-31", "days": 365}, True,
                   [{"name": "John", "email": "john@example.com", "commits": 10}],
                   ["Python"], [], [], {"code": 80, "test": 15, "doc": 5},
                   1000, {"files": 10, "commits": 100}, [], {}, 0.0),
        ProjectInfo("p3", "C", "git", {"start": "2023-01-01", "end": "2023-12-31", "days": 365}, True,
                   [{"name": "Jane", "email": "jane@example.com", "commits": 100}],
                   ["Python"], [], [], {"code": 80, "test": 15, "doc": 5},
                   1000, {"files": 10, "commits": 100}, [], {}, 0.0),
    ]
    
    ranked = rank_projects(projects, criteria="user_contrib", user_identifier="john@example.com")
    assert ranked[0].name == "A"
    assert ranked[1].name == "B" 
    assert ranked[2].name == "C"


def test_summary_with_user_contribution():
    """Test summary generation with user contribution."""
    pi = ProjectInfo("test3", "Test", "git", {"start": "2023-01-01", "end": "2023-12-31", "days": 365}, True,
                   [{"name": "John Doe", "email": "john@example.com", "commits": 75},
                    {"name": "Jane Smith", "email": "jane@example.com", "commits": 25}],
                   ["Python"], [], [], {"code": 80, "test": 15, "doc": 5},
                   1000, {"files": 10, "commits": 100}, [], {}, 0.0)
    
    summary = generate_summary(pi, user_identifier="john@example.com")
    assert "Top contributor: John Doe" in summary
    assert "75%" in summary
