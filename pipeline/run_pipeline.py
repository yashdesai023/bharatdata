import os
import sys
import argparse
import uuid
import datetime
from typing import List

# Ensure pipeline root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == 'pipeline':
    pipeline_root = current_dir
    project_root = os.path.dirname(pipeline_root)
else:
    project_root = current_dir
    pipeline_root = os.path.join(project_root, 'pipeline')

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.logger_config import pipeline_logger as logger
from utils.db_connection import get_connection, get_cursor
from ingester.ingester import NCRBIngester
from ingester.hash_tracker import HashTracker
from parser.excel_parser import parse_excel
from parser.pdf_parser import parse_pdf
from parser.json_parser import parse_json
from normalizer.normalizer import normalize_record
from loader.loader import load_batch

class PipelineOrchestrator:
    def __init__(self, years: List[int], steps: List[str], dry_run: bool = False):
        self.years = years
        self.steps = steps
        self.dry_run = dry_run
        self.run_id = str(uuid.uuid4())
        self.hash_tracker = HashTracker()
        self.stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "records_extracted": 0,
            "records_stored": 0,
            "records_skipped": 0,
            "parse_failures": 0,
            "start_time": datetime.datetime.now()
        }

    def _init_run_record(self):
        """Initialize the ingestion_runs record in the database."""
        if self.dry_run:
            logger.info(f"[Dry Run] Would initialize ingestion_run {self.run_id}")
            return

        try:
            with get_cursor() as cur:
                # Get NCRB source ID (default source for this pipeline)
                cur.execute("SELECT id FROM data_sources WHERE name LIKE 'NCRB%' LIMIT 1;")
                source_res = cur.fetchone()
                source_id = source_res[0] if source_res else None
                
                cur.execute("""
                    INSERT INTO ingestion_runs (id, source_id, status, started_at)
                    VALUES (%s, %s, 'running', %s)
                """, (self.run_id, source_id, self.stats["start_time"]))
                logger.info(f"Initialized ingestion_run {self.run_id}")
        except Exception as e:
            logger.error(f"Failed to initialize run record: {e}")

    def _update_run_record(self, status: str, error: str = None):
        """Finalize the ingestion_runs record."""
        if self.dry_run:
            logger.info(f"[Dry Run] Would update ingestion_run {self.run_id} to {status}")
            return

        try:
            with get_cursor() as cur:
                cur.execute("""
                    UPDATE ingestion_runs 
                    SET status = %s, 
                        completed_at = %s, 
                        files_processed = %s, 
                        records_extracted = %s, 
                        records_stored = %s, 
                        records_skipped = %s,
                        parse_failures = %s,
                        error_message = %s
                    WHERE id = %s
                """, (
                    status, 
                    datetime.datetime.now(), 
                    self.stats["files_processed"],
                    self.stats["records_extracted"],
                    self.stats["records_stored"],
                    self.stats["records_skipped"],
                    self.stats["parse_failures"],
                    error,
                    self.run_id
                ))
                logger.info(f"Finalized ingestion_run {self.run_id} as {status}")
        except Exception as e:
            logger.error(f"Failed to update run record: {e}")

    def run_ingest(self):
        """Step 1: Ingestion metadata check."""
        logger.info("Step: Checking source metadata...")
        # (This remains largely the same, but we mainly rely on local files for now)

    def process_files(self):
        """Step 2, 3, 4: Parse, Normalize, and Load."""
        logger.info(f"Step: Processing years {self.years} (Steps: {self.steps})")
        
        for year in self.years:
            year_path = os.path.join(project_root, "data", "raw", "ncrb-crime-in-india", str(year))
            if os.path.exists(year_path):
                for root, _, files in os.walk(year_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if file.startswith('~$') or not (file.endswith('.xlsx') or file.endswith('.pdf')):
                            continue
                        self._process_single_file(file_path, year)
            else:
                logger.warning(f"Path not found for year {year}: {year_path}")
                
            # City JSON Processing
            json_dir = os.path.join(project_root, "data", "structured", "metro-cities")
            if os.path.exists(json_dir):
                for file in os.listdir(json_dir):
                    if file.endswith('.json') and str(year) in file:
                        self._process_single_file(os.path.join(json_dir, file), year)

    def _process_single_file(self, file_path: str, year: int):
        """Parsing -> Normalization -> Loading for one file with hashing."""
        
        # Level 1: File-Level check
        if self.hash_tracker.is_file_ingested(file_path):
            logger.info(f"SKIP (Already Ingested): {os.path.basename(file_path)}")
            self.stats["files_skipped"] += 1
            return

        logger.info(f"PROCESSING: {os.path.basename(file_path)}")
        self.stats["files_processed"] += 1
        
        # 1. Parse
        if "parse" not in self.steps:
            return
            
        parsed_records = []
        if file_path.endswith('.xlsx'):
            parsed_records = parse_excel(file_path)
        elif file_path.endswith('.pdf'):
            parsed_records = parse_pdf(file_path)
        elif file_path.endswith('.json'):
            parsed_records = parse_json(file_path)
        else:
            return

        if not parsed_records:
            logger.warning(f"No records extracted from {file_path}")
            return

        self.stats["records_extracted"] += len(parsed_records)
        
        # 2. Normalize
        if "normalize" not in self.steps:
            return
            
        normalized_batch = []
        norm_logs = []
        for raw in parsed_records:
            norm, logs = normalize_record(raw, batch_id=self.run_id)
            normalized_batch.append(norm)
            norm_logs.extend(logs)

        # 3. Load
        if "load" not in self.steps:
            return
            
        if self.dry_run:
            logger.info(f"[Dry Run] Scanned {len(normalized_batch)} records for {os.path.basename(file_path)}")
            return

        try:
            res = load_batch(self.run_id, normalized_batch, norm_logs)
            self.stats["records_stored"] += res["records_stored"]
            self.stats["records_skipped"] += res["duplicates_skipped"]
            
            # Level 3: Mark file as ingested
            # Detect table type and level
            table_type = "unknown"
            geo_level = "state"
            if "District" in file_path or "district" in file_path:
                geo_level = "district"
                table_type = "crime_records_district"
            elif "City" in file_path or "city" in file_path:
                geo_level = "city"
                table_type = "crime_records_city"
            else:
                table_type = "crime_records_state"

            self.hash_tracker.mark_file_ingested(
                file_path=file_path,
                year=year,
                table_type=table_type,
                geographic_level=geo_level,
                records_extracted=len(normalized_batch)
            )
            
        except Exception as e:
            logger.error(f"Load failed for {file_path}: {e}")
            self.stats["parse_failures"] += 1

    def print_summary(self):
        """Print execution summary."""
        duration = datetime.datetime.now() - self.stats["start_time"]
        
        print("\n" + "="*50)
        print(" BHARAT DATA PIPELINE EXECUTION SUMMARY")
        print("="*50)
        print(f"Run ID:           {self.run_id}")
        print(f"Status:           {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        print(f"Started at:       {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:         {duration}")
        print("-" * 50)
        print(f"Files Processed:  {self.stats['files_processed']}")
        print(f"Files Skipped:    {self.stats['files_skipped']}")
        print(f"Total Extracted:  {self.stats['records_extracted']}")
        print(f"Records Stored:   {self.stats['records_stored']}")
        print(f"Records Skipped:  {self.stats['records_skipped']} (Duplicates)")
        print(f"Load Failures:    {self.stats['parse_failures']}")
        print("="*50 + "\n")

    def run(self):
        """Main orchestrator sequence."""
        try:
            self._init_run_record()
            
            if "ingest" in self.steps:
                self.run_ingest()
            
            if any(s in self.steps for s in ["parse", "normalize", "load"]):
                self.process_files()
            
            self._update_run_record("completed")
            self.print_summary()
            
        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user.")
            self._update_run_record("interrupted")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"FATAL Pipeline Error: {e}")
            self._update_run_record("failed", error=str(e))
            raise e

def main():
    parser = argparse.ArgumentParser(description="BharatData Crime Data Pipeline Orchestrator")
    parser.add_argument("--years", nargs="+", type=int, default=[2023], help="Years to process")
    parser.add_argument("--steps", nargs="+", default=["ingest", "parse", "normalize", "load"], 
                        choices=["ingest", "parse", "normalize", "load", "all"],
                        help="Pipeline steps to execute")
    parser.add_argument("--dry-run", action="store_true", help="Process data but don't write to DB")
    
    args = parser.parse_args()
    
    if "all" in args.steps:
        args.steps = ["ingest", "parse", "normalize", "load"]
        
    orchestrator = PipelineOrchestrator(years=args.years, steps=args.steps, dry_run=args.dry_run)
    orchestrator.run()

if __name__ == "__main__":
    main()
