import requests
import json

API_KEY = "579b464db66ec23bdd0000014e7f63a8f8fd4f896232f3d73076b8b2"

print("=" * 65)
print("TEST 1: Resource API — Summary Data (West Bengal)")
print("=" * 65)
try:
    r = requests.get(
        f"https://api.data.gov.in/resource/primary-census-abstract-2011-west-bengal?api-key={API_KEY}&format=json&limit=1",
        timeout=30
    )
    print(f"  HTTP Status : {r.status_code}")
    d = r.json()
    print(f"  API Status  : {d.get('status')}")
    print(f"  Total Rows  : {d.get('total')}")
    print(f"  Message     : {d.get('message', 'None')}")
except Exception as e:
    print(f"  EXCEPTION   : {e}")


print()
print("=" * 65)
print("TEST 2: Web Portal HTML — Granular Resource Page (Bihar)")
print("=" * 65)
try:
    r = requests.get(
        "https://data.gov.in/resource/village-town-wise-primary-census-abstract-2011-bihar",
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; BharatData/1.0)"}
    )
    print(f"  HTTP Status : {r.status_code}")
    print(f"  Page Length : {len(r.text)} bytes")
    has_uuid = any(k in r.text for k in ["api-key", "resource_id", "data-id", "index_name"])
    print(f"  Has API Ref : {has_uuid}")
    # Show a snippet
    if "api-key" in r.text:
        idx = r.text.index("api-key")
        print(f"  API Key ctx : ...{r.text[max(0,idx-50):idx+100]}...")
except Exception as e:
    print(f"  EXCEPTION   : {e}")


print()
print("=" * 65)
print("TEST 3: Resource API — Granular Data (Bihar Village-wise)")
print("=" * 65)
try:
    r = requests.get(
        f"https://api.data.gov.in/resource/village-town-wise-primary-census-abstract-2011-bihar?api-key={API_KEY}&format=json&limit=1",
        timeout=30
    )
    print(f"  HTTP Status : {r.status_code}")
    d = r.json()
    print(f"  API Status  : {d.get('status')}")
    print(f"  Total Rows  : {d.get('total')}")
    print(f"  Message     : {d.get('message', 'None')}")
except Exception as e:
    print(f"  EXCEPTION   : {e}")


print()
print("=" * 65)
print("TEST 4: Dataset Search API — Is it active at all?")
print("=" * 65)
for endpoint in ["/dataset.json", "/dataset", "/catalog", "/catalog.json"]:
    try:
        r = requests.get(
            f"https://api.data.gov.in{endpoint}?api-key={API_KEY}&format=json&limit=1",
            timeout=15
        )
        print(f"  {endpoint:<20} HTTP {r.status_code}")
    except Exception as e:
        print(f"  {endpoint:<20} TIMEOUT/ERROR")
