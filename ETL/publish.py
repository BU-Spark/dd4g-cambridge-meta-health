"""
Publish pipeline data to a HuggingFace dataset repository.

Exports the contents of the SQLite database as a Parquet file and pushes
it to a user-specified HuggingFace dataset.

Usage:
    python publish.py                       # uses environment variables
    HF_TOKEN and HF_REPO must be set (or edit the placeholders below)

The script is intentionally minimal; it is safe to run repeatedly.
"""

import os
import sqlite3
import pandas as pd

# optional huggingface_hub import; library must be installed in the environment
try:
    from huggingface_hub import HfApi
except ImportError:  # pragma: no cover
    HfApi = None

# --- configuration (override with env or edit directly) ---
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_metadata.db")
EXPORT_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_metadata.parquet")

# fill these via environment or hardcode for your repo
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_REPO = os.getenv("HF_REPO", "username/dataset-name")  # e.g. "user/cambridge-odp"

# ---------------------------------------------------------------------------

def export_to_parquet(db_path: str, output_path: str) -> None:
    """Read the database and write the ODP_datasets table to a parquet file."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM ODP_datasets", conn)
    conn.close()

    df.to_parquet(output_path, index=False)
    print(f"Exported {len(df)} rows to {output_path}")


def publish_to_hf(export_path: str, repo: str, token: str) -> None:
    """Push the parquet file to the specified HuggingFace dataset repo."""
    if HfApi is None:
        raise ImportError("huggingface_hub is not installed; install with `pip install huggingface-hub`")

    if not token:
        raise ValueError("HF_TOKEN is not set; cannot authenticate")

    api = HfApi()

    # create repository if it doesn't exist (harmless if it does)
    try:
        api.create_repo(repo_id=repo, repo_type="dataset", token=token, exist_ok=True)
        print(f"Ensured dataset repo exists: {repo}")
    except Exception as e:  # pragma: no cover
        print(f"Warning: could not create/check repo {repo}: {e}")

    # upload file
    api.upload_file(
        path_or_fileobj=export_path,
        path_in_repo=os.path.basename(export_path),
        repo_id=repo,
        repo_type="dataset",
        token=token,
        create_pr= False
    )
    print(f"Published {export_path} to HuggingFace dataset {repo}")


if __name__ == "__main__":
    print("Starting publish step...")
    export_to_parquet(DB_PATH, EXPORT_PATH)
    # only attempt publish if HF_TOKEN is provided
    if HF_TOKEN and HF_REPO:
        publish_to_hf(EXPORT_PATH, HF_REPO, HF_TOKEN)
    else:
        print("HF_TOKEN or HF_REPO not configured; skipping upload.")
