import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def truncate_supabase():
    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    
    tables = ["district_crime_stats", "state_crime_stats"]
    
    print("="*40)
    print(" TRUNCATING SUPABASE PRODUCTION ")
    print("="*40)
    
    for table in tables:
        print(f" Truncating {table}...")
        cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY")
        
    print("-"*40)
    print(" PRODUCTION TABLES CLEARED. ")
    print("="*40)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    truncate_supabase()
