from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional

from app.analyzer import analyze_resume, get_role_by_id, load_all_roles
from app.models import AnalyzeRequest, AnalysisResult

app = FastAPI(
    title="Skill-Bridge Career Navigator",
    description="AI-powered skill gap analysis and learning roadmap generator",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/roles", summary="List all available target roles")
async def get_roles() -> list[dict]:
    return load_all_roles()


@app.get("/jobs", summary="Browse and filter job listings")
async def get_jobs(role: Optional[str] = None, skill: Optional[str] = None) -> list[dict]:
    """
    Returns synthetic job listings.
    - ?role=cloud-engineer  — filter by role ID
    - ?skill=Python         — filter roles that require this skill
    """
    roles = load_all_roles()

    if role:
        role_detail = get_role_by_id(role)
        if not role_detail:
            raise HTTPException(status_code=404, detail=f"Role '{role}' not found")
        return [role_detail]

    if skill:
        from app.analyzer import _load_jobs
        data = _load_jobs()
        matched = [
            r for r in data["roles"]
            if any(skill.lower() in s.lower() for s in r["required_skills"])
        ]
        if not matched:
            raise HTTPException(status_code=404, detail=f"No roles found requiring skill '{skill}'")
        return matched

    return roles


@app.post("/analyze", response_model=AnalysisResult, summary="Analyze a resume against a target role")
async def analyze(request: AnalyzeRequest) -> AnalysisResult:
    """
    Submit resume text and a target role ID.
    Returns skill gap analysis, learning roadmap, and mock interview questions.
    Uses OpenAI GPT-4o-mini; falls back to rule-based analysis if AI is unavailable.
    """
    try:
        result = analyze_resume(request.resume_text, request.target_role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    return result


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok"}
