import requests, os, re, time, urllib.parse

session = requests.Session()
session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
bundle = os.environ.get('REQUESTS_CA_BUNDLE')
if bundle:
    session.verify = bundle

q = 'Census PCA 2011'
endpoints = [
    f'https://data.gov.in/search?search_api_fulltext={urllib.parse.quote(q)}',
    f'https://data.gov.in/catalog?search={urllib.parse.quote(q)}',
    f'https://data.gov.in/search?q={urllib.parse.quote(q)}',
    f'https://data.gov.in/search/node/{urllib.parse.quote(q)}',
    f'https://data.gov.in/catalog?keys={urllib.parse.quote(q)}'
]

found = set()
results = []
for url in endpoints:
    try:
        print('GET', url)
        r = session.get(url, timeout=30)
        txt = r.text
        # find hrefs
        links = re.findall(r'href=["\']([^"\']+)["\']', txt, flags=re.I)
        for link in links:
            if link.startswith('//'):
                link = 'https:' + link
            if link.startswith('/'):
                link = urllib.parse.urljoin(url, link)
            if re.search(r'\.(xls|xlsx|csv)$', link, flags=re.I) or 'censusindia.gov.in' in link:
                if link not in found:
                    found.add(link)
                    results.append({'resource_url': url, 'download_url': link})
            elif re.search(r'/catalog/|/dataset/|/resource/', link, flags=re.I):
                if link not in found:
                    found.add(link)
                    results.append({'resource_url': link, 'download_url': ''})
        if len(results) >= 20:
            break
    except Exception as e:
        print('error', url, e)
    time.sleep(1)

# select top 5
selected = []
for r in results:
    if r['download_url']:
        selected.append(r)
    if len(selected) >= 5:
        break
if len(selected) < 5:
    for r in results:
        if r not in selected:
            selected.append(r)
        if len(selected) >= 5:
            break

outdir = 'pipeline/engine/registry/data_gov'
os.makedirs(outdir, exist_ok=True)
for i, r in enumerate(selected):
    safe_id = 'dg_{}_{}'.format(i+1, re.sub(r'[^0-9a-zA-Z_\-]', '_', r['resource_url'])[:40])
    yaml_path = os.path.join(outdir, safe_id + '.yaml')
    title = 'data_gov resource {}'.format(i+1)
    with open(yaml_path, 'w', encoding='utf8') as fh:
        fh.write('source: data_gov\n')
        fh.write('id: {}\n'.format(safe_id))
        fh.write('title: "{}"\n'.format(title.replace('"','\\"')))
        fh.write('resource_url: "{}"\n'.format(r['resource_url']))
        if r['download_url']:
            fh.write('download_url: "{}"\n'.format(r['download_url']))
        fh.write('format: auto\nconcurrency: 1\njitter: 8\nuser_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"\nssl_verify: true\nbrowser_download: false\nallow_insecure_fallback: false\n')
    print('Wrote', yaml_path)

print('Generated', len(selected),'YAMLs')
