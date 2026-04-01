import os
import time
import logging
from pipeline.engine.orchestrator import Orchestrator
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("State_Ingestion")

load_dotenv()

def run_state_ingestion():
    yaml_path = "pipeline/engine/registry/ncrb_state_unified.yaml"
    
    max_retries = 10
    for attempt in range(max_retries):
        try:
            print(f"\n[Processing] {yaml_path} (Attempt {attempt + 1})...")
            orch = Orchestrator()
            inserted = orch.run_source(yaml_path)
            print(f"SUCCESS: Ingested {inserted} records into Supabase.")
            return # Done
            
        except Exception as e:
            print(f"FAILED (Attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Exiting.")
                raise e

if __name__ == "__main__":
    run_state_ingestion()
