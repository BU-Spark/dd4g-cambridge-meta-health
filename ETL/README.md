# Metadata Health Dashboard: Cambridge ODP

A data pipeline to monitor and evaluate the health of datasets on the Cambridge Open Data Portal (Socrata).

## Architecture

1. **Ingest (`ingest.py`):** Fetches the latest catalog from the Socrata Discovery API and upserts into the `ODP_datasets` table.
2. **Evaluate (`evaluate.py`):** Identifies "stale" or "unevaluated" records. It performs two types of checks:

- **Static Health Checks:** Programmatic checks (e.g., is the license missing? is the data update overdue?).
- **AI Metadata Evaluation:** LLM-based assessment of the description, tags, and categories for clarity and accuracy.

3. **Storage:** SQLite database acting as the state manager. A helper script
   (`setup/reset_db.py`) can delete the database file when you need to run a
   completely fresh ingest.
4. **Visualize:** Streamlit dashboard to display health scores and metadata gaps.

5. **Publish (`publish.py`):** After ingestion/evaluation the pipeline can
   export the dataset to Parquet and push it to a HuggingFace data repository.

## Running the Pipeline

### Local Execution

```bash
# Navigate to ETL directory
cd ETL

# Full pipeline (ingest + evaluate)
python pipeline.py

# Run specific steps
python pipeline.py --ingest-only      # Only fetch data from Socrata
python pipeline.py --evaluate-only    # Only run evaluations
python pipeline.py --dry-run          # Preview without saving
python pipeline.py --limit 10         # Evaluate only 10 datasets
```

### Automated Daily Execution (GitHub Actions)

The pipeline is configured to run automatically **daily at 2:00 AM UTC** via GitHub Actions.

**Workflow file:** `../.github/workflows/etl-pipeline.yml`

**Features:**

- Scheduled daily execution
- Manual trigger with custom options
- Automatic artifact archival (database snapshots)
- Failure notifications and logging

**Setup required:**

1. Configure API keys as GitHub repository secrets
2. Enable workflow in Actions tab
3. Monitor runs and download artifacts as needed

For detailed setup instructions, see: [`../.github/workflows/DEPLOYMENT.md`](../.github/workflows/DEPLOYMENT.md)

## Health Logic Definitions

| Status      | AI Evaluation (Qualitative)                                            | Static Checks (Quantitative)                                              |
| ----------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Healthy** | Description is clear, tags are relevant, and category matches content. | License present; `data_updated_at` matches expected frequency.            |
| **Warning** | Description is too short or tags are generic.                          | Missing contact email or attribution link; update is slightly late.       |
| **Fail**    | AI cannot determine what the data is from the metadata provided.       | No license; update is >2x the expected frequency; no column descriptions. |

---

## Evaluation Schema

```sql
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,         -- Links to ODP_datasets.dataset_id
    evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- AI metadata scoring
    description_score REAL,            -- {1,2,3,4,5}
    description_feedback TEXT,         -- qualitative feedback
    description_suggestion TEXT,       -- tip for improvement

    tag_score REAL,                    -- {1,2,3,4,5}
    tag_feedback TEXT,
    tag_suggestion TEXT,

    -- calculated flags / indicators
    description_exists INTEGER,        -- 0/1
    tags_count_score INTEGER,               -- 0/1
    license_exists INTEGER,            -- 0/1
    department_exists INTEGER,         -- 0/1
    category_exists INTEGER,           -- 0/1
    days_overdue INTEGER,              -- number of days update is late

    freshness_score REAL,              -- derived freshness metric
    overall_health_score REAL,         -- aggregated 0.0-1.0
    overall_health_label TEXT,         -- 'good','fair','poor','critical'

    scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dataset_id) REFERENCES ODP_datasets (dataset_id)
);

```

---

## ODP Datasets Schema

```sql
CREATE TABLE datasets (
-- Internal Primary Key
id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- ODP Identifiers
    dataset_id TEXT UNIQUE NOT NULL, -- mapping to resource.id
    title TEXT,                      -- mapping to resource.name

    -- Metadata & Contact
    contact_email TEXT,              -- mapping to resource.contact_email
    domain TEXT,                     -- mapping to metadata.domain
    permalink TEXT,                  -- mapping to permalink
    license TEXT,                    -- (Not in JSON, but reserved for your schema)
    category TEXT,                   -- mapping to classification.domain_category

    -- Timestamps
    created_at DATETIME,             -- mapping to resource.createdAt
    data_updated_at DATETIME,        -- mapping to resource.data_updated_at

    -- Metrics
    download_count INTEGER,          -- mapping to resource.download_count
    page_views_total INTEGER,        -- mapping to resource.page_views.page_views_total

    -- Complex/Array Data (Stored as JSON Text)
    column_descriptions TEXT,        -- mapping to resource.columns_description
    tags TEXT,                       -- mapping to classification.domain_tags

    -- Pipeline State Tracking
    last_evaluated_at DATETIME DEFAULT NULL

);

-- Indexing for your AI Pipeline check
CREATE INDEX idx_updates ON datasets (data_updated_at, last_evaluated_at);
```

---

## Execution Workflow

### Step 1: Ingest

The script hits the API. If `resource.id` exists, it updates the record. If the `data_updated_at` in the API is newer than what we have in `ODP_datasets`, we reset `evaluated_at` to `NULL` to trigger a re-evaluation.

### Step 2: Evaluate

The evaluator runs a query:

```sql
SELECT * FROM ODP_datasets
WHERE evaluated_at IS NULL
OR data_updated_at > evaluated_at;

```

For each result:

1. **Static Logic:** Calculate if the update is late based on the "Annually/Daily" string in the metadata.
2. **AI Logic:** Send `name`, `description`, `tags`, and `column_names` to the LLM. Ask it to score clarity on a scale of 1-10.
3. **Write:** Save results to `evaluations` and update the `evaluated_at` timestamp in `ODP_datasets`.

### Step 3: Streamlit

Streamlit joins the tables to show the most recent evaluation for every dataset:

```sql
SELECT * FROM ODP_datasets d
JOIN evaluations e ON d.dataset_id = e.dataset_id
WHERE e.id = (SELECT MAX(id) FROM evaluations WHERE dataset_id = d.dataset_id);

```

### Step 4: Publish

After evaluation completes the `publish.py` script can be run automatically via the
pipeline orchestrator or executed manually. It exports the `ODP_datasets` table
into a Parquet file and uploads it to a configured HuggingFace dataset
repository using credentials stored in environment variables (`HF_TOKEN`,
`HF_REPO`).
