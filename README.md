<h1 align="center">
  <br>
  <a href="https://www.bu.edu/spark/" target="_blank"><img src="https://www.bu.edu/spark/files/2023/08/logo.png" alt="BUSpark" width="200"></a>
  <br>
  Cambridge Open Data — Metadata Health Dashboard
  <br>
</h1>

<h4 align="center">Automated quality audit system for the City of Cambridge Open Data Portal</h4>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#how-to-use">How To Use</a> •
  <a href="#project-description">Project Description</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#scoring-rubric">Scoring Rubric</a> •
  <a href="#data-locations">Data Locations</a>
</p>

---

## Key Features

- **Automated Quality Scoring** — 6-dimension metadata audit with weighted scoring (0-100)
- **AI-Powered Enrichment** — Meta-Llama-3-8B generates improved descriptions and tags
- **Human Review Workflow** — Interactive dashboard for approving, editing, or rejecting AI suggestions
- **Interactive Analytics** — 6 specialized tabs for overview, action queue, AI review, spreadsheet view, and trends
- **Freshness Monitoring** — Dynamic staleness detection based on each dataset's update frequency
- **Real-time Filtering** — Sidebar filters by department, category, health band, and more
- **CSV Export** — Download full health report for offline analysis

### Project Components

* **`pipeline.py`** — Master orchestrator
  - Runs all 3 steps in sequence: fetch → score → enrich
  - Single command to update entire system
  
* **`fetch_data.py`** — Socrata API integration
  - Fetches all datasets from Cambridge Open Data Portal
  - Includes retry logic for transient failures
  - Stores metadata in SQLite database
  
* **`scoring_llm/score_and_flag.py`** — 6-dimension scoring engine
  - Evaluates: description, tags, license, department, category, freshness
  - Assigns health bands (Critical/Poor/Fair/Good)
  - Runs ~30 seconds for entire dataset

* **`scoring_llm/llm_enrich.py`** — AI-powered description/tag generation
  - Uses Meta-Llama-3-8B via HuggingFace Inference API
  - Generates improved descriptions with feedback
  - Suggests relevant tags using embeddings
  - Processes only pending datasets

* **`streamlit/app.py`** — Interactive dashboard (6 tabs)
  - Overview: Summary metrics and band distribution
  - Action Queue: Sorted by health score (worst first)
  - AI Descriptions: Review & approve descriptions with editing
  - AI Tags: Review & approve AI-generated tags
  - Spreadsheet: Full data table with all metrics & CSV export
  - Trends: Historical analysis and metrics visualization

* **`deploy/push_db.py`** — Database sync for deployment
  - Pushes updated database to HuggingFace for cloud hosting
  - Triggered automatically via GitHub Actions

## How To Use

### Quick Start (5 minutes)

```bash
# Clone repository
git clone https://github.com/your-org/cambridge-health-dashboard
cd cambridge-health-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your Google Gemini API key

# Run full pipeline
python pipeline.py

# Start dashboard
streamlit run streamlit/app.py
# Open http://localhost:8501 in your browser
```

### Full Setup Instructions

For complete installation, configuration, and troubleshooting, see **[Setup.md](Setup.md)** 

This includes:
- System requirements and prerequisites
- Step-by-step installation guide
- Environment configuration
- Running individual pipeline steps
- Dashboard navigation guide
- Detailed scoring rubric with examples
- Troubleshooting and maintenance

### Workflow

1. **Initialize System** — Run `python pipeline.py` (10-30 min depending on dataset size)
2. **View Dashboard** — `streamlit run streamlit/app.py` and open http://localhost:8501
3. **Review AI Suggestions** — Go to "AI Descriptions" or "AI Tags" tabs
4. **Approve or Edit** — Click buttons to approve, edit-then-approve, or reject suggestions
5. **Monitor Progress** — Check "Spreadsheet View" for full report status
6. **Export Results** — Download CSV from Spreadsheet tab for further analysis

---

## Project Description

### The Problem

