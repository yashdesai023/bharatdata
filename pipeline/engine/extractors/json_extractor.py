import json
from pipeline.engine.extractors.base_extractor import BaseExtractor

class JSONExtractor(BaseExtractor):
    def extract(self, file_path):
        """Extracts data from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        records = []
        summary_row = None
        
        # Strategy: find the first list in the JSON
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            # Look for a common key like 'data', 'results', 'records'
            for key in ['data', 'results', 'records']:
                if key in data and isinstance(data[key], list):
                    raw_list = data[key]
                    break
            else:
                # Use the values of the dict if they are lists
                for val in data.values():
                    if isinstance(val, list):
                        raw_list = val
                        break
                else:
                    raw_list = [data]
        else:
            raw_list = [data]
            
        # Map columns and identify summary
        for item in raw_list:
            if not isinstance(item, dict): continue
            
            # Check if this item is a summary record
            if self._is_summary_row(item.values()):
                summary_row = {field: item.get(pattern) for pattern, field in self.column_mapping.items() if pattern in item}
                continue
                
            record = {field: item.get(pattern) for pattern, field in self.column_mapping.items() if pattern in item}
            if record: records.append(record)
            
        return {'records': records, 'summary': summary_row}
