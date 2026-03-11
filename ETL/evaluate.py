"""
Cambridge Open Data Portal - Dataset Health Evaluation

This script evaluates the health and quality of datasets in the Cambridge ODP.
It performs two types of checks:
1. Static Health Checks: Programmatic checks (license, contact, update frequency, column descriptions)
2. AI Metadata Evaluation: LLM-based assessment of description quality, tag relevance, category fit

Database: ETL/data/cambridge_metadata.db
Tables Created: evaluations (stores health check results)
Tables Used: ODP_datasets (reads dataset metadata, updates last_evaluated_at)

Usage:
    python evaluate.py                  # Evaluate all unevaluated datasets
    python evaluate.py --limit 10       # Evaluate at most 10 datasets
    python evaluate.py --dry-run        # Preview without saving results

The script handles:
- Querying datasets that need evaluation (last_evaluated_at IS NULL)
- Running static health checks (fully implemented)
- Running AI evaluation (skeleton with TODOs for developers)
- Calculating overall health status (Healthy/Warning/Fail)
- Storing results and updating timestamps
"""

import sqlite3
import json
import os
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# ────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────

# Database path (matches ingest.py pattern)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_metadata.db")

# Evaluation thresholds (configurable)
THRESHOLDS = {
    "description_min_score": 0.5,       # AI score below this = Warning
    "description_fail_score": 0.3,      # AI score below this = Fail
    "tag_min_score": 0.5,               # Tag score below this = Warning
    "category_min_score": 0.5,          # Category score below this = Warning
    "update_late_multiplier": 2.0,      # Update >2x late = Fail
    "update_warning_multiplier": 1.2,   # Update >1.2x late = Warning
    "column_desc_min": 0.5,             # Column descriptions <50% = Warning
}

# Logging setup (matches ingest.py pattern)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# DATABASE INITIALIZATION
# ────────────────────────────────────────────────────────────

def init_evaluation_tables() -> None:
    """
    Initialize evaluations table and indexes.

    Creates:
    - evaluations table for storing health check results
    - Indexes for query optimization

    Note: The ODP_datasets table is created by ingest.py

    This function is idempotent - safe to run multiple times.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ─── evaluations Table ───
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT NOT NULL,
            evaluated_at TEXT DEFAULT (datetime('now')),

            -- AI-Generated Qualitative Scores (0.0 to 1.0)
            ai_description_score REAL,                -- LLM assessment: Is the description clear?
            ai_tag_relevance_score REAL,              -- LLM assessment: Are tags relevant?
            ai_category_fit_score REAL,               -- LLM assessment: Does category match content?
            ai_suggestions TEXT,                      -- LLM improvement suggestions

            -- Static Health Checks (0 or 1 for boolean)
            is_update_late INTEGER,                   -- Is data_updated_at overdue?
            has_license INTEGER,                      -- Is license field populated?
            has_contact_email INTEGER,                -- Is contact_email populated?
            column_desc_completion REAL,              -- % of columns with descriptions

            -- Overall Health Status
            overall_health_status TEXT,               -- 'Healthy', 'Warning', or 'Fail'

            FOREIGN KEY (dataset_id) REFERENCES ODP_datasets (dataset_id) ON DELETE CASCADE
        )
    """)

    # ─── Indexes for Query Optimization ───

    # Index for joining evaluations with datasets
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_eval_dataset
        ON evaluations (dataset_id, evaluated_at DESC)
    """)

    conn.commit()
    conn.close()
    logger.debug("Evaluations table initialized")

# ────────────────────────────────────────────────────────────
# DATABASE OPERATIONS
# ────────────────────────────────────────────────────────────

def fetch_unevaluated_datasets(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch datasets that need evaluation.

    Criteria for datasets needing evaluation:
    - last_evaluated_at IS NULL (never evaluated)
    - OR data_updated_at > last_evaluated_at (data refreshed since last eval)

    Args:
        limit: Maximum number of datasets to fetch (None = all)

    Returns:
        List of dataset dictionaries with all fields needed for evaluation
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()

    query = """
        SELECT * FROM ODP_datasets
        WHERE last_evaluated_at IS NULL
           OR data_updated_at > last_evaluated_at
        ORDER BY data_updated_at DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    logger.info(f"Found {len(results)} datasets needing evaluation")
    return results


