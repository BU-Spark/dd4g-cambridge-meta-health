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
- **Google Gemini API Key** (for AI enrichment) — [Get one here](https://makersuite.google.com/app/apikey)
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
# Google Gemini API Key - Required for AI description/tag generation
# Get from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_api_key_here

# Base directory for data storage (use absolute path)
# This is where cambridge_metadata.db will be created
BASE_DIR=/path/to/your/base/directory
```

**Example (macOS/Linux):**
```env
GEMINI_API_KEY=AIzaSyDk...your_key...
BASE_DIR=/Users/yourname/cambridge-data
```

**Example (Windows):**
```env
GEMINI_API_KEY=AIzaSyDk...your_key...
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

**Error: "GEMINI_API_KEY not found"**
- Verify `.env` file exists and has correct key
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

### Architecture

```
Cambridge Open Data Portal
           ↓
    [Step 1] fetch_data.py
           ↓
    Datasets table (SQLite)
           ↓
    [Step 2] score_and_flag.py
           ↓
    Health flags table (scoring metrics)
           ↓
    [Step 3] llm_enrich.py
           ↓
    LLM results table (AI suggestions)
           ↓
    Streamlit Dashboard
           ↓
    [Step 4] Human Review (manual approval)
           ↓
    Human Approvals table (final decisions)
           ↓
    CSV Export / Reporting
```

### Step 1: Data Fetching (fetch_data.py)

**What it does:**
- Connects to Socrata Open Data API for Cambridge
- Fetches all datasets with metadata (name, description, tags, etc.)
- Stores in `datasets` table

**Key fields fetched:**
- `id`, `name`, `description`, `category`, `department`
- `license`, `tags`, `createdAt`, `updatedAt`, `dataUpdatedAt`, `updateFrequency`

**Retry logic:**
- Automatic retries on transient failures
- Respects API rate limits
- Logs all failures for debugging

### Step 2: Health Scoring (score_and_flag.py)

**What it does:**
- Evaluates 6 dimensions of metadata quality
- Weights each dimension (see Scoring Rubric)
- Assigns health band (Critical/Poor/Fair/Good)
- Flags datasets that need attention

**Scoring dimensions:**
1. Description (25%) — Presence & quality
2. Tags (15%) — Count and relevance
3. License (15%) — Is license documented?
4. Department (10%) — Is department assigned?
5. Category (10%) — Is category assigned?
6. Freshness (25%) — How current is the data?

### Step 3: AI Enrichment (llm_enrich.py)

**What it does:**
- Uses Meta-Llama-3-8B model (via HuggingFace)
- Generates improved descriptions
- Suggests relevant tags
- Provides AI feedback/explanations

**Important:**
- Only processes datasets with `llm_status = "pending_review"`
- Uses Google Gemini API for embeddings & initial analysis
- Saves suggestions to `llm_results` table
- Does NOT modify the original dataset

### Step 4: Human Review (Streamlit)

**What it does:**
- Presents AI suggestions to human reviewers
- Allows editing before approval
- Saves approval decisions to `human_approvals` table
- Updates `llm_status` to reflect human decisions

**Approval statuses:**
- `approved` — Used AI suggestion as-is
- `edited` — Used AI suggestion but edited it
- `rejected` — Rejected AI suggestion entirely
- `pending_review` — Waiting for human review

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
