import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def repair_years():
    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    print("Repairing NULL years based on _source_id...")
    
    # 2021 records often have '2021' in the source id (e.g. ncrb_district_unified_...2021.xlsx)
    # 2022 and 2023 also matched correctly, but we'll cover all if needed.
    
    for year in [2021, 2022, 2023]:
        cur.execute(f"""
            UPDATE district_crime_stats 
            SET year = {year} 
            WHERE year IS NULL AND _source_id LIKE '%{year}%'
        """)
        print(f"  Fixed {cur.rowcount} records for year {year} in district_crime_stats")
        
        cur.execute(f"""
            UPDATE state_crime_stats 
            SET year = {year} 
            WHERE year IS NULL AND _source_id LIKE '%{year}%'
        """)
        print(f"  Fixed {cur.rowcount} records for year {year} in state_crime_stats")
        
    conn.commit()
    cur.close()
    conn.close()
    print("Repair Complete.")

if __name__ == "__main__":
    repair_years()