def save_evaluation(dataset_id: str, evaluation_result: Dict[str, Any]) -> None:
    """
    Save evaluation results to database.

    This function performs two operations:
    1. Inserts evaluation results into the evaluations table
    2. Updates the last_evaluated_at timestamp in ODP_datasets

    Args:
        dataset_id: The dataset to update
        evaluation_result: Dictionary with all evaluation fields:
            - ai_description_score (float)
            - ai_tag_relevance_score (float)
            - ai_category_fit_score (float)
            - ai_suggestions (str)
            - is_update_late (int/bool)
            - has_license (int/bool)
            - has_contact_email (int/bool)
            - column_desc_completion (float)
            - overall_health_status (str)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Insert into evaluations table
        cursor.execute("""
            INSERT INTO evaluations (
                dataset_id,
                ai_description_score,
                ai_tag_relevance_score,
                ai_category_fit_score,
                ai_suggestions,
                is_update_late,
                has_license,
                has_contact_email,
                column_desc_completion,
                overall_health_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dataset_id,
            evaluation_result['ai_description_score'],
            evaluation_result['ai_tag_relevance_score'],
            evaluation_result['ai_category_fit_score'],
            evaluation_result['ai_suggestions'],
            int(evaluation_result['is_update_late']),  # Convert bool to int
            int(evaluation_result['has_license']),
            int(evaluation_result['has_contact_email']),
            evaluation_result['column_desc_completion'],
            evaluation_result['overall_health_status']
        ))

        # Update last_evaluated_at timestamp
        cursor.execute("""
            UPDATE ODP_datasets
            SET last_evaluated_at = ?
            WHERE dataset_id = ?
        """, (datetime.utcnow().isoformat(), dataset_id))

        conn.commit()
        logger.debug(f"Saved evaluation for {dataset_id}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save evaluation for {dataset_id}: {e}")
        raise
    finally:
        conn.close()

# ────────────────────────────────────────────────────────────
# STATIC HEALTH CHECKS
# ────────────────────────────────────────────────────────────

def check_has_license(dataset: Dict[str, Any]) -> bool:
    """
    Check if dataset has a license.

    Args:
        dataset: Dataset dictionary from database

    Returns:
        True if license field is populated and non-empty
    """
    license_field = dataset.get('license')
    return license_field is not None and str(license_field).strip() != ''


def check_has_contact_email(dataset: Dict[str, Any]) -> bool:
    """
    Check if dataset has a contact email.

    Args:
        dataset: Dataset dictionary from database

    Returns:
        True if contact_email field is populated and non-empty
    """
    contact = dataset.get('contact_email')
    return contact is not None and str(contact).strip() != ''


def calculate_column_desc_completion(dataset: Dict[str, Any]) -> float:
    """
    Calculate percentage of columns with descriptions.

    This parses the columns_descriptions JSON array and counts
    how many descriptions are non-empty.

    Args:
        dataset: Dataset dictionary from database

    Returns:
        Float between 0.0 and 1.0 representing completion percentage
        (1.0 = all columns have descriptions, 0.0 = none have descriptions)
    """
    try:
        # Parse JSON arrays
        columns_names = json.loads(dataset.get('columns_names', '[]'))
        columns_descriptions = json.loads(dataset.get('columns_descriptions', '[]'))

        if not columns_names or len(columns_names) == 0:
            return 0.0

        # Count non-empty descriptions
        non_empty_descriptions = sum(
            1 for desc in columns_descriptions
            if desc and str(desc).strip()
        )

        return non_empty_descriptions / len(columns_names)

    except (json.JSONDecodeError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"Could not calculate column completion: {e}")
        return 0.0


