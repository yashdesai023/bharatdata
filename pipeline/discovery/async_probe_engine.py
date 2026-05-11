"""
BDIF Async URL Probe Engine (Phase 7 v3)
=========================================
Universal resource discovery for data.gov.in datasets.
No browser. No LLM. No cloud accounts. Pure async HTTP.

Strategy:
  1. For each partition entity (state/district/national), generate all
     known URL slug variants deterministically.
  2. Probe all variants concurrently via aiohttp.
  3. Extract UUID from HTML of successful (non-404) responses.
  4. Return resource_map → ManifestGenerator writes the Excel manifest.

Usage:
  python -m pipeline.discovery.async_probe_engine --dataset census_2011_pca
"""

import sys
import re
import asyncio
import argparse
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.discovery.manifest_generator import ManifestGenerator

# ── Configuration ─────────────────────────────────────────────────────
CONCURRENCY     = 8           # Reduced: OGD throttles aggressive probing
REQUEST_TIMEOUT = 45          # Increased: OGD portal pages are slow (933KB)
OGD_BASE        = "https://data.gov.in/resource"   # HTML portal — NOT api.data.gov.in

UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.IGNORECASE
)

# ── Canonical Entity Lists ───────────────────────────────────────────
ALL_STATES = [
    "Andaman & Nicobar Islands", "Andhra Pradesh",  "Arunachal Pradesh",
    "Assam",                     "Bihar",            "Chandigarh",
    "Chhattisgarh",              "Dadra & Nagar Haveli", "Daman & Diu",
    "Goa",                       "Gujarat",          "Haryana",
    "Himachal Pradesh",          "Jammu & Kashmir",  "Jharkhand",
    "Karnataka",                 "Kerala",           "Lakshadweep",
    "Madhya Pradesh",            "Maharashtra",      "Manipur",
    "Meghalaya",                 "Mizoram",          "Nagaland",
    "NCT of Delhi",              "Odisha",           "Puducherry",
    "Punjab",                    "Rajasthan",        "Sikkim",
    "Tamil Nadu",                "Tripura",          "Uttar Pradesh",
    "Uttarakhand",               "West Bengal"
]

