"""
Census 2011 PCA Discovery Runner
--------------------------------
Feeds the 36 discovered seed URLs into the Crawl4AI Discovery Engine.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.discovery.resource_discovery_bot import Crawl4AIDiscoveryBot
from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.discovery.manifest_generator import ManifestGenerator
from loguru import logger

SEEDS = [
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-andaman-nicobar-islands",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-andhra-pradesh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-arunachal-pradesh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-assam",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-bihar",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-chandigarh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-chhattisgarh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-dadra-nagar-haveli",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-daman-diu",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-delhi",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-goa",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-gujarat",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-haryana",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-himachal-pradesh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-jammu-kashmir",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-jharkhand",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-karnataka",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-kerala",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-lakshadweep",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-madhya-pradesh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-maharashtra",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-manipur",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-meghalaya",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-mizoram",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-nagaland",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-odisha",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-puducherry",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-punjab",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-rajasthan",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-sikkim",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-tamil-nadu",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-telangana",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-tripura",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-uttar-pradesh",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-uttarakhand",
    "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-west-bengal"
]

async def main():
    loader = DefinitionLoader(str(PROJECT_ROOT / "pipeline" / "schemas" / "source_definition_schema.yaml"))
    definition = loader.load(str(PROJECT_ROOT / "pipeline" / "definitions" / "census_2011_pca.yaml"))

    bot = Crawl4AIDiscoveryBot(definition, headless=False, seeds=SEEDS)
    resource_map = await bot.run()

    if resource_map:
        ManifestGenerator(definition).generate(resource_map)
        logger.success(f"Final Manifest generated with {len(resource_map)} resources.")
    else:
        logger.error("No resources found.")

if __name__ == "__main__":
    asyncio.run(main())
