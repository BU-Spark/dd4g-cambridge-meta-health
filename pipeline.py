"""
Pipeline orchestrator — runs fetch -> score -> LLM enrichment in sequence.
Called by GitHub Actions daily cron or manually: python pipeline.py
"""
import os
import uuid
import sqlite3
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

BASE_DIR = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "cambridge_metadata.db")


def log_run(run_id, started_at, fetched, scored, enriched, status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT,
            datasets_fetched INTEGER, datasets_scored INTEGER,
            datasets_llm_enriched INTEGER, status TEXT
        )
    """)
    conn.execute("""
        INSERT OR REPLACE INTO pipeline_runs VALUES (?,?,?,?,?,?,?)
    """, (run_id, started_at, datetime.now(timezone.utc).isoformat(),
          fetched, scored, enriched, status))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    from fetch_data import fetch_from_socrata, save_to_db
    from scoring_llm.score_and_flag import score_datasets
    from scoring_llm.llm_enrich import run_llm_enrichment

    run_id     = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    fetched = scored = enriched = 0

    try:
        logging.info("Step 1: Fetching metadata from Socrata...")
        df      = fetch_from_socrata()
        save_to_db(df, run_id)
        fetched = len(df)

        logging.info("Step 2: Scoring and flagging datasets...")
        scored = score_datasets()

        logging.info("Step 3: LLM enrichment (Gemini 1.5 Flash)...")
        enriched = run_llm_enrichment(only_low_scores=True, score_threshold=40.0)

        log_run(run_id, started_at, fetched, scored, enriched, "success")
        logging.info(f"Pipeline complete — {fetched} fetched, {scored} scored, {enriched} enriched.")

    except Exception as e:
        log_run(run_id, started_at, fetched, scored, enriched, f"failed: {str(e)[:200]}")
        logging.error(f"Pipeline failed: {e}")
        raise
