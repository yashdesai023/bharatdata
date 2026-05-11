import requests, os, sys, re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

outdir = "pipeline/engine/registry/data_gov"
os.makedirs(outdir, exist_ok=True)
q = "Census PCA 2011"
params = {"q": q, "rows": 50}

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=frozenset(['GET','POST']))
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
# prefer environment bundle if set
bundle = os.environ.get('REQUESTS_CA_BUNDLE')
if bundle:
    session.verify = bundle

print("Searching data.gov.in for:", q)
resp = session.get("https://data.gov.in/api/3/action/package_search", params=params, timeout=60)
resp.raise_for_status()
data = resp.json()
results = data.get("result", {}).get("results", [])
count = 0
for pkg in results:
    resources = pkg.get("resources", [])
    for res in resources:
        fmt = (res.get("format") or "").lower()
        name = (res.get("name") or "") or (res.get("resource_type") or "")
        desc = (res.get("description") or "").lower()
        if fmt in ("xls","xlsx","csv") or ("pca" in name.lower()) or ("primary census abstract" in desc):
            rid = res.get("id") or str(res.get("url","")).split("/")[-1][:20]
            download_url = res.get("url")
            if not download_url:
                continue
            safe_id = re.sub(r"[^0-9a-zA-Z_\-]", "_", str(rid))
            title_raw = pkg.get("title","")
            title_escaped = title_raw.replace('"','\\"')
            yaml_path = os.path.join(outdir, safe_id + ".yaml")
            with open(yaml_path, "w", encoding="utf8") as fh:
                fh.write("source: data_gov\n")
                fh.write("id: {}\n".format(safe_id))
                fh.write('title: "{}"\n'.format(title_escaped))
                fh.write('resource_url: "{}"\n'.format(pkg.get('url','')))
                fh.write('download_url: "{}"\n'.format(download_url))
                fh.write('format: {}\n'.format(fmt))
                fh.write('concurrency: 1\n')
                fh.write('jitter: 8\n')
                fh.write('user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"\n')
                fh.write('ssl_verify: true\n')
                fh.write('browser_download: false\n')
                fh.write('allow_insecure_fallback: false\n')
            print("Wrote", yaml_path)
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break
print("Generated", count, "YAML files in", outdir)
