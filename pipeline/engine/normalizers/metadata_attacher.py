from datetime import datetime
from typing import Dict, Any

class MetadataAttacher:
    def __init__(self, metadata: Dict[str, Any]):
        """
        Initializes the attacher with dataset-specific and system metadata.
        
        Args:
            metadata: A dict of metadata extracted from patterns (year, state, etc.)
                      plus system-level metadata (source_id).
        """
        self.metadata = metadata
        self.collection_date = metadata.get('last_updated', datetime.now().strftime('%Y-%m-%d'))
        self.pipeline_version = "v2.1-universal"

    def attach(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Adds source lineage and audit metadata to a record."""
        # Sys-level audit metadata with underscore prefixing
        record['_source_id'] = self.metadata.get('id')
        record['_collection_date'] = self.collection_date
        record['_ingested_at'] = datetime.now().isoformat()
        record['_pipeline_version'] = self.pipeline_version
        
        # Dataset-level metadata (year, state, etc.) at top level
        for key, val in self.metadata.items():
            if key not in ['id', 'last_updated'] and key not in record:
                record[key] = val
            
        return record
