import os
import logging
from playwright.sync_api import sync_playwright
from pipeline.engine.downloaders.base import BaseDownloader

class BrowserRenderer(BaseDownloader):
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger("BrowserRenderer")

    def download(self, url=None, dest_folder=None):
        """Renders a page, finds matching links, and downloads them."""
        target_url = url or self.config.get('url')
        output_dir = dest_folder or self.config.get('output_dir', "data/raw")
        link_selector = self.config.get('link_selector', "a")
        filters = self.config.get('filters', {})
        
        if not target_url:
            raise ValueError("BrowserRenderer requires a URL.")
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        downloaded_files = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(target_url, wait_until="networkidle")
            
            # Find all matching links
            elements = page.query_selector_all(link_selector)
            self.logger.info(f"Found {len(elements)} potential links with selector: {link_selector}")
            
            for element in elements:
                href = element.get_attribute("href")
                if not href:
                    continue
                    
                # Resolve relative URLs
                full_url = href if href.startswith("http") else f"{target_url.rstrip('/')}/{href.lstrip('/')}"
                filename = os.path.basename(href).split('?')[0] # Remove query params
                
                # Apply Filters (Include/Exclude)
                include_list = filters.get('include', [])
                exclude_list = filters.get('exclude', [])
                filter_mode = filters.get('mode', 'all')
                
                if include_list:
                    if filter_mode == 'any':
                        if not any(inc.lower() in filename.lower() for inc in include_list):
                            continue
                    else: # Default to 'all'
                        if not all(inc.lower() in filename.lower() for inc in include_list):
                            continue
                            
                if any(exc.lower() in filename.lower() for exc in exclude_list):
                    continue
                
                # Download File
                file_path = os.path.join(output_dir, filename)
                self.logger.info(f"Downloading: {filename}...")
                
                self._wait_for_rate_limit()
                
                try:
                    response = page.request.get(full_url)
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            f.write(response.body())
                        downloaded_files.append(file_path)
                    else:
                        self.logger.warning(f"Failed to download {full_url}: Status {response.status}")
                except Exception as e:
                    self.logger.error(f"Error downloading {full_url}: {e}")
                    
            browser.close()
            
        if not downloaded_files:
            self.logger.warning(f"No files were downloaded from {target_url} matching the criteria.")
            
        return downloaded_files
