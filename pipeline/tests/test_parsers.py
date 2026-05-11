import os
import glob
import yaml
import pytest

# This test suite validates that each source YAML used by the universal pipeline
# contains the minimum required metadata and that a fixture directory exists.

# Accept either legacy 'sources/' YAML shape OR registry YAML under pipeline/engine/registry
# Legacy shape: keys like name, source_url, format, available_years
# Registry shape: identity: {id,name,...}, acquisition.url, extraction.format
REQUIRED_KEYS = {"name", "source_url", "format", "available_years"}

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_source_yamls_have_required_fields():
    repo_root = os.getcwd()
    # Source YAMLs may live in 'sources/' or in pipeline/engine/registry/
    yaml_dirs = [os.path.join(repo_root, "sources"), os.path.join(repo_root, "pipeline", "engine", "registry")]
    yaml_files = []
    for d in yaml_dirs:
        yaml_files.extend(glob.glob(os.path.join(d, "*.yaml")))

    assert yaml_files, f"No source YAML files found in {yaml_dirs}"

    missing = []
    for p in yaml_files:
        data = load_yaml(p) or {}
        # If registry style YAML
        if 'identity' in data and 'extraction' in data and data['extraction'].get('format'):
            continue
        # If legacy style YAML
        if REQUIRED_KEYS.issubset(set(data.keys())):
            continue
        # Otherwise mark as missing
        missing.append((p, 'missing required top-level or registry keys'))

    if missing:
        msgs = [f"{p} missing: {m}" for p, m in missing]
        pytest.fail("; ".join(msgs))


def test_fixture_exists_for_priority_dataset():
    # Ensure tests include at least one fixture for Census 2011 under pipeline/tests/fixtures
    fixture_dir = os.path.join(os.getcwd(), "pipeline", "tests", "fixtures", "census2011")
    assert os.path.isdir(fixture_dir), f"Expected fixture directory not found: {fixture_dir}"


def test_census_extractor_on_sample():
    # Load the registry YAML for census and run the extractor on the sample fixture
    repo_root = os.getcwd()
    yaml_path = os.path.join(repo_root, 'pipeline', 'engine', 'registry', 'census_2011_pca.yaml')
    assert os.path.isfile(yaml_path), f"Registry yaml not found: {yaml_path}"

    data = load_yaml(yaml_path)
    extraction_cfg = data.get('extraction', {})
    fmt = extraction_cfg.get('format')
    assert fmt, 'No extraction format declared in registry yaml'

    from pipeline.engine.extractors.extractor_factory import ExtractorFactory

    extractor = ExtractorFactory.get_extractor(fmt, extraction_cfg)
    sample_file = os.path.join(repo_root, 'pipeline', 'tests', 'fixtures', 'census2011', 'raw', 'sample.xlsx')
    assert os.path.isfile(sample_file), f"Sample file not found: {sample_file}"

    res = extractor.extract(sample_file)
    assert 'records' in res and len(res['records']) > 0, 'Extractor returned no records'

    # Normalize using pipeline normalizers to produce final record
    from pipeline.engine.normalizers.geographic_resolver import GeographicResolver
    from pipeline.engine.normalizers.type_enforcer import TypeEnforcer
    from pipeline.engine.normalizers.null_handler import NullHandler
    from pipeline.engine.normalizers.confidence_scorer import ConfidenceScorer
    from pipeline.engine.normalizers.metadata_attacher import MetadataAttacher

    geo = GeographicResolver()
    te = TypeEnforcer()
    nh = NullHandler()
    cs = ConfidenceScorer()

    # Build metadata similar to Orchestrator
    metadata = {'id': 'census_2011_pca_sample.xlsx', 'year': 2011}
    attacher = MetadataAttacher(metadata)

    raw_record = res['records'][0]
    # apply null handler and type enforcement based on registry column_mapping
    col_map = extraction_cfg.get('column_mapping', {})
    # invert map to find types by field
    type_by_field = {}
    for pattern, info in col_map.items():
        type_by_field[info['field']] = info.get('type','str')

    for field in list(raw_record.keys()):
        strat = data.get('normalization', {}).get('null_handling', {}).get(field, 'null')
        raw_record[field] = nh.handle(raw_record.get(field), strategy=strat)
        ftype = type_by_field.get(field)
        if ftype == 'int':
            raw_record[field] = te.to_int(raw_record[field])
        elif ftype == 'float':
            raw_record[field] = te.to_float(raw_record[field])

    # resolve primary entity (state) using 'State' mapping to state_code
    res_val, deduction = geo.resolve(raw_record.get('State') or raw_record.get('state') or raw_record.get('state_code'))
    # find which field maps to State -> in registry it's state_code
    raw_record['state_code'] = res_val
    raw_record['_confidence'] = cs.calculate(fmt, deduction)

    final = attacher.attach(raw_record)

    # Load golden and compare key fields
    golden_path = os.path.join(repo_root, 'pipeline', 'tests', 'fixtures', 'census2011', 'golden', 'sample.json')
    assert os.path.isfile(golden_path), f"Golden file not found: {golden_path}"
    import json
    with open(golden_path, 'r', encoding='utf-8') as gf:
        golden = json.load(gf)

    # Compare a subset of fields
    keys_to_check = ['state_code','district_code','entity_name','total_population','male_population','female_population','year']
    for k in keys_to_check:
        a = final.get(k)
        b = golden.get(k)
        if isinstance(a, str) and isinstance(b, str):
            assert str(a).strip().lower() == str(b).strip().lower(), f"Mismatch for {k}: got {a} expected {b}"
        else:
            assert a == b, f"Mismatch for {k}: got {a} expected {b}"

    # Confidence sanity check: must be a reasonable value >= 0.4
    assert float(final.get('_confidence',0)) >= 0.4, f"Low confidence: {final.get('_confidence',0)}"
