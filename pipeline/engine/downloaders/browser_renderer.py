import os
import time
from playwright.sync_api import sync_playwright
from pipeline.engine.downloaders.base import BaseDownloader

class BrowserRenderer(BaseDownloader):
    def download(self, url=None, dest_folder=None):
        """Renders a page and downloads its content/snapshot."""
        target_url = url or self.config.get('url_pattern') or self.config.get('url')
        output_dir = dest_folder or "data/raw"
        
        if not target_url:
            raise ValueError("BrowserRenderer requires a URL.")
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        self._wait_for_rate_limit()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, wait_until="networkidle")
            
            # Simple implementation: save full page HTML
            filename = "rendered_page.html"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(page.content())
                
            browser.close()
            return file_path
