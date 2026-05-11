import os, json, sys
# Ensure repo root is on sys.path so pipeline package can be imported
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from pipeline.engine.extractors.extractor_factory import ExtractorFactory
from pipeline.engine.normalizers.geographic_resolver import GeographicResolver
from pipeline.engine.normalizers.type_enforcer import TypeEnforcer
from pipeline.engine.normalizers.null_handler import NullHandler
from pipeline.engine.normalizers.confidence_scorer import ConfidenceScorer
from pipeline.engine.normalizers.metadata_attacher import MetadataAttacher

repo_root = os.getcwd()
yaml_path = os.path.join(repo_root, 'pipeline', 'engine', 'registry', 'census_2011_pca.yaml')

import yaml
with open(yaml_path,'r',encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

ex_cfg = cfg.get('extraction', {})
fmt = ex_cfg.get('format')
extractor = ExtractorFactory.get_extractor(fmt, ex_cfg)

# Process all raw files in the raw/ directory and generate golden JSONs
raw_dir = os.path.join(repo_root, 'pipeline', 'tests', 'fixtures', 'census2011', 'raw')
files = [os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.lower().endswith(('.xlsx','.xls','.csv','.pdf'))]
if not files:
    raise SystemExit('No raw files found in fixtures raw dir')

geo = GeographicResolver()
te = TypeEnforcer()
nullh = NullHandler()
sc = ConfidenceScorer()

col_map = ex_cfg.get('column_mapping', {})

for file_path in files:
    res = extractor.extract(file_path)
    records = res.get('records', [])
    if not records:
        print(f'No records extracted from {file_path}, skipping')
        continue

    # minimal normalization per record
    clean = []
    for raw in records:
        for pattern, info in col_map.items():
            # ensure field keys exist
            f = info['field']
            if f not in raw:
                raw[f] = None
        # type enforcement and null handling
        for pattern, info in col_map.items():
            f = info['field']
            strat = cfg.get('normalization', {}).get('null_handling', {}).get(f, 'null')
            raw[f] = nullh.handle(raw.get(f), strategy=strat)
            if info.get('type') == 'int':
                raw[f] = te.to_int(raw.get(f))
            elif info.get('type') == 'float':
                raw[f] = te.to_float(raw.get(f))

        # Resolve state if present
        res_val, ded = geo.resolve(raw.get('State') or raw.get('state') or raw.get('state_code'))
        raw['state_code'] = res_val
        raw['_confidence'] = sc.calculate(fmt, ded)
        final = MetadataAttacher({'id': os.path.basename(file_path), 'year': 2011}).attach(raw)
        clean.append(final)

    # write golden for first record
    out_dir = os.path.join(repo_root, 'pipeline', 'tests', 'fixtures', 'census2011', 'golden')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(file_path))[0]
    out_path = os.path.join(out_dir, f"{base}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(clean[0], f, indent=2, ensure_ascii=False)
    print(f'Wrote golden {out_path}')