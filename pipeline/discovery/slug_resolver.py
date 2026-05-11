import requests
import re
import json
from loguru import logger

def resolve_uuid(slug: str) -> str:
    """
    Scrapes the OGD portal page for a resource slug and extracts the internal Resource UUID.
    """
    url = f"https://www.data.gov.in/resource/{slug}"
    try:
        logger.debug(f"Probing {url}...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        # OGD often embeds the resource_id in the JSON-LD or druidSettings JS block
        # Pattern: "resource_id":"ce76bb8c-2eaa-4f32-a6bd-fa2338321a46"
        match = re.search(r'"resource_id":"([a-f0-9\-]{36})"', resp.text)
        if match:
            return match.group(1)
            
        # Fallback: Look for the API tab URL in the source
        match = re.search(r'/resource/([a-f0-9\-]{36})', resp.text)
        if match:
            return match.group(1)
            
        return None
    except Exception as e:
        logger.error(f"Failed to resolve UUID for {slug}: {e}")
        return None

if __name__ == "__main__":
    test_slug = "villagetown-wise-primary-census-abstract-2011-purnia-district-bihar"
    uuid = resolve_uuid(test_slug)
    if uuid:
        print(f"SUCCESS: {uuid}")
    else:
        print("FAILED")
