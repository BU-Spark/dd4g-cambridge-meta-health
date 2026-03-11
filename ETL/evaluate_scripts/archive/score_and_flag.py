import sqlite3
import pandas as pd
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "cambridge_metadata.db")

FREQUENCY_THRESHOLDS = {
    "daily":       1,
    "weekly":      7,
    "biweekly":    14,
    "monthly":     30,
    "quarterly":   90,
    "annually":    365,
    "yearly":      365,
    "annual":      365,
    "as needed":   None,
    "historical":  None,
    "not planned": None,
    "never":       None,
}

def compute_staleness(row) -> dict:
    """Dynamically evaluate staleness relative to dataset's own update frequency."""
    freq = (row.get("updateFrequency") or "").strip().lower()
    threshold_days = FREQUENCY_THRESHOLDS.get(freq, 730)

    if threshold_days is None:
        return {"is_stale": 0, "days_overdue": 0, "freshness_score": 100.0}

    try:
        last_updated = row.get("dataUpdatedAt") or row.get("updatedAt")
        if not last_updated:
            return {"is_stale": 1, "days_overdue": -1, "freshness_score": 0.0}

        updated_dt   = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
        days_since   = (datetime.now(timezone.utc) - updated_dt).days
        days_overdue = max(0, days_since - threshold_days)
        is_stale     = 1 if days_overdue > 0 else 0

        overdue_ratio = days_since / threshold_days
        if overdue_ratio <= 1.0:
            freshness_score = 100.0
        elif overdue_ratio <= 2.0:
            freshness_score = 50.0
        else:
            freshness_score = 0.0

        return {"is_stale": is_stale, "days_overdue": days_overdue, "freshness_score": freshness_score}

    except Exception:
        return {"is_stale": 1, "days_overdue": -1, "freshness_score": 0.0}


def compute_tag_score(tags: list) -> float:
    n = len(tags)
    if n == 0:   return 0.0
    elif n <= 2: return 33.0
    elif n <= 4: return 67.0
    else:        return 100.0


def compute_col_metadata_score(col_descriptions: list) -> float:
    if not col_descriptions:
        return 0.0
    filled = sum(1 for d in col_descriptions if d and str(d).strip())
    return 100.0 if (filled / len(col_descriptions)) >= 0.5 else 0.0


def health_band(score: float) -> str:
    if score >= 80: return "Good"
    elif score >= 60: return "Fair"
    elif score >= 40: return "Poor"
    else: return "Critical"


def create_health_flags_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_flags (
            id TEXT PRIMARY KEY,
            missing_description INTEGER,
            missing_tags INTEGER,
            missing_license INTEGER,
            missing_department INTEGER,
            missing_category INTEGER,
            is_stale INTEGER,
            days_overdue INTEGER,
            desc_score REAL,
            tag_score REAL,
            license_score REAL,
            dept_score REAL,
            category_score REAL,
            freshness_score REAL,
            col_metadata_score REAL,
            health_score REAL,
            health_band TEXT,
            scored_at TEXT
        )
    """)
    conn.commit()


def score_datasets():
    """
    Scoring rubric (100 pts total):
      Description quality  25%  (heuristic pre-LLM; LLM refines after llm_enrich.py)
      Tag quality          15%  (0/33/67/100 based on tag count)
      License presence     15%  (binary)
      Department           10%  (binary)
      Category             10%  (binary)
      Freshness            20%  (dynamic per updateFrequency)
      Column metadata       5%  (>=50% columns described)
    """
    conn = sqlite3.connect(DB_PATH)
    create_health_flags_table(conn)
    df   = pd.read_sql("SELECT * FROM datasets", conn)

    WEIGHTS = {
        "desc":      0.25,
        "tags":      0.15,
        "license":   0.15,
        "dept":      0.10,
        "category":  0.10,
        "freshness": 0.20,
        "col_meta":  0.05,
    }

    records = []
    for _, row in df.iterrows():
        tags     = json.loads(row["tags"]) if row["tags"] else []
        col_desc = json.loads(row["col_descriptions"]) if row["col_descriptions"] else []

        missing_desc = 0 if (pd.notna(row["description"]) and str(row["description"]).strip()) else 1
        missing_tags = 0 if len(tags) > 0 else 1
        missing_lic  = 0 if (pd.notna(row["license"]) and str(row["license"]).strip()) else 1
        missing_dept = 0 if (pd.notna(row["department"]) and str(row["department"]).strip()) else 1
        missing_cat  = 0 if (pd.notna(row["category"]) and str(row["category"]).strip()) else 1

        desc_text = str(row["description"]).strip() if pd.notna(row["description"]) else ""
        if len(desc_text) == 0:      desc_score_raw = 0.0
        elif len(desc_text) < 30:    desc_score_raw = 25.0
        elif len(desc_text) < 100:   desc_score_raw = 50.0
        else:                        desc_score_raw = 75.0

        tag_score_raw      = compute_tag_score(tags)
        license_score_raw  = 0.0 if missing_lic  else 100.0
        dept_score_raw     = 0.0 if missing_dept else 100.0
        category_score_raw = 0.0 if missing_cat  else 100.0
        staleness          = compute_staleness(row)
        freshness_raw      = staleness["freshness_score"]
        col_meta_raw       = compute_col_metadata_score(col_desc)

        health_score = round(
            WEIGHTS["desc"]     * desc_score_raw +
            WEIGHTS["tags"]     * tag_score_raw +
            WEIGHTS["license"]  * license_score_raw +
            WEIGHTS["dept"]     * dept_score_raw +
            WEIGHTS["category"] * category_score_raw +
            WEIGHTS["freshness"]* freshness_raw +
            WEIGHTS["col_meta"] * col_meta_raw,
            1
        )

        records.append({
            "id":                 row["id"],
            "missing_description":missing_desc,
            "missing_tags":       missing_tags,
            "missing_license":    missing_lic,
            "missing_department": missing_dept,
            "missing_category":   missing_cat,
            "is_stale":           staleness["is_stale"],
            "days_overdue":       staleness["days_overdue"],
            "desc_score":         desc_score_raw,
            "tag_score":          tag_score_raw,
            "license_score":      license_score_raw,
            "dept_score":         dept_score_raw,
            "category_score":     category_score_raw,
            "freshness_score":    freshness_raw,
            "col_metadata_score": col_meta_raw,
            "health_score":       health_score,
            "health_band":        health_band(health_score),
            "scored_at":          datetime.now(timezone.utc).isoformat(),
        })

    flags_df = pd.DataFrame(records)
    for _, row in flags_df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO health_flags VALUES (
                :id, :missing_description, :missing_tags, :missing_license,
                :missing_department, :missing_category,
                :is_stale, :days_overdue,
                :desc_score, :tag_score, :license_score,
                :dept_score, :category_score, :freshness_score, :col_metadata_score,
                :health_score, :health_band, :scored_at
            )
        """, dict(row))

    conn.commit()
    conn.close()
    print(f"  Scored {len(records)} datasets.")
    return len(records)


if __name__ == "__main__":
    score_datasets()
