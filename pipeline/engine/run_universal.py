import argparse
import sys
import os
from dotenv import load_dotenv
from pipeline.engine.orchestrator import Orchestrator

# Load .env from root
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="BharatData Universal Engine CLI")
    parser.add_argument("--source", required=True, help="Path to the source definition YAML")
    parser.add_argument("--db-url", help="Database URL (defaults to DATABASE_URL env var)")
    
    args = parser.parse_args()
    
    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set in environment or provided via --db-url")
        sys.exit(1)
        
    orchestrator = Orchestrator(db_url)
    try:
        total_ingested = orchestrator.run_source(args.source)
        print(f"\nSUCCESS: Ingested {total_ingested} records from {args.source}")
    except Exception as e:
        print(f"\nFAILURE: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
