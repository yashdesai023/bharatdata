import sqlalchemy
from sqlalchemy import text
import os
import json
from dotenv import load_dotenv

load_dotenv()

def export_registry():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not found in environment.")
        return

    engine = sqlalchemy.create_engine(db_url)
    try:
        with engine.connect() as conn:
            # Check state_name and resource_id columns
            result = conn.execute(text("SELECT state_name, resource_id FROM census_ingestion_registry WHERE resource_id IS NOT NULL AND resource_id != ''"))
            mapping = {row[0]: row[1] for row in result}
            
            with open("pipeline/discovery/national_verified_mapping.json", "w") as f:
                json.dump(mapping, f, indent=4)
            
            print(f"Successfully exported {len(mapping)} verified IDs to pipeline/discovery/national_verified_mapping.json")
            for state, uid in mapping.items():
                print(f"  {state}: {uid}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_registry()
