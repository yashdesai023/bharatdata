import yaml
import json
import os
from jsonschema import validate, ValidationError

class DefinitionLoader:
    def __init__(self, schema_path=None):
        if schema_path is None:
            # Default schema location relative to project root
            self.schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "sources", "_schema", "source_definition_schema.yaml")
        else:
            self.schema_path = schema_path
        
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
        print("✅ DefinitionLoader initialized and schema loaded.")
    except Exception as e:
        print(f"❌ Failed to initialize DefinitionLoader: {e}")