The City of Cambridge maintains a public data portal with 250+ datasets covering everything from public health to transportation. However, metadata quality varies dramatically:
- 15% of datasets missing descriptions
- 20% missing categories
- 25% missing licenses
- Many datasets not updated as promised

Users struggle to find relevant datasets, and administrators lack visibility into quality issues.

### Our Solution

The **Cambridge Metadata Health Dashboard** is an AI-powered audit system that:

1. **Automatically evaluates** all datasets across 6 quality dimensions
2. **Assigns health scores** (0-100) and bands (Critical/Poor/Fair/Good)
3. **Generates AI suggestions** for missing or poor descriptions and tags
4. **Enables human review** with an intuitive approval workflow
5. **Tracks progress** with interactive dashboards and historical trends

The system combines:
- **Structured scoring** (weights, rules, thresholds)
- **Intelligent AI** (LLM-powered suggestions with embeddings)
- **Human oversight** (full audit trail of decisions)
- **Actionable insights** (sorted by priority, exportable reports)

### Impact

- Prioritizes work (sort by health score)
- Measures improvement (trend analysis)
- Saves time (AI suggestions reduce manual work)
- Creates accountability (audit trail of approvals)
- Enables iteration (run pipeline weekly to track progress)

---

## Architecture

### Data Pipeline

```
Cambridge Open Data Portal
         ↓
   [Step 1] fetch_data.py
         ↓
   Datasets Table (251 datasets)
         ↓
   [Step 2] score_and_flag.py
         ↓
   Health Flags Table (6 scores per dataset)
         ↓
   [Step 3] llm_enrich.py
         ↓
   LLM Results Table (AI suggestions)
         ↓
   Streamlit Dashboard (6 tabs)
         ↓
   [Step 4] Human Review (click approve/reject)
         ↓
   Human Approvals Table (audit trail)
         ↓
   CSV Export / Reports
```

### Database Schema

**`datasets`** — Raw metadata from Socrata API
- id, name, description, category, department
- license, tags, createdAt, updatedAt, dataUpdatedAt, updateFrequency

**`health_flags`** — Scoring metrics per dataset
- dataset_id, health_score, health_band (0-100)
- llm_desc_score, llm_desc_feedback, llm_suggested_desc
- missing_description, missing_tags, missing_license (0/1)
- missing_department, missing_category, is_stale (0/1)
- days_overdue

**`llm_results`** — AI suggestions and metadata
- dataset_id, llm_suggested_desc, llm_suggested_tags
- llm_status (pending_review, approved, edited, rejected)
- llm_generated_at

**`human_approvals`** — Review audit trail
- dataset_id, approved_description, approved_tags
- human_status (approved, edited, rejected)
- reviewed_by, reviewed_at, edit_note

**`pipeline_runs`** — Execution log
- run_id, run_timestamp, step (fetch/score/enrich)
- status (success/failure), execution_time, error_message

---

## Scoring Rubric

The health score is a **weighted combination of 6 dimensions**:

```
Health Score = (25% × Description) + (15% × Tags) + (15% × License) 
             + (10% × Department) + (10% × Category) + (25% × Freshness)
```

### Dimension Details

| Dimension | Weight | Scale | Target |
|-----------|--------|-------|--------|
| **Description** | 25% | 0-100 | Detailed, searchable |
| **Tags** | 15% | 0-100 | 3-4 relevant tags |
| **License** | 15% | 0 or 100 | Clearly documented |
| **Department** | 10% | 0 or 100 | Source agency assigned |
| **Category** | 10% | 0 or 100 | Classification assigned |
| **Freshness** | 25% | 0-100 | Updated on schedule |

### Scoring Examples

**Well-maintained ("Parks & Recreation" dataset)**
- Description: 85/100 (detailed: 200+ words with measurements)
- Tags: 100/100 (5 relevant tags)
- License: 100/100 (CC-BY-4.0)
- Department: 100/100 (Parks and Recreation)
- Category: 100/100 (Recreation)
- Freshness: 100/100 (updated daily, current)
- **Score: 95 → GOOD**

