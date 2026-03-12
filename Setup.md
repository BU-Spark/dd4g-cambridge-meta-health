# Cambridge Open Data — Metadata Health Dashboard

**Spring 2026 | SPARK DD4G | Boston University**

Automated metadata audit system for the [City of Cambridge Open Data Portal](https://data.cambridgema.gov/).

---

## Project Structure

```
dd4g-cambridge-meta-health/
├── ETL/                          # ETL Pipeline
│   ├── pipeline.py               # Main orchestrator
│   ├── ingest.py                 # Socrata API data ingestion
│   ├── evaluate.py               # Dataset health evaluation
│   ├── publish.py                # HuggingFace deployment
│   ├── requirements.txt          # Python dependencies
│   └── data/                     # SQLite database storage
│       └── cambridge_metadata.db
├── streamlit/
│   └── app.py                    # Streamlit dashboard
├── EDA/
│   ├── EDA.ipynb                 # Exploratory data analysis
│   └── fetch_data.py             # Data fetching utilities
├── dataset-documentation/        # Dataset documentation
└── .github/
    └── workflows/
        ├── etl-pipeline.yml      # Daily ETL automation
        └── DEPLOYMENT.md         # Workflow documentation
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

## Running Locally

```bash
# Navigate to ETL directory
cd ETL

# Full pipeline: ingest + evaluate
python pipeline.py

# Run specific steps
python pipeline.py --ingest-only    # Only fetch data
python pipeline.py --evaluate-only  # Only run evaluations
python pipeline.py --dry-run        # Preview without saving

# Dashboard (from root directory)
cd ..
streamlit run streamlit/app.py
```

---

## Automated Deployment (GitHub Actions)

The ETL pipeline runs automatically **daily at 2:00 AM UTC** via GitHub Actions.

### Quick Start

1. Configure API keys as GitHub Secrets (see [Workflow Documentation](.github/workflows/DEPLOYMENT.md))
2. Pipeline runs automatically on schedule
3. View results in **Actions** tab
4. Download database artifacts for analysis

### Manual Trigger

1. Go to **Actions** tab → **Daily ETL Pipeline**
2. Click **Run workflow**
3. Select options (ingest-only, evaluate-only, dry-run)
4. Click **Run workflow** button

For full documentation, setup instructions, and troubleshooting, see:
**[.github/workflows/DEPLOYMENT.md](.github/workflows/DEPLOYMENT.md)**

---

## Environment Variables

| Variable          | Purpose                                                       | Required?   |
| ----------------- | ------------------------------------------------------------- | ----------- |
| OPENAI_API_KEY    | OpenAI GPT API for metadata evaluation                        | Optional\*  |
| ANTHROPIC_API_KEY | Anthropic Claude API for metadata evaluation                  | Optional\*  |
| GOOGLE_API_KEY    | Google Gemini API for metadata evaluation                     | Optional\*  |
| HUGGINGFACE_TOKEN | HuggingFace token for model access and deployment             | Recommended |
| BASE_DIR          | Root directory for data files (defaults to current directory) | Optional    |

**\*At least one LLM API key is required** for the evaluation step. The pipeline supports multiple LLM providers - configure the one you prefer to use.

---

## Scoring Rubric (100 pts total)

| Dimension           | Weight | Logic                                  |
| ------------------- | ------ | -------------------------------------- |
| Description quality | 25%    | LLM score 1-5 mapped to 0/25/50/80/100 |
| Tag quality         | 15%    | 0 tags=0, 1-2=33, 3-4=67, 5+=100       |
| License presence    | 15%    | Present=100, missing=0                 |
| Department          | 10%    | Present=100, missing=0                 |
| Category            | 10%    | Present=100, missing=0                 |
| Freshness           | 20%    | Dynamic per updateFrequency field      |
| Column metadata     | 5%     | >=50% columns described=100, else 0    |

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

| Table           | Purpose                                      |
| --------------- | -------------------------------------------- |
| datasets        | Raw metadata from Socrata API                |
| health_flags    | Scores, flags, and sub-scores per dataset    |
| llm_results     | Gemini AI suggestions and description scores |
| human_approvals | Reviewer decisions with full audit trail     |
| pipeline_runs   | Log of every pipeline execution              |
