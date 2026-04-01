import hashlib
import json

class Deduplicator:
    @staticmethod
    def generate_hash(record, identity_fields):
        """
        Creates a unique hash for a record based on key fields.
        identity_fields: list of field names that make a record unique (e.g., ['state', 'district', 'year'])
        """
        # 1. Create a stable representation of the identity
        identity_data = {f: record.get(f) for f in identity_fields}
        # Sort keys for consistent hashing
        stable_json = json.dumps(identity_data, sort_keys=True)
        
        # 2. Hash it
        return hashlib.sha256(stable_json.encode()).hexdigest()

    @classmethod
    def process_batch(cls, records, identity_fields):
        """Attaches a unique hash to every record in the batch."""
        for record in records:
            record['_hash'] = cls.generate_hash(record, identity_fields)
        return records
