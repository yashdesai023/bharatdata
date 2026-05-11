import os
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import re

# FOLDER STRUCTURE
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_PATH = os.path.join(BASE_DIR, "data", "raw", "census-2011", "data-resource", "census_2011_registry_template.xlsx")
LOG_PATH = os.path.join(BASE_DIR, "pipeline", "logs", "discovery_log.txt")

STATES = [
    "Andaman & Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra & Nagar Haveli", "Daman & Diu", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir", "Jharkhand",
    "Karnataka", "Kerala", "Lakshadweep", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "NCT of Delhi", "Odisha",
    "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

def log(message):
    with open(LOG_PATH, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    print(message)

def run_discovery():
    log("Starting OGD Resource Discovery bot...")
    
    with sync_playwright() as p:
        # USE A PROPER USER AGENT TO AVOID BLOCKING
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        resource_map = {}
        
        # USE EXTENDED TIMEOUTS FOR OGD PORTAL LAG
        page.set_default_timeout(90000)
        
        # Use the correct production search endpoint with a retry loop
        search_url = "https://data.gov.in/search?query=Primary+Census+Abstract+2011"
        max_retries = 3
        for i in range(max_retries):
            try:
                log(f"Navigating to OGD (Attempt {i+1})...")
                page.goto(search_url, wait_until="load", timeout=90000)
                log(f"Successfully arrived at: {page.title()}")
                break
            except Exception as e:
                log(f"  [RETRY] Navigation failed: {e}")
                if i == max_retries - 1: raise e
                time.sleep(5)
        
        page_num = 1
        while page_num <= 10: # Limit to 10 pages for safety
            log(f"Processing Search Page {page_num}...")
            
            # Wide Net approach: Scan all links for /resource/ and match state names
            links = page.query_selector_all("a")
            for link_elem in links:
                try:
                    title = link_elem.inner_text().strip()
                    href = link_elem.get_attribute("href")
                    
                    if not href or "/resource/" not in href:
                        continue
                        
                    # Match state
                    matched_state = None
                    for state in STATES:
                        if state.lower() in title.lower():
                            matched_state = state
                            break
                    
                    if matched_state:
                        # Extract Resource ID (usually the last part of a resource URL)
                        res_id = href.split("/")[-1]
                        if len(res_id) > 20 and matched_state not in resource_map:
                            resource_map[matched_state] = res_id
                            log(f"  [FOUND] {matched_state}: {res_id}")
                except:
                    continue
            
            # Try next page
            next_btn = page.query_selector(".pager-next a") or page.query_selector("a:has-text('Next')")
            if next_btn:
                try:
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=30000)
                    page_num += 1
                except:
                    break
            else:
                break
                
        browser.close()
        
        # UPDATE EXCEL
        if resource_map:
            log(f"Updating Excel with {len(resource_map)} discovered IDs...")
            df = pd.read_excel(TEMPLATE_PATH)
            for state, res_id in resource_map.items():
                # Only update if current cell is empty/nan
                idx = df[df['state_name'] == state].index
                if not idx.empty:
                    if pd.isna(df.loc[idx[0], 'resource_id']) or df.loc[idx[0], 'resource_id'] == "":
                        df.loc[idx[0], 'resource_id'] = res_id
            
            df.to_excel(TEMPLATE_PATH, index=False)
            log("Excel Registry successfully updated.")
        else:
            log("No new Resource IDs discovered.")

if __name__ == "__main__":
    run_discovery()
