import requests
import pandas as pd
import json
import sqlite3
import os
from datetime import datetime

BASE_DIR = "/Users/shravani/cambridge_health_dashboard"
DB_PATH  = f"{BASE_DIR}/data/cambridge_metadata.db"

def fetch_from_socrata():
    url = "https://api.us.socrata.com/api/catalog/v1"
    params = {
        "domains": "data.cambridgema.gov",
        "only": "datasets",
        "limit": 100,
        "offset": 0
    }

    all_results = []
    while True:
        response = requests.get(url, params=params)
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        params["offset"] += 100
        print(f"Fetched {len(all_results)} datasets so far...")


    with open(f"{BASE_DIR}/data/raw_data.json", "w") as f:
        json.dump(all_results, f)

    records = []
    for item in all_results:
        resource       = item.get("resource", {})
        classification = item.get("classification", {})
        metadata       = item.get("metadata", {})


        tags = classification.get("domain_tags", [])


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
            "id":               resource.get("id"),
            "name":             resource.get("name"),
            "description":      resource.get("description"),
            "department":       resource.get("attribution"),
            "type":             resource.get("type"),
            "createdAt":        resource.get("createdAt"),
            "updatedAt":        resource.get("updatedAt"),
            "dataUpdatedAt":    resource.get("data_updated_at"),
            "tags":             json.dumps(tags),
            "category":         category,
            "license":          metadata.get("license"),
            "updateFrequency":  update_frequency,
            "pageViewsTotal":   resource.get("page_views", {}).get("page_views_total"),
            "columns":          json.dumps(columns),
            "col_names":        json.dumps(col_names),
            "col_descriptions": json.dumps(col_desc),
            "fetched_at":       datetime.utcnow().isoformat(),
        })

    return pd.DataFrame(records)


def save_to_db(df):
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id                TEXT PRIMARY KEY,
            name              TEXT,
            description       TEXT,
            department        TEXT,
            type              TEXT,
            createdAt         TEXT,
            updatedAt         TEXT,
            dataUpdatedAt     TEXT,
            tags              TEXT,
            category          TEXT,
            license           TEXT,
            updateFrequency   TEXT,
            pageViewsTotal    INTEGER,
            columns           TEXT,
            col_names         TEXT,
            col_descriptions  TEXT,
            fetched_at        TEXT
        )
    """)

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO datasets VALUES (
                :id, :name, :description, :department, :type,
                :createdAt, :updatedAt, :dataUpdatedAt, :tags,
                :category, :license, :updateFrequency, :pageViewsTotal,
                :columns, :col_names, :col_descriptions, :fetched_at
            )
        """, dict(row))

    conn.commit()
    conn.close()
    print(f"Saved {len(df)} datasets to SQLite.")


if __name__ == "__main__":

    os.makedirs(f"{BASE_DIR}/data", exist_ok=True)

    df = fetch_from_socrata()
    save_to_db(df)


    df.to_csv(f"{BASE_DIR}/data/datasets.csv", index=False)

    print(f"\nDone! {len(df)} datasets saved.")
    print(f"DB  → {DB_PATH}")
    print(f"CSV → {BASE_DIR}/data/datasets.csv")
    print(df[["name", "tags", "updateFrequency", "col_descriptions"]].head())
