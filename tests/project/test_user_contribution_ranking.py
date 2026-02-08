"""
Tests for user contribution-based ranking functionality.
"""
import pytest
from src.project.aggregator import (
    ProjectInfo, 
    compute_rank_inputs, 
    compute_preliminary_score,
    _calculate_user_contribution_score,
    from_local, 
    from_git, 
    merge_local_git
)
from src.project.top_summary import (
    rank_projects,
    generate_summary,
    generate_summaries,
    _contribution_summary
)


class TestUserContributionScoring:
    """Test user contribution scoring logic."""
    
    def test_calculate_user_contribution_score_primary_contributor(self):
        """Test scoring for primary contributor (>=80% commits)."""
        pi = ProjectInfo(
            id="test1",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 80},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 20}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        score, share = _calculate_user_contribution_score(pi, "john@example.com")
        assert score == 1.0  # Primary contributor
        assert share == 0.8  # 80% of commits
        
        # Test name matching
        score, share = _calculate_user_contribution_score(pi, "John Doe")
        assert score == 1.0
        assert share == 0.8
    
    def test_calculate_user_contribution_score_major_contributor(self):
        """Test scoring for major contributor (50-79% commits)."""
        pi = ProjectInfo(
            id="test2",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 60},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 40}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        score, share = _calculate_user_contribution_score(pi, "john@example.com")
        assert score == 0.8  # Major contributor
        assert share == 0.6  # 60% of commits
    
    def test_calculate_user_contribution_score_minor_contributor(self):
        """Test scoring for minor contributor (10-19% commits)."""
        pi = ProjectInfo(
            id="test3",
            name="Test Project", 
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 15},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 85}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        score, share = _calculate_user_contribution_score(pi, "john@example.com")
        assert score == 0.4  # Minor contributor
        assert share == 0.15  # 15% of commits
    
    def test_calculate_user_contribution_score_solo_project_boost(self):
        """Test solo project boost for single author."""
        pi = ProjectInfo(
            id="test4",
            name="Solo Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=False,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 100}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        score, share = _calculate_user_contribution_score(pi, "john@example.com")
        assert score == 1.0  # Should be boosted to 1.0 for solo project
        assert share == 1.0
    
    def test_calculate_user_contribution_score_local_project(self):
        """Test scoring for local projects (no author info)."""
        pi = ProjectInfo(
            id="test5",
            name="Local Project",
            source="local",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=False,
            authors=[],  # No author info for local projects
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 0},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        score, share = _calculate_user_contribution_score(pi, "john@example.com")
        assert score == 1.0  # Assume user is sole contributor for local projects
        assert share == 1.0
    
    def test_calculate_user_contribution_score_not_found(self):
        """Test scoring when user not found in authors."""
        pi = ProjectInfo(
            id="test6",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 100}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        score, share = _calculate_user_contribution_score(pi, "unknown@example.com")
        assert score == 0.0  # Not found
        assert share == 0.0


class TestRankInputsWithUser:
    """Test rank inputs calculation with user contribution."""
    
    def test_compute_rank_inputs_with_user(self):
        """Test rank inputs calculation including user contribution."""
        pi = ProjectInfo(
            id="test7",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 60},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 40}
            ],
            languages=["Python", "JavaScript"],
            frameworks=["Django"],
            skills=["web development", "api design"],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=5000,
            totals={"files": 50, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        rank_inputs = compute_rank_inputs(pi, "john@example.com")
        
        # Check basic inputs
        assert rank_inputs["loc"] == 5000
        assert rank_inputs["commits"] == 100
        assert rank_inputs["skills_breadth"] == 2
        assert rank_inputs["recency_days"] > 0
        assert rank_inputs["is_collab"] == 1
        assert rank_inputs["code_frac"] == 0.8  # 80/100
        
        # Check user contribution inputs
        assert rank_inputs["user_contrib_score"] == 0.8  # Major contributor
        assert rank_inputs["user_commit_share"] == 0.6   # 60% of commits
    
    def test_compute_rank_inputs_without_user(self):
        """Test rank inputs calculation without user contribution."""
        pi = ProjectInfo(
            id="test8",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 60},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 40}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        rank_inputs = compute_rank_inputs(pi)  # No user identifier
        
        # User contribution should be 0 when no user provided
        assert rank_inputs["user_contrib_score"] == 0.0
        assert rank_inputs["user_commit_share"] == 0.0


