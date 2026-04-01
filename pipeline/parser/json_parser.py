import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.logger_config import pipeline_logger as logger
from parser.pdf_parser import clean_city

def parse_json(file_path: str) -> list[dict]:
    filename = os.path.basename(file_path)
    logger.debug(f"Parsing JSON City Data: {filename}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON {file_path}: {e}")
        return []
        
    records = []
    
    # Determine category and year from filename
    year = 2023
    if '2021' in filename: year = 2021
    elif '2022' in filename: year = 2022
    elif '2023' in filename: year = 2023
        
    category_label = "Unknown JSON Category"
    if 'ipc' in filename.lower():
        category_label = "Total Cognizable IPC Crimes"
    elif 'sll' in filename.lower():
        category_label = "Total Cognizable SLL Crimes"
    elif 'total' in filename.lower():
        category_label = "Total Cognizable Crimes"
        
    for item in data:
        if not item.get('city'):
            continue
            
        record = {
            "city": clean_city(item['city']),
            "year": item.get('year', year),
            "total_cases": item.get('count'),
            "rate_per_lakh": item.get('crime_rate'),
            "chargesheeting_rate": item.get('chargesheeting_rate'),
            "confidence": 0.90,
            "source_file": filename,
            "category_label": category_label,
            "parsing_notes": ["Ingested from Stage 1 structured JSON"],
            "table_type": "city_ipc"
        }
        records.append(record)
        
    logger.debug(f"Extracted {len(records)} records from {filename}")
    return records
