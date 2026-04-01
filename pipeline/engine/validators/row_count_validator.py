class RowCountValidator:
    def __init__(self, min_rows=1, max_rows=None):
        self.min_rows = min_rows
        self.max_rows = max_rows

    def validate(self, records):
        """Checks if the number of records is within the allowed range."""
        count = len(records)
        if count < self.min_rows:
            raise ValueError(f"CRITICAL: Data underflow. Found {count} records, but expected at least {self.min_rows}.")
        
        if self.max_rows and count > self.max_rows:
            raise ValueError(f"CRITICAL: Data overflow. Found {count} records, but expected at most {self.max_rows}.")
        
        return True
