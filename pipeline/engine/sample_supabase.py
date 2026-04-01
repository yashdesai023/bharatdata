import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def sample_supabase():
    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    for table in ["district_crime_stats", "state_crime_stats"]:
        print("\n" + "="*60)
        print(f" SUPABASE {table.upper()} SAMPLE ")
        print("="*60)
        
        entity_col = "entity_name" if table == "district_crime_stats" else "state"
        cur.execute(f"SELECT year, {entity_col}, total_ipc, total_sll, _source_id FROM {table} WHERE total_ipc > 0 OR total_sll > 0 LIMIT 10")
        rows = cur.fetchall()
        for row in rows:
            ipc = row[2] if row[2] is not None else "NULL"
            sll = row[3] if row[3] is not None else "NULL"
            print(f" Year: {row[0]} | Entity: {str(row[1])[:25]:<25} | IPC: {ipc:<8} | SLL: {sll:<8}")
            
    print("\n" + "="*60)
    print(" YEARLY BREAKDOWN ")
    print("="*60)
    for table in ["district_crime_stats", "state_crime_stats"]:
        cur.execute(f"SELECT year, COUNT(*) FROM {table} GROUP BY year ORDER BY year")
        breakdown = cur.fetchall()
        print(f"\n Table: {table}")
        for yr, cnt in breakdown:
            print(f" Year: {yr} | Records: {cnt}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    sample_supabase()
