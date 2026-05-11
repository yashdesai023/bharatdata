import requests
import os
import json
from dotenv import load_dotenv
from loguru import logger

def research_ogd_bulk():
    """
    Research if the OGD Dataset API can return all granular Census resources in one call.
    """
    load_dotenv()
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        logger.error("API Key not found.")
        return

    # Targeting the broad keyword for the whole Census 2011 PCA hierarchy
    keyword = "Village/Town-wise Primary Census Abstract 2011"
    url = f"https://api.data.gov.in/dataset.json?api-key={api_key}&format=json&filters[title]={keyword}&limit=100"
    
    try:
        logger.info(f"Querying OGD for: {keyword}")
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        count = len(data.get("records", []))
        logger.info(f"Found {count} candidate datasets.")
        
        if count > 0:
            first = data["records"][0]
            logger.info(f"Sample Title: {first.get('title')}")
            # Check if it has resources listed
            resources = first.get("resources", [])
            logger.info(f"Sample contains {len(resources)} sub-resources.")
        
        # Save results for analysis
        with open("pipeline/resources/discovery_research.json", "w") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Research failed: {e}")

if __name__ == "__main__":
    research_ogd_bulk()
