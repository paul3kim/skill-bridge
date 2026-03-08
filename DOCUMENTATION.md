# Skill-Bridge Career Navigator — Design Documentation

## Problem Definition

Early-career professionals and students frequently encounter a "skills gap" between what they know and what job descriptions require. The challenge is not just knowing what's missing — it's knowing *how critical* each gap is and *what to do next*. Existing tools (job boards, LinkedIn, resume builders) describe the gap but don't close it.

**Skill-Bridge** addresses this by taking a candidate's resume and a target role, then producing three actionable outputs in a single interaction:
1. A prioritized skill gap analysis
2. A curated learning roadmap with specific resources
3. Targeted mock interview questions for the gaps identified

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (UI)                        │
│              static/index.html (Vanilla JS)             │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (fetch API)
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI Application                    │
│                    app/main.py                          │
│                                                         │
│   GET  /           → serve index.html                  │
│   GET  /roles      → list target roles                 │
│   GET  /jobs       → browse/filter job listings        │
│   POST /analyze    → resume gap analysis               │
│   GET  /health     → health check                      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│               Analysis Engine (analyzer.py)            │
│                                                         │
│   ┌──────────────────┐     ┌────────────────────────┐  │
│   │   AI Path        │     │   Fallback Path        │  │
│   │  GPT-4o-mini     │ ──► │  Regex keyword match   │  │
│   │  JSON mode       │     │  Static resource map   │  │
│   └──────────────────┘     └────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│               Synthetic Dataset                         │
│            app/data/jobs.json                           │
│   6 roles × (required_skills, salary, certs)           │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Backend framework** | FastAPI (Python) | Automatic OpenAPI docs, Pydantic validation built-in, async-ready, minimal boilerplate |
| **AI model** | OpenAI GPT-4o-mini | Low cost (~$0.002/call), reliable JSON mode output via `response_format`, strong instruction-following for structured career advice |
| **Fallback engine** | Regex keyword matching | Zero dependencies, always available, deterministic — critical for reliability |
| **Frontend** | Vanilla HTML/CSS/JS | No build step, no bundler, loads instantly. Appropriate for a time-boxed prototype |
| **Data storage** | Static JSON file | Synthetic data requirement per spec. No database setup, no scraping, fully portable |
| **Validation** | Pydantic v2 | Type-safe request/response models, validator decorators handle edge cases cleanly |
| **Testing** | pytest + unittest.mock | Standard Python testing; `mock.patch` lets us test the AI path without real API calls |
| **Config** | python-dotenv | Industry-standard `.env` pattern; `override=True` handles pre-set shell env vars |

---

## Key Design Decisions

### 1. Single-prompt AI architecture
Rather than chaining multiple AI calls (one to extract skills, one for roadmap, one for questions), the entire analysis is done in a single structured prompt with JSON mode. This keeps latency low, reduces cost, and simplifies error handling — if the call fails, one fallback handles everything.

### 2. Fallback as a first-class feature
The fallback is not just an error handler — it's a fully functional analysis path. It uses the same `AnalysisResult` response model, populates a curated static resource map for 35+ skills, and assigns priority tiers to missing skills. The UI labels which path was used, giving the user full transparency.

### 3. Demo Mode
A `DEMO_MODE=true` flag in `.env` triggers a simulated AI response that uses real keyword matching but formats output to match the AI path. This was implemented after the OpenAI account hit a quota limit during development — rather than showing a degraded experience, demo mode lets the full intended UX be demonstrated. The case study instructions explicitly permit this pattern.

### 4. No frontend build step
Using vanilla JS with `fetch()` keeps the prototype fully self-contained within a single FastAPI process. This significantly reduces setup friction for reviewers and eliminates build toolchain issues.

### 5. Pydantic validation at the boundary
Input validation lives in the `AnalyzeRequest` model rather than in route handlers. This keeps the API layer thin and makes validation logic testable in isolation.

---

## Data Model

### Request
```python
AnalyzeRequest:
  resume_text: str   # min 20 chars after stripping
  target_role_id: str  # must match a role ID in jobs.json
```

### Response
```python
AnalysisResult:
  target_role: str
  found_skills: List[str]           # required skills detected in resume
  missing_skills: List[SkillGap]    # {skill, priority: high|medium|low}
  roadmap: List[LearningResource]   # {skill, resource, url, time_estimate}
  interview_questions: List[str]    # 5 questions based on gaps
  method: str                       # "ai" | "fallback"
  fallback_reason: Optional[str]    # set when AI path was not used
```

---

## AI Prompt Design

The prompt is designed to be:
- **Role-specific**: injects the exact required skill list for the chosen role
- **Structured**: requests a strict JSON schema so output is always parseable
- **Level-appropriate**: explicitly asks for new-grad-level interview questions
- **Constrained**: uses `temperature=0.3` for consistent, factual output

The `response_format: json_object` parameter enforces valid JSON output from the model, eliminating the need for regex parsing or markdown stripping.

---

## Fallback Mechanism

Triggers when:
- `OPENAI_API_KEY` is not set or empty
- Any exception from the OpenAI client (auth error, rate limit, network failure, malformed response)
- `DEMO_MODE=true` is set (uses a variant of the fallback with improved formatting)

The fallback:
1. Runs regex keyword matching (case-insensitive) against required skills
2. Assigns priority tiers: top ⅓ of missing skills = high, middle ⅓ = medium, bottom ⅓ = low
3. Maps each missing skill to a pre-curated learning resource (35+ skills covered)
4. Generates templated interview questions based on the gaps

---

## Synthetic Dataset

`app/data/jobs.json` contains 6 roles:

| Role | Required Skills |
|---|---|
| Cloud Engineer | AWS, Azure, Terraform, Docker, Kubernetes, Python, CI/CD, Linux, Networking, IAM |
| Cybersecurity Analyst | SIEM, Threat Analysis, Incident Response, Network Security, Python, Linux, Firewall, IDS/IPS, OWASP, Penetration Testing |
| Backend Software Engineer | Python, REST APIs, SQL, Git, Docker, Microservices, Redis, PostgreSQL, Testing, System Design |
| Data Engineer | Python, SQL, Apache Spark, Airflow, dbt, AWS, Data Modeling, ETL, PostgreSQL, Kafka |
| DevOps Engineer | Docker, Kubernetes, CI/CD, Terraform, Linux, Python, AWS, Monitoring, Git, Bash |
| Machine Learning Engineer | Python, PyTorch, TensorFlow, Machine Learning, SQL, Docker, MLOps, AWS, Statistics, Feature Engineering |

Each role also includes salary range and recommended certifications for supplementary context.

---

## Security Considerations

- API keys are stored in `.env`, excluded from version control via `.gitignore`
- `.env.example` is committed as a template with no real values
- All input is validated and length-bounded before being passed to the AI
- No user data is persisted (stateless, in-memory only)
- Synthetic data only — no PII, no live web scraping

---

## Future Enhancements

| Priority | Feature | Rationale |
|---|---|---|
| High | Persistent profiles with a database | Track skill progress over time |
| High | Embedding-based similarity for fallback | Fixes cases where skills are paraphrased in the resume |
| Medium | Live job data via a jobs API | Replace static dataset with real postings |
| Medium | Multi-role comparison view | Show skill overlap across several target roles at once |
| Low | Progress tracking (mark resources complete) | Turns the roadmap into an actionable checklist |
| Low | Export to PDF | Make the roadmap shareable |
