"""
Cambridge Open Data Portal - Data Ingestion Pipeline

This script fetches dataset metadata from the Cambridge Open Data Portal
via the Socrata Discovery API and stores it in a SQLite database.

Database: ETL/data/cambridge_metadata.db
Tables Created: ODP_datasets (primary storage for dataset metadata)

Usage:
    python ingest.py              # Run standalone
    python pipeline.py            # Run as part of full pipeline (ingest + evaluate)

The script handles:
- Paginated API fetching
- Intelligent upsert (resets evaluation status when data changes)
- JSON field storage for arrays
- Database initialization (creates tables and indexes)
"""

import requests
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# ────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────

# Database path relative to this script's location
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_metadata.db")

# Socrata Discovery API configuration
API_URL = "https://api.us.socrata.com/api/catalog/v1"
API_PARAMS_BASE = {
    "domains": "data.cambridgema.gov",
    "only": "datasets",
    "limit": 100
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# DATABASE INITIALIZATION
# ────────────────────────────────────────────────────────────

def init_database() -> None:
    """
    Initialize SQLite database with schema for ingestion.

    Creates:
    - data/ directory if it doesn't exist
    - ODP_datasets table for storing dataset metadata
    - Indexes for query optimization

    Note: The evaluations table is created by evaluate.py

    This function is idempotent - safe to run multiple times.
    """
    # Create data directory if it doesn't exist
    data_dir = os.path.dirname(DB_PATH)
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"Data directory: {data_dir}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ─── ODP_datasets Table (Primary Storage) ───
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ODP_datasets (
            -- Primary Key
            dataset_id TEXT PRIMARY KEY,              -- resource.id

            -- Basic Metadata
            title TEXT NOT NULL,                      -- resource.name
            description TEXT,                         -- resource.description
            dataset_type TEXT,                        -- resource.type

            -- Contact & Attribution
            department TEXT,                          -- resource.attribution
            contact_email TEXT,                       -- resource.contact_email
            attribution_link TEXT,                    -- resource.attribution_link

            -- Domain & Licensing
            domain TEXT,                              -- metadata.domain
            permalink TEXT,                           -- permalink
            license TEXT,                             -- metadata.license

            -- Categorization
            category TEXT,                            -- classification.domain_category
            tags TEXT,                                -- classification.domain_tags (JSON array)

            -- Timestamps (ISO 8601 TEXT format)
            created_at TEXT,                          -- resource.createdAt
            updated_at TEXT,                          -- resource.updatedAt
            data_updated_at TEXT,                     -- resource.data_updated_at

            -- Usage Metrics
            download_count INTEGER DEFAULT 0,
            page_views_total INTEGER DEFAULT 0,
            page_views_last_week INTEGER DEFAULT 0,
            page_views_last_month INTEGER DEFAULT 0,

            -- Column Schema (JSON arrays)
            columns_names TEXT,                       -- resource.columns_name
            columns_field_names TEXT,                 -- resource.columns_field_name
            columns_descriptions TEXT,                -- resource.columns_description
            columns_datatypes TEXT,                   -- resource.columns_datatype

            -- Maintenance Info (extracted from domain_metadata)
            update_frequency TEXT,                    -- key: "Maintenance-Plan_Estimated-Update-Frequency"
            maintenance_plan_details TEXT,            -- key: "Maintenance-Plan_Maintenance-Plan-Details"
            specific_limitations TEXT,                -- key: "Specific-Limitations_Limitations"
            domain_metadata_full TEXT,                -- Complete domain_metadata JSON

            -- Pipeline State (CRITICAL for evaluate.py integration)
            last_evaluated_at TEXT DEFAULT NULL,      -- Timestamp of last evaluation (NULL = needs evaluation)
            fetched_at TEXT NOT NULL,                 -- Timestamp of API fetch
            previous_data_updated_at TEXT             -- Previous data_updated_at for change tracking
        )
    """)

    # ─── Indexes for Query Optimization ───

    # Index for evaluation pipeline: find datasets that need re-evaluation
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evaluation_queue
        ON ODP_datasets (last_evaluated_at, data_updated_at)
    """)

    # Index for datasets that have never been evaluated
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_unevaluated
        ON ODP_datasets (last_evaluated_at)
        WHERE last_evaluated_at IS NULL
    """)

    # Index for filtering by category (useful for Streamlit dashboard)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_category
        ON ODP_datasets (category)
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# ────────────────────────────────────────────────────────────
# API FETCHING
# ────────────────────────────────────────────────────────────

def fetch_all_datasets() -> List[Dict[str, Any]]:
    """
    Fetch all datasets from Cambridge Open Data Portal via Socrata API.

    Handles pagination automatically (100 records per request).
    Saves raw JSON response to data/raw_data.json for debugging.

    Returns:
        List of dataset dictionaries (API "results" array)

    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    all_results = []
    params = API_PARAMS_BASE.copy()
    params["offset"] = 0

    try:
        while True:
            logger.info(f"Fetching datasets at offset {params['offset']}...")

            response = requests.get(API_URL, params=params, timeout=30)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes

            data = response.json()
            results = data.get("results", [])

            if not results:
                break

            all_results.extend(results)
            logger.info(f"Fetched {len(all_results)} datasets so far...")

            params["offset"] += 100

        # Save raw API response for debugging
        raw_data_path = os.path.join(os.path.dirname(DB_PATH), "raw_data.json")
        with open(raw_data_path, "w") as f:
            json.dump(all_results, f, indent=2)
        logger.info(f"Raw data saved to {raw_data_path}")

        return all_results

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise

