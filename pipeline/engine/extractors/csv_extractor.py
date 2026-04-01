import csv
import re
from pipeline.engine.extractors.base_extractor import BaseExtractor

class CSVExtractor(BaseExtractor):
    def extract(self, file_path):
        """Extracts data from a CSV file."""
        records = []
        summary_row = None
        
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            raw_rows = list(reader)
            
        header_row_idx = None
        header_config = self.config.get('header_detection', {})
        method = header_config.get('method')
        
        if method == 'fixed_row':
            header_row_idx = header_config.get('row', 1) - 1
        elif method == 'pattern_match':
            pattern = header_config.get('pattern')
            for i, row in enumerate(raw_rows):
                if any(re.search(pattern, str(cell).strip(), re.IGNORECASE) for cell in row):
                    header_row_idx = i
                    break
                    
        if header_row_idx is None:
            raise ValueError(f"Could not find header row in {file_path}")
            
        raw_headers = raw_rows[header_row_idx]
        col_map = self._map_columns(raw_headers)
        
        for row in raw_rows[header_row_idx + 1:]:
            if not any(row): continue
            
            if self._is_summary_row(row):
                summary_data = {col_map.get(raw_headers[i]): val for i, val in enumerate(row) if col_map.get(raw_headers[i])}
                summary_row = summary_row or summary_data
                continue
            
            if self._should_skip_row(row):
                continue
                
            record = {col_map.get(raw_headers[i]): val for i, val in enumerate(row) if col_map.get(raw_headers[i])}
            if record:
                records.append(record)
                
        return {
            'records': records,
            'summary': summary_row
        }
