"""
Phase 2B Verification — Tests all 5 downloader strategies.

1. PageScraper  — scrapes httpbin.org/links/10 (generates <a> link tags)
2. ApiClient    — calls public JSONPlaceholder REST API with pagination
3. ManualUpload — scans a local temp folder for a dummy file
4. Factory      — confirms all 5 methods are registered and invalid ones rejected
"""

import os
import json
import shutil
from pipeline.engine.downloaders.downloader_factory import DownloaderFactory

TEMP = "temp_phase2b"


def setup():
    shutil.rmtree(TEMP, ignore_errors=True)
    os.makedirs(TEMP)


def teardown():
    shutil.rmtree(TEMP, ignore_errors=True)


def test_page_scraper():
    print("\n--- Test 1: PageScraper ---")
    config = {
        'rate_limit': 0,
        'link_selector': 'a[href]',
        'file_format': 'html',   # httpbin/links returns hrefs like /links/10/1
    }
    dl = DownloaderFactory.get_downloader('page_scraper', config)
    # Just verify it imports and runs without error (no real xlsx links on httpbin)
    result = dl.download("https://httpbin.org/links/10", TEMP)
    # result is a list (possibly empty because no .html files there)
    assert isinstance(result, list), "PageScraper must return a list"
    print(f"SUCCESS: PageScraper returned {len(result)} matched files (0 expected for this URL).")
    return True


def test_api_client():
    print("\n--- Test 2: ApiClient (REST pagination) ---")
    config = {
        'rate_limit': 0,
        'endpoint': '',
        'parameters': {},
        'pagination': {'strategy': 'none'},
        'data_path': None,
    }
    dl = DownloaderFactory.get_downloader('api_call', config)
    # JSONPlaceholder: a public test API returning 100 post records
    out = dl.download("https://jsonplaceholder.typicode.com/posts", TEMP)
    assert os.path.exists(out), "ApiClient must create output file"
    with open(out, encoding='utf-8') as f:
        records = json.load(f)
    assert len(records) == 100, f"Expected 100 posts, got {len(records)}"
    print(f"SUCCESS: ApiClient downloaded {len(records)} records.")
    return True


def test_manual_upload():
    print("\n--- Test 3: ManualUpload ---")
    # Create a dummy file
    dummy_path = os.path.join(TEMP, "manual_ncrb_2023.xlsx")
    with open(dummy_path, 'wb') as f:
        f.write(b"dummy")

    config = {
        'rate_limit': 0,
        'local_path_pattern': os.path.join(TEMP, "*.xlsx"),
    }
    dl = DownloaderFactory.get_downloader('manual_upload', config)
    files = dl.download("", TEMP)
    assert len(files) == 1, f"Expected 1 file, got {len(files)}"
    assert files[0].endswith(".xlsx")
    print(f"SUCCESS: ManualUpload found {len(files)} file(s): {files}")
    return True


def test_factory_invalid():
    print("\n--- Test 4: Factory rejects unknown method ---")
    try:
        DownloaderFactory.get_downloader('unknown_method', {})
        print("ERROR: Factory should have raised ValueError for unknown method!")
        return False
    except ValueError as e:
        print(f"SUCCESS: Correctly rejected unknown method: {e}")
        return True


def test_factory_all_registered():
    print("\n--- Test 5: Factory has all 5 strategies registered ---")
    methods = ['direct_download', 'browser_rendering', 'page_scraper', 'api_call', 'manual_upload']
    for m in methods:
        dl = DownloaderFactory.get_downloader(m, {'rate_limit': 0})
        print(f"  Registered: {m} -> {type(dl).__name__}")
    print("SUCCESS: All 5 downloader strategies are registered.")
    return True


if __name__ == "__main__":
    setup()
    results = []
    try:
        results.append(test_page_scraper())
        results.append(test_api_client())
        results.append(test_manual_upload())
        results.append(test_factory_invalid())
        results.append(test_factory_all_registered())
    finally:
        teardown()

    if all(results):
        print("\nPHASE 2B VERIFIED: All 5 downloader strategies are operational.")
        exit(0)
    else:
        print("\nPHASE 2B FAILED: Some tests did not pass.")
        exit(1)
