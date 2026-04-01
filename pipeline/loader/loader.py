import os
import sys
import uuid
import psycopg2.extras
from typing import List, Dict, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.db_connection import get_connection
from utils.logger_config import pipeline_logger as logger

def load_batch(run_id: str, normalized_records: List[Dict], normalization_logs: List[Dict] = None, parse_failures: List[Dict] = None) -> Dict:
    """
    Writes a batch of processed records to Postgres using batch inserts and ON CONFLICT handling.
    """
    if normalization_logs is None:
        normalization_logs = []
    if parse_failures is None:
        parse_failures = []
        
    inserted_total = 0
    skipped_total = 0
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Separate by table
                state_recs = []
                dist_recs = []
                city_recs = []
                
                for r in normalized_records:
                    if r.get('city'):
                        city_recs.append(r)
                    elif r.get('district'):
                        dist_recs.append(r)
                    else:
                        state_recs.append(r)
                
                # 2. Insert with ON CONFLICT DO NOTHING
                # Base columns (order matches the schema)
                base_cols = [
                    "id", "ingestion_run_id", "state", "state_code", "year", "category", "category_label",
                    "total_cases", "rate_per_lakh", "chargesheeted", "convicted", "acquitted",
                    "pending_investigation", "pending_trial", "confidence", "source_url", "source_file",
                    "report_name", "publishing_body", "collection_date", "normalizer_version", "boundary_note"
                ]

                # State
                if state_recs:
                    inserted, skipped = _bulk_insert(
                        cur, "crime_records_state", base_cols, state_recs, run_id, 
                        "(state, year, category, source_file)"
                    )
                    inserted_total += inserted
                    skipped_total += skipped
                
                # District
                if dist_recs:
                    # columns: id, run_id, state, state_code, district, year, category, category_label, ...
                    dist_cols = base_cols[:4] + ["district"] + base_cols[4:]
                    inserted, skipped = _bulk_insert(
                        cur, "crime_records_district", dist_cols, dist_recs, run_id, 
                        "(state, district, year, category, source_file)"
                    )
                    inserted_total += inserted
                    skipped_total += skipped
                
                # City
                if city_recs:
                    # columns for city are slightly different in base_cols order? 
                    # id, run_id, city, parent_state, year, category, label, total, rate, chargesheeted, convicted, acquitted, p_inv, p_trial, confidence, url, file, report, body, date, version
                    city_cols = ["id", "ingestion_run_id", "city", "parent_state", "year", "category", "category_label",
                                "total_cases", "rate_per_lakh", "chargesheeted", "convicted", "acquitted",
                                "pending_investigation", "pending_trial", "confidence", "source_url", "source_file",
                                "report_name", "publishing_body", "collection_date", "normalizer_version"]
                    inserted, skipped = _bulk_insert(
                        cur, "crime_records_city", city_cols, city_recs, run_id, 
                        "(city, year, category, source_file)"
                    )
                    inserted_total += inserted
                    skipped_total += skipped

                # 3. Metadata Logs
                if normalization_logs:
                    log_cols = ["record_id", "field", "input_value", "output_value", "mapping_source", "confidence_impact"]
                    psycopg2.extras.execute_values(
                        cur, 
                        f"INSERT INTO normalization_log ({', '.join(log_cols)}) VALUES %s",
                        [[l.get(c) for c in log_cols] for l in normalization_logs]
                    )
                
                if parse_failures:
                    fail_cols = ["ingestion_run_id", "source_file", "source_sheet", "row_number", "column_name", 
                                 "raw_value", "expected_type", "error_message"]
                    psycopg2.extras.execute_values(
                        cur,
                        f"INSERT INTO parse_failures ({', '.join(fail_cols)}) VALUES %s",
                        [[str(run_id)] + [f.get(c) for c in fail_cols[1:]] for f in parse_failures]
                    )

                # 4. Update Ingestion Run Metrics
                cur.execute("""
                    UPDATE ingestion_runs 
                    SET records_stored = COALESCE(records_stored, 0) + %s,
                        records_skipped = COALESCE(records_skipped, 0) + %s,
                        parse_failures = COALESCE(parse_failures, 0) + %s
                    WHERE id = %s
                """, (inserted_total, skipped_total, len(parse_failures), run_id))

        if inserted_total > 0:
            logger.success(f"Stored {inserted_total} records to DB (Skipped {skipped_total} duplicates).")
            
        return {
            "records_stored": inserted_total, 
            "duplicates_skipped": skipped_total
        }

    except Exception as e:
        logger.error(f"Batch Load Error: {e}")
        raise e

def _bulk_insert(cur, table: str, columns: List[str], records: List[Dict], run_id: str, conflict_target: str) -> Tuple[int, int]:
    """Helper for batch inserts with 'ON CONFLICT DO NOTHING'."""
    if not records:
        return 0, 0
    
    # Get count before
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count_before = cur.fetchone()[0]
    
    # Prepare values
    values = []
    for r in records:
        row = []
        for col in columns:
            if col == "ingestion_run_id":
                row.append(str(run_id))
            elif col == "parent_state" and "parent_state" not in r:
                row.append(r.get('state')) # Fallback for city parent_state
            else:
                row.append(r.get(col))
        values.append(tuple(row))
    
    # Execute batch insert
    query = f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES %s
        ON CONFLICT {conflict_target} DO NOTHING
    """
    psycopg2.extras.execute_values(cur, query, values, page_size=1000)
    
    # Get count after
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count_after = cur.fetchone()[0]
    
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

if __name__ == "__main__":
    print("Loader module loaded. Run run_pipeline.py to execute.")
