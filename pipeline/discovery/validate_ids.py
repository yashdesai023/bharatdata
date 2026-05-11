import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

def validate_ids():
    api_key = os.getenv('DATA_GOV_IN_API_KEY')
    if not api_key:
        print("Error: DATA_GOV_IN_API_KEY not found.")
        return

    mapping_path = "pipeline/discovery/national_verified_mapping.json"
    if not os.path.exists(mapping_path):
        print(f"Error: {mapping_path} not found. Run export first.")
        return

    with open(mapping_path, "r") as f:
        mapping = json.load(f)

    results = {}
    print(f"Validating {len(mapping)} Resource IDs...")
    print("-" * 50)

    for state, res_id in mapping.items():
        url = f"https://api.data.gov.in/resource/{res_id}?api-key={api_key}&format=json&limit=1"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # Check if it's actually Census PCA data
                title = data.get('title', '').lower()
                is_pca = "census" in title or "pca" in title
                
                if is_pca:
                    print(f"[VALID] {state}: VALID ({res_id})")
                    results[state] = {"id": res_id, "status": "valid", "title": data.get('title')}
                else:
                    print(f"[WARN] {state}: ID exists but title mismatch: '{data.get('title')}'")
                    results[state] = {"id": res_id, "status": "wrong_data", "title": data.get('title')}
            elif r.status_code == 404:
                print(f"[FAIL] {state}: 404 Not Found")
                results[state] = {"id": res_id, "status": "404"}
            else:
                print(f"[HTTP] {state}: HTTP {r.status_code}")
                results[state] = {"id": res_id, "status": f"http_{r.status_code}"}
        except Exception as e:
            print(f"[ERROR] {state}: Error {e}")
            results[state] = {"id": res_id, "status": "error"}
        
        time.sleep(0.3) # Avoid rate limiting

    with open("pipeline/discovery/validation_report.json", "w") as f:
        json.dump(results, f, indent=4)

    valid_count = sum(1 for x in results.values() if x['status'] == 'valid')
    print("-" * 50)
    print(f"VALIDATION COMPLETE: {valid_count} / {len(mapping)} verified as accurate.")

if __name__ == "__main__":
    validate_ids()
