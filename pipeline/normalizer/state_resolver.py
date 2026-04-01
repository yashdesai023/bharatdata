import os
import sys
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.logger_config import pipeline_logger as logger

# Load state mappings at module import
mapping_file = os.path.join(os.path.dirname(pipeline_root), "data", "canonical-mappings", "states.json")
unmapped_log = os.path.join(os.path.dirname(pipeline_root), "data", "canonical-mappings", "unmapped-entities.json")

STATE_MAP = {}
if os.path.exists(mapping_file):
    with open(mapping_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for canon, info in data.items():
            # Add canonical name itself
            STATE_MAP[canon.lower()] = info
            # Add all variations
            for var in info.get("variations", []):
                STATE_MAP[var.lower()] = info
else:
    logger.error(f"Mapping file not found at {mapping_file}. State resolver will fail.")

def resolve_state(raw_name: str) -> dict:
    if not isinstance(raw_name, str):
        return {"canonical_name": str(raw_name), "state_code": "UNKNOWN", "confidence_impact": -0.2, "type": "unknown"}
        
    cleaned = raw_name.strip().lower()
    
    if cleaned in STATE_MAP:
        info = STATE_MAP[cleaned]
        return {
            "canonical_name": info["canonical"],
            "state_code": info["code"],
            "type": info["type"],
            "confidence_impact": 0.0
        }
    
    # Log unmapped
    logger.warning(f"Unmapped state encountered: {raw_name}")
    _log_unmapped("state", raw_name)
    
    return {
        "canonical_name": raw_name.strip(),
        "state_code": "UNKNOWN",
        "type": "unknown",
        "confidence_impact": -0.2
    }

def _log_unmapped(entity_type, raw_name):
    unmapped = []
    if os.path.exists(unmapped_log):
        with open(unmapped_log, 'r') as f:
            try:
                unmapped = json.load(f)
            except:
                pass
                
    entry = {"type": entity_type, "raw": raw_name}
    if entry not in unmapped:
        unmapped.append(entry)
        with open(unmapped_log, 'w') as f:
            json.dump(unmapped, f, indent=2)
