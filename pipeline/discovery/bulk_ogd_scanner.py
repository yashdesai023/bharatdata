import requests
import os
import json
import time
from dotenv import load_dotenv
from loguru import logger

def bulk_scan_ogd(keyword: str, limit: int = 1000):
    """
    Queries the OGD Dataset API for all datasets matching a keyword.
    """
    load_dotenv()
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        logger.error("DATA_GOV_IN_API_KEY not found in .env")
        return

    url = "https://api.data.gov.in/dataset.json"
    params = {
        "api-key": api_key,
        "format": "json",
        "filters[title]": keyword,
        "limit": limit
    }

    try:
        logger.info(f"Scanning OGD for keyword: {keyword}...")
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        records = data.get("records", [])
        logger.success(f"Discovered {len(records)} matching datasets.")
        
        # Save to a temporary research file
        output_path = "pipeline/resources/ogd_discovery_results.json"
        with open(output_path, "w") as f:
            json.dump(records, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")

if __name__ == "__main__":
    bulk_scan_ogd("Village/Town-wise Primary Census Abstract, 2011")