**Neglected ("Budget" dataset)**
- Description: 25/100 (vague: "Budget information")
- Tags: 0/100 (no tags)
- License: 0/100 (missing)
- Department: 100/100 (Finance)
- Category: 0/100 (missing)
- Freshness: 0/100 (should update weekly, last updated 6 months ago)
- **Score: 23 → CRITICAL**

### Health Bands

| Band | Score Range | Interpretation | Action |
|------|-------------|-----------------|--------|
| **Good** | 80-100 | Exemplary metadata | Monitor |
| **Fair** | 60-79 | Acceptable but improvable | Plan updates |
| **Poor** | 40-59 | Multiple issues | High priority |
| **Critical** | <40 | Missing core metadata | Urgent action |

### Freshness Scoring

Freshness is **dynamic and personalized** to each dataset's own update frequency:

| Update Frequency | Expected Interval | Scoring Logic |
|------------------|-------------------|----|
| Daily | 1 day | 100 pts if ≤1 day old, 50 if 1-2 days, 0 if >2 days |
| Weekly | 7 days | 100 pts if ≤7 days old, 50 if 7-14 days, 0 if >14 days |
| Monthly | 30 days | 100 pts if ≤30 days old, 50 if 30-60 days, 0 if >60 days |
| Quarterly | 90 days | 100 pts if ≤90 days old, 50 if 90-180 days, 0 if >180 days |
| Annually | 365 days | 100 pts if ≤365 days old, 50 if 365-730 days, 0 if >730 days |
| Historical | Never | 100 pts (never stale) |

**Example:** A "Daily updated" dataset updated 3 days ago gets 0 points for freshness. A "Quarterly" dataset updated 100 days ago gets 100 points (on schedule).

---

## Data Locations

### Database
- **Local Development:** `data/cambridge_metadata.db` (auto-created)
- **Production:** Hosted on HuggingFace Hub (for web deployment)
- **Backups:** `data/cambridge_metadata.db.backup_YYYYMMDD`

### Documentation
- **Setup Guide:** [Setup.md](Setup.md)
  - System requirements, installation, configuration
  - Running pipeline and dashboard
  - Troubleshooting and maintenance
  
- **Dataset Documentation:** [dataset-documentation/DATASETDOC.md](dataset-documentation/DATASETDOC.md)
  - Detailed description of all 250+ Cambridge datasets
  - Data sources, update frequencies, quality notes
  
- **Code Documentation:**
  - [dataset-documentation/README.md](dataset-documentation/README.md) — Scoring analysis notebooks
  - [deploy/README.md](deploy/README.md) — Deployment instructions

### Analysis Notebooks
- **`EDA.ipynb`** — Exploratory data analysis of dataset characteristics
- **`compare.ipynb`** — Before/after comparison of metadata quality improvements

---

## Development

### Adding Features

1. Create feature branch: `git checkout -b feature/your-feature main`
2. Make changes and test with `streamlit run streamlit/app.py`
3. Open Pull Request to `dev` branch with description
4. After review, merge to `dev`
5. At semester end, open final PR from `dev` → `main`

### Running Tests

```bash
# Syntax check
python -m py_compile scoring_llm/*.py streamlit/app.py

# Quick pipeline test (limit runs)
LIMIT=10 python pipeline.py
```

### Environment Variables

See `.env.example` for complete list:
```env
GEMINI_API_KEY=your_api_key_here      # Required for LLM enrichment
BASE_DIR=/path/to/base/directory      # Optional: data location
```

---

## Support

- **Issues:** Create GitHub issues for bugs, feature requests
- **Documentation:** See [Setup.md](Setup.md) for detailed troubleshooting
- **Dataset Questions:** Check [dataset-documentation/DATASETDOC.md](dataset-documentation/DATASETDOC.md)

---

## Contributors

**SPARK DD4G Team | Spring 2026**
- Aastha Gidwani — Project Lead
- Boston University

---

## License

MIT License — See LICENSE file for details
