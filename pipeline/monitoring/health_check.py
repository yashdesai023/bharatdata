import os
import sys
import json
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv

# Path resolution for .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# Data sources to check
SOURCES = [
    {
        "name": "NCRB Additional Tables 2023",
        "url": "https://www.ncrb.gov.in/crime-in-india-additional-table?year=2023&category=",
        "expected_status": 200,
    },
    {
        "name": "NCRB Additional Tables 2022",
        "url": "https://www.ncrb.gov.in/crime-in-india-additional-table?year=2022&category=",
        "expected_status": 200,
    },
    {
        "name": "NCRB Additional Tables 2021",
        "url": "https://www.ncrb.gov.in/crime-in-india-additional-table?year=2021&category=",
        "expected_status": 200,
    },
    {
        "name": "NCRB Main Website",
        "url": "https://ncrb.gov.in",
        "expected_status": 200,
    },
]

def check_source(source: dict) -> dict:
    """Check a single data source URL."""
    result = {
        "name": source["name"],
        "url": source["url"],
        "checked_at": datetime.utcnow().isoformat(),
        "healthy": False,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
        "content_hash": None,
    }
    
    try:
        response = requests.get(
            source["url"],
            timeout=30,
            headers={
                "User-Agent": "BharatData Health Check (https://github.com/BharatData)"
            }
        )
        
        result["status_code"] = response.status_code
        result["response_time_ms"] = int(response.elapsed.total_seconds() * 1000)
        result["content_hash"] = hashlib.sha256(response.content).hexdigest()[:16]
        
        if response.status_code == source["expected_status"]:
            result["healthy"] = True
        else:
            result["error"] = f"Expected status {source['expected_status']}, got {response.status_code}"
    
    except requests.Timeout:
        result["error"] = "Request timed out after 30 seconds"
    except requests.ConnectionError as e:
        result["error"] = f"Connection failed: {str(e)[:200]}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)[:200]}"
    
    return result

def run_health_check() -> dict:
    """Run health checks on all registered sources."""
    print("BharatData Daily Health Check")
    print("=" * 50)
    
    results = []
    all_healthy = True
    
    for source in SOURCES:
        print(f"\nChecking: {source['name']}")
        print(f"  URL: {source['url']}")
        
        result = check_source(source)
        results.append(result)
        
        if result["healthy"]:
            print(f"  ✅ Healthy (status {result['status_code']}, {result['response_time_ms']}ms)")
        else:
            print(f"  ❌ UNHEALTHY: {result['error']}")
            all_healthy = False
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "HEALTHY" if all_healthy else "UNHEALTHY",
        "sources_checked": len(results),
        "sources_healthy": sum(1 for r in results if r["healthy"]),
        "sources_unhealthy": sum(1 for r in results if not r["healthy"]),
        "results": results,
    }
    
    print(f"\n{'=' * 50}")
    print(f"Overall: {report['status']}")
    print(f"Healthy: {report['sources_healthy']}/{report['sources_checked']}")
    
    return report

if __name__ == "__main__":
    report = run_health_check()
    
    # Write report
    report_path = os.getenv("HEALTH_REPORT_PATH", "health_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    sys.exit(0 if report["status"] == "HEALTHY" else 1)
