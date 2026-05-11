import pandas as pd
import json
import os

def populate_manifest():
    mapping_path = "pipeline/discovery/national_verified_mapping.json"
    manifest_path = "pipeline/manifests/census_2011_pca_manifest.xlsx"
    
    if not os.path.exists(mapping_path):
        print(f"Error: {mapping_path} not found.")
        return

    with open(mapping_path, "r") as f:
        mapping = json.load(f)

    # Base data for all 32 verified states
    records = []
    for state, res_id in mapping.items():
        records.append({
            "entity_name": state,
            "resource_id": res_id,
            "is_verified": "TRUE",
            "url": f"https://data.gov.in/resource/{res_id}"
        })

    df = pd.DataFrame(records)
    
    # Save to Excel
    df.to_excel(manifest_path, index=False)
    print(f"Successfully populated {manifest_path} with {len(df)} verified national records.")
    print(df[['entity_name', 'resource_id', 'is_verified']].head(10))

if __name__ == "__main__":
    populate_manifest()
