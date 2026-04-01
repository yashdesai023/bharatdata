def resolve_district(raw_name: str, state_canonical: str = None) -> dict:
    if not isinstance(raw_name, str):
        return {"canonical_name": str(raw_name), "confidence_impact": -0.1}
        
    cleaned = raw_name.strip()
    
    # In v1, we do simple title-casing and strip spaces
    # We will build a full canonical map later
    
    # Fix standard anomalies
    if cleaned.upper() == "TOTAL":
        return {"canonical_name": "Total", "confidence_impact": 0.0}
        
    canon = cleaned.title()
    
    return {
        "canonical_name": canon,
        "confidence_impact": 0.0
    }