def check_is_update_late(dataset: Dict[str, Any]) -> bool:
    """
    Determine if dataset update is overdue based on maintenance frequency.

    Logic:
    1. Parse update_frequency field (e.g., "Annually", "Monthly", "Daily")
    2. Calculate expected next update from data_updated_at
    3. If current time > expected time * THRESHOLD, mark as late

    Args:
        dataset: Dataset dictionary from database

    Returns:
        True if update is late (>2x expected frequency), False otherwise
    """
    try:
        update_freq = dataset.get('update_frequency')
        data_updated_at = dataset.get('data_updated_at')

        # If no frequency specified or no last update, can't determine lateness
        if not update_freq or not data_updated_at:
            return False

        # Special cases that are never "late"
        if any(keyword in str(update_freq).lower() for keyword in ['historical', 'as needed', 'one-time']):
            return False

        # Parse last update timestamp
        last_update = datetime.fromisoformat(data_updated_at.replace('Z', '+00:00'))
        current_time = datetime.utcnow()
        days_since_update = (current_time - last_update).days

        # Map frequency keywords to expected days
        frequency_map = {
            'daily': 1,
            'weekly': 7,
            'biweekly': 14,
            'monthly': 30,
            'quarterly': 90,
            'annually': 365,
            'annual': 365,
        }

        # Extract frequency keyword (case-insensitive)
        freq_lower = str(update_freq).lower()
        expected_days = None

        for keyword, days in frequency_map.items():
            if keyword in freq_lower:
                expected_days = days
                break

        if expected_days is None:
            return False  # Unknown frequency, can't determine lateness

        # Apply threshold (>2x expected = late)
        threshold_days = expected_days * THRESHOLDS['update_late_multiplier']
        is_late = days_since_update > threshold_days

        if is_late:
            logger.debug(f"Update late: {days_since_update} days vs {threshold_days} threshold")

        return is_late

    except (ValueError, TypeError) as e:
        logger.debug(f"Could not parse update lateness: {e}")
        return False

# ────────────────────────────────────────────────────────────
# AI EVALUATION FUNCTIONS
# ────────────────────────────────────────────────────────────

def build_evaluation_prompt(dataset: Dict[str, Any]) -> str:
    """
    Build the prompt for LLM evaluation.

    This helper function constructs a well-formatted prompt that asks
    the LLM to evaluate dataset metadata quality.

    Args:
        dataset: Dataset dictionary from database

    Returns:
        Formatted prompt string for LLM
    """
    # TODO: Implement prompt engineering
    #
    # IMPLEMENTATION GUIDE:
    # 1. Extract relevant metadata from dataset
    # 2. Create clear evaluation criteria
    # 3. Request structured JSON output
    # 4. Include examples of good vs bad metadata (optional but recommended)
    #
    # RECOMMENDED PROMPT STRUCTURE:
    # """
    # You are evaluating the quality of open data portal metadata.
    #
    # Dataset Information:
    # - Title: {title}
    # - Description: {description}
    # - Tags: {tags}
    # - Category: {category}
    # - Columns: {column_names}
    #
    # Please evaluate the following:
    # 1. Description clarity (0.0-1.0): Is it clear what data this dataset contains?
    #    - 1.0: Description is comprehensive, explains purpose and content clearly
    #    - 0.5: Description exists but is vague or incomplete
    #    - 0.0: No description or completely unclear
    #
    # 2. Tag relevance (0.0-1.0): Are tags accurate and useful for discovery?
    #    - 1.0: Tags are specific, relevant, and aid in discovery
    #    - 0.5: Tags are generic or only partially relevant
    #    - 0.0: No tags or completely irrelevant tags
    #
    # 3. Category fit (0.0-1.0): Does the assigned category match the content?
    #    - 1.0: Category perfectly matches dataset content
    #    - 0.5: Category is loosely related but not optimal
    #    - 0.0: Category doesn't match or is missing
    #
    # Respond in JSON format:
    # {
    #   "description_score": 0.0-1.0,
    #   "tag_score": 0.0-1.0,
    #   "category_score": 0.0-1.0,
    #   "suggestions": "Brief suggestions for improvement (1-2 sentences)"
    # }
    # """
    #
    # PLACEHOLDER IMPLEMENTATION:

    title = dataset.get('title', 'N/A')
    description = dataset.get('description', 'N/A')
    tags = json.loads(dataset.get('tags', '[]'))
    category = dataset.get('category', 'N/A')

    # Simple prompt (replace with proper prompt engineering)
    prompt = f"Evaluate metadata quality for dataset: {title}"

    return prompt


