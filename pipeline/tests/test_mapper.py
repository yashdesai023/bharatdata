import pytest
from pipeline.core.mapper import ColumnMapper

EXTRACTION_CONFIG = {
    "format": "json",
    "column_mapping": {
        "TOT_P|Total.*Person":    {"field": "total_population", "type": "int"},
        "District.*Code":          {"field": "district_code",    "type": "str"},
        "Area.*Name|Name":         {"field": "entity_name",      "type": "str"},
    },
    "row_filters": {
        "exclude_patterns": ["TOTAL", "State - "]
    }
}

@pytest.fixture
def mapper():
    return ColumnMapper(EXTRACTION_CONFIG)

def test_mapping_exact_and_regex(mapper):
    """Test standard and regex-based column mapping."""
    raw = [
        {"TOT_P": "1500", "District Code": "05", "Name": "Patna"},
        {"Total Person": "2000", "Dist Code": "06", "Area Name": "Gaya"} # 'Dist Code' won't match our regex
    ]
    clean, skipped = mapper.transform_batch(raw)
    
    # First record
    assert clean[0]["total_population"] == 1500
    assert clean[0]["district_code"] == "05"
    assert clean[0]["entity_name"] == "Patna"
    
    # Second record
    assert clean[1]["total_population"] == 2000
    assert "district_code" not in clean[1] # Didn't match regex
    assert clean[1]["entity_name"] == "Gaya"

def test_type_coercion_indian_format(mapper):
    """Test handling of commas in numbers and string stripping."""
    raw = [{"TOT_P": "1,23,456", "Name": "  Mumbai  "}]
    clean, _ = mapper.transform_batch(raw)
    assert clean[0]["total_population"] == 123456
    assert clean[0]["entity_name"] == "Mumbai"

def test_null_coercion(mapper):
    """Test handling of common government data null indicators."""
    raw = [
        {"TOT_P": "NA", "Name": "Test1"},
        {"TOT_P": "-", "Name": "Test2"},
        {"TOT_P": "null", "Name": "Test3"}
    ]
    clean, _ = mapper.transform_batch(raw)
    assert clean[0]["total_population"] is None
    assert clean[1]["total_population"] is None
    assert clean[2]["total_population"] is None

def test_row_exclusion(mapper):
    """Test skipping rows that match exclusion patterns."""
    raw = [
        {"Name": "Bihar", "TOT_P": "100"},
        {"Name": "TOTAL", "TOT_P": "999"},
        {"Name": "State - 09", "TOT_P": "888"}
    ]
    clean, skipped = mapper.transform_batch(raw)
    assert len(clean) == 1
    assert skipped == 2
    assert clean[0]["entity_name"] == "Bihar"

def test_required_columns_validation(mapper):
    """Test the validation of mandatory fields."""
    record = {"entity_name": "Delhi", "total_population": None}
    assert mapper.validate_required_columns(record, ["entity_name"]) is True
    assert mapper.validate_required_columns(record, ["total_population"]) is False
