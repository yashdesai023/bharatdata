def annotate_boundary(state_canonical: str, year: int) -> str:
    """Provides historical context for boundaries that shifted over time."""
    if not isinstance(state_canonical, str) or not isinstance(year, int):
        return None
        
    if state_canonical == "Telangana" and year < 2014:
        return "Telangana did not exist as a separate state before 2014."
        
    if state_canonical == "Andhra Pradesh" and year < 2014:
        return "Pre-2014 Andhra Pradesh figures include the Telangana region."
        
    if state_canonical == "Ladakh" and year < 2019:
        return "Ladakh did not exist as a separate UT before 2019."
        
    if state_canonical == "Jammu & Kashmir" and year >= 2019:
        return "Jammu & Kashmir was reorganized from a State to a UT in 2019."
        
    if state_canonical == "D&N Haveli and Daman & Diu" and year < 2020:
        return "Pre-2020 data might be reported separately as Dadra & Nagar Haveli and Daman & Diu."
        
    return None
