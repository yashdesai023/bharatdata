import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import ChunkedEncodingError, HTTPError
from urllib3.exceptions import IncompleteRead, ProtocolError
from pipeline.adapters.ogd_api import OGDApiAdapter, OGDApiError

MOCK_RESPONSE = {
    "status": "ok",
    "total": 2500,
    "count": 1000,
    "limit": "1000",
    "offset": "0",
    "fields": [{"id": "TOT_P", "type": "integer"}],
    "records": [{"TOT_P": 100}] * 1000
}

@pytest.fixture
def adapter():
    # Provide a dummy key to bypass initialization validation
    return OGDApiAdapter(api_key="test-key", batch_size=1000, retry_delay=0)


def make_success_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "{}"
    resp.json.return_value = MOCK_RESPONSE
    resp.raise_for_status = MagicMock()
    return resp

def test_adapter_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("DATA_GOV_IN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        OGDApiAdapter(api_key=None)

@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_fetch_all_paginates(mock_get, adapter):
    """Should make 3 API calls to fetch 2500 records in batches of 1000."""
    def side_effect(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        # On third call, return only 500 records
        offset = int(url.split("offset=")[1])
        data = MOCK_RESPONSE.copy()
        data["offset"] = str(offset)
        if offset == 2000:
            data["records"] = [{"TOT_P": 100}] * 500
            data["count"] = 500
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    mock_get.side_effect = side_effect
    batches = list(adapter.fetch_all("fake-resource-id"))
    
    # We expect 3 batches (1000, 1000, 500)
    assert len(batches) == 3
    assert mock_get.call_count == 3
    assert batches[0].total_count == 2500
    assert len(batches[2].data) == 500

@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_probe_returns_false_on_error(mock_get, adapter):
    mock_get.side_effect = Exception("Connection refused")
    assert adapter.probe("bad-resource-id") == False

@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_retry_logic_success(mock_get, adapter):
    """Should succeed after 1 retryable failure (500)."""
    # Create a real HTTPError with a 500 response
    fail_resp = MagicMock()
    fail_resp.status_code = 500
    
    from requests.exceptions import HTTPError
    error = HTTPError(response=fail_resp)
    
    mock_get.side_effect = [error, MagicMock(status_code=200, json=lambda: MOCK_RESPONSE, raise_for_status=lambda: None)]
    
    # This should succeed on the second attempt
    count = adapter.fetch_total_count("resource-id")
    assert count == 2500
    assert mock_get.call_count == 2


@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_retries_on_chunked_encoding_error(mock_get, adapter):
    """Should retry on mid-stream truncation and then succeed."""
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.text = "{}"
    ok_resp.json.return_value = MOCK_RESPONSE
    ok_resp.raise_for_status = MagicMock()
    mock_get.side_effect = [ChunkedEncodingError("truncated body"), ok_resp]

    count = adapter.fetch_total_count("resource-id")

    assert count == 2500
    assert mock_get.call_count == 2
    for call in mock_get.call_args_list:
        assert call.kwargs.get("stream") is False


@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_retries_on_incomplete_read(mock_get, adapter):
    """Should retry when urllib3 reports incomplete read."""
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.text = "{}"
    ok_resp.json.return_value = MOCK_RESPONSE
    ok_resp.raise_for_status = MagicMock()
    mock_get.side_effect = [IncompleteRead(1, 2), ok_resp]

    count = adapter.fetch_total_count("resource-id")

    assert count == 2500
    assert mock_get.call_count == 2
    for call in mock_get.call_args_list:
        assert call.kwargs.get("stream") is False


@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_retries_on_protocol_error(mock_get, adapter):
    """Should retry when connection drops during read."""
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.text = "{}"
    ok_resp.json.return_value = MOCK_RESPONSE
    ok_resp.raise_for_status = MagicMock()
    mock_get.side_effect = [ProtocolError("Connection broken", OSError("boom")), ok_resp]

    count = adapter.fetch_total_count("resource-id")

    assert count == 2500
    assert mock_get.call_count == 2
    for call in mock_get.call_args_list:
        assert call.kwargs.get("stream") is False


@patch("pipeline.adapters.ogd_api.requests.Session.get")
def test_http_404_fails_fast_without_retry(mock_get, adapter):
    """Should not retry on non-retryable 4xx errors."""
    fail_resp = MagicMock()
    fail_resp.status_code = 404
    error = HTTPError(response=fail_resp)
    mock_get.side_effect = [error]

    with pytest.raises(OGDApiError):
        adapter.fetch_total_count("resource-id")

    assert mock_get.call_count == 1


class TestMidStreamRetry:
    @patch("requests.Session.get")
    def test_retries_on_chunked_encoding_error_then_succeeds(self, mock_get, adapter):
        success_response = make_success_response()
        mock_get.side_effect = [
            ChunkedEncodingError("truncated body"),
            ChunkedEncodingError("truncated body again"),
            success_response,
        ]

        raw, data = adapter._request_with_retry("https://api.data.gov.in/resource/resource-id?api-key=test-key&format=json&limit=1&offset=0")

        assert data["status"] == "ok"
        assert mock_get.call_count == 3

    @patch("pipeline.adapters.ogd_api.requests.Session.get")
    def test_retries_on_incomplete_read(self, mock_get, adapter):
        success_response = make_success_response()
        mock_get.side_effect = [
            IncompleteRead(partial=b"x", expected=5000),
            success_response,
        ]

        raw, data = adapter._request_with_retry("https://api.data.gov.in/resource/resource-id?api-key=test-key&format=json&limit=1&offset=0")

        assert data["status"] == "ok"
        assert mock_get.call_count == 2

    @patch("pipeline.adapters.ogd_api.requests.Session.get")
    def test_raises_ogdapierror_after_max_retries_exhausted(self, mock_get, adapter):
        mock_get.side_effect = ChunkedEncodingError("always fails")

        with pytest.raises(OGDApiError, match="All 3 attempts failed"):
            adapter._request_with_retry("https://api.data.gov.in/resource/resource-id?api-key=test-key&format=json&limit=1&offset=0")

        assert mock_get.call_count == 3

    @patch("pipeline.adapters.ogd_api.requests.Session.get")
    def test_does_not_retry_403_forbidden(self, mock_get, adapter):
        fail_resp = MagicMock()
        fail_resp.status_code = 403
        fail_resp.raise_for_status.side_effect = HTTPError(response=fail_resp)
        mock_get.return_value = fail_resp

        with pytest.raises(OGDApiError):
            adapter._request_with_retry("https://api.data.gov.in/resource/resource-id?api-key=test-key&format=json&limit=1&offset=0")

        assert mock_get.call_count == 1
