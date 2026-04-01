def validate_ranges(record: dict) -> list:
    """Flags values outside plausible realistic bounds."""
    notes = []
    
    tc = record.get('total_cases')
    if tc is not None and not (0 <= tc <= 5000000):
        notes.append(f"total_cases {tc} outside 0-5M expected range")
        
    rpl = record.get('rate_per_lakh')
    if rpl is not None and not (0 <= rpl <= 5000):
        notes.append(f"rate_per_lakh {rpl} outside 0-5k expected range")
        
    yr = record.get('year')
    if yr is not None and not (2000 <= yr <= 2030):
        notes.append(f"year {yr} outside 2000-2030 expected range")
        
    cs = record.get('chargesheeted')
    if cs is not None and not (0 <= cs <= 5000000):
        notes.append(f"chargesheeted {cs} outside expected range")
        
    return notes
