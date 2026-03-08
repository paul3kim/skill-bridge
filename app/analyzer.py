"""
Core analysis logic.
AI path: OpenAI GPT-4o-mini with JSON mode.
Fallback path: keyword matching when AI is unavailable or returns invalid data.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from app.models import AnalysisResult, LearningResource, SkillGap

JOBS_PATH = Path(__file__).parent / "data" / "jobs.json"

# Fallback learning resources keyed by skill (lowercase)
FALLBACK_RESOURCES: dict = {
    "aws": {"resource": "AWS Cloud Practitioner Essentials (AWS Training)", "url": "https://aws.amazon.com/training/", "time_estimate": "~20 hours"},
    "azure": {"resource": "Microsoft Azure Fundamentals AZ-900 (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/", "time_estimate": "~15 hours"},
    "terraform": {"resource": "HashiCorp Learn — Terraform Get Started", "url": "https://developer.hashicorp.com/terraform/tutorials", "time_estimate": "~10 hours"},
    "docker": {"resource": "Docker 101 Tutorial (Play with Docker)", "url": "https://www.docker.com/101-tutorial/", "time_estimate": "~5 hours"},
    "kubernetes": {"resource": "Kubernetes Basics (kubernetes.io)", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "time_estimate": "~15 hours"},
    "python": {"resource": "Python for Everybody — Coursera (UMich)", "url": "https://www.coursera.org/specializations/python", "time_estimate": "~30 hours"},
    "ci/cd": {"resource": "GitHub Actions Quickstart", "url": "https://docs.github.com/en/actions/quickstart", "time_estimate": "~5 hours"},
    "linux": {"resource": "The Linux Command Line (free book)", "url": "https://linuxcommand.org/tlcl.php", "time_estimate": "~20 hours"},
    "networking": {"resource": "Computer Networking: a Top-Down Approach (Kurose & Ross)", "url": None, "time_estimate": "~40 hours"},
    "iam": {"resource": "AWS IAM Getting Started", "url": "https://aws.amazon.com/iam/getting-started/", "time_estimate": "~4 hours"},
    "siem": {"resource": "Introduction to SIEM — Cybrary (free)", "url": "https://www.cybrary.it/", "time_estimate": "~8 hours"},
    "threat analysis": {"resource": "MITRE ATT&CK Framework (free)", "url": "https://attack.mitre.org/", "time_estimate": "~10 hours"},
    "incident response": {"resource": "NIST SP 800-61 Computer Security Incident Handling Guide", "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf", "time_estimate": "~8 hours"},
    "network security": {"resource": "CompTIA Network+ Study Guide", "url": "https://www.comptia.org/certifications/network", "time_estimate": "~40 hours"},
    "firewall": {"resource": "Palo Alto Networks Free Training: Firewall Essentials", "url": "https://www.paloaltonetworks.com/services/education", "time_estimate": "~10 hours"},
    "ids/ips": {"resource": "Snort IDS/IPS Tutorial — Snort.org", "url": "https://www.snort.org/documents", "time_estimate": "~8 hours"},
    "owasp": {"resource": "OWASP Top 10 (owasp.org)", "url": "https://owasp.org/www-project-top-ten/", "time_estimate": "~6 hours"},
    "penetration testing": {"resource": "Hack The Box Academy — Penetration Testing Path", "url": "https://academy.hackthebox.com/", "time_estimate": "~80 hours"},
    "rest apis": {"resource": "REST API Tutorial (restfulapi.net)", "url": "https://restfulapi.net/", "time_estimate": "~5 hours"},
    "sql": {"resource": "SQLZoo (free, interactive)", "url": "https://sqlzoo.net/", "time_estimate": "~10 hours"},
    "git": {"resource": "Pro Git Book (free)", "url": "https://git-scm.com/book/en/v2", "time_estimate": "~8 hours"},
    "microservices": {"resource": "Microservices.io Patterns", "url": "https://microservices.io/", "time_estimate": "~10 hours"},
    "redis": {"resource": "Redis University — RU101 (free)", "url": "https://university.redis.com/courses/ru101/", "time_estimate": "~8 hours"},
    "postgresql": {"resource": "PostgreSQL Tutorial (postgresqltutorial.com)", "url": "https://www.postgresqltutorial.com/", "time_estimate": "~10 hours"},
    "testing": {"resource": "pytest Documentation + Real Python Testing Guide", "url": "https://docs.pytest.org/en/stable/", "time_estimate": "~8 hours"},
    "system design": {"resource": "System Design Primer (GitHub)", "url": "https://github.com/donnemartin/system-design-primer", "time_estimate": "~30 hours"},
    "apache spark": {"resource": "Apache Spark Official Docs + Databricks Free Training", "url": "https://spark.apache.org/docs/latest/", "time_estimate": "~20 hours"},
    "airflow": {"resource": "Apache Airflow Tutorial", "url": "https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html", "time_estimate": "~10 hours"},
    "dbt": {"resource": "dbt Learn — Free Courses (getdbt.com)", "url": "https://courses.getdbt.com/", "time_estimate": "~8 hours"},
    "data modeling": {"resource": "Data Modeling for Data Warehouses (Kimball Group)", "url": "https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/", "time_estimate": "~15 hours"},
    "etl": {"resource": "ETL Pipeline Design — Towards Data Science", "url": "https://towardsdatascience.com/", "time_estimate": "~8 hours"},
    "kafka": {"resource": "Apache Kafka Quickstart", "url": "https://kafka.apache.org/quickstart", "time_estimate": "~10 hours"},
    "monitoring": {"resource": "Prometheus + Grafana Getting Started", "url": "https://prometheus.io/docs/prometheus/latest/getting_started/", "time_estimate": "~8 hours"},
    "bash": {"resource": "Bash Scripting Tutorial (linuxconfig.org)", "url": "https://linuxconfig.org/bash-scripting-tutorial-for-beginners", "time_estimate": "~8 hours"},
    "pytorch": {"resource": "PyTorch Tutorials (pytorch.org)", "url": "https://pytorch.org/tutorials/", "time_estimate": "~30 hours"},
    "tensorflow": {"resource": "TensorFlow Get Started (tensorflow.org)", "url": "https://www.tensorflow.org/learn", "time_estimate": "~25 hours"},
    "machine learning": {"resource": "Machine Learning Specialization — Coursera (Andrew Ng)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "time_estimate": "~60 hours"},
    "mlops": {"resource": "MLOps Zoomcamp (free, DataTalks.Club)", "url": "https://github.com/DataTalksClub/mlops-zoomcamp", "time_estimate": "~40 hours"},
    "statistics": {"resource": "Statistics with Python Specialization — Coursera (UMich)", "url": "https://www.coursera.org/specializations/statistics-with-python", "time_estimate": "~30 hours"},
    "feature engineering": {"resource": "Feature Engineering for ML — Udemy / Kaggle Learn", "url": "https://www.kaggle.com/learn/feature-engineering", "time_estimate": "~10 hours"},
}

DEFAULT_RESOURCE = {"resource": "Search Coursera or freeCodeCamp for this skill", "url": "https://www.coursera.org", "time_estimate": "~10 hours"}


def _load_jobs() -> dict[str, Any]:
    with open(JOBS_PATH) as f:
        return json.load(f)


def load_all_roles() -> list[dict]:
    data = _load_jobs()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "avg_salary": r["avg_salary"],
            "common_certs": r["common_certs"],
        }
        for r in data["roles"]
    ]


def get_role_by_id(role_id: str) -> dict | None:
    data = _load_jobs()
    for role in data["roles"]:
        if role["id"] == role_id:
            return role
    return None


def _extract_skills_fallback(resume_text: str, required_skills: list[str]) -> tuple[list[str], list[str]]:
    """Keyword-match resume text against required skills."""
    text_lower = resume_text.lower()
    found, missing = [], []
    for skill in required_skills:
        # Build a regex that matches the skill as a word/phrase
        pattern = re.compile(re.escape(skill.lower()), re.IGNORECASE)
        if pattern.search(text_lower):
            found.append(skill)
        else:
            missing.append(skill)
    return found, missing


def _build_fallback_result(resume_text: str, role: dict, reason: str | None = None) -> AnalysisResult:
    found, missing_raw = _extract_skills_fallback(resume_text, role["required_skills"])

    missing_skills = []
    for i, skill in enumerate(missing_raw):
        priority = "high" if i < len(missing_raw) // 3 + 1 else ("medium" if i < 2 * len(missing_raw) // 3 + 1 else "low")
        missing_skills.append(SkillGap(skill=skill, priority=priority))

    roadmap = []
    for gap in missing_skills:
        key = gap.skill.lower()
        res = FALLBACK_RESOURCES.get(key, DEFAULT_RESOURCE)
        roadmap.append(LearningResource(
            skill=gap.skill,
            resource=res["resource"],
            url=res.get("url"),
            time_estimate=res["time_estimate"],
        ))

    # Generic interview questions for missing skills
    interview_questions = [
        f"Can you describe your experience with {gap.skill}?" for gap in missing_skills[:3]
    ] + [
        f"How would you approach learning {gap.skill} in the context of a {role['title']} role?"
        for gap in missing_skills[3:5]
    ]
    if not interview_questions:
        interview_questions = [f"Tell me about a challenging project you worked on as a {role['title']}."]

    return AnalysisResult(
        target_role=role["title"],
        found_skills=found,
        missing_skills=missing_skills,
        roadmap=roadmap,
        interview_questions=interview_questions,
        method="fallback",
        fallback_reason=reason,
    )


def _build_demo_result(resume_text: str, role: dict) -> AnalysisResult:
    """
    Demo mode: returns a realistic simulated AI response for presentation purposes.
    Triggered by DEMO_MODE=true in .env. Clearly labeled in the response.
    The skill detection still uses real keyword matching so results reflect the actual resume.
    """
    found, missing_raw = _extract_skills_fallback(resume_text, role["required_skills"])

    # Realistic priority assignment (first 2 gaps are high, next 2 medium, rest low)
    missing_skills = []
    for i, skill in enumerate(missing_raw):
        priority = "high" if i < 2 else ("medium" if i < 4 else "low")
        missing_skills.append(SkillGap(skill=skill, priority=priority))

    roadmap = []
    for gap in missing_skills:
        key = gap.skill.lower()
        res = FALLBACK_RESOURCES.get(key, DEFAULT_RESOURCE)
        roadmap.append(LearningResource(
            skill=gap.skill,
            resource=res["resource"],
            url=res.get("url"),
            time_estimate=res["time_estimate"],
        ))

    # Demo mode: generate tailored-sounding interview questions
    interview_questions = []
    for gap in missing_skills[:3]:
        interview_questions.append(
            f"Walk me through how you would use {gap.skill} in a production {role['title']} environment."
        )
    if len(missing_skills) > 3:
        interview_questions.append(
            f"You mentioned you haven't worked with {missing_skills[3].skill} yet. How would you ramp up quickly?"
        )
    if len(missing_skills) > 4:
        interview_questions.append(
            f"Describe a project where understanding {missing_skills[4].skill} would have made a significant difference."
        )
    if not interview_questions:
        interview_questions = [f"Tell me about your most impactful project relevant to the {role['title']} role."]

    return AnalysisResult(
        target_role=role["title"],
        found_skills=found,
        missing_skills=missing_skills,
        roadmap=roadmap,
        interview_questions=interview_questions,
        method="ai",
        fallback_reason="[DEMO MODE] Simulated AI response — results reflect real keyword matching with AI-style formatting.",
    )


def analyze_resume(resume_text: str, target_role_id: str) -> AnalysisResult:
    role = get_role_by_id(target_role_id)
    if role is None:
        raise ValueError(f"Unknown role ID: '{target_role_id}'")

    if os.getenv("DEMO_MODE", "").strip().lower() == "true":
        return _build_demo_result(resume_text, role)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _build_fallback_result(resume_text, role, reason="OPENAI_API_KEY not set — using rule-based fallback")

    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""You are a senior career advisor. Analyze the candidate's resume for the role of "{role['title']}".

Required skills for this role: {", ".join(role["required_skills"])}

Resume:
---
{resume_text}
---

Return ONLY a valid JSON object (no markdown, no extra text) with these exact keys:
{{
  "found_skills": ["skill1", "skill2"],
  "missing_skills": [
    {{"skill": "SkillName", "priority": "high|medium|low"}}
  ],
  "roadmap": [
    {{
      "skill": "SkillName",
      "resource": "Specific course or book name",
      "url": "https://... or null",
      "time_estimate": "~X hours"
    }}
  ],
  "interview_questions": [
    "Question 1?",
    "Question 2?",
    "Question 3?",
    "Question 4?",
    "Question 5?"
  ]
}}

Rules:
- found_skills: only include skills from the required skills list that are clearly present in the resume
- missing_skills: remaining required skills not found; priority = high (critical gap), medium, or low (nice to have exposure)
- roadmap: one entry per missing skill with a real, specific free or paid learning resource
- interview_questions: 5 targeted questions based on the skill gaps, appropriate for a new grad level
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        raw = json.loads(response.choices[0].message.content)

        missing_skills = [SkillGap(**s) for s in raw.get("missing_skills", [])]
        roadmap = [LearningResource(**r) for r in raw.get("roadmap", [])]

        return AnalysisResult(
            target_role=role["title"],
            found_skills=raw.get("found_skills", []),
            missing_skills=missing_skills,
            roadmap=roadmap,
            interview_questions=raw.get("interview_questions", []),
            method="ai",
        )

    except Exception as exc:
        return _build_fallback_result(resume_text, role, reason=f"AI unavailable ({type(exc).__name__}) — using rule-based fallback")
