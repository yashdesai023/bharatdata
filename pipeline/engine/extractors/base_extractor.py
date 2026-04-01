from abc import ABC, abstractmethod
import re

class BaseExtractor(ABC):
    def __init__(self, config):
        self.config = config
        self.column_mapping = config.get('column_mapping', {})
        self.row_filters = config.get('row_filters', {})

    @abstractmethod
    def extract(self, file_path):
        """
        Extracts structured data from a file.
        Returns a dictionary: { 'records': [...], 'summary': {...} }
        """
        pass

    def _is_summary_row(self, row_values):
        """Checks if a row contains a summary pattern (e.g. Total)."""
        summary_patterns = self.row_filters.get('summary_patterns', ['TOTAL', 'ALL INDIA'])
        
        for val in row_values:
            if val is None: continue
            str_val = str(val).strip().upper()
            for pattern in summary_patterns:
                if re.search(pattern.upper(), str_val):
                    return True
        return False

    def _should_skip_row(self, row_values):
        """Checks if a row should be filtered out (skip patterns)."""
        skip_patterns = self.row_filters.get('skip_patterns', [])
        
        for val in row_values:
            if val is None: continue
            str_val = str(val).strip().upper()
            for pattern in skip_patterns:
                if re.search(pattern.upper(), str_val):
                    return True
        return False

    def _map_columns(self, raw_headers):
        """Maps raw headers to canonical field names using regex matching from config."""
        mapped = {}
        for raw_h in raw_headers:
            if not raw_h: continue
            clean_h = str(raw_h).strip()
            
            found = False
            for pattern, info in self.column_mapping.items():
                if re.search(pattern, clean_h, re.IGNORECASE):
                    mapped[clean_h] = info['field']
                    found = True
                    break
            
            if not found:
                mapped[clean_h] = None 
        return mapped
