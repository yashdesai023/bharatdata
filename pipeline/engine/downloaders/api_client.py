import os
import requests
import json
from pipeline.engine.downloaders.base import BaseDownloader

class ApiClient(BaseDownloader):
    def download(self, url=None, dest_folder=None):
        """Fetches data from an API."""
        target_url = url or self.config.get('url_pattern') or self.config.get('url')
        output_dir = dest_folder or "data/raw"
        
        if not target_url:
            raise ValueError("ApiClient requires a URL.")
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        self._wait_for_rate_limit()
        
        # Simple API call
        response = requests.get(target_url, params=self.config.get('parameters', {}))
        response.raise_for_status()
        
        filename = "api_response.json"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f)
            
        return file_path
