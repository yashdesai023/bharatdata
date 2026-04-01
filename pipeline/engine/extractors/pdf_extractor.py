import pdfplumber
import re
from pipeline.engine.extractors.base_extractor import BaseExtractor

class PDFExtractor(BaseExtractor):
    def extract(self, file_path):
        """Extracts data from a PDF file."""
        records = []
        summary_row = None
        
        with pdfplumber.open(file_path) as pdf:
            rows = []
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    rows.extend(table)
                    
        header_row_idx = None
        header_config = self.config.get('header_detection', {})
        method = header_config.get('method')
        
        if method == 'pattern_match':
            pattern = header_config.get('pattern')
            for i, row in enumerate(rows):
                if any(re.search(pattern, str(cell).strip(), re.IGNORECASE) for cell in row if cell):
                    header_row_idx = i
                    break
        
        if header_row_idx is None:
            return {'records': [], 'summary': None}
            
        raw_headers = rows[header_row_idx]
        col_map = self._map_columns(raw_headers)
        
        for row in rows[header_row_idx + 1:]:
            if not any(row): continue
            
            if self._is_summary_row(row):
                summary_row = {col_map.get(raw_headers[i]): val for i, val in enumerate(row) if col_map.get(raw_headers[i])}
                continue
                
            record = {col_map.get(raw_headers[i]): val for i, val in enumerate(row) if col_map.get(raw_headers[i])}
            if record: records.append(record)
                
        return {'records': records, 'summary': summary_row}