def evaluate_with_ai(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform AI-based metadata evaluation.

    This function sends dataset metadata to an LLM and receives quality scores.

    Args:
        dataset: Dataset dictionary from database

    Returns:
        Dictionary with keys:
        - ai_description_score (float 0.0-1.0)
        - ai_tag_relevance_score (float 0.0-1.0)
        - ai_category_fit_score (float 0.0-1.0)
        - ai_suggestions (string)
    """
    # TODO: Implement AI evaluation logic
    #
    # IMPLEMENTATION GUIDE:
    # 1. Extract relevant fields from dataset:
    #    title = dataset.get('title')
    #    description = dataset.get('description')
    #    tags = json.loads(dataset.get('tags', '[]'))
    #    category = dataset.get('category')
    #    column_names = json.loads(dataset.get('columns_names', '[]'))
    #
    # 2. Build prompt using helper function:
    #    prompt = build_evaluation_prompt(dataset)
    #
    # 3. Call LLM using config module:
    #    from config import get_llm_client
    #    llm_client = get_llm_client()
    #    response = llm_client.evaluate(prompt)
    #
    # 4. The response will be a dictionary with scores
    #    (LLM client handles JSON parsing)
    #
    # 5. Return the structured result
    #
    # PLACEHOLDER IMPLEMENTATION (returns dummy scores):

    logger.debug(f"AI evaluation for: {dataset.get('title')}")

    # Return dummy scores until AI logic is implemented
    return {
        'ai_description_score': 0.75,  # TODO: Replace with actual LLM score
        'ai_tag_relevance_score': 0.80,  # TODO: Replace with actual LLM score
        'ai_category_fit_score': 0.70,  # TODO: Replace with actual LLM score
        'ai_suggestions': "AI evaluation not yet implemented. Implement evaluate_with_ai() in evaluate.py."
    }

# ────────────────────────────────────────────────────────────
# RESULT AGGREGATION & STORAGE
# ────────────────────────────────────────────────────────────

def calculate_overall_health(
    ai_scores: Dict[str, Any],
    static_checks: Dict[str, Any]
) -> str:
    """
    Determine overall health status based on all checks.

    Health Logic (from README):
    - Fail: AI can't determine dataset purpose (score <0.3), no license,
            update >2x late, or no column descriptions
    - Warning: Description unclear (score <0.5), tags/category poor,
               no contact, or <50% column descriptions
    - Healthy: All checks pass

    Args:
        ai_scores: Dictionary with AI evaluation results
        static_checks: Dictionary with static check results

    Returns:
        'Healthy', 'Warning', or 'Fail'
    """
    # Fail conditions (any true → Fail)
    fail_conditions = [
        ai_scores['ai_description_score'] < THRESHOLDS['description_fail_score'],
        not static_checks['has_license'],
        static_checks['is_update_late'],
        static_checks['column_desc_completion'] == 0.0
    ]

    # Warning conditions (any true → Warning)
    warning_conditions = [
        ai_scores['ai_description_score'] < THRESHOLDS['description_min_score'],
        ai_scores['ai_tag_relevance_score'] < THRESHOLDS['tag_min_score'],
        ai_scores['ai_category_fit_score'] < THRESHOLDS['category_min_score'],
        not static_checks['has_contact_email'],
        static_checks['column_desc_completion'] < THRESHOLDS['column_desc_min']
    ]

    # Fail takes precedence over Warning
    if any(fail_conditions):
        return 'Fail'
    elif any(warning_conditions):
        return 'Warning'
    else:
        return 'Healthy'


def evaluate_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform complete evaluation of a single dataset.

    This orchestrates both static checks and AI evaluation,
    then aggregates results into a final health status.

    Args:
        dataset: Dataset dictionary from database

    Returns:
        Complete evaluation result dictionary ready for database insertion
    """
    logger.debug(f"Evaluating: {dataset.get('title')}")

    # Step 1: Perform static checks (fully implemented)
    static_checks = {
        'has_license': check_has_license(dataset),
        'has_contact_email': check_has_contact_email(dataset),
        'column_desc_completion': calculate_column_desc_completion(dataset),
        'is_update_late': check_is_update_late(dataset)
    }

    # Step 2: Perform AI evaluation (skeleton with dummy scores)
    try:
        ai_scores = evaluate_with_ai(dataset)
    except Exception as e:
        logger.error(f"AI evaluation failed for {dataset.get('dataset_id')}: {e}")
        # Use fallback scores if AI fails
        ai_scores = {
            'ai_description_score': 0.5,
            'ai_tag_relevance_score': 0.5,
            'ai_category_fit_score': 0.5,
            'ai_suggestions': f"AI evaluation failed: {str(e)}"
        }

    # Step 3: Calculate overall health
    overall_health = calculate_overall_health(ai_scores, static_checks)

    # Step 4: Combine all results
    evaluation_result = {
        **ai_scores,
        **static_checks,
        'overall_health_status': overall_health
    }

    return evaluation_result

# ────────────────────────────────────────────────────────────
# COMMAND-LINE INTERFACE
# ────────────────────────────────────────────────────────────

def parse_arguments():
    """
    Parse command-line arguments.

    Supported flags:
    --limit N: Evaluate at most N datasets
    --dry-run: Show what would be evaluated without saving results
    """
    parser = argparse.ArgumentParser(
        description='Evaluate Cambridge ODP dataset health'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of datasets to evaluate (default: all)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview datasets that would be evaluated without saving results'
    )

    return parser.parse_args()

# ────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ────────────────────────────────────────────────────────────

def main():
    """
    Main evaluation pipeline execution.

    Steps:
    1. Parse command-line arguments
    2. Fetch unevaluated datasets from database
    3. Evaluate each dataset (static checks + AI)
    4. Save results to evaluations table
    5. Update last_evaluated_at timestamps
    6. Print summary statistics
    """
    logger.info("=" * 60)
    logger.info("Cambridge Open Data Portal - Evaluation Pipeline")
    logger.info("=" * 60)

    # Parse arguments
    args = parse_arguments()

    # Initialize evaluations table (if not exists)
    init_evaluation_tables()

    # Step 1: Fetch datasets needing evaluation
    logger.info(f"Step 1: Fetching datasets needing evaluation...")
    datasets = fetch_unevaluated_datasets(limit=args.limit)

    if not datasets:
        logger.info("No datasets need evaluation!")
        return

    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No results will be saved")
        logger.info("=" * 60)
        logger.info(f"Would evaluate {len(datasets)} datasets:")
        for ds in datasets[:10]:  # Show first 10
            logger.info(f"  - {ds.get('title')}")
        if len(datasets) > 10:
            logger.info(f"  ... and {len(datasets) - 10} more")
        return

    # Step 2: Evaluate each dataset
    logger.info(f"Step 2: Evaluating {len(datasets)} datasets...")

    results_summary = {
        'healthy': 0,
        'warning': 0,
        'fail': 0,
        'errors': 0
    }

    for idx, dataset in enumerate(datasets, 1):
        try:
            title = dataset.get('title', 'Unknown')
            logger.info(f"[{idx}/{len(datasets)}] {title}")

            # Evaluate dataset
            evaluation_result = evaluate_dataset(dataset)

            # Save to database
            save_evaluation(dataset['dataset_id'], evaluation_result)

            # Update summary
            status = evaluation_result['overall_health_status'].lower()
            results_summary[status] += 1

        except Exception as e:
            logger.error(f"Failed to evaluate {dataset.get('dataset_id')}: {e}")
            results_summary['errors'] += 1
            continue

    # Step 3: Print summary
    logger.info("=" * 60)
    logger.info("Evaluation Summary")
    logger.info("=" * 60)
    logger.info(f"Total evaluated: {len(datasets)}")
    logger.info(f"  Healthy: {results_summary['healthy']}")
    logger.info(f"  Warning: {results_summary['warning']}")
    logger.info(f"  Fail: {results_summary['fail']}")
    logger.info(f"  Errors: {results_summary['errors']}")
    logger.info("=" * 60)
    logger.info(f"Database: {DB_PATH}")
    logger.info("Evaluation complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