def load_districts() -> list[str]:
    dist_path = PROJECT_ROOT / "pipeline" / "resources" / "census_2011_districts.json"
    if not dist_path.exists():
        logger.error(f"District resource not found: {dist_path}")
        return []
    import json
    with open(dist_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        all_districts = []
        for state, districts in data.items():
            state_title = state.title()
            for dist in districts:
                # Format for slug: "Nandurbar district Maharashtra"
                all_districts.append(f"{dist} district {state_title}")
        return all_districts

# States where OGD uses a different slug than the canonical name
SLUG_OVERRIDES: dict[str, list[str]] = {
    "Andaman & Nicobar Islands": ["andaman-and-nicobar-islands", "andaman-nicobar-islands"],
    "NCT of Delhi":              ["delhi", "nct-delhi", "nct-of-delhi"],
    "Jammu & Kashmir":           ["jammu-and-kashmir", "jammu-kashmir"],
    "Dadra & Nagar Haveli":      ["dadra-and-nagar-haveli", "dadra-nagar-haveli"],
    "Daman & Diu":               ["daman-and-diu", "daman-diu"],
}

# URL prefix patterns — loaded from YAML if provided, else used as fallback.
# ORDER MATTERS: First match wins. Granular patterns MUST come before Summary.
URL_PREFIXES = [
    # ── GRANULAR (Village/Town-wise) — target dataset ────────────────
    "villagetown-wise-primary-census-abstract-2011-{slug}",   # ← CORRECTED SLUG
    "village-town-wise-primary-census-abstract-2011-{slug}",
    "villagetown-wise-pca-2011-{slug}",
    "villagetown-wise-primary-census-abstract-{slug}-2011",
    # ── SUMMARY (District/State level) — fallback ────────────────────
    "primary-census-abstract-2011-{slug}",
    "census-2011-primary-census-abstract-{slug}",
    "pca-2011-{slug}",
]


def to_slug(name: str) -> str:
    return (name.lower()
            .replace(" & ", "-and-")
            .replace(" ", "-")
            .replace(",", "")
            .replace("(", "")
            .replace(")", ""))


def generate_urls(state: str) -> list[str]:
    base_slug = to_slug(state)
    slugs = [base_slug] + SLUG_OVERRIDES.get(state, [])
    return [
        f"{OGD_BASE}/{prefix.format(slug=slug)}"
        for prefix in URL_PREFIXES
        for slug in slugs
    ]


async def probe_url(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(
            url,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            # OGD redirects 404s to a /not-found page — detect both ways
            if "not-found" in str(resp.url) or resp.status != 200:
                return None
            text = await resp.text(errors="replace")
            # OGD embeds the API UUID in the page HTML — extract it
            m = UUID_RE.search(text)
            if m:
                return m.group(0)
            # No UUID found — page likely exists but has no API key embedded
            return None
    except asyncio.TimeoutError:
        logger.debug(f"[TIMEOUT] {url}")
        return None
    except Exception as e:
        logger.debug(f"[ERR] {url}: {e}")
        return None


async def discover_entity(
    session: aiohttp.ClientSession,
    entity: str,
    semaphore: asyncio.Semaphore
) -> tuple[str, Optional[str]]:
    urls = generate_urls(entity)
    async with semaphore:
        for url in urls:
            uuid = await probe_url(session, url)
            if uuid:
                logger.success(f"[FOUND] {entity}: {uuid}")
                return entity, uuid
    logger.warning(f"[MISS]  {entity}: exhausted all URL variants")
    return entity, None


async def run_discovery(entities: list[str], concurrency: int = CONCURRENCY) -> dict[str, str]:
    semaphore = asyncio.Semaphore(concurrency)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BharatData/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with aiohttp.ClientSession(
        headers=headers,
        connector=aiohttp.TCPConnector(limit=concurrency, ssl=False)
    ) as session:
        tasks = [discover_entity(session, e, semaphore) for e in entities]
        results = await asyncio.gather(*tasks)
    return {entity: uid for entity, uid in results if uid}


async def async_main(dataset_id: str, concurrency: int):
    base_dir = PROJECT_ROOT / "pipeline"
    loader = DefinitionLoader(str(base_dir / "schemas" / "source_definition_schema.yaml"))
    definition = loader.load(str(base_dir / "definitions" / f"{dataset_id}.yaml"))

    partition_by = definition["acquisition"].get("partition_by", "state")
    if partition_by == "state":
        entities = ALL_STATES
    elif partition_by == "district":
        entities = load_districts()
    else:
        entities = ["National"]

    # Allow YAML to override URL prefixes for universality (any dataset)
    yaml_prefixes = definition["acquisition"].get("url_prefixes")
    if yaml_prefixes:
        global URL_PREFIXES
        URL_PREFIXES = yaml_prefixes
        logger.info(f"Using YAML-defined URL_PREFIXES ({len(URL_PREFIXES)} patterns)")

    logger.info(f"Async Probe Engine v3: {definition['identity']['name']}")
    logger.info(f"Target: {len(entities)} entities | Concurrency: {concurrency}")
    logger.info(f"Probing portal: {OGD_BASE}")

    resource_map = await run_discovery(entities, concurrency)

    found = len(resource_map)
    total = len(entities)
    logger.info(f"Discovery complete: {found}/{total} resolved ({found/total*100:.0f}%)")

    if resource_map:
        ManifestGenerator(definition).generate(resource_map)
        logger.success(f"Manifest written with {found} Resource IDs")
        logger.info("Next step: python -m pipeline.core.orchestrator --dataset census_2011_pca --dry-run")
    else:
        logger.error("No resources found — check URL_PREFIXES for this dataset type")

    return resource_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BDIF Async Probe Engine")
    parser.add_argument("--dataset",     required=True)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    args = parser.parse_args()
    asyncio.run(async_main(args.dataset, args.concurrency))
