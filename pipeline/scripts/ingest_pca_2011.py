import os
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import time

load_dotenv()

class CensusPCAIngestor:
    def __init__(self):
        self.api_key = os.getenv('DATA_GOV_IN_API_KEY')
        self.sb_url = os.getenv('SUPABASE_URL')
        self.sb_anon_key = os.getenv('SUPABASE_ANON_KEY')
        self.rest_url = f"{self.sb_url}/rest/v1/census_2011_pca?apikey={self.sb_anon_key}"
        self.ogd_base = "https://api.data.gov.in/resource"
        
        # PROPER DATABASE COLUMN NAMES (VERIFIED VIA INFORMATION_SCHEMA)
        self.column_mapping = {
            'state_code': 'state_code',
            'district_code': 'district_code',
            'subdistt_code': 'sub_district_code',
            'name': 'entity_name',
            'level': 'admin_level',
            'total_population_person': 'total_population',
            'total_population_male': 'male_population',
            'total_population_female': 'female_population',
            'literates_population_person': 'literate_population',
            'scheduled_castes_population_person': 'sc_population',
            'scheduled_tribes_population_person': 'st_population',
            'main_working_population_person': 'main_workers',
            'marginal_worker_population_person': 'marginal_workers',
            'non_working_population_person': 'non_workers'
        }
        
    def fetch_api(self, resource_id, offset=0, limit=1000):
        url = f"{self.ogd_base}/{resource_id}?api-key={self.api_key}&format=json&offset={offset}&limit={limit}"
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=60)
                if r.status_code == 200: return r.json()
                time.sleep(2)
            except:
                time.sleep(2)
        return None

    def push_rest(self, df):
        if df.empty: return False
        headers = { 'Content-Type': 'application/json', 'Prefer': 'merge-duplicates', 'Authorization': f'Bearer {self.sb_anon_key}' }
        # Add 'year' and metadata
        df['year'] = 2011
        payload = df.to_dict(orient='records')
        try:
            r = requests.post(self.rest_url, headers=headers, json=payload, timeout=60)
            if r.status_code in [200, 201]: return True
            print(f"  [ERROR] {r.status_code}: {r.text[:200]}")
            return False
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            return False

    def ingest_state(self, resource_id, state_name):
        print(f"--- Ingesting {state_name} ---")
        offset = 0
        total = 0
        while True:
            data = self.fetch_api(resource_id, offset)
            if not data or not data.get('records'): break
            
            df = pd.DataFrame(data['records'])
            # Map only existing columns
            df = df.rename(columns={k: v for k, v in self.column_mapping.items() if k in df.columns})
            current_cols = [c for c in self.column_mapping.values() if c in df.columns]
            df = df[current_cols]
            
            # Numeric conversion
            for col in df.columns:
                if col not in ['entity_name', 'admin_level']:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            if self.push_rest(df):
                total += len(df)
                print(f"  Synced Batch: {total} records.")
            
            if len(data['records']) < 1000: break
            offset += 1000
            time.sleep(0.5)
            
        print(f"--- Final: {state_name} Ingested ({total} records) ---")
        return total

if __name__ == "__main__":
    ingestor = CensusPCAIngestor()
    # Odisha
    ingestor.ingest_state('f641911e-1686-4675-95cf-92f1a5bd7173', 'Odisha')
