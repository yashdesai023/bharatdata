import os
import sys

# Add project root to path to allow imports from pipeline.engine
sys.path.append(os.getcwd())

from pipeline.engine.definition_loader import DefinitionLoader

def validate_all_definitions():
    definitions_dir = os.path.join("pipeline", "definitions")
    loader = DefinitionLoader()
    
    # Filter for .yaml files (excluding templates)
    yaml_files = [f for f in os.listdir(definitions_dir) if f.endswith(".yaml") and not f.startswith("_")]
    
    print(f"--- Validating {len(yaml_files)} Dataset Definitions ---")
    
    failures = 0
    for filename in yaml_files:
        path = os.path.join(definitions_dir, filename)
        try:
            definition = loader.load(path)
            print(f"[PASS] {filename}: {definition['identity']['name']}")
        except Exception as e:
            print(f"[FAIL] {filename}: {str(e)}")
            failures += 1
            
    print("-" * 40)
    if failures == 0:
        print("ALL DEFINITIONS ARE VALID! SUCCESS")
        return True
    else:
        print(f"FAILED: {failures} invalid definitions found.")
        return False

if __name__ == "__main__":
    success = validate_all_definitions()
    sys.exit(0 if success else 1)
