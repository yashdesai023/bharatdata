import requests, os, re, urllib.parse, time
from urllib.parse import urlparse

outdir = "pipeline/engine/registry/data_gov"
os.makedirs(outdir, exist_ok=True)
q = "Census PCA 2011"

session = requests.Session()
session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
bundle = os.environ.get('REQUESTS_CA_BUNDLE')
if bundle:
    session.verify = bundle

# Try CKAN API on likely domains first
domains = ['https://catalog.data.gov.in', 'https://data.gov.in', 'https://www.data.gov.in']
found = []
for dom in domains:
    api = dom.rstrip('/') + '/api/3/action/package_search'
    try:
        r = session.get(api, params={'q': q, 'rows': 50}, timeout=30, headers={'Accept':'application/json'})
        if r.ok and 'application/json' in r.headers.get('Content-Type',''):
            data = r.json()
            results = data.get('result', {}).get('results', [])
            for pkg in results:
                for res in pkg.get('resources', []):
                    url = res.get('url') or res.get('resource_url') or ''
                    if 'data.gov.in' in url:
                        found.append({'pkg_title': pkg.get('title',''), 'resource_url': pkg.get('url',''), 'download_url': url, 'format': (res.get('format') or '').lower()})
            if found:
                break
    except Exception as e:
        print('API attempt failed for', dom, ':', e)

# Fallback: HTML search pages and follow resource pages (restrict to data.gov.in host)
if not found:
    search_paths = ['/search?search_api_fulltext=', '/catalog?search=', '/search?q=']
    for dom in domains:
        for sp in search_paths:
            url = dom.rstrip('/') + sp + urllib.parse.quote(q)
            try:
                r = session.get(url, timeout=30)
                if not r.ok:
                    continue
                txt = r.text
                links = re.findall(r'href=["\']([^"\']+)["\']', txt, flags=re.I)
                for link in links:
                    if link.startswith('//'):
                        link = 'https:' + link
                    elif link.startswith('/'):
                        link = urllib.parse.urljoin(dom, link)
                    # direct file links on data.gov.in
                    if 'data.gov.in' in link and re.search(r'\.(xls|xlsx|csv)$', link, flags=re.I):
                        found.append({'pkg_title':'', 'resource_url': dom, 'download_url': link, 'format': 'auto'})
                    # dataset/resource pages on data.gov.in — follow and scan for file links
                    elif 'data.gov.in' in link and re.search(r'/dataset/|/resource/', link, flags=re.I):
                        try:
                            r2 = session.get(link, timeout=20)
                            links2 = re.findall(r'href=["\']([^"\']+)["\']', r2.text, flags=re.I)
                            for l2 in links2:
                                if l2.startswith('//'):
                                    l2 = 'https:' + l2
                                elif l2.startswith('/'):
                                    l2 = urllib.parse.urljoin(link, l2)
                                if 'data.gov.in' in l2 and re.search(r'\.(xls|xlsx|csv)$', l2, flags=re.I):
                                    found.append({'pkg_title':'', 'resource_url': link, 'download_url': l2, 'format': 'auto'})
                        except Exception:
                            pass
                if len(found) >= 10:
                    break
            except Exception as e:
                print('HTML search failed for', url, ':', e)
        if len(found) >= 10:
            break

# Deduplicate and keep only data.gov.in-hosted links
unique = {}
for f in found:
    du = f.get('download_url') or f.get('resource_url')
    if not du:
        continue
    parsed = urlparse(du)
    # ensure host contains data.gov.in
    if 'data.gov.in' not in parsed.netloc:
        continue
    key = du
    if key not in unique:
        unique[key] = f

results = list(unique.values())[:5]
count = 0
for i, r in enumerate(results):
    safe_id = 'dg_{}_{}'.format(i+1, re.sub(r'[^0-9a-zA-Z_\-]', '_', (r.get('download_url') or r.get('resource_url')) )[:40])
    yaml_path = os.path.join(outdir, safe_id + '.yaml')
    title = r.get('pkg_title') or 'data_gov resource {}'.format(i+1)
    with open(yaml_path, 'w', encoding='utf8') as fh:
        fh.write('source: data_gov\n')
        fh.write('id: {}\n'.format(safe_id))
        fh.write('title: "{}"\n'.format(title.replace('"','\\"')))
        fh.write('resource_url: "{}"\n'.format(r.get('resource_url','')))
        fh.write('download_url: "{}"\n'.format(r.get('download_url','')))
        fh.write('format: {}\n'.format(r.get('format','auto')))
        fh.write('concurrency: 1\n')
        fh.write('jitter: 8\n')
        fh.write('user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"\n')
        fh.write('ssl_verify: true\n')
        fh.write('browser_download: false\n')
        fh.write('allow_insecure_fallback: false\n')
    print('Wrote', yaml_path)
    count += 1

print('Generated', count, 'YAMLs')
