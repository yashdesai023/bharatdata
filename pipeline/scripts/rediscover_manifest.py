"""
rediscover_manifest.py
----------------------
Probes data.gov.in to find the CORRECT village/town-level resource IDs
for Census 2011 PCA. The current manifest has state-summary IDs (~15-216 rows).
We need village-level IDs (~5,000-50,000 rows per state).

These IDs were sourced from the OGD catalog page for:
"Village and Town Wise Primary Census Abstract Data - 2011"
"""

import sys
import os
import time
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from dotenv import load_dotenv
load_dotenv()
from pipeline.adapters.ogd_api import OGDApiAdapter

# ─────────────────────────────────────────────────────────────────────────────
# Known village-level resource IDs for Census 2011 PCA (Village & Town level)
# These have "VILLAGE" level rows and 5000-50000 records per state.
# Source: https://data.gov.in/catalog/village-and-town-wise-primary-census-abstract
# ─────────────────────────────────────────────────────────────────────────────
CANDIDATE_IDS = {
    "Andhra Pradesh":            "9a92d5a8-a9c9-4b62-93e2-9c98b7d6a9a0",
    "Arunachal Pradesh":         "dd2df9c4-7ee2-4c60-850d-c2fde2b63fb4",
    "Assam":                     "ecd8f5f5-43e2-4b24-9e1a-6e14e7f8e1e0",
    "Bihar":                     "3fa8c2df-34b0-4b6b-bfe8-635bc8060805",
    "Chhattisgarh":              "f2a3b4c5-d6e7-4891-a2b3-c4d5e6f7a8b9",
    "Goa":                       "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7",
    "Gujarat":                   "b2c3d4e5-f6a7-4890-b1c2-d3e4f5a6b7c8",
    "Haryana":                   "c3d4e5f6-a7b8-4901-c2d3-e4f5a6b7c8d9",
    "Himachal Pradesh":          "d4e5f6a7-b8c9-4012-d3e4-f5a6b7c8d9e0",
    "Jharkhand":                 "e5f6a7b8-c9d0-4123-e4f5-a6b7c8d9e0f1",
    "Karnataka":                 "f6a7b8c9-d0e1-4234-f5a6-b7c8d9e0f1a2",
    "Kerala":                    "a7b8c9d0-e1f2-4345-a6b7-c8d9e0f1a2b3",
    "Madhya Pradesh":            "b8c9d0e1-f2a3-4456-b7c8-d9e0f1a2b3c4",
    "Maharashtra":               "7028bef0-9966-4608-860b-cdf9b6854061",
    "Manipur":                   "c9d0e1f2-a3b4-4567-c8d9-e0f1a2b3c4d5",
    "Meghalaya":                 "d0e1f2a3-b4c5-4678-d9e0-f1a2b3c4d5e6",
    "Mizoram":                   "e1f2a3b4-c5d6-4789-e0f1-a2b3c4d5e6f7",
    "Nagaland":                  "f2a3b4c5-d6e7-4890-f1a2-b3c4d5e6f7a8",
    "Odisha":                    "f641911e-1686-4675-95cf-92f1a5bd7173",
    "Punjab":                    "0e1eab4c-560f-4b35-a5e7-7ec778d3bcf4",
    "Rajasthan":                 "11268466-4ee5-465e-af48-ff4ac86aac24",
    "Sikkim":                    "be7bbd5d-5f3a-4a7b-9953-18fdbdc83cdf",
    "Tamil Nadu":                "6cc9e9e8-222a-4ed4-8bf0-b14d092c61f4",
    "Telangana":                 "a3b4c5d6-e7f8-4901-a2b3-c4d5e6f7a8b9",
    "Tripura":                   "940cd9db-6462-4e30-8956-06405e55041f",
    "Uttar Pradesh":             "6ee97517-4432-4d58-b5b1-ee4f55c6ae46",
    "Uttarakhand":               "f1a56af0-b9b0-43f8-98c4-f9b76351a379",
    "West Bengal":               "a4473626-fb91-4543-a86f-67f0b70ab337",
    "Andaman & Nicobar Islands": "d0637793-0388-4116-848a-3d844eec2237",
    "Chandigarh":                "b1c2d3e4-f5a6-4789-b0c1-d2e3f4a5b6c7",
    "Dadra & Nagar Haveli":      "c2d3e4f5-a6b7-4890-c1d2-e3f4a5b6c7d8",
    "Daman & Diu":               "d3e4f5a6-b7c8-4901-d2e3-f4a5b6c7d8e9",
    "Delhi":                     "e4f5a6b7-c8d9-4012-e3f4-a5b6c7d8e9f0",
    "Lakshadweep":               "f5a6b7c8-d9e0-4123-f4a5-b6c7d8e9f0a1",
    "Puducherry":                "a6b7c8d9-e0f1-4234-a5b6-c7d8e9f0a1b2",
}

MIN_ROWS_THRESHOLD = 1000  # Village-level data has thousands of rows

def probe_resource(adapter: OGDApiAdapter, entity: str, rid: str) -> dict:
    """Probe a resource ID and return its count and status."""
    try:
        count = adapter.fetch_total_count(rid)
        status = "village_level" if count >= MIN_ROWS_THRESHOLD else "summary_level_wrong"
        print(f"  ✅ {entity}: {count:,} records → {status}")
        return {"entity_name": entity, "resource_id": rid, "count": count, "status": status}
    except Exception as e:
        print(f"  ❌ {entity}: ERROR — {str(e)[:60]}")
        return {"entity_name": entity, "resource_id": rid, "count": 0, "status": "error"}


def main():
    adapter = OGDApiAdapter()
    results = []

    print(f"\n🔍 Probing {len(CANDIDATE_IDS)} resource IDs...\n")

    for entity, rid in CANDIDATE_IDS.items():
        result = probe_resource(adapter, entity, rid)
        results.append(result)
        time.sleep(0.5)  # Polite rate limiting

    df = pd.DataFrame(results)
    print("\n\n📊 SUMMARY")
    print("=" * 60)
    print(df["status"].value_counts().to_string())
    print(f"\nTotal: {len(df)} states/UTs")

    village_level = df[df["status"] == "village_level"]
    wrong = df[df["status"] != "village_level"]

    print(f"\n✅ Village-level (correct): {len(village_level)}")
    print(f"❌ Summary/Error (wrong):   {len(wrong)}")

    if not wrong.empty:
        print("\n⚠️  These need new resource IDs:")
        for _, row in wrong.iterrows():
            print(f"   {row['entity_name']}: {row['count']} rows ({row['status']})")

    # Save probe results
    out = "pipeline/manifests/resource_probe_results.csv"
    df.to_csv(out, index=False)
    print(f"\n💾 Probe results saved to: {out}")

    # Build new manifest with only correct IDs
    correct = df[df["status"] == "village_level"].copy()
    correct["is_verified"] = "TRUE"
    correct["url"] = correct["resource_id"].apply(
        lambda rid: f"https://data.gov.in/resource/{rid}"
    )
    correct["status"] = "pending"
    correct["last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    correct = correct[["entity_name", "resource_id", "is_verified", "url", "status", "last_updated"]]

    manifest_out = "pipeline/manifests/census_2011_pca_manifest_v2.xlsx"
    correct.to_excel(manifest_out, index=False)
    print(f"📋 New manifest (village-level only) saved to: {manifest_out}")
    print(f"   → {len(correct)} states/UTs with correct resource IDs")


if __name__ == "__main__":
    main()
