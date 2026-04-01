import os
import sys
sys.path.append(os.path.abspath('.'))
from pipeline.utils.db_connection import get_cursor

CATEGORY_MAP = {
    "IPC": {"id": "ipc-total", "label": "Total IPC Crimes"},
    "SLL": {"id": "sll-total", "label": "Total SLL Crimes"},
    "Women": {"id": "crimes-against-women", "label": "Crime Against Women"},
    "Children": {"id": "crimes-against-children", "label": "Crime Against Children"},
    "SCs": {"id": "crimes-against-sc", "label": "Crime Against Scheduled Castes"},
    "STs": {"id": "crimes-against-st", "label": "Crime Against Scheduled Tribes"},
    "SrCitizen": {"id": "crimes-against-senior-citizens", "label": "Crime Against Senior Citizens"},
    "Cyber": {"id": "cyber-crimes", "label": "Cyber Crimes"},
    "Economic": {"id": "economic-offences", "label": "Economic Offences"},
    "NDPS": {"id": "ndps", "label": "NDPS Act"},
    "Missing": {"id": "missing-persons", "label": "Missing Persons"},
    "JuvenilesIPC": {"id": "juveniles-ipc", "label": "Juveniles in IPC Crimes"},
    "CrimebyJuveniles": {"id": "juveniles-ipc", "label": "Juveniles in IPC Crimes"},
    "JuvenilesSLL": {"id": "juveniles-sll", "label": "Juveniles in SLL Crimes"},
    "SLLCrimebyJuveniles": {"id": "juveniles-sll", "label": "Juveniles in SLL Crimes"},
    "Property": {"id": "property-stolen-recovered", "label": "Property Stolen & Recovered"},
    "HumanTrafficking": {"id": "human-trafficking", "label": "Human Trafficking"},
    "Environment": {"id": "environment-crimes", "label": "Environment Related Offences"},
    "Foreigners": {"id": "crimes-by-foreigners", "label": "Crimes by Foreigners"},
    "Disposal": {"id": "police-disposal", "label": "Police Disposal"},
    "Seizures": {"id": "seizures", "label": "Seizures"},
    "CasesRegistered1563": {"id": "cases-registered", "label": "Cases Registered"},
}

def guess_category(filename):
    if not filename:
        return "unknown", "Unknown"
        
    for key, val in CATEGORY_MAP.items():
        if key.lower() in filename.lower():
            # Refine matching if needed
            if key == "IPC" and "Juvenile" in filename: continue
            if key == "SLL" and "Juvenile" in filename: continue
            return val["id"], val["label"]
            
    return "unknown", "Unknown"

def fix_records(table_name):
    print(f"Fixing categories in {table_name}...")
    updates = 0
    with get_cursor() as cur:
        cur.execute(f"SELECT id, source_file FROM {table_name} WHERE category = 'unknown' OR category_label LIKE '%%Unknown%%'")
        records = cur.fetchall()
        
        from psycopg2.extras import execute_values
        
        updates_data = []
        for r_id, src_file in records:
            cat_id, cat_label = guess_category(src_file)
            
            # Additional logic for CasesRegistered1563 which usually contains the actual category
            if "CasesRegistered1563" in src_file:
                if "IPC" in src_file: cat_id, cat_label = "cases-reg-ipc", "Cases Registered 156(3) IPC"
                elif "SLL" in src_file: cat_id, cat_label = "cases-reg-sll", "Cases Registered 156(3) SLL"
                elif "Women" in src_file: cat_id, cat_label = "cases-reg-women", "Cases Registered 156(3) Women"
                elif "ST" in src_file: cat_id, cat_label = "cases-reg-st", "Cases Registered 156(3) ST"
                elif "SC" in src_file: cat_id, cat_label = "cases-reg-sc", "Cases Registered 156(3) SC"
                elif "SrCitizen" in src_file: cat_id, cat_label = "cases-reg-srcitizen", "Cases Registered 156(3) Sr Citizen"
                elif "Children" in src_file: cat_id, cat_label = "cases-reg-children", "Cases Registered 156(3) Children"

            if "PersonsDisposal" in src_file:
                if "IPC" in src_file: cat_id, cat_label = "police-disposal-ipc", "Police Disposal (IPC)"
                elif "Cyber" in src_file: cat_id, cat_label = "police-disposal-cyber", "Police Disposal (Cyber)"
                
            updates_data.append((cat_id, cat_label, r_id))
            
        if updates_data:
            update_query = f"""
                UPDATE {table_name} AS t
                SET category = e.category,
                    category_label = e.category_label
                FROM (VALUES %s) AS e(category, category_label, id)
                WHERE t.id = e.id::uuid
                  AND NOT EXISTS (
                      SELECT 1 FROM {table_name} crs 
                      WHERE crs.state = t.state AND crs.year = t.year AND crs.source_file = t.source_file
                        AND crs.category = e.category
                  )
            """
            execute_values(cur, update_query, updates_data)
            cur.connection.commit()
            print(f"Bulk updated {len(updates_data)} records in {table_name}")
        else:
            print(f"No records gracefully updated in {table_name}")

if __name__ == "__main__":
    fix_records("crime_records_state")
    fix_records("crime_records_district")
