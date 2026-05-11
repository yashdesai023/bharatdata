import os
import requests
from dotenv import load_dotenv
from loguru import logger
import json

def test_api_discovery(state_name: str):
    load_dotenv()
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        logger.error("API Key missing")
        return
        
    base_url = "https://api.data.gov.in/resource.json"
    # Filter for titles containing PCA 2011 and the state name
    params = {
        "api-key": api_key,
        "format": "json",
        "filters[title]": f"%Primary Census Abstract 2011 {state_name}%",
        "limit": 100
    }
    
    logger.info(f"Searching API for {state_name} PCA resources...")
    try:
        resp = requests.get(base_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records = data.get("records", [])
        
        print(f"\n--- API DISCOVERY TEST: {state_name} ---")
        print(f"Total Matches Found: {len(records)}")
        
        for i, rec in enumerate(records[:10]):
            print(f"{i+1}. Title: {rec.get('title')}")
            print(f"   ID: {rec.get('index_name')}") # index_name is often the UUID
            
    except Exception as e:
        logger.error(f"API Search failed: {e}")

if __name__ == "__main__":
    test_api_discovery("Bihar")
    test_api_discovery("Maharashtra")
