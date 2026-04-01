import os
import requests
from pipeline.engine.downloaders.base import BaseDownloader

class DirectDownloader(BaseDownloader):
    def download(self, url=None, dest_folder=None):
        """Downloads a file from a direct URL."""
        target_url = url or self.config.get('url_pattern') or self.config.get('url')
        output_dir = dest_folder or "data/raw"
        
        if not target_url:
            raise ValueError("DirectDownloader requires a URL.")
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        self._wait_for_rate_limit()
        
        response = requests.get(target_url, stream=True)
        response.raise_for_status()
        
        filename = os.path.basename(target_url)
        if not filename or '.' not in filename:
            filename = "downloaded_file"
            
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return file_path
