import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from pipeline.utils.db_connection import get_cursor

def list_tables():
    print("Listing all tables in public schema:")
    try:
        with get_cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [t[0] for t in cur.fetchall()]
            for table in tables:
                print(f" - {table}")
            
            if "pollution_records" in tables:
                print("\n✅ FOUND: 'pollution_records'")
            else:
                print("\n❌ NOT FOUND: 'pollution_records'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables()
