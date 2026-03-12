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

- **Automated Quality Scoring Engine** — 6-dimension multi-weighted algorithm producing standardized 0-100 health scores
- **AI-Powered Enrichment Pipeline** — Meta-Llama-3-8B LLM inference generating improved descriptions and semantic tag suggestions
- **Human-in-the-Loop Approval Workflow** — Interactive interface for approving, editing, or rejecting AI suggestions with full audit trail
- **Interactive Analytics Dashboard** — 6 specialized Streamlit tabs with real-time filtering, aggregation, and visualization
- **Dynamic Freshness Detection** — Intelligent staleness calculation based on dataset-specific update frequencies
- **Real-time Query Filtering** — Multi-dimensional filtering by department, category, health band, and custom searches
- **Structured Data Export** — CSV export with all computed metrics and approval status

### Project Components (Pipeline Modules)

* **`pipeline.py`** — Master orchestrator for the data processing pipeline
  - Manages sequential execution of ingestion → scoring → enrichment stages
  - Handles error recovery and state management across stages
  - Single entry point for reproducible pipeline runs
  
* **`fetch_data.py`** — Data ingestion layer with API client
  - Implements Socrata API client with paginated requests
  - Includes exponential backoff retry logic for transient failures
  - Normalizes and persists raw metadata to SQLite
  
* **`scoring_llm/score_and_flag.py`** — Multi-dimensional quality scoring engine
  - Applies 6-dimension weighted algorithm to assess metadata quality
  - Computes health_band classifications (Critical/Poor/Fair/Good)
  - Flags datasets for prioritization and downstream processing
  - Runtime: ~30 seconds for 250+ datasets

* **`scoring_llm/llm_enrich.py`** — AI enrichment layer using LLM inference
  - Calls HuggingFace Inference API for Meta-Llama-3-8B model
  - Generates improved descriptions and semantically-relevant tags
  - Implements selective processing (only pending_review datasets)
  - Records suggestions with metadata for human review
  - Runtime: 1-2 hours for 250+ datasets (LLM inference I/O bound)

* **`streamlit/app.py`** — Interactive web dashboard with 6 analytical views
  - **Overview**: Aggregated metrics, health band distribution, trend indicators
  - **Action Queue**: Sortable dataset list prioritized by health scores
  - **AI Descriptions**: Side-by-side comparison with edit & approval interface
  - **AI Tags**: Tag suggestion review with approve/reject workflow
  - **Spreadsheet View**: Full data table with multi-dimensional filtering and CSV export
  - **Trends**: Historical analytics, distribution charts, and performance metrics

* **`deploy/push_db.py`** — Database synchronization for cloud deployment
  - Uploads processed database to HuggingFace Hub
  - Triggered via GitHub Actions for continuous deployment
  - Enables public-facing dashboards on HuggingFace Spaces

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
# Edit .env and add your HuggingFace API token

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

### Pipeline Architecture & Data Flow

The system implements a **4-stage ETL (Extract-Transform-Load) pipeline** with clear separation of concerns and a human-in-the-loop approval stage:

```
Data Source Layer
    Cambridge Open Data Portal (Socrata API)
              ↓
Ingestion Layer
    [Stage 1] fetch_data.py — Data extraction & normalization
              ↓
         datasets table (raw ingested data)
              ↓
Processing Layer
    [Stage 2] score_and_flag.py — Quality assessment & transformation
              ↓
         health_flags table (processed metrics)
              ↓
Enrichment Layer
    [Stage 3] llm_enrich.py — AI-powered metadata generation
              ↓
         llm_results table (generated suggestions)
              ↓
Presentation & Approval Layer
    [Stage 4] Streamlit UI — Interactive review workflow
              ↓
         human_approvals table (final decisions with audit trail)
              ↓
Output Layer
         CSV/JSON exports & reporting
```

**Pipeline Orchestration:** The `pipeline.py` script manages the orchestration of stages 1-3, handling dependencies, error recovery, and state management across the entire workflow.

### Database Schema (Data Model)

The system uses SQLite with the following key tables:

**`datasets`** — Raw ingested data from source system
- Fields: id, name, description, category, department, license, tags
- Timestamps: createdAt, updatedAt, dataUpdatedAt, updateFrequency
- Purpose: Single source of truth for raw metadata

**`health_flags`** — Processed quality metrics (output of scoring stage)
- Scores: health_score (0-100), health_band, dimension-specific scores
- Flags: missing_description, missing_tags, missing_license (boolean)
- Metadata: llm_desc_score, llm_desc_feedback, days_overdue
- Purpose: Quality assessment data for filtering and prioritization

**`llm_results`** — AI-generated suggestions (output of enrichment stage)
- Suggestions: llm_suggested_desc, llm_suggested_tags
- Status: llm_status (pending_review, approved, edited, rejected)
- Metadata: llm_generated_at, llm_feedback
- Purpose: Store AI-generated improvement suggestions awaiting approval

**`human_approvals`** — Audit trail of human decisions (approval workflow output)
- Decisions: human_status (approved, edited, rejected)
- Approved content: approved_description, approved_tags
- Audit metadata: reviewed_by, reviewed_at, edit_note
- Constraints: PRIMARY KEY on dataset_id (prevents duplicate approvals)
- Purpose: Complete accountability log of all review decisions

**`pipeline_runs`** — Execution metadata and logging
- Tracking: run_id, run_timestamp, step (fetch/score/enrich)
- Status: success/failure, execution_time_in_seconds, error_message
- Purpose: Monitor pipeline health and debug failures

---

## Scoring Rubric

### Scoring Methodology

The health score uses a **multi-weighted algorithm** combining 6 dimensions into a single 0-100 score:

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
HF_TOKEN=your_huggingface_token       # Required for LLM inference
BASE_DIR=/path/to/base/directory      # Optional: data location
```

### Automated Data Refresh

The system includes a GitHub Actions workflow that automatically refreshes data **every Monday at 2 AM UTC**:

```yaml
# Triggered by: .github/workflows/weekly-refresh.yml
- Fetches latest datasets from Cambridge API
- Re-scores all metadata quality dimensions
- Generates AI-enhanced descriptions & tags
- Syncs updated database to HuggingFace Spaces
- Sends completion summary to Actions tab
```

**Setup:** Add `HF_TOKEN` secret to GitHub Settings → Secrets and variables → Actions (see [Setup.md](Setup.md#automated-weekly-refresh-github-actions) for details).

**Manual Refresh:** `python pipeline.py && python deploy/push_db.py`

---

## Support

- **Issues:** Create GitHub issues for bugs, feature requests
- **Documentation:** See [Setup.md](Setup.md) for detailed troubleshooting
- **Dataset Questions:** Check [dataset-documentation/DATASETDOC.md](dataset-documentation/DATASETDOC.md)

---

## Contributors

**SPARK DD4G Team | Spring 2026**
- Boston University

---

## License

MIT License — See LICENSE file for details
