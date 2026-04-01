import os
import sys
import json
from datetime import datetime
from typing import List, Dict

# Resolved imports
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.db_connection import get_cursor
from utils.logger_config import pipeline_logger as logger

def check_required_fields(cursor) -> dict:
    """Verify no null values in critical fields across all tables."""
    checks = {
        "crime_records_state": ["state", "state_code", "year", "category", "total_cases", "confidence"],
        "crime_records_district": ["state", "district", "year", "category", "total_cases", "confidence"],
        "crime_records_city": ["city", "parent_state", "year", "category", "total_cases", "confidence"]
    }
    issues = []
    
    for table, fields in checks.items():
        for field in fields:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} IS NULL")
            null_count = cursor.fetchone()[0]
            if null_count > 0:
                issues.append({"table": table, "field": field, "null_count": null_count, "severity": "critical"})
    
    return {"check": "required_fields", "passed": len(issues) == 0, "issues": issues}

def check_confidence_distribution(cursor) -> dict:
    """Audit the confidence scores to ensure transparency."""
    cursor.execute("""
        SELECT 
            AVG(confidence) as avg_conf,
            COUNT(*) FILTER (WHERE confidence < 0.5) as low_conf_count,
            COUNT(*) FILTER (WHERE confidence = 1.0) as perfect_conf_count,
            COUNT(*) as total
        FROM (
            SELECT confidence FROM crime_records_state
            UNION ALL
            SELECT confidence FROM crime_records_district
            UNION ALL
            SELECT confidence FROM crime_records_city
        ) combined
    """)
    avg_conf, low_count, perfect_count, total = cursor.fetchone()
    
    issues = []
    if avg_conf and avg_conf < 0.8:
        issues.append({"message": f"Average confidence {avg_conf:.2f} is lower than target 0.8", "severity": "warning"})
    
    return {
        "check": "confidence_distribution", 
        "passed": len(issues) == 0, 
        "metrics": {
            "average": float(avg_conf) if avg_conf else 0,
            "low_confidence_count": low_count,
            "perfect_confidence_count": perfect_count,
            "total_records": total
        },
        "issues": issues
    }

def check_geographic_coverage(cursor) -> dict:
    """Verify all 36 States/UTs are represented for each year."""
    cursor.execute("""
        SELECT year, COUNT(DISTINCT state) 
        FROM crime_records_state 
        GROUP BY year 
        ORDER BY year
    """)
    results = cursor.fetchall()
    
    issues = []
    coverage = {}
    for year, count in results:
        coverage[str(year)] = count
        if count < 36:
            issues.append({"message": f"Year {year} only has {count}/36 states represented", "severity": "warning"})
            
    return {"check": "geographic_coverage", "passed": len(issues) == 0, "coverage": coverage, "issues": issues}

def check_logical_consistency(cursor) -> dict:
    """Check for negative values or impossible rates."""
    issues = []
    
    # Check for negative total_cases
    tables = ["crime_records_state", "crime_records_district", "crime_records_city"]
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t} WHERE total_cases < 0")
        neg_count = cursor.fetchone()[0]
        if neg_count > 0:
            issues.append({"message": f"Negative total_cases found in {t}", "count": neg_count, "severity": "critical"})
            
    # Check for extreme rates (e.g., rate > 5000 per lakh is highly suspicious)
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t} WHERE rate_per_lakh > 5000")
        high_rate = cursor.fetchone()[0]
        if high_rate > 0:
            issues.append({"message": f"Extreme rate (>5000) found in {t}", "count": high_rate, "severity": "warning"})
            
    return {"check": "logical_consistency", "passed": len(issues) == 0, "issues": issues}

def run_all_checks() -> dict:
    """Run the complete diagnostic suite."""
    try:
        with get_cursor() as cursor:
            checks = [
                check_required_fields(cursor),
                check_confidence_distribution(cursor),
                check_geographic_coverage(cursor),
                check_logical_consistency(cursor)
            ]
            
            all_passed = all(c["passed"] for c in checks)
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "EXCELLENT" if all_passed else "ATTENTION_REQUIRED",
                "overall_health": "100%" if all_passed else f"{len([c for c in checks if c['passed']])/len(checks)*100:.0f}%",
                "checks": checks
            }
            return summary
    except Exception as e:
        logger.error(f"Quality Check Failed: {e}")
        return {"status": "ERROR", "message": str(e)}

if __name__ == "__main__":
    report = run_all_checks()
    print(json.dumps(report, indent=2))
    
    # Save as JSON for automation
    os.makedirs(os.path.join(pipeline_root, "monitoring", "reports"), exist_ok=True)
    report_path = os.path.join(pipeline_root, "monitoring", "reports", f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.success(f"Detailed Quality Report saved to {report_path}")
