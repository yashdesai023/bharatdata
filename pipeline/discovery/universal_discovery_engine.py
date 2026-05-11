"""
BDIF Universal Discovery Engine (v4)
=====================================
A data-driven resource discovery tool that searches the OGD Catalog API.
Replaces brittle URL probing with robust metadata search.

Logic:
  1. Search OGD Dataset API for Title + Org.
  2. Pick the most relevant Catalog (Dataset).
  3. Extract ALL Resource IDs (UUIDs) from that Catalog.
  4. Use fuzzy matching to map resources to States/Entities.
  5. Generate the local manifest.

Usage:
  python -m pipeline.discovery.universal_discovery_engine --dataset census_2011_pca
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from loguru import logger
from difflib import SequenceMatcher

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.discovery.manifest_generator import ManifestGenerator
from pipeline.discovery.async_probe_engine import ALL_STATES

class UniversalDiscoveryEngine:
    SEARCH_URL = "https://api.data.gov.in/dataset.json"

    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        self.api_key = os.getenv("DATA_GOV_IN_API_KEY")
        if not self.api_key:
            raise ValueError("DATA_GOV_IN_API_KEY not found in environment.")

        # Load definition
        loader = DefinitionLoader(str(PROJECT_ROOT / "pipeline" / "schemas" / "source_definition_schema.yaml"))
        self.definition = loader.load(str(PROJECT_ROOT / "pipeline" / "definitions" / f"{dataset_id}.yaml"))
        self.acq = self.definition["acquisition"]

    def _fuzzy_match_entity(self, title: str, entities: List[str]) -> Optional[str]:
        """Find the best matching entity from a list based on the resource title."""
        best_match = None
        highest_ratio = 0.0
        
        # Clean title for better matching
        clean_title = title.lower().replace("-", " ").replace("_", " ")
        
        for entity in entities:
            # Check if entity is contained in title (strong signal)
            if entity.lower() in clean_title:
                return entity
            
            # Fallback to fuzzy ratio
            ratio = SequenceMatcher(None, entity.lower(), clean_title).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = entity
                
        return best_match if highest_ratio > 0.6 else None

    def search_ogd(self, query: str, filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """General search helper for any OGD API endpoint."""
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 100
        }
        if query:
            params["title"] = query
        if filters:
            for k, v in filters.items():
                params[f"filters[{k}]"] = v

        # Try both 'dataset.json' and 'resource.json'
        # OGD is inconsistent; sometimes one works, sometimes the other.
        for endpoint in ["dataset", "resource"]:
            url = f"https://api.data.gov.in/{endpoint}"
            try:
                logger.info(f"  [API] Querying {url} for '{query}'...")
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("records", [])
                    if records:
                        logger.success(f"  [API] Found {len(records)} records on {endpoint}.")
                        return records
                else:
                    logger.warning(f"  [API] {endpoint} returned {resp.status_code}")
            except Exception as e:
                logger.debug(f"  [API] {endpoint} failed: {e}")
        
        return []

    def run(self):
        """Execute the universal discovery flow."""
        keyword = self.acq.get("search_keyword")
        org = self.definition["identity"].get("ogd_organization")
        
        resource_map = {}
        entities = ALL_STATES if self.acq.get("partition_by") == "state" else ["National"]

        # Strategy 1: Broad Search
        results = self.search_ogd(keyword, filters={"org": org} if org else None)
        if results:
            resource_map.update(self.extract_resources(results))

        # Strategy 2: State-Specific Search (Fallback for missing states)
        missing_entities = [e for e in entities if e not in resource_map]
        if missing_entities:
            logger.info(f"Missing {len(missing_entities)} entities. Trying deterministic probing...")
            
            # Pattern mapping (can be moved to YAML later)
            pattern_template = self.acq.get("deterministic_pattern")
            
            for entity in missing_entities:
                slug = None
                if pattern_template:
                    entity_slug = entity.lower().replace(" ", "-").replace("&", "and")
                    slug = pattern_template.replace("{entity}", entity_slug)
                
                if slug:
                    url = f"https://api.data.gov.in/resource/{slug}"
                    try:
                        resp = requests.get(url, params={"api-key": self.api_key, "format": "json", "limit": 1}, timeout=45)
                        if resp.status_code == 200:
                            resource_map[entity] = slug
                            logger.success(f"  [DETERMINISTIC] {entity} -> {slug}")
                            continue
                    except Exception as e:
                        logger.debug(f"  [DETERMINISTIC] {entity} probe failed: {e}")

                # Fallback to state-specific API query
                state_query = f"{keyword} {entity}"
                state_results = self.search_ogd(state_query)
                if state_results:
                    mapped = self.extract_resources(state_results)
                    resource_map.update(mapped)
                    if entity in resource_map:
                        logger.success(f"  [RESOLVED] {entity}")

        logger.info(f"Discovery Result: {len(resource_map)}/{len(entities)} resolved")
        
        if resource_map:
            gen = ManifestGenerator(self.definition)
            gen.generate(resource_map)
            logger.success(f"Manifest updated: {self.acq['manifest_file']}")
        
        return resource_map

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Discovery Engine")
    parser.add_argument("--dataset", required=True, help="Dataset ID")
    args = parser.parse_args()
    
    from dotenv import load_dotenv
    load_dotenv()
    
    engine = UniversalDiscoveryEngine(args.dataset)
    engine.run()
