FIELD_MAPPINGS = {
    # State identification (multiple variations)
    "state/ut": "state_raw",
    "states/uts": "state_raw",
    "state / ut": "state_raw",
    "states/ uts": "state_raw",
    
    # District identification
    "district": "district",
    "state/ut/district": "district",
    
    # City identification
    "city": "city",
    "metropolitan city": "city",

    # Categories
    "crime head": "category_label",
    "offence": "category_label",
    
    # Total counts (Comprehensive list)
    "total cognizable ipc crimes": "total_cases",
    "total ipc crimes": "total_cases",
    "total cognizable sll crimes": "total_cases",
    "total sll crimes": "total_cases",
    "total cognizable crimes": "total_cases",
    "total crimes": "total_cases",
    "grand total": "total_cases",
    "cases reported during the year": "total_cases",
    "cases reported": "total_cases",
    "incidence": "total_cases",
    
    # Rates
    "crime rate": "rate_per_lakh",
    "rate of total cognizable": "rate_per_lakh",
    "rate of total cognizable crimes": "rate_per_lakh",
    "rate of total cognizable ipc crimes": "rate_per_lakh",
    "rate of total cognizable sll crimes": "rate_per_lakh",
    "rate per lakh": "rate_per_lakh",
    "rate per lakh population": "rate_per_lakh",
    
    # Disposal pipeline
    "cases charge sheeted": "chargesheeted",
    "cases charge-sheeted": "chargesheeted",
    "cases convicted": "convicted",
    "cases conviction": "convicted",
    "cases acquittal/discharge": "acquitted",
    "cases acquitted": "acquitted",
    "cases pending investigation": "pending_investigation",
    "cases pending trial": "pending_trial",
    "pending trial": "pending_trial",
    "trials completed": "trials_completed",
}

def map_column(raw_col: str) -> str:
    """Map a raw NCRB column (possibly combined from multiple rows) to canonical string."""
    if not isinstance(raw_col, str):
        return "_unknown"
    
    cleaned = raw_col.strip().lower()
    
    # Exact match first
    for key, val in FIELD_MAPPINGS.items():
        if key == cleaned:
            return val
            
    # Explicit skips for serial numbers (Must come before substring match)
    if any(x in cleaned for x in ["sl. no", "s.no", "sl.no", "s. no", "sr. no", "sl ", "s. no."]):
        return "_skip"

    # Special case for combined header in district context
    if "state" in cleaned and "district" in cleaned:
        return "district"
    if "state / ut" in cleaned or "state/ut" in cleaned:
        return "state_raw"
    if cleaned == "district":
        return "district"

    # Substring match if exact fails
    for key, val in FIELD_MAPPINGS.items():
        if key in cleaned:
            return val

    # Fuzzy Regex Fallbacks for unpredictable Total columns
    import re
    if re.search(r'\btotal\b.*\b(cases?|crimes?|offences?|seizures?|acts?)\b', cleaned):
        return "total_cases"

    return "_unknown"
    
