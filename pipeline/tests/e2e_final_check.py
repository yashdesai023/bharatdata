import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from pipeline.utils.db_connection import get_cursor
from pipeline.engine.definition_loader import DefinitionLoader

def run_check():
    print("--- Final Stage 4 Verification ---")
    
    # Check Registry Discovery
    try:
        loader = DefinitionLoader()
        d = loader.load('sources/e2e_test/pollution_stats.yaml')
        print(f"[SUCCESS] Registry Load: {d['identity']['id']} (Found: {d['identity']['name']})")
    except Exception as e:
        print(f"[FAILURE] Registry Load Failed: {e}")
        return

    # Check Database Ingestion
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pollution_records")
            count = cur.fetchone()[0]
            print(f"[SUCCESS] Database Ingestion: {count} records found in 'pollution_records'.")
            
            cur.execute("SELECT * FROM pollution_records LIMIT 3")
            rows = cur.fetchall()
            print("\nSample Data:")
            for r in rows:
                print(f" - {r}")
    except Exception as e:
        print(f"❌ Database Verification Failed: {e}")

if __name__ == "__main__":
    run_check()
