import os
import logging
from playwright.sync_api import sync_playwright
from pipeline.engine.downloaders.base import BaseDownloader


class BrowserRenderer(BaseDownloader):
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger("BrowserRenderer")

    def _sanitize_filename(self, filename):
        """Remove problematic characters from filename."""
        # Remove query params
        filename = filename.split('?')[0]
        # Remove path separators and problematic chars
        filename = os.path.basename(filename)
        # Keep only safe characters (ASCII + allowed special chars)
        safe = ''.join(c if ord(c) > 31 and c not in '<>:"/\\|?*' else '_' for c in filename)
        return safe if safe else 'download'

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
            page.goto(target_url, wait_until="domcontentloaded", timeout=45000)

            # Wait for dynamic content
            page.wait_for_timeout(2000)

            # Find all matching links
            elements = page.query_selector_all(link_selector)
            self.logger.info(f"Found {len(elements)} potential links with selector: {link_selector}")

            for element in elements:
                href = element.get_attribute("href")
                if not href:
                    continue

                # Resolve relative URLs - FIX: properly join relative URLs
                if href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    # Handle absolute paths on same domain
                    base = target_url.rstrip('/')
                    full_url = base + href
                else:
                    # Handle relative paths
                    base = target_url.rstrip('/')
                    full_url = base + "/" + href.lstrip('/')

                # FIX: Sanitize filename
                raw_filename = href.split('?')[0]
                filename = self._sanitize_filename(raw_filename)

                # Skip empty filenames or just paths
                if not filename or filename in ['', '/', '.']:
                    continue

                # Apply Filters (Include/Exclude)
                include_list = filters.get('include', [])
                exclude_list = filters.get('exclude', [])
                filter_mode = filters.get('mode', 'all')

                if include_list:
                    if filter_mode == 'any':
                        if not any(inc.lower() in filename.lower() for inc in include_list):
                            continue
                    else:  # Default to 'all'
                        if not all(inc.lower() in filename.lower() for inc in include_list):
                            continue

                if exclude_list and any(exc.lower() in filename.lower() for exc in exclude_list):
                    continue

                # Download File
                file_path = os.path.join(output_dir, filename)
                self.logger.info(f"Downloading: {filename}...")

                self._wait_for_rate_limit()

                try:
                    response = page.request.get(full_url)
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        content_length = len(response.body())

                        # Skip HTML pages (usually not actual downloads)
                        if 'text/html' in content_type and content_length > 10000:
                            self.logger.info(f"Skipping HTML page: {filename} ({content_length} bytes)")
                            continue

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
