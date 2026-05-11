import pytest
from unittest.mock import patch, MagicMock
from pipeline.core.loader import SupabaseLoader, LoadResult, SupabaseLoadError

@pytest.fixture
def loader():
    return SupabaseLoader(
        table="test_table",
        unique_key=["id"],
        supabase_url="https://xyz.supabase.co",
        supabase_key="secret-key",
        batch_size=2
    )

def test_load_result_metrics():
    """Test the metrics calculation in LoadResult."""
    res = LoadResult(total_submitted=10, total_inserted=8, total_failed=2)
    assert res.success_rate == 80.0
    assert "Processed: 8" in str(res)

@patch("requests.Session.post")
def test_load_batch_success(mock_post, loader):
    """Test successful load of multiple batches."""
    # Mock a successful response returning the representations of processed rows
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = [{"id": 1}, {"id": 2}]
    mock_post.return_value = mock_resp

    records = [{"id": 1}, {"id": 2}, {"id": 3}] # Should split into 2 batches (size=2)
    result = loader.load_batch(records)

    assert result.total_submitted == 3
    assert result.total_inserted == 4 # 2 from first batch + 2 from second (mocked)
    assert result.total_failed == 0
    assert mock_post.call_count == 2

@patch("requests.Session.post")
def test_load_batch_retry_on_server_error(mock_post, loader):
    """Test that the loader retries on 500 errors."""
    fail_resp = MagicMock(status_code=500)
    success_resp = MagicMock(status_code=201, json=lambda: [{"id": 1}])
    
    mock_post.side_effect = [fail_resp, success_resp]
    
    # Increase delay speed for tests
    loader.RETRY_DELAY = 0.01

    result = loader.load_batch([{"id": 1}])
    assert result.total_inserted == 1
    assert mock_post.call_count == 2

@patch("requests.Session.post")
def test_load_batch_fail_on_409(mock_post, loader):
    """Test that it fails on 409 Conflict (invalid constraint)."""
    mock_resp = MagicMock(status_code=409, text="Constraint error")
    mock_post.return_value = mock_resp

    result = loader.load_batch([{"id": 1}])
    assert result.total_failed == 1
    assert "Unique constraint conflict" in result.errors[0]

@patch("requests.Session.get")
def test_count_rows(mock_get, loader):
    """Test row count retrieval logic."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Range": "0-0/1234"}
    mock_get.return_value = mock_resp

    count = loader.count_rows()
    assert count == 1234
    
    # Check that it sent the correct headers
    args, kwargs = mock_get.call_args
    assert kwargs["headers"]["Prefer"] == "count=exact"
