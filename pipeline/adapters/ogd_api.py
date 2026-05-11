"""
OGD API Adapter
---------------
Handles all communication with the Data.gov.in REST API.
Provides paginated record fetching with retry logic and error classification.
"""

import os
import time
from typing import Generator, List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import requests
from requests.exceptions import ChunkedEncodingError
from urllib3.exceptions import IncompleteRead, ProtocolError
from loguru import logger

@dataclass
class OGDRecord:
    """A single record + metadata from the OGD API."""
    resource_id: str
    data: List[Dict[str, Any]]
    total_count: int
    fields: List[Dict[str, str]]
    raw_payload: str = ""


class OGDApiError(Exception):
    """Raised when the OGD API returns an unexpected or error response."""
    pass


class OGDRateLimitError(OGDApiError):
    """Raised specifically for HTTP 429 rate limit responses."""
    pass


class OGDApiAdapter:
    """
    A resilient, paginating adapter for the Data.gov.in REST API.

    Usage:
        adapter = OGDApiAdapter(api_key="your_key")
        for batch in adapter.fetch_all("resource-uuid"):
            # batch.data is a list of dicts
            process(batch.data)
    """

    BASE_URL = "https://api.data.gov.in/resource"
    DEFAULT_LIMIT = 1000
    DEFAULT_TIMEOUT = 60   # seconds per request
    RATE_LIMIT_BACKOFF = 60  # seconds to wait on 429

    def __init__(
        self,
        api_key: Optional[str] = None,
        batch_size: int = DEFAULT_LIMIT,
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Args:
            api_key: OGD API key. Falls back to DATA_GOV_IN_API_KEY env var.
            batch_size: Records per API request (max 1000).
            max_retries: Number of retry attempts on failure.
            retry_delay: Seconds between retries (doubles each attempt).
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("DATA_GOV_IN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OGD API key is required. Set DATA_GOV_IN_API_KEY in your .env file."
            )
        self.batch_size = min(batch_size, self.DEFAULT_LIMIT)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BharatData-BDIF/1.0 (https://bharatdata.in)"
        })

    def _build_url(self, resource_id: str, offset: int) -> str:
        """Construct the full paginated API URL."""
        return (
            f"{self.BASE_URL}/{resource_id}"
            f"?api-key={self.api_key}"
            f"&format=json"
            f"&limit={self.batch_size}"
            f"&offset={offset}"
        )

    def _request_with_retry(self, url: str, params: dict = None) -> Tuple[str, Dict[str, Any]]:
        """
        Make an HTTP GET request with exponential backoff retry.
        
        Returns:
            Tuple of (Raw JSON string, Parsed JSON dict).
        
        Raises:
            OGDApiError: When all retries are exhausted.
            OGDRateLimitError: When rate-limited (HTTP 429).
        """
        delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                log_url = url.replace(self.api_key, "HIDDEN_KEY") if self.api_key else url
                logger.debug(f"GET {log_url} (Attempt {attempt}/{self.max_retries})")

                resp = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    stream=False,
                )

                if resp.status_code == 429:
                    logger.warning(f"Rate limited (429). Waiting {self.RATE_LIMIT_BACKOFF}s...")
                    time.sleep(self.RATE_LIMIT_BACKOFF)
                    continue

                resp.raise_for_status()
                data = resp.json()
                if data.get("status") != "ok":
                    raise OGDApiError(
                        f"API returned non-ok status: {data.get('status')} | {data}"
                    )
                return resp.text, data

            except ChunkedEncodingError as e:
                logger.warning(
                    f"Retryable ChunkedEncodingError (Attempt {attempt}/{self.max_retries}): {e}"
                )
            except IncompleteRead as e:
                logger.warning(
                    f"Retryable IncompleteRead (Attempt {attempt}/{self.max_retries})"
                )
            except ProtocolError as e:
                logger.warning(
                    f"Retryable ProtocolError (Attempt {attempt}/{self.max_retries}): {e}"
                )
            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Retryable ConnectionError (Attempt {attempt}/{self.max_retries}): {e}"
                )
            except requests.exceptions.Timeout as e:
                logger.warning(
                    f"Retryable Timeout (Attempt {attempt}/{self.max_retries}): {e}"
                )
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                if status_code is not None and 400 <= status_code < 500:
                    logger.error(f"Non-retryable HTTP {status_code}: {e}")
                    raise OGDApiError(f"Non-retryable HTTP {status_code}: {e}")
                if status_code is not None and 500 <= status_code < 600:
                    logger.warning(
                        f"Retryable server error {status_code} (Attempt {attempt}/{self.max_retries})"
                    )
                else:
                    logger.error(f"HTTP error without retryable status: {e}")
                    raise OGDApiError(str(e))
            except OGDApiError:
                raise
            except Exception as e:
                logger.error(f"Unexpected non-retryable error: {e}")
                raise OGDApiError(str(e))

            if attempt < self.max_retries:
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 120)

        raise OGDApiError(f"All {self.max_retries} attempts failed: {url}")

    def fetch_total_count(self, resource_id: str) -> int:
        """
        Fetch the total record count for a resource without loading all records.
        Useful for pre-flight checks and progress reporting.
        """
        url = self._build_url(resource_id, offset=0)
        # Fetch just 1 record to get the total count efficiently
        url_single = url.replace(f"limit={self.batch_size}", "limit=1")
        raw_text, data = self._request_with_retry(url_single)
        
        # OGD API can return total in various keys depending on the endpoint/version
        total = data.get("total") or data.get("count") or data.get("totalRecords") or 0
        return int(total)

    def fetch_fields(self, resource_id: str) -> List[Dict[str, str]]:
        """
        Fetch the field definitions (schema) of a resource.
        Returns a list of {"id": column_name, "type": data_type} dicts.
        """
        url = self._build_url(resource_id, offset=0)
        url_single = url.replace(f"limit={self.batch_size}", "limit=1")
        raw_text, data = self._request_with_retry(url_single)
        return data.get("fields", [])

    def list_resources_by_catalog(self, catalog_uuid: str, limit: int = 100) -> List[str]:
        """
        Given a catalog UUID, list resources belonging to that catalog using the
        OGD catalog endpoint. Returns a list of resource index_name values
        (the resource identifiers suitable for OGDApiAdapter.fetch_all).

        Important notes:
        - Use the /catalog/{catalog_uuid} path (not a resource filter query).
        - Build the URL as a raw f-string so the API receives literal brackets
          (requests encoding of params like filters[...] can break the endpoint).
        - This method does NOT pass a params dict; it constructs the query string
          inline to avoid percent-encoding issues.
        """
        catalog_base = "https://api.data.gov.in/catalog"
        url = (
            f"{catalog_base}/{catalog_uuid}"
            f"?api-key={self.api_key}"
            f"&format=json"
            f"&limit={limit}"
        )

        raw_text, data = self._request_with_retry(url)
        records = data.get("records", []) if isinstance(data, dict) else []

        return [r["index_name"] for r in records if r.get("index_name")]

    def fetch_all(
        self,
        resource_id: str,
        progress_callback=None
    ) -> Generator[OGDRecord, None, None]:
        """
        Generator that lazily fetches all records for a resource in batches.
        
        Args:
            resource_id: The OGD resource UUID.
            progress_callback: Optional callable(fetched_count, total_count) for UI updates.
        
        Yields:
            OGDRecord objects with .data (list of dicts) and .total_count.
        """
        offset = 0
        total = None
        fetched = 0
        fields = []

        while True:
            url = self._build_url(resource_id, offset=offset)
            raw_text, raw = self._request_with_retry(url)

            # Capture total on first page
            if total is None:
                # Robust total count detection
                total = raw.get("total") or raw.get("count") or raw.get("totalRecords")
                if total is not None:
                    total = int(total)
                else:
                    logger.warning(f"Resource [{resource_id}]: Total count not found in response. Will paginate until empty.")
                    total = float('inf')
                
                fields = raw.get("fields", [])
                logger.info(
                    f"Resource [{resource_id}]: {total} total records | {len(fields)} columns"
                )

            records = raw.get("records", [])
            if not records:
                logger.debug(f"No more records returned at offset {offset}.")
                break

            fetched += len(records)
            if progress_callback:
                progress_callback(fetched, total)

            yield OGDRecord(
                resource_id=resource_id,
                data=records,
                total_count=total,
                fields=fields,
                raw_payload=raw_text,
            )

            # Check if we've fetched all records or reached the end
            if total != float('inf') and fetched >= total:
                break
            
            if len(records) < self.batch_size:
                # OGD sometimes returns fewer records than requested on the last page
                logger.debug("Fetched fewer records than batch_size, assuming last page.")
                break

            offset += len(records) # Better to use actual length than self.batch_size
            time.sleep(0.3)  # Polite delay between pages

    def probe(self, resource_id: str) -> bool:
        """
        Quick check: Does this resource ID return valid data?
        Returns True if the resource is accessible, False otherwise.
        """
        try:
            count = self.fetch_total_count(resource_id)
            logger.info(f"Probe OK: {resource_id} has {count} records.")
            return True
        except (OGDApiError, Exception) as e:
            logger.warning(f"Probe FAILED for {resource_id}: {e}")
            return False

    def search_datasets(self, title: str, organization: str = None) -> List[Dict[str, Any]]:
        """
        Search for datasets by title or organization.
        """
        search_url = (
            f"https://api.data.gov.in/dataset.json"
            f"?api-key={self.api_key}"
            f"&format=json&limit=50"
        )
        if title:
            # Wrap in wildcards for robustness
            wildcard_title = f"%{title}%" if "%" not in title else title
            search_url += f"&filters[title]={requests.utils.quote(wildcard_title)}"
            
        if organization:
            search_url += f"&filters[organization]={requests.utils.quote(organization)}"
        
        try:
            raw_text, data = self._request_with_retry(search_url)
            return data.get("records", [])
        except Exception as e:
            logger.error(f"Dataset search failed: {e}")
            return []

    def search_resources(self, title: str, organization: str = None) -> List[Dict[str, Any]]:
        """
        Search for specific resource IDs.
        """
        search_url = (
            f"https://api.data.gov.in/resource.json"
            f"?api-key={self.api_key}"
            f"&format=json&limit=50"
        )
        if title:
            # Wrap in wildcards for robustness
            wildcard_title = f"%{title}%" if "%" not in title else title
            search_url += f"&filters[title]={requests.utils.quote(wildcard_title)}"
            
        if organization:
            search_url += f"&filters[organization]={requests.utils.quote(organization)}"
        
        try:
            raw_text, data = self._request_with_retry(search_url)
            return data.get("records", [])
        except Exception as e:
            logger.error(f"Resource search failed: {e}")
            return []

    def fetch_resource_by_id(self, resource_id: str) -> Dict[str, Any]:
        """
        Fetches metadata for a specific resource ID directly via the path.
        This is the most reliable way to verify a canonical ID.
        """
        url = f"https://api.data.gov.in/resource/{resource_id}"
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 1
        }
        
        try:
            raw_text, data = self._request_with_retry(url, params=params)
            return data
        except Exception as e:
            logger.error(f"Direct resource fetch failed for {resource_id}: {e}")
            return {}
