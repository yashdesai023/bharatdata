import json
import os
import re

class GeographicResolver:
    def __init__(self, mapping_file=None):
        self.mapping = {}
        if mapping_file and os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    self.mapping = {k.upper(): v for k, v in json.load(f).items()}
            except Exception as e:
                print(f"ERROR: Could not load mapping file {mapping_file}: {e}")

    def resolve(self, raw_name, level='state'):
        """
        Resolves a raw name to its canonical form.
        Returns (canonical_name, confidence_deduction).
        """
        if not raw_name:
            return None, 0.5
            
        # Hard cast to string and clean
        if isinstance(raw_name, dict):
            # Some Excel cells have rich text as dicts
            clean_name = str(list(raw_name.values())[0]).strip().upper()
        else:
            clean_name = str(raw_name).strip().upper()
        
        # 1. Pre-process/Cleanup (Regex-based)
        clean_name = re.sub(r'^(STATE|UT|DISTRICT|NCT|THE)\s+(OF\s+)?', '', clean_name)
        clean_name = re.sub(r'\s+(STATE|UT|DISTRICT)$', '', clean_name)
        clean_name = clean_name.replace('.', '').strip()

        # 2. Primary: Mapping Lookup
        if clean_name in self.mapping:
            entry = self.mapping[clean_name]
            if isinstance(entry, dict):
                return str(entry.get('canonical', entry)), 0.0
            return str(entry), 0.0
            
        # 3. Fallback: Title Case
        return str(clean_name.title()), 0.2
