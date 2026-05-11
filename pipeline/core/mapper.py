"""
Column Mapper Engine
---------------------
Transforms raw API records (with inconsistent column names) into
clean records matching the database schema, using YAML regex patterns.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger


class MappingError(Exception):
    """Raised when a required column cannot be mapped."""
    pass


class ColumnMapper:
    """
    Maps raw records from a data source to the target database schema
    using regex patterns defined in a YAML column_mapping block.

    Usage:
        mapper = ColumnMapper(definition["extraction"])
        clean_records, skipped = mapper.transform_batch(raw_records)
    """

    # TYPE_COERCERS handle dirty government data strings (commas, null indicators)
    TYPE_COERCERS = {
        "int":   lambda v: int(float(str(v).replace(",", "").strip())) if v not in (None, "", "NA", "N/A", "-", "null") else None,
        "float": lambda v: float(str(v).replace(",", "").strip()) if v not in (None, "", "NA", "N/A", "-", "null") else None,
        "str":   lambda v: str(v).strip() if v is not None else None,
        "date":  lambda v: str(v).strip() if v is not None else None,
        "bool":  lambda v: str(v).strip().lower() in ("true", "1", "yes") if v is not None else None,
    }

    def __init__(self, extraction_config: Dict[str, Any]):
        """
        Args:
            extraction_config: The 'extraction' block from the YAML definition.
        """
        self.column_mapping = extraction_config.get("column_mapping", {})
        self.row_filters = extraction_config.get("row_filters", {})
        self.strip_whitespace = True

        # Pre-compile all regex patterns for performance and catch invalid regex early
        self._compiled_patterns: List[Tuple[re.Pattern, str, str]] = []
        for pattern_str, mapping in self.column_mapping.items():
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
                field_name = mapping["field"]
                field_type = mapping.get("type", "str")
                self._compiled_patterns.append((compiled, field_name, field_type))
            except re.error as e:
                logger.error(f"Invalid regex pattern in YAML: '{pattern_str}' | {e}")
                raise

        # Pre-compile exclude patterns for row filtering
        self._exclude_patterns = []
        for p in self.row_filters.get("exclude_patterns", []):
            try:
                self._exclude_patterns.append(re.compile(p, re.IGNORECASE | re.UNICODE))
            except re.error as e:
                logger.error(f"Invalid exclude regex pattern: '{p}' | {e}")

        logger.info(
            f"Mapper Initialized: {len(self._compiled_patterns)} patterns, "
            f"{len(self._exclude_patterns)} exclusion filters."
        )

    def _resolve_column(self, raw_col_name: str) -> Optional[Tuple[str, str]]:
        """
        Find the target field name and type for a given raw column name.
        """
        for pattern, field_name, field_type in self._compiled_patterns:
            if pattern.search(raw_col_name):
                return field_name, field_type
        return None

    def _build_column_index(self, sample_record: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
        """
        Build a mapping of raw_column → (target_field, type) from the first record.
        This index is reused for the entire batch.
        """
        index = {}
        unmapped = []

        for raw_col in sample_record.keys():
            result = self._resolve_column(raw_col)
            if result:
                field_name, field_type = result
                index[raw_col] = (field_name, field_type)
                logger.debug(f"Mapped: '{raw_col}' → '{field_name}' ({field_type})")
            else:
                unmapped.append(raw_col)

        if unmapped and len(unmapped) < 10: # Only log if few unmapped to keep log clean
            logger.debug(f"Unmapped columns (dropped): {unmapped}")

        return index

    def _coerce(self, value: Any, field_type: str) -> Any:
        """Apply type coercion. Returns None on failure."""
        coercer = self.TYPE_COERCERS.get(field_type, self.TYPE_COERCERS["str"])
        try:
            return coercer(value)
        except (ValueError, TypeError, AttributeError):
            return None

    def _should_exclude_row(self, record: Dict[str, Any]) -> bool:
        """Return True if this row should be skipped based on exclude patterns."""
        if not self._exclude_patterns:
            return False

        # If any value in the record matches an exclusion pattern, drop the row
        for value in record.values():
            if isinstance(value, str):
                for pattern in self._exclude_patterns:
                    if pattern.search(value):
                        return True
        return False

    def transform_record(
        self,
        raw_record: Dict[str, Any],
        column_index: Dict[str, Optional[Tuple[str, str]]]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single raw record into a clean database record.
        """
        if self._should_exclude_row(raw_record):
            return None

        clean = {}
        for raw_col, raw_val in raw_record.items():
            # Lazy resolution: if we haven't seen this column in this batch yet, resolve it
            if raw_col not in column_index:
                column_index[raw_col] = self._resolve_column(raw_col)

            res = column_index[raw_col]
            if res:
                field_name, field_type = res
                coerced = self._coerce(raw_val, field_type)
                clean[field_name] = coerced

        return clean if clean else None

    def transform_batch(
        self,
        raw_records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Transform a full batch of raw records.
        Returns: (clean_records, skipped_count)
        """
        if not raw_records:
            return [], 0

        # Build initial column index from the first record
        column_index = self._build_column_index(raw_records[0])

        clean_records = []
        skipped = 0

        for raw in raw_records:
            clean = self.transform_record(raw, column_index)
            if clean is None:
                skipped += 1
            else:
                clean_records.append(clean)

        return clean_records, skipped

    def validate_required_columns(
        self,
        record: Dict[str, Any],
        required: List[str]
    ) -> bool:
        """Check that all required columns are present and non-null."""
        for col in required:
            if record.get(col) is None:
                return False
        return True
