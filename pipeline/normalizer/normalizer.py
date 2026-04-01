import uuid
import datetime
import os
import sys
import copy

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from normalizer.state_resolver import resolve_state
from normalizer.district_resolver import resolve_district
from normalizer.city_resolver import resolve_city
from normalizer.type_enforcer import enforce_type
from normalizer.category_mapper import map_category
from normalizer.boundary_annotator import annotate_boundary
from normalizer.confidence_scorer import score_confidence
from normalizer.range_validator import validate_ranges
from utils.logger_config import pipeline_logger as logger

def normalize_record(raw_record: dict, batch_id: str = None) -> tuple:
    """
    Transforms a parsed record into canonical form.
    Returns: (normalized_record_dict, list_of_normalization_logs)
    """
    rec = copy.deepcopy(raw_record)
    logs = []
    impacts = []
    
    # Generate common ID for record and its logs
    record_uuid = str(uuid.uuid4())
    
    # 1. State Name Resolution
    raw_state = rec.get('state_raw')
    state_res = resolve_state(raw_state)
    state_canon = state_res['canonical_name']
    impacts.append(state_res['confidence_impact'])
    
    if state_canon != str(raw_state):
        logs.append({
            "record_id": record_uuid,
            "field": "state",
            "input_value": str(raw_state) if raw_state is not None else "MISSING",
            "output_value": str(state_canon),
            "mapping_source": "states.json",
            "confidence_impact": state_res['confidence_impact']
        })
        
    # 2 & 3. District & City Resolution
    district_canon = None
    city_canon = None
    
    if rec.get('district'):
        dist_res = resolve_district(rec['district'], state_canon)
        district_canon = dist_res['canonical_name']
        impacts.append(dist_res['confidence_impact'])
        
        if district_canon != str(rec['district']):
             logs.append({
                "record_id": record_uuid,
                "field": "district",
                "input_value": str(rec['district']),
                "output_value": str(district_canon),
                "mapping_source": "districts.json",
                "confidence_impact": dist_res['confidence_impact']
            })
        
    if rec.get('city'):
        city_res = resolve_city(rec['city'])
        city_canon = city_res['canonical_name']
        impacts.append(city_res['confidence_impact'])
        
    # 4. Data Type Enforcement (Metrics)
    metrics = {
        'total_cases': 'int',
        'rate_per_lakh': 'float',
        'chargesheeted': 'int',
        'convicted': 'int',
        'acquitted': 'int',
        'pending_investigation': 'int',
        'pending_trial': 'int'
    }
    
    # Track parse notes early
    parse_notes = rec.get('parsing_notes', [])
    table_type = rec.get('table_type', 'unknown') # Get table_type for contextual handling
    
    for field, expected_type in metrics.items():
        # Get raw value or None if missing
        raw_val = rec.get(field)
        clean_val = None 

        # Contextual handling for specific fields and values
        if field == "total_cases":
            # Impute 0 for total_cases if missing/empty/dash based on table type
            if (raw_val is None or str(raw_val).strip() == "" or str(raw_val).strip() == "-") and table_type in ["crime_records_state", "crime_records_district"]:
                clean_val = 0
                parse_notes.append(f"Imputed 0 for {field} from missing/empty/dash for {table_type}")
                impacts.append(-0.05)
            elif str(raw_val).strip() == "-" and table_type == "crime_records_city":
                clean_val = 0
                parse_notes.append(f"Imputed 0 for {field} from dash for {table_type}")
                impacts.append(-0.05)
            else:
                # For other cases, enforce type normally
                clean_val = enforce_type(raw_val, expected_type)
        # Null disposal metrics (dash -> None)
        elif field in ["chargesheeted", "convicted", "acquitted", "pending_investigation", "pending_trial"]:
            if str(raw_val).strip() == "-":
                clean_val = None
                parse_notes.append(f"Converted dash to null for missing metric {field}")
                impacts.append(-0.05)
            else:
                clean_val = enforce_type(raw_val, expected_type)
        else:
            # Default type enforcement for all other metrics
            clean_val = enforce_type(raw_val, expected_type)
            
        if raw_val is not None and clean_val != raw_val and str(raw_val).strip() != "-":
            if str(raw_val).strip() != "":
                logs.append({
                    "record_id": record_uuid,
                    "field": field,
                    "input_value": str(raw_val),
                    "output_value": str(clean_val),
                    "mapping_source": "type_enforcer",
                    "confidence_impact": 0.0
                })
        
        # Update rec dictionary so later get() calls see the cleaned value
        rec[field] = clean_val
            
    # Year validation
    rec['year'] = enforce_type(rec.get('year'), 'int')
            
    # 5. Category Mapping
    raw_category = rec.get('category_label', 'Unknown')
    cat_slug = map_category(raw_category)
    
    # 6. Historical Boundary Annotation
    bound_note = annotate_boundary(state_canon, rec.get('year'))
    
    # 8. Confidence Adjustment
    final_conf = score_confidence(rec.get('confidence', 1.0), impacts)
    
    # 10. Range Validation
    range_notes = validate_ranges(rec)
    parse_notes = rec.get('parsing_notes', []) + range_notes
    
    # Assemble standard normalized record matching schema
    normalized = {
        "id": record_uuid,
        "state": state_canon,
        "state_code": state_res['state_code'],
        "year": rec.get('year'),
        "category": cat_slug,
        "category_label": raw_category,
        "total_cases": rec.get('total_cases'),
        "rate_per_lakh": rec.get('rate_per_lakh'),
        "chargesheeted": rec.get('chargesheeted'),
        "convicted": rec.get('convicted'),
        "acquitted": rec.get('acquitted'),
        "pending_investigation": rec.get('pending_investigation'),
        "pending_trial": rec.get('pending_trial'),
        "confidence": final_conf,
        
        # Geographies
        "district": district_canon,
        "city": city_canon,
        
        # Attributions
        "source_url": "https://ncrb.gov.in",
        "source_file": rec.get('source_file'),
        "report_name": f"Crime in India {rec.get('year')}",
        "publishing_body": "National Crime Records Bureau",
        "collection_date": datetime.datetime.now().isoformat(),
        "normalizer_version": "1.0.0",
        "ingestion_batch_id": batch_id or str(uuid.uuid4()),
        "boundary_note": bound_note,
        
        # Internal passthrough stats
        "__parsing_notes": parse_notes,
        "__table_type": rec.get('table_type', 'unknown')
    }
    
    return normalized, logs
