import argparse
import sys
import os

# Add root to sys.path so we can import from 'pipeline' as a package
# Script is 2 levels deep from root (pipeline/engine/run_universal.py)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from dotenv import load_dotenv
from pipeline.engine.orchestrator import Orchestrator

# Load .env from root
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="BharatData Universal Engine CLI")
    parser.add_argument("--source", required=True, help="Path to the source definition YAML")
    parser.add_argument("--db-url", help="Database URL (defaults to DATABASE_URL env var)")
    parser.add_argument("--dry-run", action="store_true", help="Run without loading into database")
    
    args = parser.parse_args()
    
    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("Error: DATABASE_URL not set in environment or provided via --db-url")
        sys.exit(1)
        
    orchestrator = Orchestrator(db_url)
    try:
        total_ingested = orchestrator.run_source(args.source, dry_run=args.dry_run)
        mode = "PROCESSED" if args.dry_run else "INGESTED"
        print(f"\nSUCCESS: {mode} {total_ingested} records from {args.source}")
    except Exception as e:
        print(f"\nFAILURE: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
