import requests
import pandas as pd
from typing import List, Dict, Any, Optional, Union

class BharatData:
    def __init__(self, base_url: str = "https://api.bharatdata.org"):
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None, return_full: bool = False) -> Any:
        url = f"{self.base_url}{path}"
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = response.text
            raise Exception(f"API Error: {error_msg} (Status: {response.status_code})")
        
        res_json = response.json()
        if return_full:
            return res_json
        return res_json.get("data")

    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets in the BharatData Registry."""
        return self._request("/v1/registry")

    def get_dataset_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """Get full metadata for a specific dataset."""
        return self._request(f"/v1/registry/{dataset_id}")

    def query(self, dataset_id: str, level: str, **params) -> Dict[str, Any]:
        """
        Universal Query: Fetch data from any registered dataset.
        
        Args:
            dataset_id: The ID of the dataset (e.g., 'ncrb-crime')
            level: The granularity level (e.g., 'summary', 'state', 'district')
            **params: Query parameters (e.g., entity='Delhi', year=2023)
        """
        return self._request(f"/v1/data/{dataset_id}/{level}", params=params, return_full=True)

    def get_crime_summary(self, state: str, year: int, category: str) -> List[Dict[str, Any]]:
        """Backward compatibility for existing crime reports."""
        params = {"entity": state, "year": year, "category": category}
        res = self.query("ncrb-crime", "summary", **params)
        return res.get("data", [])

    def to_dataframe(self, response: Union[List[Dict[str, Any]], Dict[str, Any]]) -> pd.DataFrame:
        """
        Converts API response to a pandas DataFrame.
        Handles both the raw data list and the full response envelope.
        """
        if isinstance(response, dict):
            data = response.get("data", [])
        else:
            data = response
            
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # If it was a full response, attach metadata as an attribute
        if isinstance(response, dict) and "metadata" in response:
            df.attrs["metadata"] = response["metadata"]
            
        return df

    def get_states(self) -> List[str]: return self._request("/v1/meta/states")
    def get_categories(self) -> List[str]: return self._request("/v1/meta/categories")
    def get_years(self) -> List[int]: return self._request("/v1/meta/years")

    def cite(self, record_or_df: Union[Dict[str, Any], pd.DataFrame]) -> str:
        """Generate a standard citation for a data record or DataFrame."""
        if isinstance(record_or_df, pd.DataFrame):
            meta = record_or_df.attrs.get("metadata", {})
            source = meta.get("attribution", "BharatData / Government of India")
            dataset = meta.get("dataset", "Unknown Dataset")
            return f"Source: {source} (via BharatData: {dataset}). Accessed: {meta.get('timestamp', 'Recent')}"
        
        source = record_or_df.get("source_file", "Official Report")
        date = record_or_df.get("collection_date", "Unspecified")
        return f"Source: BharatData / Government Source ({source}). Accessed: {date}"
