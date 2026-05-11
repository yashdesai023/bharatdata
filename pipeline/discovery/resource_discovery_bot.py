"""
BDIF Discovery Engine (Crawl4AI Edition)
------------------------------------------
Uses the Crawl4AI framework to dynamically discover OGD Resource IDs.
Handles searching, paginating, and extracting dataset metadata using
advanced extraction strategies.

Usage:
    python -m pipeline.discovery.resource_discovery_bot --dataset census_2011_pca
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from loguru import logger

from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.discovery.manifest_generator import ManifestGenerator

# ─── Canonical Entity Mapping ─────────────
ALL_STATES = [
    "Andaman & Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh",
    "Assam", "Bihar", "Chandigarh", "Chhattisgarh", "Dadra & Nagar Haveli",
    "Daman & Diu", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jammu & Kashmir", "Jharkhand", "Karnataka", "Kerala", "Lakshadweep",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "NCT of Delhi", "Odisha", "Puducherry", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal"
]

def load_districts() -> List[str]:
    dist_path = PROJECT_ROOT / "pipeline" / "resources" / "census_2011_districts.json"
    if not dist_path.exists():
        return []
    with open(dist_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        all_districts = []
        for state, districts in data.items():
            for dist in districts:
                all_districts.append(f"{dist} ({state})")
        return all_districts

def normalize_entity_name(raw: str, entities: List[str]) -> Optional[str]:
    raw_lower = raw.strip().lower()
    for entity in entities:
        # For districts, they might be formatted like "Nandurbar (Maharashtra)"
        # Match if the core name is in the title
        core_name = entity.split(" (")[0].lower() if " (" in entity else entity.lower()
        if core_name in raw_lower:
            return entity
    return None

class Crawl4AIDiscoveryBot:
    """
    Discovery Bot powered by Crawl4AI framework.
    """
    OGD_BASE = "https://data.gov.in"
    
    def __init__(self, definition: Dict[str, Any], headless: bool = True, seeds: List[str] = None):
        self.definition = definition
        self.headless = headless
        self.seeds = seeds or []
        self.search_keyword = definition["acquisition"]["search_keyword"]
        self.partition_by = definition["acquisition"].get("partition_by", "state")
        self.entities = load_districts() if self.partition_by == "district" else ALL_STATES
        self.resource_map: Dict[str, str] = {}

    async def run(self):
        logger.info(f"Starting Crawl4AI Discovery for: {self.search_keyword}")
        
        # 1. Configure the Crawler
        browser_config = BrowserConfig(
            headless=self.headless,
            user_agent_mode="random", # Use diverse residential-style UAs
        )
        
        # Define Extraction Strategy for Search results
        extraction_strategy = JsonCssExtractionStrategy(
            schema={
                "name": "Dataset Results",
                "baseSelector": "article.search-result, .views-row",
                "fields": [
                    {"name": "title", "selector": "h2 a, h3 a", "type": "text"},
                    {"name": "url", "selector": "h2 a, h3 a", "type": "attribute", "attribute": "href"}
                ]
            }
        )

        run_config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            cache_mode=CacheMode.BYPASS,
            magic=True,                  # Enables automated stealth and bypass
            wait_for_timeout=15000       # OGD is slow
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Strategy A: Use Seeds if provided (Search Bridge)
            if self.seeds:
                logger.info(f"  Starting with {len(self.seeds)} seed URLs from Search Bridge")
                candidates = [{"url": s, "title": s.split("/")[-1]} for s in self.seeds]
            else:
                # Strategy B: Portal Search
                search_url = f"{self.OGD_BASE}/search?query={self.search_keyword.replace(' ', '+')}"
                logger.info(f"  Crawling portal search: {search_url}")
                
                result = await crawler.arun(url=search_url, config=run_config)
                
                if not result.success:
                    logger.error(f"  Crawl failed: {result.error_message}")
                    return self.resource_map

                candidates = json.loads(result.extracted_content)
                logger.info(f"  Extraction successful: {len(candidates)} candidates found.")

            # Step 2: Extract Resource IDs
            for item in candidates:
                title = item.get("title", "")
                url = item.get("url", "")
                if not url.startswith("http"):
                    url = f"{self.OGD_BASE}{url}"

                partition = normalize_entity_name(title, self.entities) if self.partition_by != "national" else "National"
                if not partition or partition in self.resource_map:
                    continue

                logger.info(f"  Visiting potential match: {partition}")
                
                # Detailed Resource ID extraction for this dataset
                res_result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS, wait_for_timeout=5000)
                )
                
                if res_result.success:
                    # Look for UUID in BOTH HTML and Markdown
                    # OGD UUIDs are often in API links or metadata blocks
                    full_source = f"{res_result.html} {res_result.markdown}"
                    
                    # Pattern for UUID - often found after /resource/ or in JSON blocks
                    match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', full_source, re.I)
                    
                    if match:
                        res_id = match.group(0)
                        self.resource_map[partition] = res_id
                        logger.success(f"  [SUCCESS] Discovered {partition}: {res_id}")
                    else:
                        logger.warning(f"  [MISS] No ID found on page: {partition}")
            
        return self.resource_map

import re

async def async_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()

    base_dir = PROJECT_ROOT / "pipeline"
    loader = DefinitionLoader(str(base_dir / "schemas" / "source_definition_schema.yaml"))
    definition = loader.load(str(base_dir / "definitions" / f"{args.dataset}.yaml"))

    bot = Crawl4AIDiscoveryBot(definition, headless=not args.visible)
    resource_map = await bot.run()

    if resource_map:
        ManifestGenerator(definition).generate(resource_map)
        logger.info(f"Manifest generated with {len(resource_map)} resources.")
    else:
        logger.error("No resources found via Crawl4AI.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(async_main())
