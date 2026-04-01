from parser.field_mapper import FIELD_MAPPINGS

def detect_header_row_index(df_values) -> int:
    """
    Scans the top 15 rows of a dataframe to find the header row.
    Returns the integer index of the header row.
    Defaults to 0 if no valid header is identified.
    """
    for i in range(min(15, len(df_values))):
        row = df_values[i]
        valid_count = 0
        for cell in row:
            if isinstance(cell, str):
                cleaned = cell.strip()
                if cleaned in FIELD_MAPPINGS:
                    valid_count += 1
        
        # If we see 3 or more recognizable columns, this is almost certainly the header row
        if valid_count >= 3:
            return i
            
        # If the file is very small or simple, a threshold of 2 might be needed for simple tables
        if valid_count >= 2 and len(row) < 5:
            return i
            
    return 0  # Fallback
    
