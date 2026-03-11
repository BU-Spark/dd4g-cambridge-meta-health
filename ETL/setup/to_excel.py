"""
Export all tables from a SQLite database to an Excel file.

This script connects to the configured SQLite database, discovers whatever tables
exist (typically datasets and evaluations, though names may vary), and writes
each table to its own worksheet.  If a table is missing the script simply
skips it; an empty database is handled gracefully.

Usage:
    python to_excel.py

Output:
    ETL/data/cambridge_odp_export.xlsx

Sheets:
    - One sheet per table found in the database. The sheet name matches the table
      name.
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

DB_PATH = os.path.join(os.path.dirname(__file__), "../data", "cambridge_metadata.db")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "../data", "cambridge_odp_export.xlsx")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────

def expand_json_columns(df, json_columns):
    """
    Expand JSON string columns into readable format.
    
    Args:
        df: DataFrame to process
        json_columns: List of column names that contain JSON strings
    
    Returns:
        DataFrame with JSON columns expanded
    """
    df_copy = df.copy()
    
    for col in json_columns:
        if col in df_copy.columns:
            def safe_json_expand(x):
                if not x:
                    return None
                try:
                    return json.dumps(json.loads(x), indent=2)
                except (json.JSONDecodeError, TypeError):
                    return str(x)  # Return as-is if not valid JSON
            
            df_copy[col] = df_copy[col].apply(safe_json_expand)
    
    return df_copy


def create_summary_sheet(conn):
    """
    Create a summary statistics DataFrame.
    
    Args:
        conn: SQLite database connection
    
    Returns:
        DataFrame with summary statistics
    """
    cursor = conn.cursor()
    
    # Check if evaluations table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='evaluations'
    """)
    evaluations_exists = cursor.fetchone() is not None
    
    summary_data = []
    
    # Total datasets
    cursor.execute("SELECT COUNT(*) FROM ODP_datasets")
    total_datasets = cursor.fetchone()[0]
    summary_data.append({"Metric": "Total Datasets", "Value": total_datasets})
    
    if evaluations_exists:
        # Datasets evaluated
        cursor.execute("SELECT COUNT(*) FROM ODP_datasets WHERE last_evaluated_at IS NOT NULL")
        evaluated = cursor.fetchone()[0]
        summary_data.append({"Metric": "Datasets Evaluated", "Value": evaluated})
        
        # Health status counts
        cursor.execute("""
            SELECT overall_health_status, COUNT(*) 
            FROM evaluations 
            WHERE id IN (
                SELECT MAX(id) FROM evaluations GROUP BY dataset_id
            )
            GROUP BY overall_health_status
        """)
        for status, count in cursor.fetchall():
            summary_data.append({"Metric": f"Status: {status}", "Value": count})
    else:
        summary_data.append({"Metric": "Datasets Evaluated", "Value": "N/A (evaluations table not yet created)"})
    
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

        # Check if evaluations table exists
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='evaluations'
        """)
        evaluations_exists = cursor.fetchone() is not None

        # ─── Sheet 2: evaluations ───
        if evaluations_exists:
            logger.info("Exporting evaluations table...")
            df_evaluations = pd.read_sql_query("SELECT * FROM evaluations", conn)
            logger.info(f"  {len(df_evaluations)} evaluations loaded")
        else:
            logger.warning("Evaluations table does not exist yet - skipping evaluations export")
            df_evaluations = None

        # ─── Sheet 3: Summary Statistics ───
        logger.info("Creating summary statistics...")
        df_summary = create_summary_sheet(conn)

        # ─── Sheet 4: Datasets with Evaluations (Join) ───
        if evaluations_exists:
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
        else:
            logger.warning("Skipping joined view - evaluations table does not exist yet")
            df_joined = None

        # ─── Write to Excel ───
        logger.info(f"Writing to Excel file: {EXCEL_PATH}")

        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            # Sheet 1: Summary (put first for easy access)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

            # Sheet 2: Datasets + Evaluations (most useful for analysis) - only if evaluations exist
            if df_joined is not None:
                df_joined.to_excel(writer, sheet_name='Datasets_With_Health', index=False)

            # Sheet 3: All Dataset Metadata (expanded JSON)
            df_datasets_readable.to_excel(writer, sheet_name='All_Datasets', index=False)

            # Sheet 4: Evaluations Only - only if evaluations exist
            if df_evaluations is not None:
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
        if df_evaluations is not None:
            logger.info(f"Total evaluations exported: {len(df_evaluations)}")
        else:
            logger.info("Total evaluations exported: 0 (evaluations table not yet created)")
        logger.info(f"Output file: {EXCEL_PATH}")
        logger.info(f"File size: {os.path.getsize(EXCEL_PATH) / 1024:.2f} KB")
        logger.info("=" * 60)
        logger.info("Sheets created:")
        sheet_num = 1
        logger.info(f"  {sheet_num}. Summary - High-level statistics")
        sheet_num += 1
        if df_joined is not None:
            logger.info(f"  {sheet_num}. Datasets_With_Health - Datasets joined with latest evaluations")
            sheet_num += 1
        logger.info(f"  {sheet_num}. All_Datasets - Complete dataset metadata")
        sheet_num += 1
        if df_evaluations is not None:
            logger.info(f"  {sheet_num}. Evaluations - All evaluation records")
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
