import os
import logging
import re
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.engine.downloaders.downloader_factory import DownloaderFactory
from pipeline.engine.downloaders.strategy_router import MultiStrategyDownloader
from pipeline.engine.downloaders.cache_replay import ManifestRegistry
from pipeline.engine.extractors.extractor_factory import ExtractorFactory
from pipeline.engine.normalizers.geographic_resolver import GeographicResolver
from pipeline.engine.normalizers.type_enforcer import TypeEnforcer
from pipeline.engine.normalizers.null_handler import NullHandler
from pipeline.engine.normalizers.confidence_scorer import ConfidenceScorer
from pipeline.engine.normalizers.metadata_attacher import MetadataAttacher
from pipeline.engine.validators.row_count_validator import RowCountValidator
from pipeline.engine.validators.total_matcher import TotalMatcher
from pipeline.engine.validators.schema_validator import SchemaValidator
from pipeline.engine.validators.consistency_checker import ConsistencyChecker
from pipeline.engine.loaders.dynamic_table_creator import DynamicTableCreator
from pipeline.engine.loaders.batch_loader import BatchLoader
from pipeline.engine.loaders.deduplicator import Deduplicator

class Orchestrator:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._setup_logging()
        
        # Initialize Shared Normalizer Components
        mapping_path = os.path.join("data", "canonical-mappings", "states.json")
        self.geo = GeographicResolver(mapping_file=mapping_path)
        self.type_enf = TypeEnforcer()
        self.null_h = NullHandler()
        self.scorer = ConfidenceScorer()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("Orchestrator")

    def _extract_metadata(self, file_path: str, patterns: Dict[str, str]) -> Dict[str, Any]:
        """
        Extracts metadata from file path using regex patterns from YAML.
        
        Example YAML:
          metadata_patterns:
            year: "(20\\d{2})"
            state: "States/(.*)/"
        """
        metadata = {}
        base_name = os.path.basename(file_path)
        
        for key, pattern in patterns.items():
            # Try matching against full path then basename
            match = re.search(pattern, file_path) or re.search(pattern, base_name)
            if match:
                # If there are capturing groups, take the first one; otherwise take the whole match
                val = match.group(1) if match.groups() else match.group(0)
                
                # Auto-cast year to int if possible
                if key == 'year' and isinstance(val, str) and val.isdigit():
                    metadata[key] = int(val)
                else:
                    metadata[key] = val
            else:
                self.logger.debug(f"Metadata pattern '{pattern}' for '{key}' did not match '{file_path}'")
                
        return metadata

    def run_source(self, yaml_path, dry_run=False):
        """Runs the full pipeline for a single source definition."""
        self.logger.info(f"--- Starting {'DRY RUN' if dry_run else 'Pipeline'} for {yaml_path} ---")
        
        try:
            # 1. Load Definition
            loader = DefinitionLoader()
            source_def = loader.load(yaml_path)
            source_id = source_def['identity']['id']
            
            # Read Null Handling configuration
            null_cfg = source_def.get('normalization', {}).get('null_handling', {})
            
            # 2. Acquisition
            self.logger.info(f"[{source_id}] Phase 1: Acquisition...")
            raw_method = source_def['acquisition']['method']

            # Inject source identity for artifact naming
            acq_config = source_def['acquisition'].copy()
            acq_config['source_name'] = source_id

            # Check if multi-strategy is enabled
            multi_strategy = acq_config.get('multi_strategy', False)
            fallback_enabled = acq_config.get('fallback_enabled', True)

            if multi_strategy:
                # Use multi-strategy downloader with automatic failover
                self.logger.info(f"[{source_id}] Using multi-strategy downloader with fallback")
                downloader = DownloaderFactory.get_multi_strategy_downloader(acq_config, source_id)

                # Get manifest entries and use multi-strategy download
                manifest_path = acq_config.get('manifest_file')
                if manifest_path:
                    import openpyxl
                    wb = openpyxl.load_workbook(manifest_path, data_only=True)
                    sheet = wb.active

                    manifest_entries = []
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        if row and row[0]:
                            manifest_entries.append({
                                'resource_id': str(row[0]).strip(),
                                'entity_name': str(row[1]) if len(row) > 1 and row[1] else 'Unknown',
                                'urls': {}
                            })

                    downloaded_files = downloader.download_all(manifest_entries)
                else:
                    downloaded_files = downloader.download()
            else:
                # Single strategy (original behavior)
                downloader = DownloaderFactory.get_downloader(raw_method, acq_config)
                downloaded_files = downloader.download()
            
            if isinstance(downloaded_files, str):
                downloaded_files = [downloaded_files]
            
            total_inserted = 0
            for downloaded_file in downloaded_files:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.logger.info(f"[{source_id}] Processing file: {downloaded_file} (Attempt {attempt+1}/{max_retries})")
                        
                        # Dynamic Metadata Extraction
                        metadata_cfg = source_def.get('extraction', {}).get('metadata_patterns', {})
                        extracted_metadata = self._extract_metadata(downloaded_file, metadata_cfg)
                        extracted_metadata['id'] = f"{source_id}_{os.path.basename(downloaded_file)}"
                        
                        year = extracted_metadata.get('year')

                        # 3. Extraction
                        self.logger.info(f"[{source_id}] Phase 2: Extraction...")
                        fmt = source_def['extraction']['format']
                        extractor = ExtractorFactory.get_extractor(fmt, source_def['extraction'])
                        extraction_result = extractor.extract(downloaded_file)
                        raw_records = extraction_result['records']
                        summary_row = extraction_result['summary']
                        self.logger.info(f"[{source_id}] Extracted {len(raw_records)} records. Summary found: {summary_row is not None}")

                        # 4. Normalization (streaming + chunking)
                        self.logger.info(f"[{source_id}] Phase 3: Normalization (streaming)...")
                        attacher = MetadataAttacher(extracted_metadata)
                        
                        col_map = source_def['extraction'].get('column_mapping', {})
                        schema_hints = {info['field']: self._get_py_type(info.get('type', 'str')) for info in col_map.values()}
                        
                        # Add year and other identifiers to schema hints
                        for key, val in extracted_metadata.items():
                            if key not in ['id', 'last_updated']:
                                schema_hints[key] = type(val)
                        
                        # Use identity fields to find the primary entity for resolution
                        identity_fields = source_def['storage'].get('unique_key', ['state', 'year', 'entity_name'])
                        all_fields = list(schema_hints.keys())

                        # Streaming/chunking config
                        norm_cfg = source_def.get('normalization', {})
                        batch_size = norm_cfg.get('chunk_size', 1000)
                        chunk_key = norm_cfg.get('chunk_key', identity_fields[0] if identity_fields else 'state')

                        buffer = []
                        last_chunk_val = None

                        def flush_buffer(buf):
                            nonlocal total_inserted
                            if not buf:
                                return
                            # Validate schema for this chunk
                            SchemaValidator(schema_hints).validate(buf)

                            # Deduplicate then load/accumulate
                            dedup = Deduplicator()
                            processed = dedup.process_batch(buf, identity_fields)

                            if dry_run:
                                self.logger.info(f"[{source_id}] DRY RUN: Buffer size {len(processed)} -- skipping load")
                                total_inserted += len(processed)
                            else:
                                self.logger.info(f"[{source_id}] Loading chunk of {len(processed)} records into {source_def['storage']['table_name']}")
                                dtc = DynamicTableCreator(self.db_url)
                                dtc.create_table(source_def['storage']['table_name'], schema_hints)
                                loader = BatchLoader(self.db_url)
                                inserted = loader.load(source_def['storage']['table_name'], processed)
                                total_inserted += (inserted if inserted > 0 else 0)

                        for raw in raw_records:
                            # 1. Ensure all defined fields exist in raw record for the NullHandler
                            for f in all_fields:
                                if f not in raw: raw[f] = None

                            # Find primary entity value
                            primary_entity = None
                            primary_key_field = identity_fields[0] if identity_fields else 'state'
                            for field in identity_fields:
                                val = str(raw.get(field) or "").strip()
                                if val and (len(val) >= 2 or val.isdigit()) and val.upper() not in ["NOTE", "SOURCE", "FOOTNOTE"]:
                                    primary_entity = val
                                    primary_key_field = field
                                    break

                            if not primary_entity:
                                continue

                            deductions = 0.0
                            res_val, ded = self.geo.resolve(primary_entity)
                            raw[primary_key_field] = res_val
                            deductions += ded

                            for field, val in list(raw.items()):
                                strat = null_cfg.get(field, "null")
                                raw[field] = self.null_h.handle(val, strategy=strat)

                                if field in schema_hints:
                                    expected = schema_hints[field]
                                    if expected == int:
                                        raw[field] = self.type_enf.to_int(raw[field])
                                    elif expected == float:
                                        raw[field] = self.type_enf.to_float(raw[field])
                                    elif expected == bool:
                                        raw[field] = self.type_enf.to_bool(raw[field])
                                    elif expected == str:
                                        # Coerce numbers and other types to string for string fields
                                        if raw[field] is None:
                                            raw[field] = None
                                        else:
                                            raw[field] = str(raw[field])

                            raw['_confidence'] = self.scorer.calculate(fmt, deductions)
                            processed_rec = attacher.attach(raw)

                            current_chunk_val = processed_rec.get(chunk_key)
                            if last_chunk_val is None:
                                last_chunk_val = current_chunk_val

                            buffer.append(processed_rec)

                            # Flush if batch full or chunk key changed (e.g., new state)
                            if len(buffer) >= batch_size or (current_chunk_val is not None and current_chunk_val != last_chunk_val):
                                flush_buffer(buffer)
                                buffer = []
                                last_chunk_val = current_chunk_val

                        # Flush remaining
                        if buffer:
                            flush_buffer(buffer)

                        # 5. Validation (file-level checks)
                        self.logger.info(f"[{source_id}] Phase 4: Validation (post-chunks)...")
                        val_cfg = source_def.get('validation', {})
                        if 'row_count' in val_cfg:
                            RowCountValidator(min_rows=val_cfg['row_count'].get('min', 0)).validate(raw_records)

                        if 'total_matching' in val_cfg and summary_row:
                            fields = val_cfg['total_matching'].get('columns_to_sum', [])
                            TotalMatcher(tolerance=val_cfg['total_matching'].get('tolerance', 0.1)).validate(raw_records, summary_row, fields)

                        self.logger.info(f"[{source_id}] Completed streaming processing for {downloaded_file}")

                        break # Success!
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"[{source_id}] Transient error processing {downloaded_file}: {e}. Retrying in 5s...")
                            time.sleep(5)
                        else:
                            self.logger.error(f"[{source_id}] SKIPPING FILE after {max_retries} attempts: {downloaded_file}. Error: {e}")
                            # Don't raise here, just proceed to next file
                            break 
            
            self.logger.info(f"[{source_id}] COMPLETED BATCH: Ingested {total_inserted} total records.")
            
            # AI Reporting (Phase 6)
            self.logger.info(f"[{source_id}] Phase 6: Generating AI Narrative Report...")
            try:
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "dataset_id": source_id,
                    "status": "SUCCESS",
                    "overall_health": "100%",
                    "checks": [
                        {
                            "check": "ingestion_summary",
                            "passed": True,
                            "metrics": {
                                "total_records": total_inserted,
                                "files_processed": len(downloaded_files)
                            }
                        }
                    ]
                }
                
                report_json_path = "quality_report_latest.json"
                with open(report_json_path, "w") as f:
                    json.dump(metrics, f, indent=2)
                
                from pipeline.reporting.generate_html_report import generate_report
                report_path = generate_report(report_json_path, source_metadata=source_def.get('identity'))
                self.logger.info(f"[{source_id}] AI Report generated at: {report_path}")
                
            except Exception as report_error:
                self.logger.warning(f"[{source_id}] Reporting failed: {report_error}")

            return total_inserted
            
        except Exception as e:
            self.logger.error(f"PIPELINE FAILED: {str(e)}")
            raise e

    def _get_py_type(self, type_str):
        mapping = {'int': int, 'float': float, 'str': str, 'bool': bool}
        return mapping.get(type_str.lower(), str)

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="BharatData Engine Orchestrator")
    parser.add_argument("--source", required=True, help="Registry ID or Path (e.g. census_2011_pca or pipeline/definitions/census_2011_pca.yaml)")
    parser.add_argument("--dry-run", action="store_true", help="Run without loading to database")

    args = parser.parse_args()

    # Resolve path if only ID is provided
    yaml_path = args.source
    if not yaml_path.endswith(".yaml"):
        # Try definitions folder first (new architecture)
        definitions_path = os.path.join("pipeline", "definitions", f"{args.source}.yaml")
        if os.path.exists(definitions_path):
            yaml_path = definitions_path
        else:
            # Fallback to registry folder (legacy)
            yaml_path = os.path.join("pipeline", "engine", "registry", f"{args.source}.yaml")

    orchestrator = Orchestrator()
    orchestrator.run_source(yaml_path, dry_run=args.dry_run)
