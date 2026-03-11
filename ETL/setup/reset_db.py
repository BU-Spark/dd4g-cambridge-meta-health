"""
Utility script for resetting the pipeline database during development.

Removes the SQLite file so that a fresh `ingest.py` run will create a new
empty database. Safe to run multiple times.

Usage:
    python setup/reset_db.py
"""

import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cambridge_metadata.db"


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Deleted database file: {DB_PATH}")
    else:
        print(f"Database does not exist at {DB_PATH}; nothing to do.")


if __name__ == "__main__":
    main()
