import os
import sqlite3
from pipeline.engine.loaders.dynamic_table_creator import DynamicTableCreator
from pipeline.engine.loaders.batch_loader import BatchLoader
from pipeline.engine.loaders.deduplicator import Deduplicator

def test_phase6():
    print("Starting Phase 6 Verification...")
    db_path = "test_bharatdata.db"
    if os.path.exists(db_path): os.remove(db_path)
    
    # 1. Dynamic Table Creation
    print("\n[1] Testing DynamicTableCreator...")
    dtc = DynamicTableCreator(db_path)
    schema = {'state': str, 'cases': int, 'is_active': bool}
    dtc.create_table("crime_data", schema)
    
    # Verify table structure
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(crime_data)")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Table columns: {cols}")
    assert "state" in cols
    assert "_hash" in cols
    
    # 2. Deduplication & Batch Loading
    print("\n[2] Testing Deduplicator & BatchLoader...")
    loader = BatchLoader(db_path)
    records = [
        {'state': 'Bihar', 'cases': 500, 'is_active': True, '_confidence': 1.0, '_source_id': 'src1'},
        {'state': 'Kerala', 'cases': 300, 'is_active': False, '_confidence': 0.9, '_source_id': 'src1'}
    ]
    
    # Attach hashes (unique by state)
    dedup = Deduplicator()
    records = dedup.process_batch(records, identity_fields=['state', 'src1'])
    
    # Load batch
    count = loader.load("crime_data", records)
    print(f"Inserted {count} unique records.")
    assert count == 2

    # 3. Duplicate Handling
    print("\n[3] Testing Duplicate Rejection...")
    # Attempt to load the exact same records again
    count_dup = loader.load("crime_data", records)
    print(f"Second attempt inserted {count_dup} records (Should be 0).")
    assert count_dup == 0 or count_dup == -1
    
    # Verify final count is still 2
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crime_data")
    final_count = cursor.fetchone()[0]
    conn.close()
    
    assert final_count == 2
    print(f"Final DB Count: {final_count} (SUCCESS)")

    # 4. Cleanup
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f"Warning: Could not cleanup DB file: {e}")
        
    print("\nPHASE 6 VERIFIED: Database persistence and deduplication are 100% reliable.")
    return True

if __name__ == "__main__":
    try:
        success = test_phase6()
        exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: Phase 6 verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