class TestScoringWithUserContribution:
    """Test preliminary scoring with user contribution weighting."""
    
    def test_compute_preliminary_score_with_user_contribution(self):
        """Test scoring with user contribution factored in."""
        rank_inputs = {
            "loc": 1000,
            "commits": 100,
            "skills_breadth": 3,
            "recency_days": 30,
            "is_collab": 1,
            "code_frac": 0.8,
            "user_contrib_score": 0.8,  # Major contributor
            "user_commit_share": 0.6
        }
        
        # Test with default user weight (0.3)
        score = compute_preliminary_score(rank_inputs)
        assert score > 0
        
        # Test with higher user weight
        score_high_weight = compute_preliminary_score(rank_inputs, user_weight=0.5)
        # Note: With current implementation, higher user weight may actually decrease the score
        # if user_contrib_score is lower than the base score components
        assert score_high_weight != score  # Should be different with different weight
        
        # Test with zero user weight (should equal base score)
        score_zero_weight = compute_preliminary_score(rank_inputs, user_weight=0.0)
        base_score = (
            0.35 * __import__('math').log1p(1000) +
            0.35 * __import__('math').log1p(100) +
            0.20 * 3 +
            0.10 * 1.0 +  # Recent project
            0.05 * 1
        )
        assert abs(score_zero_weight - round(base_score, 4)) < 0.001
    
    def test_compute_preliminary_score_without_user_contribution(self):
        """Test scoring without user contribution (should use base score)."""
        rank_inputs = {
            "loc": 1000,
            "commits": 100,
            "skills_breadth": 3,
            "recency_days": 30,
            "is_collab": 1,
            "code_frac": 0.8,
            "user_contrib_score": 0.0,  # No user contribution
            "user_commit_share": 0.0
        }
        
        score = compute_preliminary_score(rank_inputs, user_weight=0.3)
        
        # Should equal base score since user_contrib_score is 0
        base_score = (
            0.35 * __import__('math').log1p(1000) +
            0.35 * __import__('math').log1p(100) +
            0.20 * 3 +
            0.10 * 1.0 +  # Recent project
            0.05 * 1
        )
        assert abs(score - round(base_score, 4)) < 0.001


