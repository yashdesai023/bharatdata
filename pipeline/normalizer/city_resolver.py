import re

def resolve_city(raw_name: str) -> dict:
    if not isinstance(raw_name, str):
        return {"canonical_name": str(raw_name), "confidence_impact": -0.2}
        
    cleaned = raw_name.strip()
    # Strip " City" suffixes naturally
    cleaned = re.sub(r'(?i)\s+City$', '', cleaned)
    
    fixes = {
        "Durg-Bhilainagar": "Durg-Bhilainagar",
        "Kolkata": "Kolkata",
        "Delhi": "Delhi",
        "Bengaluru": "Bengaluru",
        "Bangalore": "Bengaluru",
        "Mumbai": "Mumbai",
        "Bombay": "Mumbai",
        "Allahabad": "Prayagraj",
        "Pune": "Pune"
    }
    
    # Fallback to Title case if not explicitly fixed
    if cleaned in fixes:
        canon = fixes[cleaned]
    else:
        canon = cleaned.title()
        
    return {
        "canonical_name": canon,
        "confidence_impact": 0.0
    }
