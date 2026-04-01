from pipeline.engine.definition_loader import DefinitionLoader
import os

def test_phase1():
    print("Starting Phase 1 Verification...")
    
    # 1. Initialize Loader
    loader = DefinitionLoader()
    print("SUCCESS: DefinitionLoader initialized.")

    # 2. Test Real Definition
    real_def_path = os.path.join("sources", "ncrb", "crime_in_india_2023.yaml")
    try:
        data = loader.load(real_def_path)
        print(f"SUCCESS: Successfully loaded and validated: {real_def_path}")
        print(f"   Source ID: {data['identity']['id']}")
        print(f"   Table Name: {data['storage']['table_name']}")
    except Exception as e:
        print(f"ERROR: Failed to load real definition: {e}")
        return False

    # 3. Test Invalid Definition (Dummy)
    invalid_def_path = "sources/invalid_test.yaml"
    with open(invalid_def_path, "w") as f:
        f.write("identity:\n  id: 'missing-fields'\n") # Missing name, publishing_body, etc.
    
    try:
        loader.load(invalid_def_path)
        print("ERROR: Invalid definition passed validation unexpectedly!")
        return False
    except ValueError as e:
        print(f"SUCCESS: Correctly rejected invalid definition: {e}")
    finally:
        if os.path.exists(invalid_def_path):
            os.remove(invalid_def_path)

    print("\nPHASE 1 VERIFIED: Schema and Loader are working perfectly.")
    return True

if __name__ == "__main__":
    success = test_phase1()
    exit(0 if success else 1)
