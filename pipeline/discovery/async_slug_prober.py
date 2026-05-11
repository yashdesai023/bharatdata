import os
import time
import json
import requests
import pandas as pd
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_KEY = os.getenv("DATA_GOV_IN_API_KEY")
BASE_URL = "https://api.data.gov.in/resource"

# Multiple common OGD slug patterns for Census 2011
SLUG_PATTERNS = [
    "villagetown-wise-primary-census-abstract-2011-{dist}-district-{state}",
    "villagetown-wise-primary-census-abstract-2011-{dist}-district-of-{state}"
]

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
        logger.error(f"Districts file not found: {dist_path}")
        return {}
    with open(dist_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def probe_with_backoff(url: str, params: dict, max_retries: int = 5) -> dict:
    """Probe OGD API with exponential backoff. Handles 429/502/503/504."""
    wait = 3  # Start with 3 second wait
    
    for attempt in range(1, max_retries + 1):
        try:
            # Using verify=False to bypass SSL issues during outages, matching our previous logic
            resp = requests.get(url, params=params, timeout=60, verify=False)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") != "error":
                    return data
                else:
                    # Specific OGD "Meta not found" error - pattern failed, don't retry
                    return {"status": "error", "message": "Meta not found"}
            
            elif resp.status_code in (429, 502, 503, 504):
                logger.warning(f"    [RETRY {attempt}/{max_retries}] Status {resp.status_code} — waiting {wait}s")
                time.sleep(wait)
                wait *= 2  # Exponential backoff: 3 → 6 → 12 → 24 → 48
            
            else:
                logger.error(f"    [SKIP] Unrecoverable status {resp.status_code}")
                return {}
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"    [RETRY {attempt}/{max_retries}] {type(e).__name__} — waiting {wait}s")
            time.sleep(wait)
            wait *= 2
    
    logger.error(f"    [FAILED] Exhausted {max_retries} retries for URL: {url}")
    return {}

def run_national_probe(limit_state=None):
    districts_data = load_all_districts()
    results = []
    
    # Track states for sequential processing
    target_states = [limit_state] if limit_state else list(districts_data.keys())
    
    total_to_process = sum(len(districts_data[s]) for s in target_states if s in districts_data)
    processed_count = 0

    logger.info(f"Starting sequential probe for {len(target_states)} states ({total_to_process} districts)...")

    for state in target_states:
        if state not in districts_data:
            continue
            
        logger.info(f">>> Processing State: {state}")
        state_slug = to_slug(state)
        
        for dist in districts_data[state]:
            processed_count += 1
            dist_slug = to_slug(dist)
            found_this_dist = False
            
            # Try each slug pattern sequentially
            for pattern in SLUG_PATTERNS:
                slug = pattern.format(dist=dist_slug, state=state_slug)
                url = f"{BASE_URL}/{slug}"
                
                params = {"api-key": API_KEY, "format": "json", "limit": 0}
                data = probe_with_backoff(url, params)
                
                if data.get("status") == "ok" or data.get("total") is not None and data.get("status") != "error":
                    record_count = data.get("total", 0)
                    resource_id = data.get("resource_id", data.get("id", slug))
                    logger.success(f"  [{processed_count}/{total_to_process}] {dist}: {record_count} records")
                    results.append({
                        "state": state, "district": dist, "slug": slug,
                        "resource_id": resource_id, "total_records": record_count,
                        "status": "OK", "is_verified": "TRUE", "method": "slug_direct"
                    })
                    found_this_dist = True
                    break # Success! Skip other patterns for this district
                
                # If we get here, this pattern failed (likely Meta Not Found)
                # Continue to next pattern
            
            if not found_this_dist:
                logger.error(f"  [{processed_count}/{total_to_process}] {dist}: NOT FOUND (Tried all patterns)")
                results.append({
                    "state": state, "district": dist, "slug": "NOT_FOUND",
                    "resource_id": "NOT_FOUND", "total_records": 0, "status": "FAILED", "is_verified": "FALSE"
                })
            
            # CRITICAL: Mandatory delay to respect OGD rate limits
            time.sleep(1.5)

    # Save results
    df = pd.DataFrame(results)
    manifest_dir = PROJECT_ROOT / "pipeline" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    
    output_name = "national_discovery_results.xlsx" if not limit_state else f"{limit_state.lower()}_discovery_results.xlsx"
    output_path = manifest_dir / output_name
    df.to_excel(output_path, index=False)
    
    success_count = len(df[df.status == "OK"])
    logger.info(f"Discovery Complete. Found {success_count}/{len(df)} resources.")
    logger.info(f"Manifest saved to: {output_path}")
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", help="Limit to state")
    args = parser.parse_args()
    
    # Disable warnings for SSL verification bypass
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    run_national_probe(limit_state=args.state)
