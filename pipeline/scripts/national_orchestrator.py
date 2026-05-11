import os
import pandas as pd
import sqlalchemy
from sqlalchemy import text
from dotenv import load_dotenv
import time
from ingest_pca_2011 import CensusPCAIngestor

load_dotenv()

class NationalOrchestrator:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.db_url = os.getenv('DATABASE_URL')
        self.engine = sqlalchemy.create_engine(self.db_url)
        self.ingestor = CensusPCAIngestor()

    def sync_registry_from_excel(self):
        print(f"Reading manifest from {self.excel_path}...")
        df = pd.read_excel(self.excel_path)
        # Filter out rows where resource_id is blank
        df = df[df['resource_id'].notna() & (df['resource_id'] != '')]
        
        if df.empty:
            print("No Resource IDs found in the Excel sheet. Please fill it first.")
            return False

        print(f"Synching {len(df)} states to the database registry...")
        for _, row in df.iterrows():
            sql = """
            INSERT INTO census_ingestion_registry (state_name, resource_id, status)
            VALUES (:s, :r, 'pending')
            ON CONFLICT (state_name) DO UPDATE SET resource_id = EXCLUDED.resource_id;
            """
            with self.engine.begin() as conn:
                conn.execute(text(sql), {"s": row['state_name'], "r": row['resource_id']})
        return True

    def run_ingestion_loop(self):
        while True:
            # Pick the next pending state
            query = "SELECT state_name, resource_id FROM census_ingestion_registry WHERE status = 'pending' LIMIT 1"
            with self.engine.connect() as conn:
                res = conn.execute(text(query)).fetchone()
            
            if not res:
                print("All pending states completed or no pending states found.")
                break
            
            state_name, resource_id = res
            
            # Update status to in_progress
            update_status = "UPDATE census_ingestion_registry SET status = 'in_progress' WHERE state_name = :s"
            with self.engine.begin() as conn:
                conn.execute(text(update_status), {"s": state_name})
            
            try:
                # RUN INGESTION
                count = self.ingestor.ingest_state(resource_id, state_name)
                
                # Update status and record count
                update_final = """
                UPDATE census_ingestion_registry 
                SET status = 'completed', record_count = :c, last_ingested_at = NOW() 
                WHERE state_name = :s
                """
                with self.engine.begin() as conn:
                    conn.execute(text(update_final), {"s": state_name, "c": count})
                    
            except Exception as e:
                print(f"Failed to ingest {state_name}: {e}")
                update_fail = "UPDATE census_ingestion_registry SET status = 'failed', error_message = :e WHERE state_name = :s"
                with self.engine.begin() as conn:
                    conn.execute(text(update_fail), {"s": state_name, "e": str(e)})
            
            print(f"Resting for 5 seconds before next state...")
            time.sleep(5)

if __name__ == "__main__":
    # Updated path to the user's filled registry
    excel_file = os.path.join("data", "raw", "census-2011", "data-resource", "census_2011_registry_template.xlsx")
    orchestrator = NationalOrchestrator(excel_file)
    
    # Step 1: Sync Registry
    if orchestrator.sync_registry_from_excel():
        # Step 2: Run Loop
        orchestrator.run_ingestion_loop()
