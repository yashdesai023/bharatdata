import os

class CrossReference:
    def __init__(self, master_list_path=None):
        self.master_list = set()
        if master_list_path and os.path.exists(master_list_path):
            with open(master_list_path, 'r', encoding='utf-8') as f:
                self.master_list = set(line.strip().upper() for line in f if line.strip())

    def validate(self, records, field_name='state'):
        """Checks if all values in 'field_name' are present in the master list."""
        if not self.master_list: return True # Skip if no master list provided
        
        errors = []
        for idx, record in enumerate(records):
            val = record.get(field_name)
            if val and str(val).upper() not in self.master_list:
                errors.append(f"Row {idx+1}: '{val}' is not in master list for '{field_name}'")
        
        if errors:
            raise ValueError("Cross-Ref Violation: " + " | ".join(errors[:3]))
            
        return True
