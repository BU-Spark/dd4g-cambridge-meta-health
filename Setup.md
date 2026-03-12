# Cambridge Open Data — Metadata Health Dashboard
## Complete Setup & Deployment Guide

**Spring 2026 | SPARK DD4G | Boston University**

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the System](#running-the-system)
6. [Dashboard Access](#dashboard-access)
7. [Data Pipeline Explained](#data-pipeline-explained)
8. [Scoring Rubric](#scoring-rubric)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance & Updates](#maintenance--updates)

---

## Project Overview

The Cambridge Open Data Metadata Health Dashboard is an automated audit system that evaluates metadata quality for datasets on the [City of Cambridge Open Data Portal](https://data.cambridgema.gov/). 

**Key Features:**
- Automated metadata quality scoring (0-100)
- AI-powered description and tag suggestions using Meta-Llama-3-8B
- Interactive dashboard with 6 analytical views
- Human review workflow for AI suggestions
- Historical trending and analytics
- CSV export of health metrics

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.9+** (tested with 3.13)
- **Git** for version control
- **HuggingFace API Token** (for LLM inference) — [Get one here](https://huggingface.co/settings/tokens)
- **Internet connection** (for Socrata API, HuggingFace models)
- **~2GB disk space** (for database and models)

### System Requirements
- **RAM:** 4GB minimum (8GB+ recommended for LLM inference)
- **CPU:** Any modern processor (LLM inference benefits from multi-core)
- **OS:** macOS, Linux, or Windows with Git Bash

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/cambridge-health-dashboard
cd cambridge-health-dashboard
```

### Step 2: Create a Python Virtual Environment

```bash
# Using venv (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Or using conda:
```bash
conda create -n cambridge python=3.11
conda activate cambridge
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- `streamlit` — Interactive dashboard framework
- `pandas` — Data manipulation & analysis
- `plotly` — Interactive visualizations
- `requests` — HTTP client for APIs
- `huggingface_hub` — LLM model access
- `pyyaml` — Configuration parsing

---

## Configuration

### Step 1: Set Up Environment Variables

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```bash
nano .env  # Or use your preferred editor
```

**Required variables:**

```env
# HuggingFace API Token - Required for LLM inference (Meta-Llama-3-8B)
# Get from: https://huggingface.co/settings/tokens
HF_TOKEN=your_actual_token_here

# Base directory for data storage (use absolute path)
# This is where cambridge_metadata.db will be created
BASE_DIR=/path/to/your/base/directory
```

**Example (macOS/Linux):**
```env
HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWx...
BASE_DIR=/Users/yourname/cambridge-data
```

**Example (Windows):**
```env
HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWx...
BASE_DIR=C:\Users\yourname\cambridge-data
```

### Step 2: Create Data Directory

```bash
mkdir -p data
```

The database will be created automatically in `data/cambridge_metadata.db` when you run the pipeline.

---

## Running the System

### Option A: Full Pipeline (Recommended First Run)

Run all 3 steps in sequence:

```bash
python pipeline.py
```

**This does:**
1. Fetches all datasets from Cambridge Open Data Portal (Socrata API)
2. Scores metadata quality (description, tags, license, department, category, freshness)
3. Generates AI-powered suggestions for descriptions and tags
4. Saves everything to `cambridge_metadata.db`

**Typical run time:** 10-30 minutes (depending on internet speed and number of datasets)

### Option B: Individual Steps

If you want to run steps separately:

```bash
# Step 1: Fetch data from Socrata API
python fetch_data.py

# Step 2: Score metadata quality
python scoring_llm/score_and_flag.py

# Step 3: Generate AI suggestions
python scoring_llm/llm_enrich.py
```

### Troubleshooting Pipeline Runs

**Error: "ModuleNotFoundError"**
- Ensure you activated the virtual environment: `source venv/bin/activate`

**Error: "HF_TOKEN not found"**
- Verify `.env` file exists and has correct HuggingFace token
- Restart the terminal after editing `.env`

**Error: "Connection refused" / API timeout**
- Check internet connection
- Cambridge API rate limits: 5,000 calls/hour
- The script includes retry logic; wait and try again

**Database locked error**
- Close any other Streamlit/database connections
- Delete `data/cambridge_metadata.db` to start fresh: `rm data/cambridge_metadata.db`

---

## Dashboard Access

### Starting the Streamlit App

```bash
streamlit run streamlit/app.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

### Opening the Dashboard

1. Open your web browser
2. Go to `http://localhost:8501`
3. The dashboard should load with 6 tabs

### Dashboard Navigation

| Tab | Purpose |
|-----|----------|
| **Overview** | Summary metrics, health band distribution, score breakdown |
| **Action Queue** | Sorted list of datasets needing attention (worst scores first) |
| **AI Descriptions** | Review & approve AI-generated descriptions (with editing) |
| **AI Tags** | Review & approve AI-generated tags |
| **Spreadsheet View** | Full data table with all metrics, export to CSV |
| **Trends** | Historical analysis, license coverage, tag distribution |

### Sidebar Filters

- **Search:** Filter by dataset name
- **Department:** Filter by department (e.g., "Planning", "Public Health")
- **Category:** Filter by category
- **Health Band:** Filter by score band (Critical/Poor/Fair/Good)
- **License Status:** Has/Missing license
- **Description Status:** Has/Missing description
- **Tags Status:** Has/Missing tags

### Using the Review Workflow

1. Go to **AI Descriptions** tab
2. Find a dataset marked "pending_review"
3. Click the expander to view details
4. See original vs. AI-suggested description
5. **Choose one:**
   - **Approve** — Accept AI suggestion as-is
   - **Approve Edited** — Edit the suggestion first, then approve
   - **Reject** — Reject the AI suggestion
6. Click the button — saves to database immediately
7. Check **Spreadsheet View** → "Approved" column shows status

---

## Data Pipeline Explained

### Pipeline Architecture

The system implements a 4-stage data processing pipeline with clear separation of concerns:

```
Cambridge Open Data Portal (Data Source)
           ↓
    [Stage 1] Data Ingestion Layer (fetch_data.py)
           ↓
    Datasets Table (Raw Data)
           ↓
    [Stage 2] Processing & Scoring Layer (score_and_flag.py)
           ↓
    Health Flags Table (Transformed Data)
           ↓
    [Stage 3] AI Enrichment Layer (llm_enrich.py)
           ↓
    LLM Results Table (AI-Generated Data)
           ↓
    [Stage 4] User Interface & Review Layer (Streamlit)
           ↓
    Human Approvals Table (Final Output)
           ↓
    CSV Export / Reporting
```

**Pipeline Orchestration:**
The `pipeline.py` script orchestrates all three stages (ingestion, processing, enrichment) in sequence, managing dependencies and error handling across the entire data workflow.

### Step 1: Data Ingestion (fetch_data.py)

**Technical Purpose:**
This stage implements the ingestion layer of the data pipeline, responsible for extracting raw metadata from the source system.

**What it does:**
- Connects to Cambridge's Socrata API (the data source)
- Implements paginated requests with exponential backoff retry logic to handle transient failures
- Parses JSON responses and normalizes data structure
- Writes records to the `datasets` table in SQLite

**Key data fields ingested:**
- Identifiers: `id`, `name`
- Metadata: `description`, `category`, `department`, `license`, `tags`
- Timestamps: `createdAt`, `updatedAt`, `dataUpdatedAt`, `updateFrequency`

**Error Handling:**
- Respects API rate limits (5,000 calls/hour) with intelligent backoff
- Logs all failures with timestamp and error context for debugging
- Supports resume capability if the ingestion is interrupted

**Performance:** Typically 2-5 minutes for 250+ datasets

### Step 2: Quality Assessment & Scoring (score_and_flag.py)

**Technical Purpose:**
This processing stage transforms raw metadata into quality metrics using a weighted multi-dimensional scoring algorithm.

**What it does:**
- Iterates through all ingested datasets and applies a 6-dimensional scoring model
- Calculates dimension-specific scores based on predefined rules and thresholds
- Aggregates scores using weighted formula (see Scoring Rubric)
- Assigns health bands based on score ranges (Critical/Poor/Fair/Good)
- Flags datasets meeting specific quality thresholds for downstream processing

**Why this architecture matters:**
- Transparent, rule-based scoring (not a black box)
- Consistent evaluation across all 250+ datasets
- Weights can be easily adjusted for different policy priorities
- Flagging system identifies candidates for AI enrichment

**Output Storage:**
Results written to `health_flags` table with:
- Overall `health_score` (0-100) and `health_band` classification
- Dimension-specific scores for breakdown analysis
- Quality flags (missing description, missing license, stale data, etc.)
- Metadata like days overdue for freshness calculations

**Performance:** ~30 seconds for full dataset processing

### Step 3: AI Enrichment (llm_enrich.py)

**Technical Purpose:**
This stage uses a large language model (LLM) to generate AI-powered suggestions for improving metadata, implementing the enrichment layer of the pipeline.

**What it does:**
- Filters datasets with `llm_status = "pending_review"` (datasets flagged by scoring stage)
- Sends dataset metadata to HuggingFace's Meta-Llama-3-8B model for inference
- Generates improved descriptions using LLM-based text generation
- Suggests relevant tags using semantic understanding and embeddings
- Provides explanatory feedback on why improvements were suggested

**Architecture Details:**
- Uses HuggingFace Inference API (serverless LLM inference)
- Implements async request handling for efficiency
- Caches model responses to avoid redundant API calls
- Writes suggestions to `llm_results` table with metadata

**Important Constraints:**
- Read-only operation: Does NOT modify source datasets
- Results are suggestions only: require human approval before application
- Selective processing: only handles pending datasets (avoids redundant inference)
- Status tracking: records `llm_status` for approval workflow state management

**Performance:** 1-2 hours for 250 datasets (awaiting LLM inference service)

### Step 4: Human Review Interface (Streamlit Application)

**Technical Purpose:**
Implements the final stage: human-in-the-loop approval workflow with complete audit trail logging.

**What it does:**
- Presents AI suggestions through an interactive web interface
- Accepts human review decisions: approve, edit-then-approve, or reject
- Implements optimistic concurrency control (PRIMARY KEY constraint prevents duplicates)
- Records all decisions with metadata to `human_approvals` table for audit trail
- Updates `llm_status` in upstream tables to reflect approval state

**Approval State Management:**
Possible statuses:
- `pending_review` — Awaiting human review (initial state)
- `approved` — Suggestion accepted as-is
- `edited` — Suggestion accepted after human modification
- `rejected` — Suggestion not used

**Audit & Accountability:**
- Full record of reviewer name, timestamp, and any notes
- Complete history enables performance tracking and decision reversal if needed
- State transitions trigger upstream updates for consistency

---

## Scoring Rubric

### Overall Score (0-100)

The health score is a weighted average of 6 dimensions:

```
Health Score = (25% × Description) + (15% × Tags) + (15% × License) 
             + (10% × Department) + (10% × Category) + (25% × Freshness)
```

### Dimension Details

#### 1. Description Quality (25% weight)

| Score | Criteria |
|-------|----------|
| **0** | Missing description |
| **50** | Description exists (minimum threshold) |
| **75-100** | AI refines after analysis |

**How it works:**
- Initially: 0 or 50 (binary check)
- After LLM enrichment: Refined to 0-100 based on length, clarity, informativeness
- Key metric: Description length and specificity

#### 2. Tag Quality (15% weight)

| Tag Count | Score | Interpretation |
|-----------|-------|----------|
| 0 tags | 0 | No tags assigned |
| 1-2 tags | 33 | Minimal tags |
| 3-4 tags | 67 | Good tag coverage (target) |
| 5+ tags | 100 | Excellent tag coverage |

**Why 3 tags is the target:**
- 3-4 tags provides good discoverability
- More than 4 tags rarely add value
- Fewer than 3 tags insufficient for search

#### 3. License (15% weight)

| Status | Score | Meaning |
|--------|-------|----------|
| License present | 100 | License field populated |
| License missing | 0 | No license specified |

**Why it matters:**
- Users need to know how they can use the data
- Required for compliance and reusability
- Missing: 25% of Cambridge datasets

#### 4. Department (10% weight)

| Status | Score | Meaning |
|--------|-------|----------|
| Department assigned | 100 | Department field populated |
| Department missing | 0 | No department |

**Why it matters:**
- Helps users find datasets by source agency
- Improves metadata organization
- Missing: ~10% of Cambridge datasets

#### 5. Category (10% weight)

| Status | Score | Meaning |
|--------|-------|----------|
| Category assigned | 100 | Category field populated |
| Category missing | 0 | No category |

**Why it matters:**
- Categorization improves search and browsing
- Users filter by category
- Missing: ~20% of Cambridge datasets

#### 6. Freshness (25% weight) — The Most Important!

**Dynamic scoring based on dataset's own update frequency:**

| Update Frequency | Expected Interval | Overdue Days = Stale? |
|------------------|-------------------|-----------------------|
| Daily | 1 day | > 1 day |
| Weekly | 7 days | > 7 days |
| Biweekly | 14 days | > 14 days |
| Monthly | 30 days | > 30 days |
| Quarterly | 90 days | > 90 days |
| Annually | 365 days | > 365 days |
| Historical | Never | Never stale |

**Freshness Score Logic:**

```python
Days since update / Expected interval = Overdue Ratio

If ratio ≤ 1.0: Score = 100 (current)
If ratio ≤ 2.0: Score = 50  (somewhat stale)
If ratio > 2.0:  Score = 0   (very stale)
```

**Example:**
- Dataset: "Daily updated" but last update was 3 days ago
- Overdue ratio = 3 / 1 = 3.0
- Freshness score = 0 (critically stale)

### Health Bands (Final Categories)

```
Score ≥ 80 → GOOD      Exemplary metadata
Score 60-79 → FAIR     Acceptable but needs work
Score 40-59 → POOR     Multiple issues
Score < 40 → CRITICAL  Missing core metadata
```

### Example Calculations

**Example 1: Well-maintained dataset**
- Description: 80 points (present + detailed)
- Tags: 100 points (5 tags)
- License: 100 points
- Department: 100 points
- Category: 100 points
- Freshness: 100 points (updated on schedule)

Health Score = 0.25(80) + 0.15(100) + 0.15(100) + 0.10(100) + 0.10(100) + 0.25(100) = **95 → GOOD**

**Example 2: Neglected dataset**
- Description: 50 points (exists but vague)
- Tags: 0 points (no tags)
- License: 0 points (missing)
- Department: 100 points
- Category: 0 points (missing)
- Freshness: 25 points (very overdue)

Health Score = 0.25(50) + 0.15(0) + 0.15(0) + 0.10(100) + 0.10(0) + 0.25(25) = **23 → CRITICAL**

---

## Troubleshooting

### Dashboard Won't Load

**Problem:** "StreamlitAPIException: Cannot load image"

**Solution:**
```bash
# Clear Streamlit cache
streamlit cache clear

# Restart the app
streamlit run streamlit/app.py
```

### Database Errors

**Problem:** "database is locked"

**Solution:**
1. Close all Streamlit connections
2. Delete old database: `rm data/cambridge_metadata.db`
3. Re-run pipeline: `python pipeline.py`

### API Key Not Working

**Problem:** "INVALID_ARGUMENT: Invalid API Key"

**Solution:**
1. Verify API key is correct in `.env`
2. Check key hasn't expired on Google Cloud Console
3. Ensure BASE_DIR is set correctly
4. Restart terminal (environment variables cache)

### Out of Memory

**Problem:** LLM inference crashes with "CUDA out of memory"

**Solution:**
- This system uses CPU inference (no GPU requirement)
- If running on very low-RAM system, run one step at a time
- Consider running on machine with 8GB+ RAM

### Slow Performance

**Common causes:**
- Large number of datasets (100+)
- Network latency to Socrata API
- Streamlit recomputing on every interaction

**Solutions:**
- Use sidebar filters to reduce visible rows
- Run pipeline during off-hours
- Clear cache: `streamlit cache clear`

---

## Maintenance & Updates

### Regular Tasks

#### Weekly
- Review "Critical" health band datasets
- Check freshness for datasets marked "stale"
- Monitor "AI Descriptions" tab for new suggestions

#### Monthly
- Run full pipeline refresh: `python pipeline.py`
- Export health report (Spreadsheet tab → Download CSV)
- Review trends in Tab 6

#### Quarterly
- Review AI suggestion quality
- Identify patterns in missing metadata
- Plan targeted improvement campaigns

### Updating Dependencies

```bash
# Check for updates
pip list --outdated

# Update all packages
pip install --upgrade -r requirements.txt

# Test the dashboard still works
streamlit run streamlit/app.py
```

### Backing Up Data

```bash
# Backup the database
cp data/cambridge_metadata.db data/cambridge_metadata.db.backup_$(date +%Y%m%d)

# Keep 5 most recent backups
ls -t data/cambridge_metadata.db.backup_* | tail -n +6 | xargs rm
```

### Automated Weekly Refresh (GitHub Actions)

The system includes a fully automated weekly data refresh workflow that runs every Monday at 2 AM UTC.

**What it does:**
1. Fetches fresh data from the Cambridge Open Data Portal
2. Re-scores all datasets with updated freshness metrics
3. Regenerates AI enrichment (descriptions & tags)
4. Syncs the updated database to HuggingFace Spaces
5. Your dashboard automatically reflects the latest data

**Setup Instructions:**

1. **Add HuggingFace Token Secret**
   - Go to GitHub → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `HF_TOKEN`
   - Value: Your HuggingFace API token
   - Click Add

2. **Verify Workflow**
   - Go to Actions tab in GitHub
   - Look for "Weekly Data Refresh Pipeline"
   - Confirm it's enabled (green checkmark)

3. **Manual Trigger (Optional)**
   - Go to Actions → "Weekly Data Refresh Pipeline"
   - Click "Run workflow" → "Run workflow" button
   - Monitor progress in real-time

4. **View Logs**
   - Actions tab → Click latest run
   - See pipeline output, database sync status, timestamp
   - Receives success/failure summary

**Customizing Schedule:**
Edit `.github/workflows/weekly-refresh.yml`:
- Line 7: `- cron: '0 2 * * 1'` (currently Monday 2 AM UTC)
- Examples:
  - `'0 3 * * 0'` = Sunday 3 AM UTC
  - `'0 9 * * 1-5'` = Weekdays 9 AM UTC
  - `'0 */6 * * *'` = Every 6 hours

**What happens if it fails:**
- GitHub sends notification
- Check Actions logs for error
- Common issues: API rate limits, HuggingFace token expired
- Run manually: `python pipeline.py && python deploy/push_db.py`

---

### Deploying to Production

See [deploy/README.md](deploy/README.md) for cloud deployment instructions.

---

## Support & Documentation

- **Detailed Data Documentation:** [dataset-documentation/DATASETDOC.md](dataset-documentation/DATASETDOC.md)
- **Project README:** [README.md](README.md)
- **Issue Tracking:** Create issues in GitHub

---

## Frequently Asked Questions

**Q: How often should I run the pipeline?**
A: Weekly for production, daily if you're actively improving metadata. Use GitHub Actions (see `.github/workflows/refresh.yml`) to automate.

**Q: Can I edit dataset descriptions directly in the database?**
A: Not recommended. Always use the dashboard review workflow to maintain audit trail.

**Q: What if the AI suggestions are bad?**
A: Click "Reject" and they won't be used. The system learns over time.

**Q: How do I add new datasets?**
A: They're auto-fetched from the Cambridge Open Data Portal each pipeline run.

**Q: Can I customize the scoring weights?**
A: Yes! Edit `WEIGHTS` dict in `scoring_llm/score_and_flag.py` and re-run pipeline.

---

## Quick Reference

```bash
# Full setup from scratch
git clone https://github.com/your-org/cambridge-health-dashboard
cd cambridge-health-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API key
python pipeline.py
streamlit run streamlit/app.py
# Open http://localhost:8501
```

---

**Version:** 1.0 | **Last Updated:** March 11, 2026
