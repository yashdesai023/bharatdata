"""
BDIF Core Orchestrator
-----------------------
The universal ETL controller. Reads a dataset YAML, iterates through
its Excel manifest, and processes each resource end-to-end.

Usage:
    python -m pipeline.core.orchestrator --dataset census_2011_pca
    python -m pipeline.core.orchestrator --dataset ncrb_state_crime --dry-run
"""

import os
import sys
import time
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
import pandas as pd
from loguru import logger

load_dotenv()

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.adapters.ogd_api import OGDApiAdapter, OGDApiError, OGDRecord
from pipeline.adapters.direct_download import DirectDownloadAdapter, DirectDownloadError
from pipeline.core.mapper import ColumnMapper
from pipeline.core.loader import SupabaseLoader, LoadResult
from pipeline.audit.db_inspector import AuditWriter
from pipeline.core.SourceResolver import SourceResolver

# ─── Loguru Setup ──────────────────────────────────────────────
LOG_DIR = PROJECT_ROOT / "pipeline" / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(LOG_DIR / "pipeline.log", rotation="10 MB", level="INFO")


class IngestionHalt(Exception):
    """Raised when data surety checks fail."""
    pass


@dataclass
class RunSummary:
    dataset_id: str
    total_entities: int = 0
    successful_entities: int = 0
    failed_entities: List[str] = field(default_factory=list)
    skipped_entities: List[str] = field(default_factory=list)
    total_records_loaded: int = 0
    validation_passed: bool = False
    start_time: float = field(default_factory=time.time)

    def print_report(self) -> None:
        duration = time.time() - self.start_time
        logger.info("========== RUN SUMMARY ==========")
        logger.info(f"Dataset: {self.dataset_id}")
        logger.info(f"Total entities: {self.total_entities}")
        logger.info(f"Successful: {self.successful_entities}")
        logger.info(f"Failed: {len(self.failed_entities)}")
        logger.info(f"Skipped: {len(self.skipped_entities)}")
        logger.info(f"Total records loaded: {self.total_records_loaded}")
        logger.info(f"Duration: {duration:.1f}s")

        production_ready = self.validation_passed and len(self.failed_entities) == 0
        if production_ready:
            logger.info("STATUS: PRODUCTION READY")
        else:
            logger.info("STATUS: NOT PRODUCTION READY")


