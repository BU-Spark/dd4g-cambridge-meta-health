"""
Cambridge Open Data Portal - Main Pipeline Orchestrator

This script orchestrates the complete ETL pipeline:
1. Ingest: Fetch latest data from Socrata API (ingest.py)
2. Evaluate: Run health checks on datasets (evaluate.py)

Usage:
    python pipeline.py                      # Run full pipeline (ingest + evaluate)
    python pipeline.py --ingest-only        # Only fetch data from API
    python pipeline.py --evaluate-only      # Only run evaluations
    python pipeline.py --dry-run            # Preview without saving
    python pipeline.py --limit 10           # Evaluate only 10 datasets

The pipeline provides:
- Sequential execution of ingest and evaluate steps
- Flexible step selection via command-line flags
- Summary statistics before and after execution
- Error handling and graceful failures
"""

import subprocess
import logging
import argparse
import sys
import time
from datetime import datetime
import sqlite3
import os

# ────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_metadata.db")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────

def run_script(script_name: str, args: list = None) -> bool:
    """
    Run a Python script as a subprocess.

    Args:
        script_name: Name of the script to run (e.g., 'ingest.py')
        args: Optional list of command-line arguments

    Returns:
        True if script succeeded, False otherwise
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    command = [sys.executable, script_path]

    if args:
        command.extend(args)

    logger.info(f"Running: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=False,  # Let output go to console
            text=True
        )
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Script {script_name} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        logger.error(f"Script not found: {script_path}")
        return False


def get_pipeline_stats() -> dict:
    """
    Get current pipeline statistics from database.

    Returns:
        Dictionary with pipeline metrics:
        - total_datasets: Total number of datasets
        - needs_evaluation: Datasets not yet evaluated
        - evaluated: Datasets that have been evaluated
        - healthy: Count of healthy datasets
        - warning: Count of warning datasets
        - fail: Count of failed datasets
    """
    if not os.path.exists(DB_PATH):
        return {
            'total_datasets': 0,
            'needs_evaluation': 0,
            'evaluated': 0,
            'healthy': 0,
            'warning': 0,
            'fail': 0
        }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total datasets
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets")
    total_datasets = cursor.fetchone()[0]

    # Datasets needing evaluation
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets WHERE last_evaluated_at IS NULL")
    needs_evaluation = cursor.fetchone()[0]

    # Evaluated datasets
    evaluated = total_datasets - needs_evaluation

    # Health status counts from latest evaluations
    cursor.execute("""
        SELECT e.overall_health_status, COUNT(*)
        FROM ODP_datasets d
        JOIN evaluations e ON d.dataset_id = e.dataset_id
        WHERE e.id = (
            SELECT MAX(id)
            FROM evaluations
            WHERE dataset_id = d.dataset_id
        )
        GROUP BY e.overall_health_status
    """)
    health_counts = dict(cursor.fetchall())

    conn.close()

    return {
        'total_datasets': total_datasets,
        'needs_evaluation': needs_evaluation,
        'evaluated': evaluated,
        'healthy': health_counts.get('Healthy', 0),
        'warning': health_counts.get('Warning', 0),
        'fail': health_counts.get('Fail', 0)
    }


def print_summary(stats_before: dict, stats_after: dict, elapsed_time: float):
    """
    Print pipeline execution summary.

    Args:
        stats_before: Statistics before pipeline run
        stats_after: Statistics after pipeline run
        elapsed_time: Total execution time in seconds
    """
    logger.info("=" * 60)
    logger.info("PIPELINE EXECUTION SUMMARY")
    logger.info("=" * 60)

    logger.info(f"Execution time: {elapsed_time:.2f} seconds")
    logger.info("")

    logger.info("Dataset Counts:")
    logger.info(f"  Total datasets: {stats_after['total_datasets']} "
                f"(+{stats_after['total_datasets'] - stats_before['total_datasets']})")
    logger.info(f"  Evaluated: {stats_after['evaluated']} "
                f"(+{stats_after['evaluated'] - stats_before['evaluated']})")
    logger.info(f"  Needs evaluation: {stats_after['needs_evaluation']}")
    logger.info("")

    logger.info("Health Status Distribution:")
    logger.info(f"  Healthy: {stats_after['healthy']} "
                f"(+{stats_after['healthy'] - stats_before['healthy']})")
    logger.info(f"  Warning: {stats_after['warning']} "
                f"(+{stats_after['warning'] - stats_before['warning']})")
    logger.info(f"  Fail: {stats_after['fail']} "
                f"(+{stats_after['fail'] - stats_before['fail']})")

    logger.info("=" * 60)

# ────────────────────────────────────────────────────────────
# COMMAND-LINE INTERFACE
# ────────────────────────────────────────────────────────────

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Cambridge ODP Pipeline Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py                    # Run full pipeline (ingest + evaluate)
  python pipeline.py --ingest-only      # Only fetch data from API
  python pipeline.py --evaluate-only    # Only run evaluations
  python pipeline.py --dry-run          # Preview without saving results
  python pipeline.py --limit 10         # Evaluate only 10 datasets
        """
    )

    # Pipeline stage selection
    parser.add_argument(
        '--ingest-only',
        action='store_true',
        help='Only run ingest.py (fetch data from API)'
    )

    parser.add_argument(
        '--evaluate-only',
        action='store_true',
        help='Only run evaluate.py (skip data fetch)'
    )

    # Evaluation options
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of datasets to evaluate'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview datasets without saving evaluation results'
    )

    return parser.parse_args()

# ────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ────────────────────────────────────────────────────────────

def main():
    """
    Main pipeline execution.

    Orchestrates ingest and evaluate steps based on command-line flags.
    Provides before/after statistics and execution summary.
    """
    logger.info("=" * 60)
    logger.info("CAMBRIDGE OPEN DATA PORTAL - PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # Parse arguments
    args = parse_arguments()

    # Get initial statistics
    stats_before = get_pipeline_stats()
    start_time = time.time()

    # Determine what to run
    run_ingest = not args.evaluate_only
    run_evaluate = not args.ingest_only

    success = True

    # Step 1: Ingest (if enabled)
    if run_ingest:
        logger.info("STEP 1: INGEST")
        logger.info("-" * 60)

        if not run_script('ingest.py'):
            logger.error("Ingest step failed!")
            success = False

            # Ask if we should continue
            if run_evaluate:
                logger.warning("Evaluate step will run with existing data")

        logger.info("")

    # Step 2: Evaluate (if enabled)
    if run_evaluate and success:
        logger.info("STEP 2: EVALUATE")
        logger.info("-" * 60)

        # Build evaluate.py arguments
        eval_args = []
        if args.limit:
            eval_args.extend(['--limit', str(args.limit)])
        if args.dry_run:
            eval_args.append('--dry-run')

        if not run_script('evaluate.py', eval_args):
            logger.error("Evaluate step failed!")
            success = False

        logger.info("")

    # Get final statistics
    stats_after = get_pipeline_stats()
    elapsed_time = time.time() - start_time

    # Print summary
    if not args.dry_run:
        print_summary(stats_before, stats_after, elapsed_time)
    else:
        logger.info("=" * 60)
        logger.info("DRY RUN COMPLETE - No changes saved")
        logger.info("=" * 60)

    if success:
        logger.info("Pipeline completed successfully!")
    else:
        logger.error("Pipeline completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
