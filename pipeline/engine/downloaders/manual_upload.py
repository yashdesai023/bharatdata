import os
import glob
from pipeline.engine.downloaders.base import BaseDownloader

class ManualUpload(BaseDownloader):
    def download(self, url=None, dest_folder=None):
        """Scans local path pattern for matching files."""
        # Check both naming conventions for compatibility
        path_pattern = self.config.get('search_pattern') or self.config.get('local_path_pattern')
        
        if not path_pattern:
            raise ValueError("ManualUpload requires 'search_pattern' or 'local_path_pattern'.")
            
        matched = glob.glob(path_pattern, recursive=True)
        if not matched:
            raise FileNotFoundError(f"No files matched pattern '{path_pattern}'.")
            
        # Return ALL matches so Orchestrator can loop over them (e.g. multi-year files)
        return matched