class BDIFOrchestrator:
    """
    The Universal BDIF ETL Orchestrator.
    Handles the orchestration of the Extract → Transform → Load pipeline.
    """

    DEFINITIONS_DIR = PROJECT_ROOT / "pipeline" / "definitions"
    SCHEMAS_DIR     = PROJECT_ROOT / "pipeline" / "schemas"

    STATUS_PENDING   = "pending"
    STATUS_RUNNING   = "in_progress"
    STATUS_DONE      = "completed"
    STATUS_FAILED    = "failed"

    def __init__(self, dataset_id: str, dry_run: bool = False):
        """
        Args:
            dataset_id: The snake_case ID matching a YAML in definitions/.
            dry_run: If True, skip DB writes but perform extraction and transformation.
        """
        self.dataset_id = dataset_id
        self.dry_run = dry_run
        self.definition = self._load_definition()
        self.acq = self.definition["acquisition"]
        self.storage = self.definition["storage"]
        self.manifest_path = PROJECT_ROOT / self.acq["manifest_file"]

        # Initialize core components
        method = self.acq.get("method", "data_gov_api")
        if method == "direct_download":
            self.adapter = DirectDownloadAdapter(
                max_retries=self.acq.get("max_retries", 3),
                retry_delay=self.acq.get("retry_delay_seconds", 5),
            )
        else:
            self.adapter = OGDApiAdapter(
                batch_size=self.acq.get("batch_size", 1000),
                max_retries=self.acq.get("max_retries", 3),
                retry_delay=self.acq.get("retry_delay_seconds", 5),
            )
            
        self.mapper = ColumnMapper(self.definition["extraction"])
        
        if not dry_run:
            self.loader = SupabaseLoader(
                table=self.storage["table_name"],
                unique_key=self.storage["unique_key"],
            )
            self.audit = AuditWriter(dataset_id=dataset_id)
        else:
            self.loader = None
            self.audit = None

        self.resolver = SourceResolver()
        logger.info(f"BDIF Orchestrator ready for dataset: {dataset_id}")

    def _load_definition(self) -> Dict[str, Any]:
        """Load and validate the YAML definition."""
        yaml_path = self.DEFINITIONS_DIR / f"{self.dataset_id}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Definition not found: {yaml_path}")
        
        schema_path = self.SCHEMAS_DIR / "source_definition_schema.yaml"
        loader = DefinitionLoader(schema_path=str(schema_path))
        return loader.load(str(yaml_path))

    def _load_manifest_df(self) -> pd.DataFrame:
        """Load the manifest Excel into a DataFrame."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file missing: {self.manifest_path}")
        
        # Read with status column to manage state
        if self.manifest_path.suffix.lower() == '.csv':
            df = pd.read_csv(self.manifest_path, dtype=str)
        else:
            df = pd.read_excel(self.manifest_path, dtype=str)
        df.columns = [c.strip().lower() for c in df.columns]
        
        if "status" not in df.columns:
            df["status"] = self.STATUS_PENDING
        df["status"] = df["status"].fillna(self.STATUS_PENDING)
        
        return df

    def _update_manifest_status(self, entity_id: str, status: str, record_count: int = 0):
        """Update status of an entity (state_name or entity_name) in the manifest."""
        if self.manifest_path.suffix.lower() == '.csv':
            df = pd.read_csv(self.manifest_path, dtype=str)
        else:
            df = pd.read_excel(self.manifest_path, dtype=str)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Identity columns: 'entity_name' or 'state_name'
        id_cols = [c for c in df.columns if c in ("entity_name", "state_name")]
        if not id_cols:
            logger.warning("Manifest missing entity/state name columns.")
            return

        # Find row by entity id
        mask = df[id_cols[0]].str.strip().str.lower() == entity_id.lower().strip()
        if not mask.any():
            return
            
        df.loc[mask, "status"] = status
        df.loc[mask, "last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if record_count > 0:
            df.loc[mask, "record_count"] = str(record_count)
            
        if self.manifest_path.suffix.lower() == '.csv':
            df.to_csv(self.manifest_path, index=False)
        else:
            df.to_excel(self.manifest_path, index=False)

    def _process_resource(self, row: pd.Series) -> LoadResult:
        """Process a single resource from extraction to ingestion."""
        # Flexibility for manifest column naming
        entity_name = row.get("entity_name") or row.get("state_name") or row.get("state_district", "Unknown")
        resource_id = str(row.get("resource_id", "")).strip()
        download_url = str(row.get("download_url", "")).strip()
        
        # URL Template Resolution
        url_template = self.definition.get("acquisition", {}).get("url_template")
        if url_template and (not download_url or download_url.lower() in ("nan", "")):
            try:
                # Prepare formatting context
                context = row.to_dict()
                api_key_env = self.definition.get("acquisition", {}).get("api_key_env")
                if api_key_env:
                    context["api_key"] = os.getenv(api_key_env, "")
                
                # Fill template
                download_url = url_template.format(**context)
                logger.debug(f"  [{entity_name}] Resolved URL from template: {download_url}")
            except Exception as e:
                logger.error(f"  [{entity_name}] URL Template error: {e}")

        is_verified = str(row.get("is_verified", "FALSE")).strip().upper()
        
        method = self.definition.get("acquisition", {}).get("method", "data_gov_api")

        # Registry-driven Discovery Fallback
        if method == "data_gov_api" and (not resource_id or resource_id.lower() in ("nan", "")):
            logger.info(f"  [{entity_name}] Missing resource_id in manifest. Resolving from registry...")
            resource_id = self.resolver.get_resource_id(self.dataset_id, entity_name)
            if resource_id:
                logger.info(f"  [{entity_name}] Resolved UUID: {resource_id}")
            else:
                logger.warning(f"  [{entity_name}] No resource_id found in manifest or registry. Skipping.")
                return LoadResult()
            
        if method == "direct_download" and (not download_url or download_url.lower() in ("nan", "")):
            logger.warning(f"  [{entity_name}] No download_url found. Skipping.")
            return LoadResult()

        if is_verified != "TRUE":
            logger.warning(f"  [{entity_name}] Nazar Check: Data is NOT verified (is_verified={is_verified}). Skipping.")
            return LoadResult()

        logger.info(f"Processing Resource: {entity_name} ({resource_id})")
        
        # 1. Update Manifest Status to RUNNING
        self._update_manifest_status(entity_name, self.STATUS_RUNNING)
        
        aggregate_result = LoadResult()
        
        payload_hash = None
        validation = self.definition.get("validation", {})
        lower_bound = validation.get("expected_row_count_lower_bound", 0)
        upper_bound = validation.get("expected_row_count_upper_bound", float('inf'))
        
        try:
            batch_num = 0
            
            if method == "direct_download":
                ext = download_url.split("?")[0].split(".")[-1]
                if ext not in ["csv", "xls", "xlsx"]:
                    ext = "csv"
                dest_dir = PROJECT_ROOT / "data" / "raw" / self.dataset_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / f"{entity_name.replace(' ', '_').replace('/', '_')}.{ext}"
                
                force = self.definition.get("acquisition", {}).get("force_redownload", False)
                check_etag = self.definition.get("acquisition", {}).get("check_etag", True)

                # Download and parse
                file_path, content_type = self.adapter.download(
                    download_url, 
                    dest_path, 
                    force_redownload=force,
                    check_etag=check_etag
                )
                
                # Detect format from Content-Type if possible
                if "csv" in content_type.lower():
                    ext = "csv"
                elif "excel" in content_type.lower() or "spreadsheet" in content_type.lower():
                    ext = "xlsx"
                elif "json" in content_type.lower():
                    ext = "json"

                if ext == "csv":
                    df = pd.read_csv(file_path)
                elif ext in ["xlsx", "xls"]:
                    df = pd.read_excel(file_path)
                elif ext == "json":
                    with open(file_path) as f:
                        data = json.load(f)
                    # OGD JSONs often have records in a 'records' key
                    records_list = data.get("records", data) if isinstance(data, dict) else data
                    
                    # Truncation Guard for OGD API
                    if isinstance(data, dict) and "total" in data:
                        total = data.get("total", 0)
                        fetched = len(records_list)
                        if fetched < total:
                            logger.error(f"  [{entity_name}] TRUNCATION DETECTED: Got {fetched}/{total} records.")
                            raise DirectDownloadError(f"OGD API response is paginated ({fetched}/{total}). Use data_gov_api method instead.")

                    df = pd.DataFrame(records_list)
                else:
                    df = pd.read_csv(file_path)
                    
                records = df.to_dict(orient="records")
                
                # Mock a batch object compatible with loop
                batch = OGDRecord(
                    resource_id=entity_name,
                    data=records,
                    total_count=len(records),
                    fields=[],
                    raw_payload=""
                )
                batches = [batch]
            else:
                batches = self.adapter.fetch_all(resource_id)

            for batch in batches:
                batch_num += 1
                logger.info(f"  [{entity_name}] Batch {batch_num} fetched: {len(batch.data)} records.")
                
                # Integrity Hashing
                if batch.raw_payload:
                    payload_hash = hashlib.sha256(batch.raw_payload.encode('utf-8')).hexdigest()
                    logger.debug(f"  [{entity_name}] Payload hash generated: {payload_hash[:8]}...")

                # Check Bounds
                if batch.total_count < lower_bound:
                    raise IngestionHalt(f"Row count {batch.total_count} is below lower bound {lower_bound}")
                if batch.total_count > upper_bound:
                    raise IngestionHalt(f"Row count {batch.total_count} exceeds upper bound {upper_bound}")
                
                # Transform
                clean_records, skipped = self.mapper.transform_batch(batch.data)
                
                # Load
                if self.dry_run:
                    logger.info(f"  [DRY RUN] Would load {len(clean_records)} records.")
                    aggregate_result.total_inserted += len(clean_records)
                    aggregate_result.total_submitted += len(clean_records)
                else:
                    batch_res = self.loader.load_batch(clean_records)
                    aggregate_result.total_inserted += batch_res.total_inserted
                    aggregate_result.total_failed += batch_res.total_failed
                    aggregate_result.errors.extend(batch_res.errors)
                    aggregate_result.total_submitted += batch_res.total_submitted

            # Success
            logger.success(f"  [{entity_name}] Completed! Processed {aggregate_result.total_inserted} records.")
            self._update_manifest_status(entity_name, self.STATUS_DONE, record_count=aggregate_result.total_inserted)
            
            if self.audit:
                self.audit.log_event(entity_name, self.STATUS_DONE, resource_id, record_count=aggregate_result.total_inserted, payload_hash=payload_hash)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"  [{entity_name}] FAILED: {error_msg}")
            self._update_manifest_status(entity_name, self.STATUS_FAILED)
            if self.audit:
                self.audit.log_event(entity_name, self.STATUS_FAILED, resource_id, error_message=error_msg, payload_hash=payload_hash)
            aggregate_result.errors.append(error_msg)

        return aggregate_result

    def run_validation_gate(self) -> bool:
        validation_config = self.definition.get("validation", {})
        checks_passed = []
        checks_failed = []

        try:
            actual = self.loader.count_rows()
            lb = validation_config.get("expected_row_count_lower_bound", 0)
            ub = validation_config.get("expected_row_count_upper_bound", float("inf"))
            detail = f"Row count: {actual:,} (expected {lb:,}–{ub:,})"
            if lb <= actual <= ub:
                checks_passed.append(("row_count", detail))
                logger.info(f"[PASS] {detail}")
            else:
                checks_failed.append(("row_count", detail))
                logger.error(f"[FAIL] {detail}")
        except Exception as e:
            checks_failed.append(("row_count", str(e)))

        all_passed = len(checks_failed) == 0
        status = "VALIDATED" if all_passed else "VALIDATION_FAILED"

        try:
            self.audit.write_validation(
                dataset_id=self.dataset_id,
                status=status,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        except Exception as e:
            logger.warning(f"Could not write validation result: {e}")

        return all_passed

    def run(self):
        """Run the orchestration loop for all resources with entity isolation."""
        logger.info(f"Starting orchestration for dataset '{self.dataset_id}'...")
        summary = RunSummary(dataset_id=self.dataset_id)

        try:
            manifest_rows = self._load_manifest_df()
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            summary.print_report()
            return summary

        # Apply optional entity filter set by CLI (orchestrator.entities_filter)
        entities_filter = getattr(self, 'entities_filter', None)
        if entities_filter:
            col = 'entityname' if 'entityname' in manifest_rows.columns else ('entity_name' if 'entity_name' in manifest_rows.columns else None)
            if col:
                manifest_rows = manifest_rows[manifest_rows['entity_name'].isin(entities_filter)]
                logger.info(f"Entity filter applied: {len(manifest_rows)} entities → {entities_filter}")

        summary.total_entities = len(manifest_rows)
        if summary.total_entities == 0:
            logger.info("Manifest has no rows. Nothing to process.")
            summary.print_report()
            return summary

        for row in manifest_rows.itertuples():
            row_series = manifest_rows.loc[getattr(row, "Index")]
            entity_name = (
                getattr(row, "entity_name", None)
                or getattr(row, "state_name", None)
                or getattr(row, "entityname", None)
                or str(getattr(row, "Index"))
            )
            is_verified = str(
                getattr(row, "is_verified", getattr(row, "isverified", ""))
            ).upper() == "TRUE"
            row_status = str(getattr(row, "status", self.STATUS_PENDING)).strip().lower()

            # Resumable behavior: only process pending rows
            if row_status != self.STATUS_PENDING:
                summary.skipped_entities.append(entity_name)
                continue

            if not is_verified:
                summary.skipped_entities.append(entity_name)
                continue

            try:
                result = self._process_resource(row_series)

                if result.errors:
                    error_msg = f"ProcessingError: {result.errors[0][:500]}"
                    logger.error(f"FAILED: {entity_name} — {error_msg}")
                    self._update_manifest_status(entity_name, status=self.STATUS_FAILED)
                    if self.audit:
                        resource_id = str(row_series.get("resource_id", "")).strip()
                        self.audit.log_event(
                            entity_name,
                            self.STATUS_FAILED,
                            resource_id,
                            error_message=error_msg,
                        )
                    summary.failed_entities.append(entity_name)
                    continue

                self._update_manifest_status(
                    entity_name,
                    status=self.STATUS_DONE,
                    record_count=getattr(result, "total_inserted", 0),
                )
                if self.audit:
                    resource_id = str(row_series.get("resource_id", "")).strip()
                    self.audit.log_event(
                        entity_name,
                        self.STATUS_DONE,
                        resource_id,
                        record_count=getattr(result, "total_inserted", 0),
                    )
                summary.successful_entities += 1
                summary.total_records_loaded += getattr(result, "total_inserted", 0)

            except OGDApiError as e:
                error_msg = f"OGDApiError: {str(e)[:500]}"
                logger.error(f"FAILED: {entity_name} — {error_msg}")
                self._update_manifest_status(entity_name, status=self.STATUS_FAILED)
                if self.audit:
                    resource_id = str(row_series.get("resource_id", "")).strip()
                    self.audit.log_event(
                        entity_name,
                        self.STATUS_FAILED,
                        resource_id,
                        error_message=error_msg,
                    )
                summary.failed_entities.append(entity_name)
                continue

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)[:500]}"
                logger.error(f"FAILED (unexpected): {entity_name} — {error_msg}", exc_info=True)
                self._update_manifest_status(entity_name, status=self.STATUS_FAILED)
                if self.audit:
                    resource_id = str(row_series.get("resource_id", "")).strip()
                    self.audit.log_event(
                        entity_name,
                        self.STATUS_FAILED,
                        resource_id,
                        error_message=error_msg,
                    )
                summary.failed_entities.append(entity_name)
                continue

        if not self.dry_run:
            summary.validation_passed = self.run_validation_gate()

        summary.print_report()
        return summary


def main():
    parser = argparse.ArgumentParser(description="BDIF Core Orchestrator")
    parser.add_argument("--dataset", required=True, help="Dataset ID matching definitions directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform everything except DB ingestion")
    parser.add_argument("--entities", type=str, default=None, help="Comma-separated entity names to run. Example: 'Goa,Sikkim,Bihar'. Runs all pending if not set.")
    args = parser.parse_args()

    try:
        entities_filter = [e.strip() for e in args.entities.split(",")] if args.entities else None

        orchestrator = BDIFOrchestrator(dataset_id=args.dataset, dry_run=args.dry_run)

        if entities_filter:
            orchestrator.entities_filter = entities_filter
            logger.info(f"Entity filter set: {entities_filter}")

        orchestrator.run()
    except Exception as e:
        logger.critical(f"Orchestrator encountered a fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
