# Cambridge Open Data — Metadata Health Dashboard

**Spring 2026 | SPARK DD4G | Boston University**

Automated metadata audit system for the [City of Cambridge Open Data Portal](https://data.cambridgema.gov/).

---

## Project Structure

```
cambridge-health-dashboard/
├── streamlit/
│   └── app.py                    # Streamlit dashboard (6 tabs)
├── fetch_data.py                 # Socrata API ingestion with retry logic
├── pipeline.py                   # Orchestrator: run all 3 steps in order
├── scoring_llm/
│   ├── score_and_flag.py         # 6-dimension scoring engine
│   └── llm_enrich.py             # HuggingFace Meta-Llama-3-8B AI enrichment
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
export HF_TOKEN="your_huggingface_token_here"
export BASE_DIR="$(pwd)"
```

---

## Running

```bash
# Full pipeline: fetch + score + LLM enrichment
python pipeline.py

# Dashboard only (requires DB to exist)
streamlit run streamlit/app.py
```

---

## Environment Variables

| Variable         | Purpose                                      |
|------------------|----------------------------------------------|
| HF_TOKEN         | HuggingFace API token (inference + deployment) |
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
| Freshness           | 25%    | Dynamic per updateFrequency field            |

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

1. Create Space at `huggingface.co/spaces/your-user/cambridge-health-dashboard`
2. Set type: **Streamlit**, visibility: **Private**
3. Add `HF_TOKEN` as a Space secret (needed for inference API + file uploads)
4. Clone the Space repo and push this codebase
5. Streamlit app will auto-start on deployment
6. GitHub Actions can auto-sync database daily: set `HF_TOKEN` as GitHub secret

---

## Database Tables

| Table             | Purpose                                      |
|-------------------|----------------------------------------------|
| datasets          | Raw metadata from Socrata API                |
| health_flags      | Scores, flags, and sub-scores per dataset    |
| llm_results       | HuggingFace LLM suggestions and scores       |
| human_approvals   | Reviewer decisions with full audit trail     |
| pipeline_runs     | Log of every pipeline execution              |