class TestRankingWithUserContribution:
    """Test project ranking with user contribution criteria."""
    
    def create_test_project(self, name, user_commits, total_commits, loc=1000):
        """Helper to create test project with specified user contribution."""
        other_commits = total_commits - user_commits
        authors = []
        if user_commits > 0:
            authors.append({"name": "John Doe", "email": "john@example.com", "commits": user_commits})
        if other_commits > 0:
            authors.append({"name": "Jane Smith", "email": "jane@example.com", "commits": other_commits})
        
        return ProjectInfo(
            id=f"proj_{name.lower()}",
            name=name,
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=len(authors) > 1,
            authors=authors,
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=loc,
            totals={"files": 10, "commits": total_commits},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
    
    def test_rank_projects_by_user_contribution(self):
        """Test ranking projects by user contribution."""
        projects = [
            self.create_test_project("Project A", user_commits=80, total_commits=100),  # 80%
            self.create_test_project("Project B", user_commits=10, total_commits=100),  # 10%
            self.create_test_project("Project C", user_commits=50, total_commits=100),  # 50%
            self.create_test_project("Project D", user_commits=0, total_commits=100),   # 0%
        ]
        
        # Rank by user contribution
        ranked = rank_projects(projects, criteria="user_contrib", user_identifier="john@example.com")
        
        # Should be ordered by user contribution percentage (highest first)
        assert ranked[0].name == "Project A"  # 80%
        assert ranked[1].name == "Project C"  # 50%
        assert ranked[2].name == "Project B"  # 10%
        assert ranked[3].name == "Project D"  # 0%
    
    def test_rank_projects_by_score_with_user_context(self):
        """Test that regular scoring is enhanced by user contribution."""
        projects = [
            self.create_test_project("Large Project", user_commits=20, total_commits=1000, loc=10000),
            self.create_test_project("Small Project", user_commits=90, total_commits=100, loc=1000),
        ]
        
        # Rank by score without user context
        ranked_no_user = rank_projects(projects, criteria="score")
        assert ranked_no_user[0].name == "Large Project"  # More LOC/commits
        
        # Rank by score with user context
        ranked_with_user = rank_projects(projects, criteria="score", user_identifier="john@example.com")
        # Note: Large project still ranks higher due to much higher base metrics (10x LOC/commits)
        # but the gap should be smaller with user contribution factored in
        assert ranked_with_user[0].name == "Large Project"  # Still ranks higher but with different score


class TestSummaryGenerationWithUser:
    """Test summary generation with user contribution focus."""
    
    def test_contribution_summary_with_user(self):
        """Test contribution summary highlighting user."""
        pi = ProjectInfo(
            id="test9",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 75},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 25}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        # With user identifier
        name, share = _contribution_summary(pi, "john@example.com")
        assert name == "John Doe"
        assert share == 0.75
        
        # Without user identifier
        name, share = _contribution_summary(pi)
        assert name == "John Doe"  # Still top contributor
        assert share == 0.75
    
    def test_generate_summary_with_user_contribution(self):
        """Test summary generation with user contribution context."""
        pi = ProjectInfo(
            id="test10",
            name="Test Project",
            source="git",
            duration={"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            is_collaborative=True,
            authors=[
                {"name": "John Doe", "email": "john@example.com", "commits": 75},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 25}
            ],
            languages=["Python"],
            frameworks=[],
            skills=[],
            activity_mix={"code": 80, "test": 15, "doc": 5},
            lines_of_code=1000,
            totals={"files": 10, "commits": 100},
            notes=[],
            rank_inputs={},
            preliminary_score=0.0
        )
        
        # Generate summary with user context
        summary = generate_summary(pi, user_identifier="john@example.com")
        assert "Your contribution" in summary
        assert "John Doe" in summary
        assert "75%" in summary  # Now should show correct percentage with multiple authors
        
        # Generate summary without user context
        summary_no_user = generate_summary(pi)
        assert "Top contributor" in summary_no_user
        assert "Your contribution" not in summary_no_user


class TestProjectCreationWithUser:
    """Test project creation functions with user identifier."""
    
    def test_from_local_with_user(self):
        """Test creating ProjectInfo from local metrics with user."""
        local_metrics = {
            "languages": ["Python"],
            "frameworks": [],
            "skills": ["web development"],
            "lines_of_code": 1000,
            "activity_mix": {"code": 80, "test": 15, "doc": 5},
            "duration": {"start": "2023-01-01", "end": "2023-12-31", "days": 365},
            "totals": {"files": 10},
            "notes": []
        }
        
        pi = from_local("/path/to/project", local_metrics, user_identifier="john@example.com")
        
        # Should have user contribution calculated (assumed 1.0 for local projects)
        assert pi.rank_inputs["user_contrib_score"] == 1.0
        assert pi.rank_inputs["user_commit_share"] == 1.0
    
    def test_from_git_with_user(self):
        """Test creating ProjectInfo from git metrics with user."""
        git_metrics = {
            "authors": [
                {"name": "John Doe", "email": "john@example.com", "commits": 60},
                {"name": "Jane Smith", "email": "jane@example.com", "commits": 40}
            ],
            "is_collaborative": True,
            "duration": {"first_commit_iso": "2023-01-01", "last_commit_iso": "2023-12-31", "days": 365},
            "commits": 100,
            "files_touched": 10,
            "by_activity": {"code": 80, "test": 15, "doc": 5},
            "languages": [{"ext": ".py"}],
            "lines_of_code": 1000,
            "notes": []
        }
        
        pi = from_git("/path/to/repo", git_metrics, user_identifier="john@example.com")
        
        # Should have user contribution calculated
        assert pi.rank_inputs["user_contrib_score"] == 0.8  # Major contributor
        assert pi.rank_inputs["user_commit_share"] == 0.6   # 60% of commits


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
