import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_KEY = os.getenv("DATA_GOV_IN_API_KEY")
BASE_URL = "https://api.data.gov.in/resource"

# URL Prefix pattern from user
SLUG_PATTERN = "villagetown-wise-primary-census-abstract-2011-{dist}-district-{state}"

def to_slug(name: str) -> str:
    return (name.lower()
            .replace(" & ", "-and-")
            .replace(" ", "-")
            .replace(",", "")
            .replace("(", "")
            .replace(")", ""))

def load_all_districts():
    dist_path = PROJECT_ROOT / "pipeline" / "resources" / "census_2011_districts.json"
    if not dist_path.exists():
        logger.error(f"District resource not found: {dist_path}")
        return {}
    with open(dist_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def probe_all_districts(limit_state=None):
    districts_data = load_all_districts()
    results = []
    
    total_found = 0
    total_attempted = 0
    
    for state, districts in districts_data.items():
        if limit_state and state.upper() != limit_state.upper():
            continue
            
        state_slug = to_slug(state)
        logger.info(f"Probing {len(districts)} districts in {state}...")
        
        for dist in districts:
            dist_slug = to_slug(dist)
            slug = SLUG_PATTERN.format(dist=dist_slug, state=state_slug)
            url = f"{BASE_URL}/{slug}"
            
            total_attempted += 1
            success = False
            resource_id = slug
            record_count = 0
            
            try:
                # Use a smaller timeout for initial probe, retry if needed
                resp = requests.get(url, params={
                    "api-key": API_KEY, "format": "json", "limit": 0
                }, timeout=20)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") != "error":
                        record_count = data.get("total", 0)
                        # OGD API sometimes returns the actual UUID in the response even if called by slug
                        resource_id = data.get("resource_id", data.get("id", slug))
                        success = True
                        total_found += 1
                        logger.success(f"  [OK] {dist}: {record_count} records | ID: {resource_id}")
                    else:
                        logger.warning(f"  [FAIL] {dist}: API error - {data.get('message')}")
                else:
                    logger.warning(f"  [FAIL] {dist}: Status {resp.status_code}")
                    
            except Exception as e:
                logger.error(f"  [ERR] {dist}: {e}")
            
            results.append({
                "state": state,
                "district": dist,
                "slug": slug,
                "resource_id": resource_id,
                "total_records": record_count,
                "status": "OK" if success else "FAILED",
                "is_verified": "TRUE" if success else "FALSE"
            })
            
            # Rate limit politeness
            time.sleep(0.3)
            
    # Save results
    df = pd.DataFrame(results)
    manifest_dir = PROJECT_ROOT / "pipeline" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    
    output_name = f"national_slug_probe_results.xlsx" if not limit_state else f"{limit_state.lower()}_slug_probe_results.xlsx"
    output_path = manifest_dir / output_name
    df.to_excel(output_path, index=False)
    
    logger.info(f"Probe complete. Found {total_found}/{total_attempted} resources.")
    logger.info(f"Manifest saved to: {output_path}")
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", help="Limit probe to a specific state (e.g. MAHARASHTRA)")
    args = parser.parse_args()
    
    probe_all_districts(limit_state=args.state)
