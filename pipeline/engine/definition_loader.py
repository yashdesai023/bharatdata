import yaml
import json
import os
from jsonschema import validate, ValidationError

class DefinitionLoader:
    def __init__(self, schema_path=None):
        if schema_path is None:
            # Robust schema location: navigate from this file to the schema directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.schema_path = os.path.join(base_dir, "schema", "source_definition_schema.yaml")
        else:
            self.schema_path = schema_path
        
        if not os.path.exists(self.schema_path):
            raise FileNotFoundError(f"Source definition schema not found at: {self.schema_path}")
            
        self.schema = self._load_yaml(self.schema_path)

    def _load_yaml(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load(self, source_path):
        """Loads and validates a source definition YAML."""
        definition = self._load_yaml(source_path)
        try:
            validate(instance=definition, schema=self.schema)
            return definition
        except ValidationError as e:
            raise ValueError(f"Invalid Source Definition at {source_path}: {e.message}")

if __name__ == "__main__":
    # Test loader with the schema itself (placeholder test)
    try:
        loader = DefinitionLoader()
        print("SUCCESS: DefinitionLoader initialized and schema loaded.")
    except Exception as e:
        print(f"ERROR: Failed to initialize DefinitionLoader: {e}")
