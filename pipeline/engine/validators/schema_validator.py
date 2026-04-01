class SchemaValidator:
    def __init__(self, schema):
        self.schema = schema # Dict of field_name: expected_type (e.g., 'count': int)

    def validate(self, records):
        """Checks every record against the defined schema types."""
        errors = []
        for idx, record in enumerate(records):
            for field, expected_type in self.schema.items():
                val = record.get(field)
                if val is not None and not isinstance(val, expected_type):
                    errors.append(f"Row {idx+1}: Field '{field}' expected {expected_type.__name__}, got {type(val).__name__}")
        
        if errors:
            # Report first 5 errors to avoid flooding
            raise ValueError("Schema Violation: " + " | ".join(errors[:5]))
            
        return True
