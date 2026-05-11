import requests, os
s = requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
bundle = os.environ.get('REQUESTS_CA_BUNDLE')
if bundle:
    s.verify = bundle
r = s.get("https://data.gov.in/api/3/action/package_search", params={'q':'Census PCA 2011','rows':10}, timeout=60)
print('STATUS', r.status_code)
print('HEADERS', dict(r.headers))
print('TEXT_SNIPPET:\n', r.text[:4000])
