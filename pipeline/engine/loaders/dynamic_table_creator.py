import os
import psycopg2
import psycopg2

class DynamicTableCreator:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL")

    def create_table(self, table_name, schema):
        """
        Creates a PostgreSQL table if it doesn't exist.
        schema: {field_name: python_type}
        """
        type_map = {
            int: "INTEGER",
            float: "DOUBLE PRECISION",
            str: "TEXT",
            bool: "BOOLEAN"
        }
        
        columns = []
        # Add a unique primary key for the record
        columns.append('"_id" UUID PRIMARY KEY DEFAULT gen_random_uuid()')
        
        for field, py_type in schema.items():
            sql_type = type_map.get(py_type, "TEXT")
            columns.append(f'"{field}" {sql_type}')
            
        # Add internal audit columns
        columns.append('"_source_id" TEXT')
        columns.append('"_collection_date" TEXT')
        columns.append('"_ingested_at" TIMESTAMPTZ DEFAULT NOW()')
        columns.append('"_pipeline_version" TEXT')
        columns.append('"_confidence" DOUBLE PRECISION')
        columns.append('"_hash" TEXT UNIQUE') # For deduplication / UPSERT
        
        sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cursor:
                    # Enable pgcrypto for gen_random_uuid if needed
                    cursor.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
                    cursor.execute(sql)
                conn.commit()
            return True
        except Exception as e:
            print(f"Error creating table in Supabase: {e}")
            return False
