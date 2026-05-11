import os
import yaml
import json
import logging

# Configuration
REGISTRY_DIR = os.path.join("..", "..", "pipeline", "engine", "registry")
OUTPUT_FILE = os.path.join("src", "registry", "generated-registry.json")

def sync():
    logging.info(f"Syncing registries from {REGISTRY_DIR}...")
    definitions = []

    if not os.path.exists(REGISTRY_DIR):
        logging.error(f"Registry directory not found: {REGISTRY_DIR}")
        return

    for filename in os.listdir(REGISTRY_DIR):
        if filename.endswith(".yaml"):
            path = os.path.join(REGISTRY_DIR, filename)
            with open(path, "r") as f:
                try:
                    source_def = yaml.safe_load(f)
                    
                    # Map YAML structure to API structure
                    api_def = {
                        "id": source_def["identity"]["id"],
                        "name": source_def["identity"]["name"],
                        "publishingBody": source_def["identity"]["publishing_body"],
                        "description": source_def["identity"].get("description", ""),
                        "updateFrequency": source_def["identity"]["update_frequency"],
                        "tableName": source_def["storage"]["table_name"],
                        "conceptMapping": {
                            # Default mappings for API search filters
                            "entity": "state_name" if "state_name" in str(source_def) else "state",
                            "year": "year",
                        },
                        "availableFields": list(source_def["extraction"]["column_mapping"].keys()) + ["_confidence", "_source_id", "_ingested_at"]
                    }
                    
                    # Logical field mapping for API (Mapping logical field Name -> DB field name)
                    api_def["fieldMapping"] = {
                        info["field"]: info["field"] for info in source_def["extraction"]["column_mapping"].values()
                    }
                    
                    definitions.append(api_def)
                    logging.info(f"Loaded {api_def['id']} from {filename}")
                except Exception as e:
                    logging.error(f"Failed to parse {filename}: {e}")

    # Write the resulting JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(definitions, f, indent=2)
    
    logging.info(f"SUCCESS: Generated {OUTPUT_FILE} with {len(definitions)} datasets.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync()
