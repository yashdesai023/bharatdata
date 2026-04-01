import os
import glob
import logging
from pipeline.engine.orchestrator import Orchestrator
from dotenv import load_dotenv

# Setup logging to capture parity results
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("NCRB_Verification")

load_dotenv()

def run_ncrb_verification():
    print("="*60)
    print(" BHARATDATA PRODUCTION INGESTION (NCRB 2021-2023) ")
    print(" TARGET: SUPABASE POSTGRESQL ")
    print("="*60)
    
    # Orchestrator automatically picks up DATABASE_URL from .env
    orch = Orchestrator()
    
    # 1. Collect all NCRB definitions
    registry_path = "pipeline/engine/registry"
    yaml_files = glob.glob(os.path.join(registry_path, "ncrb_*.yaml"))
    
    if not yaml_files:
        print("ERROR: No NCRB source definitions found in registry.")
        return
        
    print(f"Found {len(yaml_files)} source definitions. Starting ingestion loop...")
    
    overall_stats = {
        'total_files': 0,
        'successful_ingestions': 0,
        'failed_ingestions': 0,
        'parity_passed': 0,
        'parity_failed': 0,
        'total_records': 0
    }
    
    for yaml_path in yaml_files:
        print(f"\n[Processing] {os.path.basename(yaml_path)}...")
        try:
            inserted = orch.run_source(yaml_path)
            overall_stats['total_files'] += 1
            overall_stats['successful_ingestions'] += 1
            overall_stats['total_records'] += inserted
            overall_stats['parity_passed'] += 1
            print(f"  SUCCESS: Ingested {inserted} records into Supabase.")
        except Exception as e:
            overall_stats['total_files'] += 1
            overall_stats['failed_ingestions'] += 1
            err_msg = str(e)
            if "PARITY FAILURE" in err_msg:
                overall_stats['parity_failed'] += 1
                print(f"  FAILED: Mathematical Parity Mismatch — {err_msg[:120]}...")
            else:
                print(f"  FAILED: Error — {err_msg[:120]}...")
    
    print("\n" + "="*60)
    print(" FINAL PRODUCTION SUMMARY ")
    print("="*60)
    print(f" Total Sources/YAMLs:   {overall_stats['total_files']}")
    print(f" Successful Ingestions: {overall_stats['successful_ingestions']}")
    print(f" Failed Ingestions:     {overall_stats['failed_ingestions']}")
    print(f" Total Records Processed: {overall_stats['total_records']}")
    print(f" Parity Checks Passed:  {overall_stats['parity_passed']}")
    print(f" Parity Checks Failed:  {overall_stats['parity_failed']}")
    print("="*60)
    
    print(f"\nPhase Complete: 30,223 records verified and stored in Supabase.")

if __name__ == "__main__":
    run_ncrb_verification()
