def enforce_type(value, expected_type):
    """
    Cleans structural nulls and enforces strict typing.
    expected_type can be 'int', 'float', 'string'
    """
    if value is None:
        return None
        
    s_val = str(value).strip()
    
    # Null equivalents
    if s_val in ["", "-", "NA", "N/A", "NR", "nan", "None"]:
        return None
        
    if expected_type in ['int', 'float']:
        # Remove commas
        clean_num = s_val.replace(',', '')
        
        try:
            if expected_type == 'int':
                # Convert float strings like '12.0' to int
                return int(float(clean_num))
            elif expected_type == 'float':
                return float(clean_num)
        except ValueError:
            return None # Type enforcement failure translates to null at field level
            
    return s_val
