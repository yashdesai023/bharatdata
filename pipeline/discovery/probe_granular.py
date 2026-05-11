"""
OGD Deterministic Prober (Census 2011 Granular)
==============================================
Attempts to resolve Resource IDs for granular Census 2011 PCA data
by testing hypothesized slug patterns.

Pattern: village-town-wise-primary-census-abstract-2011-{state_slug}
"""

import requests
import time
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DATA_GOV_IN_API_KEY")
BASE_URL = "https://api.data.gov.in/resource"

STATES = [
    "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal-pradesh", "jammu-kashmir",
    "jharkhand", "karnataka", "kerala", "madhya-pradesh", "maharashtra",
    "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil-nadu", "tripura", "uttar-pradesh",
    "uttarakhand", "west-bengal", "andaman-nicobar", "chandigarh",
    "dadra-nagar-haveli", "daman-diu", "delhi", "lakshadweep", "puducherry",
    "telangana"
]

def probe():
    results = {}
    for state in STATES:
        slug = f"village-town-wise-primary-census-abstract-2011-{state}"
        url = f"{BASE_URL}/{slug}"
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 1
        }
        
        try:
            logger.info(f"Probing: {slug}...")
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                logger.success(f"  [FOUND] {state} -> {slug}")
                results[state] = slug
            elif resp.status_code == 502:
                logger.warning(f"  [TIMEOUT/502] OGD is struggling. Retrying in 5s...")
                time.sleep(5)
                # One retry
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    logger.success(f"  [FOUND] {state} -> {slug}")
                    results[state] = slug
            else:
                logger.error(f"  [NOT FOUND] {state} (Code: {resp.status_code})")
            
            time.sleep(1) # Be nice to OGD
        except Exception as e:
            logger.error(f"  [ERROR] {state}: {e}")
    
    logger.info(f"Results: {len(results)}/{len(STATES)} discovered.")
    return results

if __name__ == "__main__":
    probe()
