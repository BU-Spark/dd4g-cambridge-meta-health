"""
Export Cambridge ODP SQLite Database to Excel

This script reads data from the SQLite database and exports it to an Excel file
with multiple sheets for easy analysis and sharing.

Usage:
    python to_excel.py

Output:
    ETL/data/cambridge_odp_export.xlsx

Sheets:
    - ODP_datasets: All dataset metadata
    - evaluations: AI health check results (empty until evaluate.py runs)
    - summary: High-level statistics and metrics
"""

import sqlite3
import pandas as pd
import json
import os
from datetime import datetime
import logging

# ────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_metadata.db")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "data", "cambridge_odp_export.xlsx")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────

def expand_json_columns(df: pd.DataFrame, json_columns: list) -> pd.DataFrame:
    """
    Expand JSON array columns into readable strings.

    Args:
        df: DataFrame with JSON columns
        json_columns: List of column names containing JSON arrays

    Returns:
        DataFrame with JSON arrays converted to comma-separated strings
    """
    df_copy = df.copy()

    for col in json_columns:
        if col in df_copy.columns:
            def parse_json_array(val):
                if pd.isna(val) or val is None:
                    return ""
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        # Filter out empty strings and join with comma
                        return ", ".join([str(item) for item in parsed if item])
                    return str(parsed)
                except (json.JSONDecodeError, TypeError):
                    return str(val)

            df_copy[col] = df_copy[col].apply(parse_json_array)

    return df_copy

def create_summary_sheet(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Create a summary statistics DataFrame.

    Args:
        conn: SQLite connection

    Returns:
        DataFrame with summary metrics
    """
    cursor = conn.cursor()

    summary_data = []

    # Total datasets
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets")
    total = cursor.fetchone()[0]
    summary_data.append({"Metric": "Total Datasets", "Value": total})

    # Datasets needing evaluation
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets WHERE last_evaluated_at IS NULL")
    needs_eval = cursor.fetchone()[0]
    summary_data.append({"Metric": "Datasets Needing Evaluation", "Value": needs_eval})

    # Datasets with license
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets WHERE license IS NOT NULL AND license != ''")
    with_license = cursor.fetchone()[0]
    summary_data.append({"Metric": "Datasets With License", "Value": with_license})

    # Datasets with contact email
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets WHERE contact_email IS NOT NULL AND contact_email != ''")
    with_contact = cursor.fetchone()[0]
    summary_data.append({"Metric": "Datasets With Contact Email", "Value": with_contact})

    # Total evaluations
    cursor.execute("SELECT COUNT(*) FROM evaluations")
    total_evals = cursor.fetchone()[0]
    summary_data.append({"Metric": "Total Evaluations Performed", "Value": total_evals})

    summary_data.append({"Metric": "", "Value": ""})  # Blank row
    summary_data.append({"Metric": "─── By Category ───", "Value": ""})

    # Datasets by category
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM ODP_datasets
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
    """)
    for category, count in cursor.fetchall():
        summary_data.append({"Metric": f"  {category}", "Value": count})

    summary_data.append({"Metric": "", "Value": ""})  # Blank row
    summary_data.append({"Metric": "─── By Update Frequency ───", "Value": ""})

    # Datasets by update frequency
    cursor.execute("""
        SELECT update_frequency, COUNT(*) as count
        FROM ODP_datasets
        WHERE update_frequency IS NOT NULL
        GROUP BY update_frequency
        ORDER BY count DESC
    """)
    for freq, count in cursor.fetchall():
        summary_data.append({"Metric": f"  {freq}", "Value": count})

    return pd.DataFrame(summary_data)

# ────────────────────────────────────────────────────────────
# MAIN EXPORT FUNCTION
# ────────────────────────────────────────────────────────────

