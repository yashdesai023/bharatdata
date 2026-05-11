import requests
import re
import os

def extract_maharashtra_links():
    url = "https://www.data.gov.in/catalog/villagetown-wise-primary-census-abstract-2011-maharashtra"
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        
        # Look for resource URLs
        urls = re.findall(r'(\/resource\/[^\s\"\'\>]+)', resp.text)
        unique_urls = sorted(list(set(urls)))
        
        print(f"Total Unique Resource URLs found: {len(unique_urls)}")
        for u in unique_urls[:100]:
            print(u)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_maharashtra_links()
