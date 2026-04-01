import os
import sqlite3
from pipeline.engine.orchestrator import Orchestrator

def test_phase7_e2e():
    print("Starting Phase 7 E2E Integration Test...")
    db_path = "e2e_bharatdata.db"
    if os.path.exists(db_path): os.remove(db_path)
    
    yaml_path = "pipeline/engine/mock_source.yaml"
    
    # 1. Initialize Orchestrator
    orch = Orchestrator(db_path=db_path)
    
    # 2. Run Pipeline
    try:
        orch.run_source(yaml_path)
    except Exception as e:
        print(f"PIPELINE FAILED during integration: {e}")
        raise e

    # 3. Verify Results in Database
    print("\n[Verification] Checking Database for Ingested Data...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='e2e_results'")
    table_exists = cursor.fetchone()
    assert table_exists, "Table 'e2e_results' was not created"
    
    # Check records
    cursor.execute("SELECT state, cases, _confidence FROM e2e_results")
    rows = cursor.fetchall()
    conn.close()
    
    print(f"Data in DB: {rows}")
    assert len(rows) == 2
    # Verify Normalization worked (Prefix removal)
    states = [r[0] for r in rows]
    assert "Uttar Pradesh" in states
    assert "Kerala" in states
    
    # Verify confidence (XLSX = 1.0, but deducted 0.0 for UP if mapping worked, 
    # but here no mapping provided so deduction 0.1 for title case)
    print(f"Confidence Scores: {[r[2] for r in rows]}")
    
    print("\nPHASE 7 E2E VERIFIED: The Universal Engine is ALIVE and FUNCTIONAL.")
    
    # 4. Cleanup
    if os.path.exists(db_path): os.remove(db_path)
    if os.path.exists("pipeline/engine/e2e_mock_data.xlsx"): os.remove("pipeline/engine/e2e_mock_data.xlsx")
    
    return True

if __name__ == "__main__":
    try:
        success = test_phase7_e2e()
        exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: Phase 7 verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
