import requests
import re
import json
import os
import difflib
import time
from dotenv import load_dotenv
from loguru import logger
from typing import List, Dict, Optional

from urllib3.util import Retry
from requests.adapters import HTTPAdapter

class DiscoveryCrawler:
    """
    Crawls the OGD Portal to resolve Resource IDs for district-level Census PCA data.
    Uses fuzzy matching to handle spelling discrepancies and robust session handling for timeouts.
    """
    
    BASE_URL = "https://www.data.gov.in"
    RE_RESOURCE_ID = r'"resource_id":"([a-f0-9\-]{36})"'
    
    def __init__(self, districts_json_path: str):
        with open(districts_json_path, "r") as f:
            self.districts_data = json.load(f)
        self.manifest = {}
        self.session = requests.Session()
        
        # Configure Retries
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def resolve_state_catalog(self, state_name: str) -> List[Dict]:
        """
        Visits the OGD Catalog page for a state and extracts all resource links.
        """
        search_url = f"{self.BASE_URL}/catalogs?title=Village/Town-wise Primary Census Abstract 2011 {state_name}"
        logger.info(f"Searching catalog for state: {state_name}...")
        
        try:
            # Use 120s timeout for the flaky OGD portal
            resp = self.session.get(search_url, timeout=120)
            resp.raise_for_status()
                
            # Find the first catalog link
            catalog_match = re.search(fr'href="(/catalogs/villagetown-wise-primary-census-abstract-2011-{state_name.lower().replace(" ", "-")}[^"]*)"', resp.text)
            if not catalog_match:
                catalog_match = re.search(r'href="(/catalogs/[^"]+)"', resp.text)
            
            if catalog_match:
                catalog_url = self.BASE_URL + catalog_match.group(1)
                logger.info(f"Found Catalog: {catalog_url}")
                return self._parse_catalog_resources(catalog_url)
            else:
                logger.warning(f"No catalog found for {state_name}. Trying search parse.")
                return self._parse_search_resources(search_url)
                    
        except Exception as e:
            logger.error(f"Failed to resolve state catalog for {state_name}: {e}")
            return []

    def _parse_catalog_resources(self, catalog_url: str) -> List[Dict]:
        """
        Parses all resource links from a catalog page.
        """
        resp = self.session.get(catalog_url, timeout=120)
        # Links are like /resource/villagetown-wise-primary-census-abstract-2011-purnia-district-bihar
        links = re.findall(r'href="(/resource/villagetown-wise-primary-census-abstract-2011-([^"]+)-district-[^"]+)"', resp.text)
        
        resources = []
        for href, dist_slug in links:
            resources.append({
                "slug": href.split("/")[-1],
                "district_slug": dist_slug.replace("-", " ").title(),
                "url": self.BASE_URL + href
            })
        return resources

    def _parse_search_resources(self, search_url: str) -> List[Dict]:
        """Fallback: Parse resources directly from search results."""
        resp = self.session.get(search_url, timeout=120)
        links = re.findall(r'href="(/resource/villagetown-wise-primary-census-abstract-2011-([^"]+)-district-[^"]+)"', resp.text)
        return [{"slug": h.split("/")[-1], "district_slug": d.replace("-", " ").title(), "url": self.BASE_URL+h} for h, d in links]

    def resolve_district_id(self, target_district: str, available_resources: List[Dict]) -> Optional[str]:
        """
        Matches a target district name against available resources using fuzzy matching.
        Then visits the resource page to get the UUID.
        """
        dist_names = [r["district_slug"] for r in available_resources]
        matches = difflib.get_close_matches(target_district, dist_names, n=1, cutoff=0.6)
        
        if not matches:
            return None
            
        best_match = matches[0]
        resource = next(r for r in available_resources if r["district_slug"] == best_match)
        
        logger.debug(f"Resolved '{target_district}' to '{best_match}'")
        
        # Now get the UUID
        try:
            r_resp = self.session.get(resource["url"], timeout=120)
            uuid_match = re.search(self.RE_RESOURCE_ID, r_resp.text)
            if uuid_match:
                return uuid_match.group(1)
        except Exception as e:
            logger.error(f"Failed to get UUID for {best_match}: {e}")
            
        return None

    def discover_state(self, state_name: str) -> Dict:
        """
        Orchestrates discovery for an entire state.
        """
        districts = self.districts_data.get(state_name.upper())
        if districts is None:
            logger.error(f"State {state_name} not found in districts JSON")
            return {}
            
        available_resources = self.resolve_state_catalog(state_name)
        results = {"state": state_name, "total_districts": len(districts), "resolved": 0, "discrepancies": [], "mapping": {}}
        
        for district in districts:
            uuid = self.resolve_district_id(district, available_resources)
            if uuid:
                results["mapping"][district] = uuid
                results["resolved"] += 1
            else:
                results["discrepancies"].append(district)
                
        return results

if __name__ == "__main__":
    crawler = DiscoveryCrawler("pipeline/resources/census_2011_districts.json")
    
    # Trial add two states: Bihar and Maharashtra
    states_to_test = ["BIHAR", "MAHARASHTRA"]
    final_report = []
    
    all_mapping = {}
    
    # Hardcoded seeds for Pilot to bypass flaky OGD search
    CATALOG_SEEDS = {
        "BIHAR": "https://www.data.gov.in/catalog/villagetown-wise-primary-census-abstract-2011-bihar",
        "MAHARASHTRA": "https://www.data.gov.in/catalog/villagetown-wise-primary-census-abstract-2011-maharashtra"
    }

    for state in states_to_test:
        if state in CATALOG_SEEDS:
            logger.info(f"Using Seed Catalog for {state}: {CATALOG_SEEDS[state]}")
            available_resources = crawler._parse_catalog_resources(CATALOG_SEEDS[state])
            
            districts = crawler.districts_data.get(state.upper())
            report = {"state": state, "total_districts": len(districts), "resolved": 0, "discrepancies": [], "mapping": {}}
            
            for district in districts:
                uuid = crawler.resolve_district_id(district, available_resources)
                if uuid:
                    report["mapping"][district] = uuid
                    report["resolved"] += 1
                else:
                    report["discrepancies"].append(district)
            
            final_report.append(report)
            all_mapping.update(report["mapping"])
        else:
            report = crawler.discover_state(state)
            final_report.append(report)
            all_mapping.update(report["mapping"])
        
    # Save the temporary manifest
    with open("pipeline/resources/trial_manifest.json", "w") as f:
        json.dump(all_mapping, f, indent=2)
        
    # Final Output for User
    print("\n--- DISCOVERY TRIAL REPORT ---")
    for r in final_report:
        print(f"State: {r['state']}")
        print(f"  Expected Districts: {r['total_districts']}")
        print(f"  Resolved Resource IDs: {r['resolved']}")
        if r['discrepancies']:
            print(f"  Failed (Discrepancies): {', '.join(r['discrepancies'])}")
    print("------------------------------\n")
