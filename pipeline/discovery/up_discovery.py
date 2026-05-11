import os
import time
import requests
import pandas as pd
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_KEY = os.getenv("DATA_GOV_IN_API_KEY")
BASE_URL = "https://api.data.gov.in/resource"

# Hardcoded Uttar Pradesh Districts
UP_DISTRICTS = [
    "Agra", "Aligarh", "Allahabad", "Ambedkar Nagar", "Auraiya", "Azamgarh", 
    "Baghpat", "Bahraich", "Ballia", "Balrampur", "Banda", "Barabanki", 
    "Bareilly", "Basti", "Bijnor", "Budaun", "Bulandshahr", "Chandauli", 
    "Chitrakoot", "Deoria", "Etah", "Etawah", "Faizabad", "Farrukhabad", 
    "Fatehpur", "Firozabad", "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", 
    "Gonda", "Gorakhpur", "Hamirpur", "Hardoi", "Jalaun", "Jaunpur", "Jhansi", 
    "Jyotiba Phule Nagar", "Kannauj", "Kanpur Dehat", "Kanpur Nagar", 
    "Kanshiram Nagar", "Kaushambi", "Kheri", "Kushinagar", "Lalitpur", 
    "Lucknow", "Maharajganj", "Mahamaya Nagar", "Mahoba", "Mainpuri", 
    "Mathura", "Mau", "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", 
    "Pilibhit", "Pratapgarh", "Rae Bareli", "Rampur", "Saharanpur", 
    "Sant Kabir Nagar", "Sant Ravidas Nagar (Bhadohi)", "Shahjahanpur", 
    "Shrawasti", "Siddharthnagar", "Sitapur", "Sonbhadra", "Sultanpur", 
    "Unnao", "Varanasi"
]

STATE = "UTTAR PRADESH"

# Multiple common OGD slug patterns
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

def probe_with_backoff(url: str, params: dict, max_retries: int = 5) -> dict:
    """Probe OGD API with exponential backoff. Handles 429/502/503/504."""
    wait = 3
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=60, verify=False)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") != "error":
                    return data
                else:
                    return {"status": "error", "message": "Meta not found"}
            
            elif resp.status_code in (429, 502, 503, 504):
                logger.warning(f"    [RETRY {attempt}/{max_retries}] Status {resp.status_code} — waiting {wait}s")
                time.sleep(wait)
                wait *= 2
            
            else:
                logger.error(f"    [SKIP] Unrecoverable status {resp.status_code}")
                return {}
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"    [RETRY {attempt}/{max_retries}] {type(e).__name__} — waiting {wait}s")
            time.sleep(wait)
            wait *= 2
    
    logger.error(f"    [FAILED] Exhausted {max_retries} retries for URL: {url}")
    return {}

def run_up_probe():
    results = []
    total_districts = len(UP_DISTRICTS)
    state_slug = to_slug(STATE)
    
    logger.info(f"Starting standalone probe for {STATE} ({total_districts} districts)...")
    
    for i, dist in enumerate(UP_DISTRICTS, 1):
        dist_slug = to_slug(dist)
        found_this_dist = False
        
        # Try each slug pattern
        for pattern in SLUG_PATTERNS:
            slug = pattern.format(dist=dist_slug, state=state_slug)
            url = f"{BASE_URL}/{slug}"
            
            params = {"api-key": API_KEY, "format": "json", "limit": 0}
            data = probe_with_backoff(url, params)
            
            if data.get("status") == "ok" or (data.get("total") is not None and data.get("status") != "error"):
                record_count = data.get("total", 0)
                resource_id = data.get("resource_id", data.get("id", slug))
                logger.success(f"  [{i}/{total_districts}] {dist}: {record_count} records (Found via {pattern.split('{')[0]}...)")
                results.append({
                    "state": STATE, "district": dist, "slug": slug,
                    "resource_id": resource_id, "total_records": record_count,
                    "status": "OK", "is_verified": "TRUE", "method": "slug_direct"
                })
                found_this_dist = True
                break
                
        if not found_this_dist:
            logger.error(f"  [{i}/{total_districts}] {dist}: NOT FOUND (Tried all patterns)")
            results.append({
                "state": STATE, "district": dist, "slug": "NOT_FOUND",
                "resource_id": "NOT_FOUND", "total_records": 0, "status": "FAILED", "is_verified": "FALSE"
            })
        
        # Mandatory 1.5s delay to avoid triggering 502s
        time.sleep(1.5)

    # Save results
    df = pd.DataFrame(results)
    manifest_dir = PROJECT_ROOT / "pipeline" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = manifest_dir / "up_discovery_results.xlsx"
    df.to_excel(output_path, index=False)
    
    success_count = len(df[df.status == "OK"])
    logger.info(f"Discovery Complete for UP. Found {success_count}/{total_districts} resources.")
    logger.info(f"Manifest saved to: {output_path}")

if __name__ == "__main__":
    run_up_probe()
