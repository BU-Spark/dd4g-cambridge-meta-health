import requests
import pandas as pd
import json
import sqlite3
import os
import uuid
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "cambridge_metadata.db")

def make_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def fetch_from_socrata() -> pd.DataFrame:
    session = make_session()
    url     = "https://api.us.socrata.com/api/catalog/v1"
    params  = {"domains": "data.cambridgema.gov", "only": "datasets", "limit": 100, "offset": 0}
    all_results = []

    while True:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data    = response.json()
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        params["offset"] += 100
        print(f"  Fetched {len(all_results)} datasets...")

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(os.path.join(BASE_DIR, "data", "raw_data.json"), "w") as f:
        json.dump(all_results, f, indent=2)

    records = []
    for item in all_results:
        resource       = item.get("resource", {})
        classification = item.get("classification", {})
        metadata       = item.get("metadata", {})

        tags     = classification.get("domain_tags", [])
        category = classification.get("domain_category")

        update_frequency = next(
            (entry["value"] for entry in classification.get("domain_metadata", [])
             if entry["key"] == "Maintenance-Plan_Estimated-Update-Frequency"),
            None
        )

        columns   = resource.get("columns_field_name", [])
        col_names = resource.get("columns_name", [])
        col_desc  = resource.get("columns_description", [])

        records.append({
            "id":              resource.get("id"),
            "name":            resource.get("name"),
            "description":     resource.get("description"),
            "department":      resource.get("attribution"),
            "type":            resource.get("type"),
            "createdAt":       resource.get("createdAt"),
            "updatedAt":       resource.get("updatedAt"),
            "dataUpdatedAt":   resource.get("data_updated_at"),
            "tags":            json.dumps(tags),
            "category":        category,
            "license":         metadata.get("license"),
            "updateFrequency": update_frequency,
            "pageViewsTotal":  resource.get("page_views", {}).get("page_views_total"),
            "columns":         json.dumps(columns),
            "col_names":       json.dumps(col_names),
            "col_descriptions":json.dumps(col_desc),
            "fetched_at":      datetime.now(timezone.utc).isoformat(),
        })

    return pd.DataFrame(records)

def save_to_db(df: pd.DataFrame, run_id: str):
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            department TEXT,
            type TEXT,
            createdAt TEXT,
            updatedAt TEXT,
            dataUpdatedAt TEXT,
            tags TEXT,
            category TEXT,
            license TEXT,
            updateFrequency TEXT,
            pageViewsTotal INTEGER,
            columns TEXT,
            col_names TEXT,
            col_descriptions TEXT,
            fetched_at TEXT,
            fetched_run_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT,
            finished_at TEXT,
            datasets_fetched INTEGER,
            datasets_scored INTEGER,
            datasets_llm_enriched INTEGER,
            status TEXT
        )
    """)

    for _, row in df.iterrows():
        row_dict = dict(row)
        row_dict["fetched_run_id"] = run_id
        cursor.execute("""
            INSERT OR REPLACE INTO datasets VALUES (
                :id, :name, :description, :department, :type,
                :createdAt, :updatedAt, :dataUpdatedAt, :tags,
                :category, :license, :updateFrequency, :pageViewsTotal,
                :columns, :col_names, :col_descriptions, :fetched_at, :fetched_run_id
            )
        """, row_dict)

    conn.commit()
    conn.close()
    print(f"  Saved {len(df)} datasets to SQLite.")

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    run_id = str(uuid.uuid4())
    df = fetch_from_socrata()
    save_to_db(df, run_id)
    df.to_csv(os.path.join(BASE_DIR, "data", "datasets.csv"), index=False)
    print(f"\nDone! {len(df)} datasets saved.")
    print(f"DB  -> {DB_PATH}")
