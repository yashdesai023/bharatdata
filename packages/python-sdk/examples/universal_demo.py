from bharatdata import BharatData
import pandas as pd
import json

def sdk_demo():
    # Initialize with local dev server or production
    # bd = BharatData("http://127.0.0.1:8787")
    bd = BharatData("https://api.bharatdata.org")
    
    print("--- 1. Registry Discovery ---")
    try:
        datasets = bd.list_datasets()
        print(f"Available datasets: {[d['id'] for d in datasets]}")
        
        if datasets:
            meta = bd.get_dataset_metadata(datasets[0]['id'])
            print(f"Metadata for {datasets[0]['id']}: {meta['title']}")
    except Exception as e:
        print(f"Registry check skipped (expected if server offline): {e}")

    print("\n--- 2. Universal Query (Mock Pattern) ---")
    # This shows how the code will look. 
    # In a real test, this would hit the Stage 4 backend.
    print("Query Pattern: bd.query('ncrb-crime', 'summary', entity='Delhi', year=2023)")
    
    print("\n--- 3. Pandas Integration ---")
    mock_data = {
        "data": [{"entity_name": "Delhi", "year": 2023, "total_cases": 500}],
        "metadata": {"dataset": "ncrb-crime", "attribution": "NCRB Official"}
    }
    df = bd.to_dataframe(mock_data)
    print("DataFrame Head:")
    print(df.head())
    print(f"\nCitation: {bd.cite(df)}")

if __name__ == "__main__":
    sdk_demo()
