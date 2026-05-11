import os
import yaml
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

from pipeline.adapters.ogd_api import OGDApiAdapter

logger = logging.getLogger(__name__)


class DiscoveryError(Exception):
    """Raised when resource discovery (catalog → resources) fails loudly.

    Use this exception to indicate that automatic resolution of district/resource
    IDs from a catalog UUID failed and upstream callers should abort.
    """
    pass

class SourceResolver:
    """
    Resolves data sources for BharatData datasets using a central registry.
    Supports priority-based source selection and manual overrides.
    """
    
    def __init__(self, registry_path: str = "pipeline/resources/source_registry.yaml"):
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()
        self.manifest_path = Path(__file__).parent.parent / "resources" / "district_uuids_manifest.yaml"
        self.manifest = self._load_manifest()
        
    def _load_registry(self) -> Dict:
        if not self.registry_path.exists():
            logger.error(f"Registry not found at {self.registry_path}")
            return {}
            
        with open(self.registry_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_manifest(self) -> Dict:
        """Load district UUID manifest if it exists."""
        if not self.manifest_path.exists():
            return {}
        try:
            with open(self.manifest_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load manifest {self.manifest_path}: {e}")
            return {}
            
    def get_dataset_config(self, dataset_id: str) -> Optional[Dict]:
        """Returns the full configuration for a specific dataset."""
        return self.registry.get("datasets", {}).get(dataset_id)
        
    def _extract_state(self, entity_name: str) -> str:
        """
        Extracts the state name from an entity name string.
        Example: "Ahmednagar district MAHARASHTRA" -> "Maharashtra"
        """
        # Common pattern: "District Name district STATE NAME"
        match = re.search(r'district\s+([A-Z\s&]+)$', entity_name, re.IGNORECASE)
        if match:
            state = match.group(1).strip().title()
            # Normalize common variations
            mapping = {
                "Maharashtra": "Maharashtra",
                "Andaman & Nicobar Islands": "A & N Islands",
                "Dadra & Nagar Haveli": "D & N Haveli",
                "Jammu And Kashmir": "Jammu & Kashmir",
            }
            return mapping.get(state, state)
        return entity_name.strip().title()
        
    def resolve_sources(self, dataset_id: str, state: str) -> List[Dict]:
        """
        Returns a prioritized list of available sources for a state in a dataset.
        Handles state-specific mapping (e.g. Telangana -> AP).
        """
        config = self.get_dataset_config(dataset_id)
        if not config:
            logger.warning(f"Dataset {dataset_id} not found in registry")
            return []
            
        sources = config.get("sources", [])
        # Sort by priority (lower number = higher priority)
        sorted_sources = sorted(sources, key=lambda x: x.get("priority", 99))
        
        resolved = []
        for source in sorted_sources:
            portal = source.get("portal")
            method = source.get("method")
            
            # Extract state-specific ID/UUID from the source
            state_info = None
            
            if method == "catalog_uuid":
                uuids = source.get("catalog_uuids", [])
                state_info = next((item for item in uuids if item["state"] == state), None)
                
                # Handle Special Mapping: Telangana -> Andhra Pradesh
                if not state_info and state == "Telangana":
                    state_info = next((item for item in uuids if item["state"] == "Andhra Pradesh"), None)
                    if state_info:
                        logger.info(f"Mapping Telangana to Andhra Pradesh source for {dataset_id}")
            
            elif method == "direct_download":
                # Check for state-specific catalog IDs or base URLs
                catalog_ids = source.get("catalog_ids", [])
                state_info = next((item for item in catalog_ids if item["state"] == state), None)
                
            # If we found state-specific info OR if the source is global (no state_info needed)
            if state_info or method == "direct_download" and source.get("base_url"):
                resolved_item = {
                    "portal": portal,
                    "method": method,
                    "priority": source.get("priority"),
                    "details": state_info if state_info else {"url": source.get("base_url")}
                }
                resolved.append(resolved_item)
                
        return resolved

    def _extract_district(self, entity_name: str) -> Optional[str]:
        """
        Extract district name from entity_name if present.
        Example: "Ahmadnagar district Maharashtra" -> "ahmadnagar"
        """
        # Pattern: "District Name" (first word before "district")
        match = re.search(r'^([A-Za-z\s&]+?)\s+district', entity_name, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
        return None

    def get_resource_ids(self, dataset_id: str, entity_name: str, district: Optional[str] = None, api_key: Optional[str] = None) -> Optional[List[str]]:
        """Return a list of resource IDs for a dataset/entity.

        Priority:
          1. Check district_uuids_manifest.yaml: if district found with non-empty UUID, return it
          2. If registry has resource_uuid, return it as a single-item list
          3. If only catalog_uuid present, attempt API discovery
          4. Raise DiscoveryError if all else fails (no silent fallbacks)

        The optional api_key parameter is passed to OGDApiAdapter for API discovery.

        IMPORTANT: If a catalog_uuid is present but the catalog-listing call fails,
        raise DiscoveryError loudly — do not silently return the catalog UUID.
        """
        # Determine state and district keys (allow explicit district param)
        state = self._extract_state(entity_name)
        district_key = (district or self._extract_district(entity_name) or "").lower()
        state_key = (state or "").lower()

        # Step 1: Check manifest first (manifest-first discovery)
        if district_key:
            if state_key in self.manifest:
                state_manifest = self.manifest[state_key] or {}
                if district_key in state_manifest:
                    uuid_val = state_manifest[district_key]
                    if uuid_val and str(uuid_val).strip():  # non-empty
                        logger.info(f"Found {district_key} in manifest: {uuid_val}")
                        return [str(uuid_val)]

        # Step 2: Check registry for explicit resource_uuid
        sources = self.resolve_sources(dataset_id, state)
        for s in sources:
            if s.get("portal") == "data_gov_api":
                details = s.get("details", {}) or {}
                resource_uuid = details.get("resource_uuid")
                if resource_uuid:
                    logger.info(f"Found resource_uuid in registry for {state}: {resource_uuid}")
                    return [resource_uuid]

                # Step 3: Attempt API discovery if only catalog_uuid present
                catalog_uuid = details.get("catalog_uuid")
                if catalog_uuid:
                    adapter = OGDApiAdapter(api_key=api_key or os.getenv("DATA_GOV_IN_API_KEY"))
                    try:
                        ids = adapter.list_resources_by_catalog(catalog_uuid)
                        if not ids:
                            raise DiscoveryError(f"No resources found for catalog {catalog_uuid}")
                        logger.info(f"Discovered {len(ids)} resources for {state}")
                        return ids
                    except Exception as e:
                        raise DiscoveryError(f"Failed to list resources for catalog {catalog_uuid}: {e}")

        # If we reach here, discovery completely failed
        if district_key and state_key:
            raise DiscoveryError(f"No resource UUID found for {state} / {district_key} (not in manifest, registry, or API)")
        else:
            raise DiscoveryError(f"Could not resolve resource ID for {entity_name}")

    def get_resource_id(self, dataset_id: str, entity_name: str) -> Optional[str]:
        """Backward-compatible convenience wrapper: returns the first resource ID or None."""
        ids = self.get_resource_ids(dataset_id, entity_name)
        return ids[0] if ids else None