# ────────────────────────────────────────────────────────────
# DATA PARSING & TRANSFORMATION
# ────────────────────────────────────────────────────────────

def extract_domain_metadata_field(
    domain_metadata: List[Dict[str, str]],
    key: str
) -> Optional[str]:
    """
    Extract a specific field from classification.domain_metadata array.

    The domain_metadata is an array of {key: ..., value: ...} objects.
    Common keys include:
    - "Maintenance-Plan_Estimated-Update-Frequency"
    - "Maintenance-Plan_Maintenance-Plan-Details"
    - "Specific-Limitations_Limitations"

    Args:
        domain_metadata: The classification.domain_metadata array
        key: The key to search for

    Returns:
        The value if found, None otherwise
    """
    if not domain_metadata:
        return None

    for item in domain_metadata:
        if item.get("key") == key:
            return item.get("value")

    return None

def parse_dataset(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a single API result item into a flat dictionary for database insertion.

    This function maps the nested API structure to our flat database schema:
    - resource.* → basic metadata fields
    - classification.* → categorization fields
    - metadata.* → domain and licensing

    Args:
        item: Single item from API results array

    Returns:
        Dictionary with keys matching ODP_datasets table columns
    """
    resource = item.get("resource", {})
    classification = item.get("classification", {})
    metadata = item.get("metadata", {})

    # Extract domain_metadata array for specific fields
    domain_metadata = classification.get("domain_metadata", [])

    # Safely extract page_views (can be null)
    page_views = resource.get("page_views", {}) or {}

    # Build record with defensive extraction (handle None/missing values)
    record = {
        # Primary key
        "dataset_id": resource.get("id"),

        # Basic metadata
        "title": resource.get("name"),
        "description": resource.get("description"),
        "dataset_type": resource.get("type"),

        # Contact & attribution
        "department": resource.get("attribution"),
        "contact_email": resource.get("contact_email"),
        "attribution_link": resource.get("attribution_link"),

        # Domain & licensing
        "domain": metadata.get("domain"),
        "permalink": item.get("permalink"),
        "license": metadata.get("license"),

        # Categorization
        "category": classification.get("domain_category"),
        "tags": json.dumps(classification.get("domain_tags", [])),

        # Timestamps (already in ISO 8601 format from API)
        "created_at": resource.get("createdAt"),
        "updated_at": resource.get("updatedAt"),
        "data_updated_at": resource.get("data_updated_at"),

        # Usage metrics (handle None by defaulting to 0)
        "download_count": resource.get("download_count", 0) or 0,
        "page_views_total": page_views.get("page_views_total", 0) or 0,
        "page_views_last_week": page_views.get("page_views_last_week", 0) or 0,
        "page_views_last_month": page_views.get("page_views_last_month", 0) or 0,

        # Column schema (store as JSON arrays)
        "columns_names": json.dumps(resource.get("columns_name", [])),
        "columns_field_names": json.dumps(resource.get("columns_field_name", [])),
        "columns_descriptions": json.dumps(resource.get("columns_description", [])),
        "columns_datatypes": json.dumps(resource.get("columns_datatype", [])),

        # Maintenance info (extracted from domain_metadata)
        "update_frequency": extract_domain_metadata_field(
            domain_metadata,
            "Maintenance-Plan_Estimated-Update-Frequency"
        ),
        "maintenance_plan_details": extract_domain_metadata_field(
            domain_metadata,
            "Maintenance-Plan_Maintenance-Plan-Details"
        ),
        "specific_limitations": extract_domain_metadata_field(
            domain_metadata,
            "Specific-Limitations_Limitations"
        ),
        "domain_metadata_full": json.dumps(domain_metadata),

        # Pipeline state
        "fetched_at": datetime.utcnow().isoformat(),
        "last_evaluated_at": None,  # Will be set by upsert logic
        "previous_data_updated_at": None  # Will be set by upsert logic
    }

    return record

# ────────────────────────────────────────────────────────────
# DATABASE OPERATIONS
# ────────────────────────────────────────────────────────────

def upsert_datasets(records: List[Dict[str, Any]]) -> None:
    """
    Insert or update datasets in the database.

    INTELLIGENT UPSERT LOGIC:
    1. If dataset_id exists in database:
       a. Check if data_updated_at has changed
       b. If changed: reset last_evaluated_at to NULL (triggers re-evaluation)
       c. If unchanged: preserve existing last_evaluated_at
    2. If dataset_id is new:
       a. Insert with last_evaluated_at = NULL (needs evaluation)

    This ensures evaluate.py will process:
    - All new datasets
    - All datasets where the data has been refreshed

    Args:
        records: List of parsed dataset dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    new_count = 0
    updated_count = 0
    data_refreshed_count = 0

    for record in records:
        dataset_id = record["dataset_id"]
        new_data_updated_at = record["data_updated_at"]

        # Check if dataset already exists
        cursor.execute(
            "SELECT data_updated_at, last_evaluated_at FROM ODP_datasets WHERE dataset_id = ?",
            (dataset_id,)
        )
        existing = cursor.fetchone()

        if existing:
            old_data_updated_at, old_last_evaluated_at = existing

            # Check if the actual data has been refreshed
            if new_data_updated_at != old_data_updated_at:
                # Data changed - trigger re-evaluation
                record["last_evaluated_at"] = None
                record["previous_data_updated_at"] = old_data_updated_at
                data_refreshed_count += 1
                logger.debug(f"Data refreshed for {dataset_id}: {old_data_updated_at} → {new_data_updated_at}")
            else:
                # Data unchanged - preserve evaluation timestamp
                record["last_evaluated_at"] = old_last_evaluated_at
                record["previous_data_updated_at"] = old_data_updated_at

            updated_count += 1
        else:
            # New dataset - needs evaluation
            record["last_evaluated_at"] = None
            record["previous_data_updated_at"] = None
            new_count += 1

        # Perform upsert
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?" for _ in record])

        cursor.execute(f"""
            INSERT OR REPLACE INTO ODP_datasets ({columns})
            VALUES ({placeholders})
        """, tuple(record.values()))

    conn.commit()
    conn.close()

    logger.info(f"Upsert complete: {new_count} new, {updated_count} updated, {data_refreshed_count} data refreshed")

# ────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ────────────────────────────────────────────────────────────

def main() -> None:
    """
    Main data ingestion execution.

    This script is typically called by pipeline.py as the first step
    in the ETL pipeline, but can also be run standalone.

    Steps:
    1. Initialize database (create tables if needed)
    2. Fetch all datasets from Socrata API
    3. Parse datasets into database format
    4. Upsert into database with intelligent re-evaluation logic
    5. Print summary statistics

    Pipeline Integration:
    - After ingest.py completes, evaluate.py processes datasets where
      last_evaluated_at IS NULL (new or data-refreshed datasets)
    - Use pipeline.py to run the complete workflow: ingest → evaluate

    Usage:
        python ingest.py              # Run standalone
        python pipeline.py            # Run as part of full pipeline
    """
    logger.info("=" * 60)
    logger.info("Cambridge Open Data Portal - Ingestion Pipeline")
    logger.info("=" * 60)

    # Step 1: Initialize database
    logger.info("Step 1: Initializing database...")
    init_database()

    # Step 2: Fetch from API
    logger.info("Step 2: Fetching datasets from Socrata API...")
    all_results = fetch_all_datasets()
    logger.info(f"Successfully fetched {len(all_results)} datasets")

    # Step 3: Parse datasets
    logger.info("Step 3: Parsing datasets...")
    records = [parse_dataset(item) for item in all_results]
    logger.info(f"Parsed {len(records)} records")

    # Step 4: Upsert into database
    logger.info("Step 4: Upserting into database...")
    upsert_datasets(records)

    # Step 5: Print summary statistics
    logger.info("=" * 60)
    logger.info("Summary Statistics")
    logger.info("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total datasets
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets")
    total = cursor.fetchone()[0]
    logger.info(f"Total datasets in database: {total}")

    # Datasets needing evaluation
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets WHERE last_evaluated_at IS NULL")
    needs_eval = cursor.fetchone()[0]
    logger.info(f"Datasets needing evaluation: {needs_eval}")

    # Datasets by category
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM ODP_datasets
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
        LIMIT 5
    """)
    logger.info("\nTop 5 categories:")
    for category, count in cursor.fetchall():
        logger.info(f"  {category}: {count}")

    # Update frequency distribution
    cursor.execute("""
        SELECT update_frequency, COUNT(*) as count
        FROM ODP_datasets
        WHERE update_frequency IS NOT NULL
        GROUP BY update_frequency
        ORDER BY count DESC
        LIMIT 5
    """)
    logger.info("\nUpdate frequency distribution:")
    for freq, count in cursor.fetchall():
        logger.info(f"  {freq}: {count}")

    conn.close()

    logger.info("=" * 60)
    logger.info(f"Database: {DB_PATH}")
    logger.info("Ingestion complete!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
