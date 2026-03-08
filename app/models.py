from pydantic import BaseModel, field_validator
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    resume_text: str
    target_role_id: str

    @field_validator("resume_text")
    @classmethod
    def resume_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Resume text cannot be empty")
        if len(v.strip()) < 20:
            raise ValueError("Resume text is too short — please provide more detail")
        return v.strip()

    @field_validator("target_role_id")
    @classmethod
    def role_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Target role must be selected")
        return v.strip()


class RoleSummary(BaseModel):
    id: str
    title: str
    description: str
    avg_salary: str
    common_certs: List[str]


class SkillGap(BaseModel):
    skill: str
    priority: str  # "high", "medium", "low"


class LearningResource(BaseModel):
    skill: str
    resource: str
    url: Optional[str] = None
    time_estimate: str


class AnalysisResult(BaseModel):
    target_role: str
    found_skills: List[str]
    missing_skills: List[SkillGap]
    roadmap: List[LearningResource]
    interview_questions: List[str]
    method: str  # "ai" or "fallback"
    fallback_reason: Optional[str] = None
