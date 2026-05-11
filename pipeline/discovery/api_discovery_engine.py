"""
Universal API Discovery Engine
------------------------------
Uses OGD Metadata APIs and local district hierarchies to resolve
thousands of Resource IDs programmatically.
"""

import os
import json
import time
import pandas as pd
import yaml
from pathlib import Path
from loguru import logger
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Ensure we can import from the root
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from pipeline.adapters.ogd_api import OGDApiAdapter, OGDApiError

class APIDiscoveryEngine:
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        self.config = self._load_config()
        self.adapter = OGDApiAdapter()
        
        # Paths
        self.resource_dir = Path("pipeline/resources")
        self.manifest_dir = Path("pipeline/manifests")
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        config_path = Path(f"pipeline/definitions/{self.dataset_id}.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Dataset config not found: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _load_districts(self) -> Dict[str, List[str]]:
        districts_path = self.resource_dir / "census_2011_districts.json"
        if not districts_path.exists():
            logger.error(f"Districts JSON not found: {districts_path}")
            return {}
        with open(districts_path, "r") as f:
            return json.load(f)

    def discover(self, target_state: str = None):
        """Main discovery loop."""
        logger.info(f"Starting API Discovery for {self.dataset_id}...")
        
        hierarchy = self._load_districts()
        if not hierarchy:
            logger.error("No district hierarchy found. Aborting.")
            return

        # Get search templates from config
        discovery_settings = self.config.get("discovery_settings", {})
        title_template = discovery_settings.get("title_template")
        
        if not title_template:
            logger.error("No title_template found in dataset config.")
            return

        manifest_data = []

        for state, districts in hierarchy.items():
            if target_state and state.upper() != target_state.upper():
                continue
                
            logger.info(f"Processing State: {state} ({len(districts)} districts)...")
            
            for district in districts:
                # Format search title
                search_title = title_template.format(district=district, state=state)
                
                logger.debug(f"Searching for: {search_title}")
                
                # We use search_resources because PCA is often indexed as individual resources
                results = self.adapter.search_resources(search_title)
                
                if results:
                    # Pick the best match
                    best_match = results[0]
                    resource_id = best_match.get("index_name") or best_match.get("id")
                    
                    logger.success(f"  [FOUND] {district}: {resource_id}")
                    manifest_data.append({
                        "state_name": state,
                        "district_name": district,
                        "resource_id": resource_id,
                        "status": "pending"
                    })
                else:
                    logger.warning(f"  [NOT FOUND] {district}")
                    manifest_data.append({
                        "state_name": state,
                        "district_name": district,
                        "resource_id": "NOT_FOUND",
                        "status": "failed_discovery"
                    })
                
                # Polite delay
                time.sleep(1.0)

        # Save results... (rest of the code)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--state", help="Limit discovery to a specific state")
    args = parser.parse_args()

    engine = APIDiscoveryEngine(args.dataset)
    engine.discover(target_state=args.state)

