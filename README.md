# Skill-Bridge Career Navigator

**Candidate Name:** Paul Kim
**Scenario Chosen:** Skill-Bridge Career Navigator (Scenario 2)
**Estimated Time Spent:** ~4 hours

---

## Problem

Students and early-career professionals often don't know which specific skills stand between them and their target role. Browsing job boards is time-consuming, and the gap between what they know and what employers want is rarely surfaced clearly.

**Skill-Bridge** solves this by taking a user's resume text and a target role, then producing:
1. A **skill gap analysis** — what they have vs. what the role requires
2. A **learning roadmap** — specific resources to close each gap
3. **Mock interview questions** — targeted practice based on missing skills

---

## Quick Start

### Prerequisites
- Python 3.11+
- An OpenAI API key (or run without one — the app falls back to rule-based analysis)

### Setup & Run

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd skill-bridge

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Start the server
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Test Commands

```bash
pytest tests/ -v
```

---

## Architecture

```
skill-bridge/
├── app/
│   ├── main.py          # FastAPI routes
│   ├── analyzer.py      # AI analysis + rule-based fallback
│   ├── models.py        # Pydantic request/response models
│   └── data/
│       └── jobs.json    # Synthetic job dataset (6 roles)
├── static/
│   └── index.html       # Single-page web UI
├── tests/
│   └── test_analyzer.py # 7 tests (happy paths + edge cases)
├── .env.example
├── .gitignore
└── README.md
```

### Tech Stack
| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI (Python) | Fast, typed, auto-docs via OpenAPI |
| AI | OpenAI GPT-4o-mini | Low cost, strong JSON output, widely available |
| Fallback | Regex keyword matching | Zero dependencies, always available |
| Frontend | Vanilla HTML/JS | No build step, fast to iterate |
| Data | Synthetic JSON | No scraping, deterministic for testing |
| Tests | pytest + unittest.mock | Standard Python testing |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/roles` | List all available target roles |
| `GET` | `/jobs?role=<id>&skill=<name>` | Browse/filter job listings |
| `POST` | `/analyze` | Analyze resume against a role |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Auto-generated API docs (Swagger UI) |

### Example `/analyze` request
```json
POST /analyze
{
  "resume_text": "2 years Python. Built REST APIs. Used Docker and AWS EC2. Git daily.",
  "target_role_id": "backend-engineer"
}
```

---

## AI Integration & Fallback

**AI path (OpenAI GPT-4o-mini):**
Sends resume text + role requirements in a single structured prompt. Uses `response_format: json_object` to ensure parseable output. Returns skill gaps, a learning roadmap with real resource links, and 5 targeted mock interview questions.

**Fallback path (rule-based):**
Triggered automatically when:
- `OPENAI_API_KEY` is not set
- The OpenAI API is unavailable (network error, rate limit, etc.)
- The AI returns malformed JSON

The fallback uses regex keyword matching to identify skills present/absent in the resume, then maps each missing skill to a curated static resource list. The UI clearly labels which mode produced the result.

---

## Synthetic Dataset

`app/data/jobs.json` contains 6 roles with required skills, salary ranges, and cert paths:
- Cloud Engineer
- Cybersecurity Analyst
- Backend Software Engineer
- Data Engineer
- DevOps Engineer
- Machine Learning Engineer

No real personal data is used anywhere.

---

## AI Disclosure

- **Did you use an AI assistant?** Yes — Claude Code (Anthropic) for development assistance.
- **How did I verify suggestions?** Read every generated file, checked logic manually, ran tests, and confirmed the fallback path works without an API key.
- **Example of a suggestion I changed:** The initial fallback assigned all missing skills the same "high" priority. I changed it to distribute priority across thirds (high/medium/low) to give users a more actionable, ranked roadmap.

---

## Tradeoffs & Prioritization

**What I cut to stay in scope:**
- No user auth or saved profiles (would need a database)
- No real job board scraping (used synthetic data instead per requirements)
- No gap-vs-time visualization dashboard

**What I'd build next with more time:**
1. **Persistent profiles** — save multiple resumes, track progress over time
2. **Real job data integration** — connect to a jobs API for live postings (with rate limiting + caching)
3. **Progress tracking** — mark resources as completed, recalculate score
4. **Role comparison** — compare skill overlap across multiple target roles at once

**Known limitations:**
- The fallback keyword matching can miss skills described differently (e.g., "cloud infrastructure" vs "AWS")
- AI analysis quality depends on how much detail the user provides in their resume text
- `jobs.json` is static — role requirements don't update with market changes

---

## Video

> https://youtu.be/7PI4zA9qUq4
