import os
import json
import csv
from pipeline.engine.extractors.extractor_factory import ExtractorFactory

def test_csv():
    print("\n--- Testing CSVExtractor ---")
    path = "test_data.csv"
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "State", "Cases"])
        writer.writerow([1, "Kerala", 100])
        writer.writerow([2, "Bihar", 200])
        
    config = {
        'column_mapping': {
            'State': {'field': 'state'},
            'Cases': {'field': 'count'}
        }
    }
    extractor = ExtractorFactory.get_extractor('csv', config)
    results = extractor.extract(path)
    os.remove(path)
    
    assert len(results) == 2
    assert results[0]['state'] == "Kerala"
    print(f"SUCCESS: CSV extraction worked. Record 1: {results[0]}")
    return True

def test_html():
    print("\n--- Testing HTMLExtractor ---")
    path = "test_data.html"
    html_content = """
    <html><body><table>
    <tr><th>State</th><th>Total</th></tr>
    <tr><td>Punjab</td><td>50</td></tr>
    <tr><td>Goa</td><td>10</td></tr>
    </table></body></html>
    """
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    config = {
        'column_mapping': {
            'State': {'field': 'state'},
            'Total': {'field': 'count'}
        }
    }
    extractor = ExtractorFactory.get_extractor('html', config)
    results = extractor.extract(path)
    os.remove(path)
    
    assert len(results) == 2
    assert results[1]['state'] == "Goa"
    print(f"SUCCESS: HTML extraction worked. Record 2: {results[1]}")
    return True

def test_json():
    print("\n--- Testing JSONExtractor ---")
    path = "test_data.json"
    data = {
        "status": "success",
        "data": {
            "records": [
                {"raw_state": "Sikkim", "val": 5},
                {"raw_state": "Assam", "val": 15}
            ]
        }
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
        
    config = {
        'records_path': 'data.records',
        'column_mapping': {
            'raw_state': {'field': 'state'},
            'val': {'field': 'count'}
        }
    }
    extractor = ExtractorFactory.get_extractor('json', config)
    results = extractor.extract(path)
    os.remove(path)
    
    assert len(results) == 2
    assert results[0]['state'] == "Sikkim"
    print(f"SUCCESS: JSON extraction worked. Record 1: {results[0]}")
    return True

if __name__ == "__main__":
    print("Starting Phase 3B Verification...")
    try:
        test_csv()
        test_html()
        test_json()
        print("\nPHASE 3B VERIFIED: All extraction strategies are operational.")
    except Exception as e:
        print(f"ERROR: Phase 3B verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
