from datetime import datetime

class MetadataAttacher:
    def __init__(self, source_config):
        self.source_id = source_config.get('id')
        self.year = source_config.get('year')
        self.collection_date = source_config.get('last_updated', datetime.now().strftime('%Y-%m-%d'))
        self.pipeline_version = "v2.0-universal"

    def attach(self, record):
        """Adds source lineage and audit metadata to a record."""
        record['_source_id'] = self.source_id
        record['_collection_date'] = self.collection_date
        record['_ingested_at'] = datetime.now().isoformat()
        record['_pipeline_version'] = self.pipeline_version
        
        # Attach year as top-level field if it doesn't exist, for unique_key matching
        if self.year and 'year' not in record:
            record['year'] = self.year
            
        return record