def export_to_excel():
    """
    Export SQLite database to Excel with multiple sheets.
    """
    logger.info("=" * 60)
    logger.info("Cambridge ODP Database → Excel Export")
    logger.info("=" * 60)

    # Check if database exists
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        logger.error("Run ingest.py first to create the database")
        return

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    logger.info(f"Connected to database: {DB_PATH}")

    try:
        # ─── Sheet 1: ODP_datasets (Main Data) ───
        logger.info("Exporting ODP_datasets table...")

        # Read all datasets
        df_datasets = pd.read_sql_query("SELECT * FROM ODP_datasets", conn)

        # JSON columns to expand (make human-readable)
        json_columns = [
            'tags', 'columns_names', 'columns_field_names',
            'columns_descriptions', 'columns_datatypes', 'domain_metadata_full'
        ]

        # Create two versions: one with expanded JSON, one with raw JSON
        df_datasets_readable = expand_json_columns(df_datasets, json_columns)

        logger.info(f"  {len(df_datasets)} datasets loaded")

        # ─── Sheet 2: evaluations ───
        logger.info("Exporting evaluations table...")
        df_evaluations = pd.read_sql_query("SELECT * FROM evaluations", conn)
        logger.info(f"  {len(df_evaluations)} evaluations loaded")

        # ─── Sheet 3: Summary Statistics ───
        logger.info("Creating summary statistics...")
        df_summary = create_summary_sheet(conn)

        # ─── Sheet 4: Datasets with Evaluations (Join) ───
        logger.info("Creating joined view (datasets + latest evaluations)...")

        # This query joins datasets with their most recent evaluation
        join_query = """
        SELECT
            d.dataset_id,
            d.title,
            d.description,
            d.category,
            d.department,
            d.license,
            d.contact_email,
            d.update_frequency,
            d.data_updated_at,
            d.page_views_total,
            d.download_count,
            d.last_evaluated_at,
            e.overall_health_status,
            e.ai_description_score,
            e.ai_tag_relevance_score,
            e.ai_category_fit_score,
            e.column_desc_completion,
            e.has_license,
            e.has_contact_email,
            e.is_update_late,
            e.ai_suggestions
        FROM ODP_datasets d
        LEFT JOIN (
            SELECT dataset_id, MAX(id) as latest_id
            FROM evaluations
            GROUP BY dataset_id
        ) latest ON d.dataset_id = latest.dataset_id
        LEFT JOIN evaluations e ON latest.latest_id = e.id
        ORDER BY d.title
        """

        df_joined = pd.read_sql_query(join_query, conn)
        logger.info(f"  {len(df_joined)} datasets in joined view")

        # ─── Write to Excel ───
        logger.info(f"Writing to Excel file: {EXCEL_PATH}")

        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            # Sheet 1: Summary (put first for easy access)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

            # Sheet 2: Datasets + Evaluations (most useful for analysis)
            df_joined.to_excel(writer, sheet_name='Datasets_With_Health', index=False)

            # Sheet 3: All Dataset Metadata (expanded JSON)
            df_datasets_readable.to_excel(writer, sheet_name='All_Datasets', index=False)

            # Sheet 4: Evaluations Only
            df_evaluations.to_excel(writer, sheet_name='Evaluations', index=False)

            # Auto-adjust column widths for better readability
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass

                    # Set width (max 50 to avoid super wide columns)
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        logger.info("=" * 60)
        logger.info("Export Summary")
        logger.info("=" * 60)
        logger.info(f"Total datasets exported: {len(df_datasets)}")
        logger.info(f"Total evaluations exported: {len(df_evaluations)}")
        logger.info(f"Output file: {EXCEL_PATH}")
        logger.info(f"File size: {os.path.getsize(EXCEL_PATH) / 1024:.2f} KB")
        logger.info("=" * 60)
        logger.info("Sheets created:")
        logger.info("  1. Summary - High-level statistics")
        logger.info("  2. Datasets_With_Health - Datasets joined with latest evaluations")
        logger.info("  3. All_Datasets - Complete dataset metadata")
        logger.info("  4. Evaluations - All evaluation records")
        logger.info("=" * 60)
        logger.info("Export complete!")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise

    finally:
        conn.close()

# ────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        export_to_excel()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
