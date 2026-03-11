"""
Pushes the updated SQLite database to the HuggingFace Space after each pipeline run.
Requires HF_TOKEN env var with write access to the Space repo.
Update SPACE_REPO to your actual HuggingFace Space name.
"""
import os
from huggingface_hub import HfApi

HF_TOKEN   = os.environ["HF_TOKEN"]
SPACE_REPO = "spark-dd4g/cambridge-health-dashboard"
BASE_DIR   = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_LOCAL   = os.path.join(BASE_DIR, "data", "cambridge_metadata.db")

api = HfApi(token=HF_TOKEN)
api.upload_file(
    path_or_fileobj=DB_LOCAL,
    path_in_repo="data/cambridge_metadata.db",
    repo_id=SPACE_REPO,
    repo_type="space",
    commit_message="Auto-refresh: daily metadata pipeline update"
)
print(f"Database pushed to HuggingFace Space: {SPACE_REPO}")
