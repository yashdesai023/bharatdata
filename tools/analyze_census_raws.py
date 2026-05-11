import os, sys, traceback
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)
from pipeline.engine.definition_loader import DefinitionLoader
from pipeline.engine.extractors.extractor_factory import ExtractorFactory

yaml_path = os.path.join(root, 'pipeline','engine','registry','census_2011_pca.yaml')
loader = DefinitionLoader()
source_def = loader.load(yaml_path)
ex_cfg = source_def.get('extraction', {})

raw_dir = os.path.join(root, 'data','raw','census-2011')
if not os.path.isdir(raw_dir):
    print('RAW_DIR_MISSING', raw_dir)
    sys.exit(0)

files = sorted([os.path.join(raw_dir,f) for f in os.listdir(raw_dir) if os.path.isfile(os.path.join(raw_dir,f))])
print('FOUND_FILES', len(files))
total = 0
errors = []
for f in files:
    try:
        ext = os.path.splitext(f)[1].lower().lstrip('.')
        fmt = 'xlsx' if ext in ('xlsx','xls') else ('csv' if ext=='csv' else ext)
        extractor = ExtractorFactory.get_extractor(fmt, ex_cfg)
        res = extractor.extract(f)
        cnt = len(res.get('records', []))
        print(f"OK\t{cnt}\t{f}")
        total += cnt
    except Exception as e:
        print(f"ERR\t{type(e).__name__}: {e}\t{f}")
        traceback.print_exc()
        errors.append(f)

print('\nSUMMARY')
print('TOTAL_RECORDS', total)
print('FILES_COUNT', len(files))
print('ERROR_FILES', len(errors))
if errors:
    for e in errors:
        print('ERR_FILE', e)
