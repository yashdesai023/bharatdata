import os
import psycopg2
from psycopg2.extras import execute_values

class BatchLoader:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL")

    def load(self, table_name, records):
        """
        Inserts a batch of records into the PostgreSQL table using high-performance execute_values.
        Using ON CONFLICT ("_hash") DO NOTHING to handle duplicates.
        """
        if not records:
            return 0
        
        # 1. Identify all fields (columns)
        fields = list(records[0].keys())
        columns = ", ".join([f'"{f}"' for f in fields])
        
        # 2. Extract values for each record into a list of tuples
        data_to_insert = [tuple(r.get(f) for f in fields) for r in records]
        
        # 3. Construct the UPSERT SQL
        # PostgreSQL ON CONFLICT requires a constraint or column name (we use _hash)
        sql = f"""
            INSERT INTO "{table_name}" ({columns})
            VALUES %s
            ON CONFLICT ("_hash") DO NOTHING
        """
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, sql, data_to_insert)
                    count = cursor.rowcount
                conn.commit()
            return count
        except Exception as e:
            print(f"Error loading to Supabase: {e}")
            return 0
