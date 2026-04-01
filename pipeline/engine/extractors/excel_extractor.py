import openpyxl
import re
from pipeline.engine.extractors.base_extractor import BaseExtractor

class ExcelExtractor(BaseExtractor):
    def extract(self, file_path):
        """Extracts data and identifies the summary row."""
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
        
        records = []
        summary_row = None
        header_row_idx = None
        
        # 1. Detect Header Row
        header_config = self.config.get('header_detection', {})
        method = header_config.get('method')
        
        if method == 'fixed_row':
            header_row_idx = header_config.get('row', 1)
        elif method == 'pattern_match':
            pattern = header_config.get('pattern')
            for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
                if any(re.search(pattern, str(cell).strip(), re.IGNORECASE) for cell in row if cell):
                    header_row_idx = row_idx
                    # Note: We don't have self.logger here, but we can print if needed, 
                    # however BaseExtractor doesn't have logger. 
                    # We'll just rely on the ValueError message for now.
                    break
        
        if not header_row_idx:
            raise ValueError(f"Could not find header row in {file_path}")

        # 2. Map Columns
        raw_headers = [cell for cell in next(sheet.iter_rows(min_row=header_row_idx, max_row=header_row_idx, values_only=True))]
        col_map = self._map_columns(raw_headers)
        
        # 3. Process Data
        for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
            if not any(row): continue
            
            # Identify Summary Row (e.g. Total)
            if self._is_summary_row(row):
                summary_data = {}
                for col_idx, val in enumerate(row):
                    header = raw_headers[col_idx]
                    field = col_map.get(header)
                    if field: summary_data[field] = val
                summary_row = summary_data
                continue # Do not include summary in records
            
            # Skip Rows
            if self._should_skip_row(row):
                continue
            
            record = {}
            for col_idx, val in enumerate(row):
                header = raw_headers[col_idx]
                field = col_map.get(header)
                if field: record[field] = val
            
            if record:
                records.append(record)
                
        return {
            'records': records,
            'summary': summary_row,
            'col_map': col_map
        }
