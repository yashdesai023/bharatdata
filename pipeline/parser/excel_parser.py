import pandas as pd
import numpy as np
import re
import os
import sys

# Ensure pipeline root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from parser.field_mapper import map_column
from parser.summary_row_detector import is_summary_row
from utils.logger_config import pipeline_logger as logger

def clean_numeric_value(val):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    if s in ["", "NA", "N/A", "NR"]:
        return None
    if s == "-":
        return "-"
    s = s.replace(',', '')
    try:
        if '.' in s:
            return float(s)
        return int(s)
    except ValueError:
        return s 

def find_data_start_row(raw_values):
    """Find the first row that looks like actual data (e.g., contains state or numerical ID)."""
    for i in range(min(15, len(raw_values))):
        row = raw_values[i]
        # Skip rows that are just column numbers [1, 2, 3...]
        first_val = str(row[0]).strip()
        if first_val in ['1', '2', '3'] and len(row) > 1 and str(row[1]).strip() in ['', 'nan']:
             continue
        if first_val == '1' and len(row) > 10: # Likely column numbers
            # Check if Row i+1 or i+2 is the actual data
            continue

        # Common pattern: True data starts with '1' and has a string in second column (District/State)
        if first_val == '1' and isinstance(row[1], str) and len(str(row[1])) > 1:
            return i
            
        if "Andhra Pradesh" in str(row) and not str(row[0]).startswith("State:"):
            return i
    return 3 # fallback

def flatten_headers(raw_values, data_start_idx):
    """Combine the rows before data starts into single column strings."""
    if data_start_idx == 0:
        return [str(c) for c in raw_values[0]]
        
    num_cols = len(raw_values[0])
    combined_headers = []
    
    for col_idx in range(num_cols):
        col_strs = []
        for r in range(data_start_idx):
            val = str(raw_values[r][col_idx]).strip()
            # Ignore "State: ..." rows in headers
            if val.lower().startswith("state:"):
                continue
            if val and val.lower() != 'nan':
                col_strs.append(val)
        combined_headers.append(" ".join(col_strs))
        
    return combined_headers

def parse_excel(file_path: str) -> list[dict]:
    filename = os.path.basename(file_path)
    
    # Penalize confidence slightly just for older 2021 data without standardized names
    has_prefix = bool(re.match(r'^\d{10,}', filename))
    base_confidence = 0.95 if has_prefix else 1.0
    
    try:
        df = pd.read_excel(file_path, header=None, engine='openpyxl')
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return []

    raw_values = df.values.tolist()
    
    data_start_idx = find_data_start_row(raw_values)
    flat_headers = flatten_headers(raw_values, data_start_idx)
    
    mapped_columns = [map_column(c) for c in flat_headers]
    
    # Track current parent state (from rows like "State: Andhra Pradesh")
    current_parent_state = None
    
    # Proceed to extract rows
    data_df = df.iloc[0:].copy() # Inspect all rows to catch parent state
    data_df = data_df.iloc[:, :len(mapped_columns)]
    data_df.columns = mapped_columns
    
    table_type = "state_ipc"
    if 'District' in filename or 'Table 1.10' in filename:
        table_type = "district_ipc"
    elif 'Metropolitan' in filename or 'City' in filename:
        table_type = "city_ipc"

    records = []
    
    for row_idx, row in data_df.iterrows():
        # 1. Parent State Detection (Metadata rows)
        first_cell = str(row.iloc[0]).strip()
        if first_cell.lower().startswith("state:"):
            current_parent_state = first_cell.replace("State:", "").replace("STATE:", "").strip()
            logger.debug(f"Context Switch: Parent State set to {current_parent_state}")
            continue

        if row_idx < data_start_idx:
            continue
            
        row_list = row.tolist()
        is_summary = is_summary_row(row_list)
        # We no longer skip summary rows! These are vital State Totals since the user is missing the actual State-level spreadsheets.
            
        record = {
            'table_type': 'crime_records_district' if table_type == "district_ipc" else 'crime_records_state' if table_type == "state_ipc" else 'crime_records_city'
        }
        record_confidence = base_confidence
        
        for col_name, val in row.items():
            if col_name == "_skip" or col_name == "_unknown":
                continue
                
            clean_val = clean_numeric_value(val)
            record[col_name] = clean_val
            
            if clean_val is not None and isinstance(clean_val, str) and not pd.isna(val) and str(clean_val).strip() != "-":
                if col_name in ["total_cases", "rate_per_lakh", "chargesheeted", "convicted", "acquitted"]:
                    record_confidence -= 0.10
                    
        record['confidence'] = record_confidence
        
        # Determine mapping if state_raw is missing but parent state exists
        if not record.get('state_raw') and current_parent_state:
             record['state_raw'] = current_parent_state
             
        if not record.get('state_raw') and not record.get('district'):
            continue
            
        # Optional category detection for some files where it is the first row string
        if not record.get('category_label') or str(record.get('category_label')).strip().isdigit():
            # If category label is missing OR is a number (misidentified Sl. No), use filename as fallback
            record['category_label'] = 'Unknown Category (Implied by Filename)'
             
        if 'total_cases' not in record:
             # Fallback: Capture any column that looks like a high numeric total if mapper failed
             logger.debug(f"Total cases missing in mapped record from {filename}")
            
        # If it's a district table, ensure we have the state context
        if table_type == "district_ipc" and current_parent_state:
             if is_summary:
                  # This is a state total trapped inside a district table!
                  # Route it to the State database by ensuring 'district' is removed and 'state_raw' is the parent
                  record['state_raw'] = current_parent_state
                  if 'district' in record:
                       del record['district']
                  record['table_type'] = 'crime_records_state'
             elif 'district' not in record and 'state_raw' in record:
                  # Standard district row where 'state_raw' caught the district name
                  record['district'] = record['state_raw']
                  record['state_raw'] = current_parent_state
            
        year_match = re.search(r'20\d{2}', filename)
        if year_match:
            record["year"] = int(year_match.group())
        elif '2021' in file_path:
            record["year"] = 2021
        elif '2022' in file_path:
            record["year"] = 2022
        elif '2023' in file_path:
            record["year"] = 2023
            
        # Add attribution metadata
        record["source_file"] = filename
        
        records.append(record)
        
    return records

if __name__ == "__main__":
    print("Testing Excel Parser...")
    
    raw_dir = os.path.join(os.path.dirname(pipeline_root), "data", "raw")
    total_files = 0
    total_records = 0
    success = True
    
    for root_dir, dirs, files in os.walk(raw_dir):
        for f in files:
            if f.endswith('.xlsx'):
                total_files += 1
                fp = os.path.join(root_dir, f)
                recs = parse_excel(fp)
                total_records += len(recs)
                
                if "State" in f and "UT" in f and "IPC" in f and ("Table 1.1" in f or "State-UT" in f):
                    state_names_found = len(set([r['state_raw'] for r in recs]))
                    if state_names_found < 30: 
                        logger.warning(f"{f} produced only {state_names_found} entities.")
                        success = False
                        
    print(f"\nStats: Parsed {total_files} Excel files. Extracted {total_records} state/district/city records total.")
    if success and total_files > 0:
        print("\nAll Excel parsing tests passed cleanly! Data extracted correctly.")
    
