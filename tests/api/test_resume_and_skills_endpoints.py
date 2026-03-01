import os
import shutil
import sys
import tempfile
from pathlib import Path
import inspect
import httpx

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.api import deps
from src.api.app import app
from src.insights.storage import ProjectInsightsStore
from src.pipeline.presentation_pipeline import PresentationPipeline
from tests.insights.utils import build_pipeline_payload

# Compatibility shim: older httpx versions don't accept the 'app' kwarg used by Starlette's TestClient
if "app" not in inspect.signature(httpx.Client.__init__).parameters:
    _orig_httpx_init = httpx.Client.__init__

    def _patched_httpx_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _orig_httpx_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_init


def _seed_store(db_path: str) -> tuple[ProjectInsightsStore, int]:
    store = ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")
    payload = build_pipeline_payload(project_names=("ProjectAlpha",), include_presentation=True)
    store.record_pipeline_run(os.path.join(os.path.dirname(db_path), "seed.zip"), payload)
    projects = PresentationPipeline(insights_store=store).list_available_projects()
    project_id = next(item["project_id"] for item in projects if item["project_name"] == "ProjectAlpha")
    return store, project_id


def test_skills_and_resume_endpoints():
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "app.db")
        store, project_id = _seed_store(db_path)

        app.dependency_overrides[deps.get_store] = lambda: store
        client = TestClient(app)

        # GET /skills (original behavior - all skills)
        resp = client.get("/skills")
        assert resp.status_code == 200
        skills_response = resp.json()
        assert "skills" in skills_response
        skills = skills_response["skills"]
        assert isinstance(skills, list)
        assert all(isinstance(s, str) for s in skills)

        # GET /skills with filtering (new functionality)
        resp = client.get("/skills?skills=python")
        assert resp.status_code == 200
        filtered = resp.json()
        assert "filter" in filtered
        assert "projects" in filtered
        assert filtered["filter"]["requested_skills"] == ["python"]
        assert isinstance(filtered["filter"]["matching_projects_count"], int)
        assert isinstance(filtered["projects"], list)

        # Test multiple skills filtering
        resp = client.get("/skills?skills=python,java")
        assert resp.status_code == 200
        multi_filtered = resp.json()
        assert multi_filtered["filter"]["requested_skills"] == ["python", "java"]
        assert len(multi_filtered["projects"]) >= 0

        # Verify project structure in filtered response
        if multi_filtered["projects"]:
            project = multi_filtered["projects"][0]
            assert "project_id" in project
            assert "project_name" in project
            assert "skills" in project
            assert "matching_skills" in project
            assert isinstance(project["skills"], list)
            assert isinstance(project["matching_skills"], list)

        # GET /resume/{id}
        resp = client.get(f"/resume/{project_id}")
        assert resp.status_code == 200
        resume = resp.json()["resume_item"]
        assert isinstance(resume, dict)
        assert "bullets" in resume

        # POST /resume/generate (regenerate, returns resume)
        resp = client.post("/resume/generate", params={"project_id": project_id})
        assert resp.status_code == 200
        gen_resume = resp.json()["resume_item"]
        assert isinstance(gen_resume, dict)
        assert "bullets" in gen_resume

        # POST /resume/{id}/edit (persist bullets)
        new_bullets = ["Defined API contracts", "Increased coverage"]
        resp = client.post(f"/resume/{project_id}/edit", json={"bullets": new_bullets})
        assert resp.status_code == 200
        edited = resp.json()["resume_item"]
        assert edited["bullets"] == new_bullets

        # POST /portfolio/generate (regenerate portfolio)
        resp = client.post("/portfolio/generate", params={"project_id": project_id})
        assert resp.status_code == 200
        portfolio = resp.json()["portfolio_item"]
        assert isinstance(portfolio, dict)
        assert "description" in portfolio

        # POST /portfolio/{id}/edit (persist fields)
        resp = client.post(
            f"/portfolio/{project_id}/edit",
            json={
                "tagline": "High-impact data project",
                "is_collaborative": True,
                "key_features": ["P1", "P2"],
            },
        )
        assert resp.status_code == 200
        updated_portfolio = resp.json()["portfolio_item"]
        assert updated_portfolio["tagline"] == "High-impact data project"
        assert updated_portfolio["is_collaborative"] is True
        assert updated_portfolio["key_features"] == ["P1", "P2"]
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(td, ignore_errors=True)


def test_skills_filtering_edge_cases():
    """Test edge cases for skills filtering functionality"""
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "app.db")
        store, project_id = _seed_store(db_path)

        app.dependency_overrides[deps.get_store] = lambda: store
        client = TestClient(app)

        # Test empty skills parameter
        resp = client.get("/skills?skills=")
        assert resp.status_code == 200
        # Should return all skills when skills parameter is empty
        assert isinstance(resp.json(), list)

        # Test whitespace-only skills parameter
        resp = client.get("/skills?skills=   ")
        assert resp.status_code == 200
        # Should return all skills when skills parameter is only whitespace
        assert isinstance(resp.json(), list)

        # Test non-existent skill
        resp = client.get("/skills?skills=nonexistent_skill_xyz")
        assert resp.status_code == 200
        filtered = resp.json()
        assert filtered["filter"]["requested_skills"] == ["nonexistent_skill_xyz"]
        assert filtered["filter"]["matching_projects_count"] == 0
        assert filtered["projects"] == []

        # Test case-insensitive matching
        resp = client.get("/skills?skills=PYTHON")
        assert resp.status_code == 200
        case_insensitive = resp.json()
        assert case_insensitive["filter"]["requested_skills"] == ["PYTHON"]

        # Test mixed case and whitespace
        resp = client.get("/skills?skills= python , java ,  sql ")
        assert resp.status_code == 200
        mixed_case = resp.json()
        assert mixed_case["filter"]["requested_skills"] == ["python", "java", "sql"]

    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(td, ignore_errors=True)
