"""
Tests for the Skill-Bridge analyzer.
- Happy path: valid resume + valid role → correct structure returned
- Edge case: empty resume → ValidationError raised
- Edge case: unknown role → ValueError raised
- Fallback: AI disabled → rule-based result still structurally correct
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.models import AnalyzeRequest, AnalysisResult
from app.analyzer import analyze_resume, get_role_by_id, _build_fallback_result, _extract_skills_fallback


SAMPLE_RESUME = """
Software Engineer with 2 years of experience.
- Proficient in Python and REST APIs
- Built and deployed Docker containers on AWS EC2
- Used Git and GitHub Actions for CI/CD pipelines
- Familiar with Linux command line and PostgreSQL databases
- Wrote unit tests with pytest
"""


# ---------------------------------------------------------------------------
# Happy path: fallback analysis returns correct structure
# ---------------------------------------------------------------------------

def test_fallback_analysis_happy_path():
    """A resume with several matching skills should return a valid AnalysisResult."""
    role = get_role_by_id("backend-engineer")
    assert role is not None, "backend-engineer role should exist in jobs.json"

    result = _build_fallback_result(SAMPLE_RESUME, role)

    assert isinstance(result, AnalysisResult)
    assert result.target_role == role["title"]
    assert result.method == "fallback"
    assert isinstance(result.found_skills, list)
    assert isinstance(result.missing_skills, list)
    assert isinstance(result.roadmap, list)
    assert isinstance(result.interview_questions, list)

    # Python, Docker, AWS, Git, REST APIs are all in the resume
    found_lower = [s.lower() for s in result.found_skills]
    assert "python" in found_lower
    assert "docker" in found_lower


# ---------------------------------------------------------------------------
# Happy path: analyze_resume uses fallback when no API key is set
# ---------------------------------------------------------------------------

def test_analyze_resume_no_api_key_uses_fallback():
    """With no OPENAI_API_KEY, analyze_resume should return a fallback result."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        result = analyze_resume(SAMPLE_RESUME, "backend-engineer")

    assert isinstance(result, AnalysisResult)
    assert result.method == "fallback"
    assert "OPENAI_API_KEY not set" in (result.fallback_reason or "")


# ---------------------------------------------------------------------------
# Edge case: invalid / unknown role raises ValueError
# ---------------------------------------------------------------------------

def test_analyze_resume_unknown_role_raises():
    """Requesting a non-existent role ID should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown role ID"):
        analyze_resume(SAMPLE_RESUME, "nonexistent-role-xyz")


# ---------------------------------------------------------------------------
# Edge case: Pydantic validation rejects empty resume
# ---------------------------------------------------------------------------

def test_analyze_request_empty_resume_invalid():
    """AnalyzeRequest should raise ValidationError for an empty resume."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AnalyzeRequest(resume_text="", target_role_id="backend-engineer")


def test_analyze_request_too_short_resume_invalid():
    """AnalyzeRequest should reject a resume that is too short to be meaningful."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AnalyzeRequest(resume_text="hi", target_role_id="backend-engineer")


# ---------------------------------------------------------------------------
# Edge case: resume with NO matching skills
# ---------------------------------------------------------------------------

def test_fallback_no_matching_skills():
    """A resume with zero matching skills should still return a valid result with an empty found_skills list."""
    role = get_role_by_id("cybersecurity-analyst")
    empty_resume = "I enjoy painting and cooking. No technical background."
    result = _build_fallback_result(empty_resume, role)

    assert result.found_skills == []
    assert len(result.missing_skills) == len(role["required_skills"])
    assert len(result.roadmap) == len(role["required_skills"])


# ---------------------------------------------------------------------------
# Unit: skill extraction helper
# ---------------------------------------------------------------------------

def test_extract_skills_fallback_case_insensitive():
    """Skill extraction should be case-insensitive."""
    text = "Experienced with PYTHON, docker and aws."
    required = ["Python", "Docker", "Kubernetes", "AWS"]
    found, missing = _extract_skills_fallback(text, required)

    assert "Python" in found
    assert "Docker" in found
    assert "AWS" in found
    assert "Kubernetes" in missing


# ---------------------------------------------------------------------------
# AI path: mocked OpenAI call returns expected structure
# ---------------------------------------------------------------------------

def test_analyze_resume_ai_path_mocked():
    """When OpenAI returns valid JSON, result should have method='ai'."""
    mock_ai_response = {
        "found_skills": ["Python", "Docker", "AWS"],
        "missing_skills": [
            {"skill": "Kubernetes", "priority": "high"},
            {"skill": "Redis", "priority": "medium"},
        ],
        "roadmap": [
            {"skill": "Kubernetes", "resource": "Kubernetes Basics", "url": "https://kubernetes.io", "time_estimate": "~15 hours"},
            {"skill": "Redis", "resource": "Redis University RU101", "url": "https://university.redis.com", "time_estimate": "~8 hours"},
        ],
        "interview_questions": [
            "Describe how you'd set up a Kubernetes deployment.",
            "What Redis data structures have you used?",
            "How does container orchestration differ from bare Docker?",
            "Explain a microservices pattern you'd apply here.",
            "How would you handle a Redis cache miss?",
        ],
    }

    import json
    mock_message = MagicMock()
    mock_message.content = json.dumps(mock_ai_response)
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake-key-for-testing"}):
        with patch("app.analyzer.OpenAI", return_value=mock_client):
            result = analyze_resume(SAMPLE_RESUME, "backend-engineer")

    assert result.method == "ai"
    assert "Python" in result.found_skills
    assert any(s.skill == "Kubernetes" for s in result.missing_skills)
    assert len(result.interview_questions) == 5
