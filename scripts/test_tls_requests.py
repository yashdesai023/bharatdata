import requests,sys
urls = ["https://data.gov.in","https://censusindia.gov.in"]
for u in urls:
    try:
        r = requests.get(u, timeout=10)
        print(u, r.status_code)
    except Exception as e:
        print(u, "ERROR:", type(e).__name__, e)
