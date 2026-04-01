import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_overview():
    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    tables = {
        "district_crime_stats": "Contains district-level and metro-city crime statistics (IPC, SLL, Women, Children, etc.)",
        "state_crime_stats": "Contains state-level annual crime aggregates and disposal statistics"
    }
    
    print("="*60)
    print(" BHARATDATA DATABASE SCHEMA OVERVIEW ")
    print("="*60)
    
    for table, desc in tables.items():
        print(f"\nTABLE: {table.upper()}")
        print(f"DESCRIPTION: {desc}")
        
        # Get count
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"TOTAL RECORDS: {count}")
        
        # Get unique entities
        entity_col = "entity_name" if table == "district_crime_stats" else "state"
        cur.execute(f"SELECT COUNT(DISTINCT {entity_col}) FROM {table}")
        distinct_count = cur.fetchone()[0]
        print(f"UNIQUE ENTITIES ({entity_col}): {distinct_count}")
        
        # Get columns
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        print("\nCOLUMNS:")
        for col, dtype in cols:
            print(f"  - {col:<25} ({dtype})")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    get_db_overview()
