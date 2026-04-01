import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.logger_config import pipeline_logger as logger

def filter_duplicates(cur, records: list) -> list:
    """
    Checks each record against the DB. Returns a list of records 
    that DO NOT already exist based on (state, year, category, source_file).
    """
    if not records:
        return []
        
    unique_records = []
    duplicate_count = 0
    
    for r in records:
        table = "crime_records_state"
        if r.get("city"):
            table = "crime_records_city"
        elif r.get("district"):
            table = "crime_records_district"
            
        # Unique composite key heuristic
        query = f"""
            SELECT id FROM {table} 
            WHERE state = %s AND year = %s AND category = %s AND source_file = %s
        """
        params = [r.get('state'), r.get('year'), r.get('category'), r.get('source_file')]
        
        # Add geography specificity
        if table == "crime_records_city":
            query += " AND city = %s"
            params.append(r.get('city'))
        elif table == "crime_records_district":
            query += " AND district = %s"
            params.append(r.get('district'))
            
        cur.execute(query + " LIMIT 1;", tuple(params))
        
        if cur.fetchone():
            duplicate_count += 1
        else:
            unique_records.append(r)
            
    if duplicate_count > 0:
        logger.info(f"Deduplicator removed {duplicate_count} existing records from batch.")
        
    return unique_records
