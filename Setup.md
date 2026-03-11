# Cambridge Open Data — Metadata Health Dashboard

**Spring 2026 | SPARK DD4G | Boston University**

Automated metadata audit system for the [City of Cambridge Open Data Portal](https://data.cambridgema.gov/).

---

## Project Structure

```
cambridge-health-dashboard/
├── app.py                        # Streamlit dashboard (6 tabs)
├── fetch_data.py                 # Socrata API ingestion with retry logic
├── score_and_flag.py             # 7-dimension scoring engine
├── llm_enrich.py                 # Gemini 1.5 Flash AI enrichment
├── pipeline.py                   # Orchestrator: run all 3 steps in order
├── requirements.txt
├── data/
│   └── cambridge_metadata.db     # SQLite database
├── deploy/
│   └── push_db.py                # Push DB to HuggingFace after refresh
└── .github/
    └── workflows/
        └── refresh.yml           # GitHub Actions daily cron
```

---

## Setup

```bash
git clone https://github.com/your-org/cambridge-health-dashboard
cd cambridge-health-dashboard
pip install -r requirements.txt
```

Set environment variables:

```bash
export GEMINI_API_KEY="your_gemini_key_here"
export BASE_DIR="$(pwd)"
```

---

## Running

```bash
# Full pipeline: fetch + score + LLM enrichment
python pipeline.py

# Dashboard only (requires DB to exist)
streamlit run app.py
```

---

## Environment Variables

| Variable         | Purpose                                      |
|------------------|----------------------------------------------|
| GEMINI_API_KEY   | Google Gemini API key (free tier)            |
| HF_TOKEN         | HuggingFace write token (for deployment)     |
| BASE_DIR         | Root directory for data files (optional)     |

---

## Scoring Rubric (100 pts total)

| Dimension           | Weight | Logic                                        |
|---------------------|--------|----------------------------------------------|
| Description quality | 25%    | LLM score 1-5 mapped to 0/25/50/80/100      |
| Tag quality         | 15%    | 0 tags=0, 1-2=33, 3-4=67, 5+=100           |
| License presence    | 15%    | Present=100, missing=0                       |
| Department          | 10%    | Present=100, missing=0                       |
| Category            | 10%    | Present=100, missing=0                       |
| Freshness           | 20%    | Dynamic per updateFrequency field            |
| Column metadata     | 5%     | >=50% columns described=100, else 0         |

Health bands: Good (80-100) | Fair (60-79) | Poor (40-59) | Critical (0-39)

---

## Dynamic Staleness Logic

Staleness is evaluated against each dataset's own `updateFrequency`:
- Daily datasets flagged after 1 day overdue
- Weekly after 7 days, Monthly after 30, Annually after 365
- Historical/as-needed datasets are excluded from staleness checks
- Graduated freshness score: 100 (on time), 50 (1-2x overdue), 0 (2x+ overdue)

---

## Deployment (HuggingFace Spaces)

1. Create Space at `huggingface.co/spaces/spark-dd4g/cambridge-health-dashboard`
2. Set type: **Streamlit**, visibility: **Private**
3. Add `GEMINI_API_KEY` as a Space secret
4. Push this repo to the Space git remote
5. Add `GEMINI_API_KEY` and `HF_TOKEN` as GitHub repository secrets
6. GitHub Actions will auto-push the updated DB daily at 6 AM UTC

---

## Database Tables

| Table             | Purpose                                      |
|-------------------|----------------------------------------------|
| datasets          | Raw metadata from Socrata API                |
| health_flags      | Scores, flags, and sub-scores per dataset    |
| llm_results       | Gemini AI suggestions and description scores |
| human_approvals   | Reviewer decisions with full audit trail     |
| pipeline_runs     | Log of every pipeline execution              |
