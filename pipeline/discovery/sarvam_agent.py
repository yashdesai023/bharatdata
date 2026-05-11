"""
Sarvam AI Discovery Agent
-------------------------
Replaces fragile web scrapers by fetching the raw JSON catalog from data.gov.in
and using the Sarvam-M model to semantically identify and map accurate Resource IDs.
Handles Indic spelling variations, strictly maps state/entity names, and filters out non-data files (e.g., PDFs).

UPGRADE: Accuracy-First logic injected to prevent granularity mismatch.
"""

import os
import json
import yaml
import requests
from pathlib import Path
from loguru import logger
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# Ensure we can import from the pipeline package
import sys
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from pipeline.adapters.ogd_api import OGDApiAdapter

load_dotenv()

class SarvamAgent:
    SARVAM_ENDPOINT = "https://api.sarvam.ai/v1/chat/completions"
    SARVAM_MODEL = "sarvam-m"

    def __init__(self, sarvam_api_key: str = None, ogd_api_key: str = None):
        self.sarvam_key = sarvam_api_key or os.getenv("SARVAM_API_KEY")
        self.ogd_key = ogd_api_key or os.getenv("DATA_GOV_IN_API_KEY")
        
        if not self.sarvam_key:
            logger.warning("SARVAM_API_KEY not found. Agent will fail if called.")
        
        # Initialize the OGD adapter for verified probing
        self.adapter = OGDApiAdapter(api_key=self.ogd_key)
            
        # Ensure temp_mappings dir exists
        self.temp_dir = Path(__file__).resolve().parent / "temp_mappings"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def search_catalog(self, keyword: str = "", org_id: str = None, deterministic_pattern: str = None) -> list:
        """
        Hits the OGD API to find candidate resources.
        Uses the OGDApiAdapter's search_resources for reliability.
        [Fix 1]: FAILS LOUDLY and supports Organization & Deterministic fallbacks.
        """
        logger.info(f"Searching OGD Catalog for '{keyword}' (Org: {org_id})")
        
        try:
            # 1. Primary: Exact Title search
            records = self.adapter.search_resources(title=keyword)
            
            # 2. Secondary: Organization-based discovery if title search fails
            if not records and org_id:
                logger.warning("No records for exact title. Falling back to Organization search...")
                org_records = self.adapter.search_resources(title=None, organization=org_id)
                # Filter for relevant PCA keywords semantically in Python
                records = [r for r in org_records if "Primary Census Abstract" in r.get("title", "")]
                logger.info(f"Found {len(records)} relevant records under Organization: {org_id}")

            # 3. Tertiary: Nuclear Option - Deterministic Slug Probing (Experimental but reliable for Census)
            if not records and deterministic_pattern:
                logger.warning(f"Searching failed. Attempting Deterministic Slug Probing using pattern: {deterministic_pattern}")
                # We'll return a special 'seed' record that triggers the probe
                return [{"is_deterministic_seed": True, "pattern": deterministic_pattern}]
                
            if not records:
                logger.error(f"Discovery Failed: No records found for keyword '{keyword}' or organization '{org_id}'")
                return []
                
            logger.info(f"Ready for mapping: {len(records)} candidate resources identified.")
            return records
            
        except Exception as e:
            logger.critical(f"OGD API Unreachable: {e}")
            raise ConnectionError(f"Critical OGD Communication Error: {e}")

    def generate_deterministic_mapping(self, pattern: str) -> dict:
        """
        [Accuracy Breakthrough]: Bypasses search instability by brute-forcing hypothesized slugs.
        Slug example: 'village-town-wise-primary-census-abstract-2011-maharashtra'
        """
        logger.info(f"Generating deterministic mapping from pattern: {pattern}")
        states = [
            "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal-pradesh", "jammu-kashmir",
            "jharkhand", "karnataka", "kerala", "madhya-pradesh", "maharashtra",
            "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
            "rajasthan", "sikkim", "tamil-nadu", "tripura", "uttar-pradesh",
            "uttarakhand", "west-bengal", "andaman-nicobar", "chandigarh",
            "dadra-nagar-haveli", "daman-diu", "delhi", "lakshadweep", "puducherry",
            "telangana"
        ]
        
        mapping = {}
        for state_slug in states:
            display_name = state_slug.replace("-", " ").title()
            resource_id = pattern.format(entity=state_slug)
            mapping[display_name] = resource_id
            
        return mapping

    def validate_granularity(self, mapping: dict, definition: dict) -> Tuple[dict, dict]:
        """
        [Fix 3]: Probe-Before-Manifest Pattern.
        Verifies discovered IDs against the row count threshold in the YAML definition.
        Returns (verified_mapping, rejected_mapping).
        """
        logger.info("Starting Physical Granularity Validation (Real-time Probe)...")
        
        # Get threshold from definition (e.g., 1000 rows for PCA)
        threshold = definition.get('validation', {}).get('expected_row_count_lower_bound', 0)
        
        verified = {}
        rejected = {}
        
        for entity, resource_id in mapping.items():
            try:
                # Direct API hit to check 'total' records
                total_records = self.adapter.fetch_total_count(resource_id)
                
                if total_records >= threshold:
                    logger.success(f"✅ {entity}: {resource_id} | {total_records} rows (Threshold: {threshold}) -> VERIFIED")
                    verified[entity] = resource_id
                else:
                    logger.warning(f"❌ {entity}: {resource_id} | ONLY {total_records} rows -> REJECTED (LOW FIDELITY SUMMARY)")
                    rejected[entity] = {"id": resource_id, "rows": total_records, "reason": "Low record count/Summary data"}
                    
            except Exception as e:
                logger.error(f"⚠️ {entity}: Probe failed for {resource_id}. Error: {e}")
                rejected[entity] = {"id": resource_id, "reason": f"Probe error: {str(e)}"}
                
        return verified, rejected

    def classify_and_map(self, catalog_results: list, partition_by: str) -> dict:
        """
        [Fix 2]: Upgraded System Prompt with strict GRANULARITY heuristics.
        """
        if not catalog_results:
            return {}
            
        logger.info("Passing candidate resources to Sarvam AI for Semantic Filtering...")
        
        # Payload simplification
        simplified_catalog = []
        for r in catalog_results:
            simplified_catalog.append({
                "title": r.get('title', ''),
                "desc": r.get('desc', ''),
                "resource_id": r.get('index_name', r.get('resource_id', '')), 
            })
            
        catalog_json_str = json.dumps(simplified_catalog, indent=2)
        
        # [Fix 2]: The High-Fidelity Prompt
        system_prompt = f"""You are an expert data cataloger for data.gov.in.
GOAL: Identify Resource IDs for VILLAGE/TOWN-LEVEL granular data for each {partition_by}.

CRITICAL RULES:
1. REJECT resources titled "District", "State", "Summary", "Abstract", or "Total" (UNLESS it says "Village-wise Abstract").
2. ACCEPT only the most granular version available (keywords: "Village", "Town", "Village-wise", "Town-wise").
3. Normalize state names to standard English (e.g., "UP" -> "Uttar Pradesh", "J & K" -> "Jammu & Kashmir", "A & N" -> "Andaman & Nicobar Islands").
4. Output ONLY a strictly valid JSON object: {{"StateName": "resource_id"}}.
5. NO markdown formatting. NO conversational filler.

If multiple IDs exist for one state, pick the one that looks like a full dataset, not a subset."""

        user_prompt = f"CANDIDATE CATALOG:\n{catalog_json_str}\n\nMap these strictly to a JSON mapping."

        headers = {
            "api-subscription-key": self.sarvam_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.SARVAM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0, # Strict deterministic output
        }

        try:
            response = requests.post(self.SARVAM_ENDPOINT, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Sanitization logic
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            content = content.replace("```json", "").replace("```", "").strip()
            
            mapping = json.loads(content)
            logger.success(f"Sarvam semantically identified {len(mapping)} candidate mappings.")
            return mapping
            
        except Exception as e:
            logger.error(f"Sarvam AI classification failed: {e}")
            return {}

    def discover_dataset(self, dataset_id: str, keyword: str) -> str:
        """
        Full Accuracy-First Discovery Loop.
        1. Search OGD Resources (with Deterministic Fallback)
        2. Semantic/Deterministic Mapping
        3. Physical record count validation (The Physical Gate)
        4. Save Verified Mapping
        """
        # Load the YAML definition for thresholding
        def_file = Path(__file__).resolve().parents[1] / "definitions" / f"{dataset_id}.yaml"
        if not def_file.exists():
            logger.error(f"Definition file {def_file} not found.")
            return ""
            
        with open(def_file, "r") as f:
            definition = yaml.safe_load(f)

        partition_by = definition.get('acquisition', {}).get('partition_by', 'state')
        identity = definition.get("identity", {})
        org_id = identity.get("ogd_organization")
        det_pattern = definition.get("acquisition", {}).get("deterministic_pattern")

        # 1. Catalog Phase
        try:
            records = self.search_catalog(keyword=keyword, org_id=org_id, deterministic_pattern=det_pattern)
        except ConnectionError as e:
            logger.error(f"Discovery aborted: {e}")
            return ""
            
        if not records:
            return ""
            
        # 2. Mapping Phase
        if records[0].get("is_deterministic_seed"):
            # Nuclear Option: Bypass LLM and use Slug Probing
            pattern = records[0]["pattern"]
            logger.info(f"Using Deterministic Pattern Probing: {pattern}")
            ai_mapping = self.generate_deterministic_mapping(pattern)
        else:
            # Semantic Phase (LLM)
            ai_mapping = self.classify_and_map(records, partition_by)
            
        if not ai_mapping:
            return ""
            
        # 3. Validation Phase (The 'Physical Gate')
        verified, rejected = self.validate_granularity(ai_mapping, definition)
        
        # 4. Persistence
        out_file = self.temp_dir / f"{dataset_id}_verified_mapping.json"
        report = {
            "dataset": dataset_id,
            "verified": verified,
            "rejected": rejected
        }
        with open(out_file, "w") as f:
            json.dump(report, f, indent=4)
            
        logger.success(f"Discovery Complete! Verified: {len(verified)} | Rejected: {len(rejected)}")
        logger.info(f"Full Validation Report: {out_file}")
        
        return str(out_file)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sarvam AI OGD Discovery Agent (Accuracy-First Version)")
    parser.add_argument("--dataset", required=True, help="e.g., census_2011_pca")
    parser.add_argument("--keyword", required=True, help="Search query")
    
    args = parser.parse_args()
    
    agent = SarvamAgent()
    agent.discover_dataset(
        dataset_id=args.dataset,
        keyword=args.keyword
    )
