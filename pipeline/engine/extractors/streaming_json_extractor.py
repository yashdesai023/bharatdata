"""
Streaming JSON Extractor
-----------------------
Extracts data from OGD API JSON responses with streaming/generator support.
Handles the OGD-specific structure where data comes in a 'records' array.
"""

import json
import re
from typing import Generator, Dict, Any, Optional

from pipeline.engine.extractors.base_extractor import BaseExtractor


class StreamingJSONExtractor(BaseExtractor):
    """
    Extracts records from JSON files, optimized for OGD API response format.
    Supports both file-based and dict-based input with streaming record yield.
    """

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts all records from a JSON file.
        Returns dict with 'records' list and optional 'summary'.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        records = []
        summary_row = None

        # Handle OGD API structure: {"resource_id": "...", "total": N, "records": [...]}
        if isinstance(data, dict):
            raw_list = data.get('records', [])

            # Check if first record is a summary
            if raw_list and self._is_summary_row(list(raw_list[0].values()) if raw_list else []):
                # First record is summary, use remaining as data
                summary_row = raw_list[0]
                raw_list = raw_list[1:]
        elif isinstance(data, list):
            raw_list = data
        else:
            raw_list = [data]

        # Map columns and extract records
        if raw_list:
            # Get column mapping from first record's keys
            first_record = raw_list[0]
            col_map = self._build_column_map(list(first_record.keys()))

            for item in raw_list:
                if not isinstance(item, dict):
                    continue

                # Check for summary row
                if self._is_summary_row(list(item.values())):
                    summary_row = self._map_record(item, col_map)
                    continue

                record = self._map_record(item, col_map)
                if record:
                    records.append(record)

        return {
            'records': records,
            'summary': summary_row,
            'col_map': col_map
        }

    def extract_streaming(self, file_path: str) -> Generator[Dict[str, Any], None, None]:
        """
        Generator that yields records one-by-one for memory efficiency.
        Use this for large files.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        raw_list = data.get('records', []) if isinstance(data, dict) else data

        if raw_list:
            col_map = self._build_column_map(list(raw_list[0].keys()))

            for item in raw_list:
                if not isinstance(item, dict):
                    continue

                if self._is_summary_row(list(item.values())):
                    continue  # Skip summary in streaming mode

                record = self._map_record(item, col_map)
                if record:
                    yield record

    def _build_column_map(self, keys: list) -> Dict[str, Optional[str]]:
        """
        Builds column mapping from raw keys using configured patterns.
        Only includes keys that match configured column_mapping patterns.
        Unmapped keys are silently ignored.
        """
        mapped = {}
        for raw_key in keys:
            if not raw_key:
                continue

            clean_key = str(raw_key).strip()

            # Try to match against configured column_mapping patterns
            for pattern, info in self.column_mapping.items():
                if re.search(pattern, clean_key, re.IGNORECASE):
                    mapped[clean_key] = info.get('field', clean_key)
                    break

            # If no match, DON'T include this key (ignore unmapped columns)
            # This prevents unknown columns from being passed through

        return mapped

    def _map_record(self, item: Dict, col_map: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
        """
        Maps raw record to canonical fields using column mapping.
        """
        record = {}
        for raw_key, field_name in col_map.items():
            if field_name and raw_key in item:
                record[field_name] = item[raw_key]

        return record if record else None