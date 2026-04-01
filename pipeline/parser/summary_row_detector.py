SUMMARY_INDICATORS = [
    "total", 
    "grand total", 
    "all india", 
    "total (all india)", 
    "total states", 
    "total uts",
    "total (states)", 
    "total (uts)", 
    "total (states+uts)",
    "total(state)",
    "total(ut)",
    "total districts",
    "total districts / states / uts",
    "total state",
    "total ut"
]

def is_summary_row(row_values: list) -> bool:
    """
    Given a list of row values, determines if the row represents an 
    aggregated summary row (like 'Total (States)') instead of real entity data.
    """
    import re
    for cell in row_values:
        if isinstance(cell, str):
            # Normalize multiple spaces and common inconsistencies
            cleaned = re.sub(r'\s+', ' ', cell.strip().lower())
            
            # Direct match check against normalized string
            if cleaned in SUMMARY_INDICATORS:
                return True
                
            # Substring match for Total variations explicitly
            if cleaned.startswith("total (") and ("states" in cleaned or "uts" in cleaned):
                return True
            if cleaned.startswith("total ") and "india" in cleaned:
                return True
            if cleaned == "total":
                return True
                
    return False
    
