import pypdf
import os
import sys
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.logger_config import pipeline_logger as logger

def clean_city(name: str) -> str:
    """Standardize city names for simple parsing normalization."""
    name = name.strip()
    name = re.sub(r' City$', '', name, flags=re.IGNORECASE)
    
    # Common fixes
    fixes = {
        "Durg-Bhilainagar": "Durg-Bhilainagar",
        "Kolkata": "Kolkata",
        "Delhi": "Delhi",
        "Bengaluru": "Bengaluru",
        "Mumbai": "Mumbai",
        "Allahabad": "Prayagraj"  # Handle historical rename
    }
    return fixes.get(name, name)

def parse_pdf(file_path: str) -> list[dict]:
    filename = os.path.basename(file_path)
    logger.debug(f"Parsing PDF: {filename}")
    
    # Infer year
    year_match = re.search(r'20\d{2}', file_path)
    year = int(year_match.group()) if year_match else 2023
    
    records = []
    
    try:
        reader = pypdf.PdfReader(file_path)
    except Exception as e:
        logger.error(f"Failed to read PDF {file_path}: {e}")
        return records
        
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
            
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            # Target columns for Year T: [Sl, City, T-2, T-1, T, Pop, Rate, Chargesheet_Rate]
            # Match line starting with Number then City then numbers
            # Example: "1 Agra 5665 6947 7026 17.5 402.4 79.3"
            match = re.match(r'^(\d+)\s+([A-Za-z\s\-\&]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)', line)
            
            if match:
                sl, city, y_prev2, y_prev1, y_curr, pop, rate, cs_rate = match.groups()
                
                record = {
                    "city": clean_city(city),
                    "year": year,
                    "total_cases": int(y_curr),
                    "rate_per_lakh": float(rate),
                    "chargesheeting_rate": float(cs_rate),  # PDF holds the rate, not raw count
                    "confidence": 0.90,  # Base 0.9 for PDF extraction
                    "source_file": filename,
                    "source_row": (page_num * 1000) + line_idx,
                    "parsing_notes": ["Extracted from PDF Regex"],
                    "table_type": "city_ipc"
                }
                
                # Try to determine category from known PDF filenames
                if 'TABLE1B14' in filename or 'TABLE1B1.' in filename:
                    record['category_label'] = "Total Cognizable IPC Crimes"
                elif 'TABLE1B22' in filename or 'TABLE1B2.' in filename:
                    record['category_label'] = "Total Cognizable SLL Crimes"
                elif 'TABLE1B32' in filename or 'TABLE1B3.' in filename:
                    record['category_label'] = "Total Cognizable Crimes"
                else:
                    record['category_label'] = "Unknown PDF Category"
                    
                records.append(record)
                
    logger.debug(f"Extracted {len(records)} records from {filename}")
    return records

if __name__ == "__main__":
    print("Testing PDF Parser...")
    
    raw_dir = os.path.join(os.path.dirname(pipeline_root), "data", "raw")
    total_files = 0
    total_records = 0
    
    agra_2023_count = None
    all_cities_found = set()
    
    for root_dir, dirs, files in os.walk(raw_dir):
        for f in files:
            if f.endswith('.pdf') and 'TABLE' in f.upper():
                total_files += 1
                fp = os.path.join(root_dir, f)
                recs = parse_pdf(fp)
                total_records += len(recs)
                
                for r in recs:
                    all_cities_found.add(r['city'])
                    if r['city'] == 'Agra' and r['year'] == 2023 and 'IPC' in r['category_label']:
                        agra_2023_count = r['total_cases']
                        
    print(f"\nStats: Parsed {total_files} PDF files. Extracted {total_records} metropolitan city records.")
    
    # Validation constraints
    success = True
    if agra_2023_count != 7026:
        print(f"FAILED: Expected Agra 2023 IPC = 7026, found {agra_2023_count}")
        success = False
    else:
        print(f"Ground Truth Benchmark (Agra 2023 IPC = 7026) -> Verified")
        
    num_cities = len(all_cities_found)
    if num_cities != 34:
        print(f"FAILED: Expected exactly 34 metropolitan entities, found {num_cities}")
        success = False
    else:
        print(f"Metropolitan Entity Coverage (34 Cities) -> Verified")
        
    if success and total_files > 0:
        print("\nAll PDF parsing tests passed cleanly! Data extracted correctly.")
    
