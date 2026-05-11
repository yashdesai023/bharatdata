import requests
import os
import json
from loguru import logger

def verify_canonical_links():
    """
    Verifies if state catalogs can be reached via canonical slugs.
    """
    states = ["bihar", "maharashtra"]
    results = {}
    
    for state in states:
        url = f"https://www.data.gov.in/catalogs/villagetown-wise-primary-census-abstract-2011-{state}"
        try:
            logger.info(f"Checking {state} at {url}...")
            resp = requests.get(url, timeout=30)
            results[state] = resp.status_code
            if resp.status_code == 200:
                logger.success(f"Confirmed: {state} catalog found.")
            else:
                logger.warning(f"Failed: {state} returned {resp.status_code}")
        except Exception as e:
            logger.error(f"Error checking {state}: {e}")
            results[state] = str(e)
            
    return results

if __name__ == "__main__":
    verify_canonical_links()
