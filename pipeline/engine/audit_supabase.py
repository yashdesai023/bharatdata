import os
import psycopg2
import time
from dotenv import load_dotenv

load_dotenv()

def audit_supabase():
    url = os.getenv("DATABASE_URL")
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(url)
            cur = conn.cursor()
            
            tables = ["district_crime_stats", "state_crime_stats"]
            total = 0
            
            print("="*40)
            print(" SUPABASE PRODUCTION AUDIT ")
            print("="*40)
            
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f" Table: {table:<25} | Records: {count}")
                total += count
                
            print("-"*40)
            print(f" TOTAL VERIFIED RECORDS: {total}")
            print("="*40)
            
            cur.close()
            conn.close()
            return # Success
            
        except psycopg2.OperationalError as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Exiting.")
                raise e

if __name__ == "__main__":
    audit_supabase()
