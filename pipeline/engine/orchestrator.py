import os
import logging
import re
import json
import time
from datetime import datetime
from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.engine.downloaders.downloader_factory import DownloaderFactory
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

    def run_source(self, yaml_path):
        """Runs the full pipeline for a single source definition."""
        self.logger.info(f"--- Starting Pipeline for {yaml_path} ---")
        
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
            downloader = DownloaderFactory.get_downloader(raw_method, source_def['acquisition'])
            downloaded_files = downloader.download()
            
            if isinstance(downloaded_files, str):
                downloaded_files = [downloaded_files]
            
            import time
            total_inserted = 0
            for downloaded_file in downloaded_files:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.logger.info(f"[{source_id}] Processing file: {downloaded_file} (Attempt {attempt+1}/{max_retries})")
                        
                        # Extract year and category from filename/path
                        base_name = os.path.basename(downloaded_file)
                        year = None
                        # Try path first (e.g., .../2021/districts/...) then filename
                        year_match = re.search(r'(202\d)', downloaded_file)
                        if year_match: year = int(year_match.group(1))

                        # 3. Extraction
                        self.logger.info(f"[{source_id}] Phase 2: Extraction...")
                        fmt = source_def['extraction']['format']
                        extractor = ExtractorFactory.get_extractor(fmt, source_def['extraction'])
                        extraction_result = extractor.extract(downloaded_file)
                        raw_records = extraction_result['records']
                        summary_row = extraction_result['summary']
                        self.logger.info(f"[{source_id}] Extracted {len(raw_records)} records. Summary found: {summary_row is not None}")
                        
                        if raw_records and len(raw_records) > 0:
                            self.logger.debug(f"[{source_id}] First record fields: {list(raw_records[0].keys())}")

                        # 4. Normalization
                        self.logger.info(f"[{source_id}] Phase 3: Normalization...")
                        # Log the mapping for debugging
                        self.logger.info(f"[{source_id}] Column Mapping: {extraction_result.get('col_map') or 'N/A'}")
                        
                        # Use sub-id to distinguish categories in unified table
                        sub_id = f"{source_id}_{base_name}"
                        attacher = MetadataAttacher({'id': sub_id, 'year': year})
                        clean_records = []
                        
                        col_map = source_def['extraction'].get('column_mapping', {})
                        schema_hints = {info['field']: self._get_py_type(info.get('type', 'str')) for info in col_map.values()}
                        
                        # IMPORTANT: Add year to schema hints if it's being attached
                        if year and 'year' not in schema_hints:
                            schema_hints['year'] = int
                        
                        identity_fields = source_def['storage'].get('unique_key', ['state', 'year', 'entity_name'])
                        
                        # Initialize all fields from schema hints to ensure NullHandler touches everything
                        all_fields = list(schema_hints.keys())
                        
                        for raw in raw_records:
                            # 1. Ensure all defined fields exist in raw record for the NullHandler
                            for f in all_fields:
                                if f not in raw: raw[f] = None
                                
                            # Skip garbage footer rows (merged cells often result in dicts or single-char non-data)
                            primary_entity = str(raw.get('state') or raw.get('entity_name') or "").strip()
                            if not primary_entity or len(primary_entity) < 2 or primary_entity.upper() in ["NOTE", "SOURCE"]:
                                self.logger.debug(f"[{source_id}] Skipping row with invalid entity: '{primary_entity}'")
                                continue
                            
                            deductions = 0.0
                            res_val, ded = self.geo.resolve(primary_entity)
                            
                            if 'state' in raw: raw['state'] = res_val
                            elif 'entity_name' in raw: raw['entity_name'] = res_val
                            deductions += ded
                            
                            for field, val in raw.items():
                                # Consult YAML for null handling strategy (default: "null")
                                strat = null_cfg.get(field, "null")
                                raw[field] = self.null_h.handle(val, strategy=strat)
                                
                                if field in schema_hints:
                                    if schema_hints[field] == int: raw[field] = self.type_enf.to_int(raw[field])
                                    elif schema_hints[field] == float: raw[field] = self.type_enf.to_float(raw[field])
                                    elif schema_hints[field] == bool: raw[field] = self.type_enf.to_bool(raw[field])
                            
                            raw['_confidence'] = self.scorer.calculate(fmt, deductions)
                            clean_records.append(attacher.attach(raw))
                        
                        # 5. Validation
                        self.logger.info(f"[{source_id}] Phase 4: Validation...")
                        val_cfg = source_def.get('validation', {})
                        if 'row_count' in val_cfg:
                            RowCountValidator(min_rows=val_cfg['row_count'].get('min', 0)).validate(clean_records)
                        
                        if 'total_matching' in val_cfg and summary_row:
                            fields = val_cfg['total_matching'].get('columns_to_sum', [])
                            TotalMatcher(tolerance=val_cfg['total_matching'].get('tolerance', 0.1)).validate(raw_records, summary_row, fields)
                        
                        SchemaValidator(schema_hints).validate(clean_records)
                        
                        # 6. Loading
                        self.logger.info(f"[{source_id}] Phase 5: Loading (Supabase)...")
                        target_table = source_def['storage']['table_name']
                        
                        dedup = Deduplicator()
                        processed_records = dedup.process_batch(clean_records, identity_fields)
                        
                        dtc = DynamicTableCreator(self.db_url)
                        dtc.create_table(target_table, schema_hints)
                        
                        loader = BatchLoader(self.db_url)
                        inserted = loader.load(target_table, processed_records)
                        total_inserted += (inserted if inserted > 0 else 0)
                        
                        break # Success! Move to next file
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"Transient error processing {downloaded_file}: {e}. Retrying in 5s...")
                            time.sleep(5)
                        else:
                            raise e
            
            self.logger.info(f"[{source_id}] SUCCESS: Ingested {total_inserted} total records.")
            
            # 7. Post-Ingestion Reporting (Stage 4)
            self.logger.info(f"[{source_id}] Phase 6: Generating AI Narrative Report...")
            try:
                # We save a simplified metrics JSON for the reporter
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "dataset_id": source_id,
                    "status": "SUCCESS",
                    "overall_health": "100%", # Placeholder, could be calculated from validators
                    "checks": [
                        {
                            "check": "ingestion_summary",
                            "passed": True,
                            "metrics": {
                                "total_records": total_inserted,
                                "average": self.scorer.calculate("agg", 0.0), # Current avg
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
                self.logger.warning(f"[{source_id}] Reporting failed (non-critical): {report_error}")

            return total_inserted
            
        except Exception as e:
            self.logger.error(f"PIPELINE FAILED for {yaml_path}: {str(e)}")
            raise e

    def _get_py_type(self, type_str):
        mapping = {'int': int, 'float': float, 'str': str, 'bool': bool}
        return mapping.get(type_str.lower(), str)
