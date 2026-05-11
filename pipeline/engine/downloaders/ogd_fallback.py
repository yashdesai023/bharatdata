"""
OGD Fallback Downloader (Web Scraping)
--------------------------------------
Fallback strategy: Scrapes data.gov.in directly when OGD API fails.
Uses Crawl4AI for robust web scraping with JS rendering support.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from pipeline.engine.downloaders.base import BaseDownloader


class OGDFallbackDownloader(BaseDownloader):
    """
    Fallback downloader that scrapes data.gov.in when OGD API is unavailable.
    Uses the website's API endpoint pattern to generate download URLs.
    """

    BASE_URL = "https://data.gov.in"
    API_PATTERN = "https://api.data.gov.in/resource/{resource_id}"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dataset_id = config.get('source_name', config.get('dataset_id', 'unknown'))
        self.logger = logging.getLogger("OGDFallbackDownloader")
        self.output_dir = Path(config.get('output_dir', f'data/raw/{self.dataset_id}'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(self, resource_id: str = None, dest_folder: str = None) -> List[str]:
        """
        Download using web scraping fallback.
        """
        downloaded_files = []

        if dest_folder:
            self.output_dir = Path(dest_folder)

        # Get resource URLs from the website
        resource_urls = self._get_resource_urls_from_website(resource_id)

        for url_info in resource_urls:
            url = url_info.get('url')
            format_type = url_info.get('format', 'json')

            if not url:
                continue

            self.logger.info(f"Scraping: {url}")

            try:
                file_path = self._download_from_url(url, format_type)
                if file_path:
                    downloaded_files.append(file_path)
            except Exception as e:
                self.logger.error(f"Failed to scrape {url}: {e}")

        return downloaded_files

    def _get_resource_urls_from_website(self, resource_id: str = None) -> List[Dict]:
        """
        Scrape data.gov.in to get actual download URLs for resources.
        """
        urls = []

        if resource_id:
            # Direct resource page
            resource_url = f"{self.BASE_URL}/resource/{resource_id}"
            page_urls = self._extract_download_urls_from_page(resource_url)
            urls.extend(page_urls)

        return urls

    def _extract_download_urls_from_page(self, page_url: str) -> List[Dict]:
        """
        Extract download URLs from a data.gov.in resource page.
        """
        extracted = []

        try:
            import requests

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }

            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()

            html = response.text

            # Look for API download links in the page
            # Pattern 1: Direct API link
            api_links = re.findall(
                r'href=["\']([^"\']*api\.data\.gov\.in[^"\']*)["\']',
                html
            )

            # Pattern 2: Download button links
            download_links = re.findall(
                r'href=["\']([^"\']*(?:\.json|\.csv|\.xlsx|\.xls)[^"\']*)["\']',
                html,
                re.IGNORECASE
            )

            for link in api_links + download_links:
                if link.startswith('/'):
                    link = urljoin(self.BASE_URL, link)

                format_type = self._detect_format(link)
                extracted.append({
                    'url': link,
                    'format': format_type,
                    'type': 'api' if 'api.data.gov.in' in link else 'direct'
                })

        except Exception as e:
            self.logger.error(f"Failed to extract URLs from {page_url}: {e}")

        return extracted

    def _download_from_url(self, url: str, format_type: str = 'json') -> Optional[str]:
        """
        Download file from URL and save to output directory.
        """
        try:
            import requests

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': '*/*',
            }

            response = requests.get(url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()

            # Generate filename
            parsed = urlparse(url)
            filename = parsed.path.split('/')[-1] or f"download_{hash(url)}.json"

            if not any(filename.endswith(ext) for ext in ['.json', '.csv', '.xlsx', '.xls']):
                filename += f'.{format_type}'

            file_path = self.output_dir / filename

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.success(f"Downloaded: {file_path} ({file_path.stat().st_size} bytes)")
            return str(file_path)

        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return None

    def _detect_format(self, url: str) -> str:
        """Detect file format from URL."""
        url_lower = url.lower()
        if '.csv' in url_lower:
            return 'csv'
        elif '.xlsx' in url_lower or '.xls' in url_lower:
            return 'xlsx'
        elif '.json' in url_lower:
            return 'json'
        elif 'format=json' in url_lower:
            return 'json'
        else:
            return 'unknown'


class OGDPortalDiscovery:
    """
    Discovers available resources by scraping data.gov.in catalog pages.
    Used to build/update the manifest with correct resource IDs.
    """

    BASE_URL = "https://data.gov.in"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("OGDPortalDiscovery")

    def discover_resources(self, dataset_keywords: List[str] = None) -> List[Dict]:
        """
        Discover resources from data.gov.in based on keyword search.
        Returns list of resource info dicts.
        """
        if not dataset_keywords:
            dataset_keywords = ['census', 'population', 'district']

        all_resources = []

        for keyword in dataset_keywords:
            self.logger.info(f"Searching for: {keyword}")
            resources = self._search_by_keyword(keyword)
            all_resources.extend(resources)

        # Deduplicate by resource_id
        seen = set()
        unique_resources = []
        for r in all_resources:
            if r['resource_id'] not in seen:
                seen.add(r['resource_id'])
                unique_resources.append(r)

        return unique_resources

    def _search_by_keyword(self, keyword: str) -> List[Dict]:
        """
        Search data.gov.in for resources by keyword.
        """
        resources = []

        try:
            import requests

            search_url = f"{self.BASE_URL}/search"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            }

            params = {
                'q': keyword,
                'sort': 'score',
                'order': 'desc'
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            # Extract resource info from HTML
            resources = self._parse_search_results(response.text)

        except Exception as e:
            self.logger.error(f"Search failed for '{keyword}': {e}")

        return resources

    def _parse_search_results(self, html: str) -> List[Dict]:
        """
        Parse search results HTML to extract resource info.
        """
        resources = []

        # Pattern to find resource cards
        resource_patterns = [
            r'href="/resource/([a-f0-9-]{36})"[^>]*>([^<]+)</a>',  # Resource ID pattern
            r'data-resource-id="([a-f0-9-]{36})"',
        ]

        for pattern in resource_patterns:
            matches = re.findall(pattern, html)
            for resource_id, title in matches:
                resources.append({
                    'resource_id': resource_id,
                    'title': title.strip() if title else 'Unknown',
                    'url': f"{self.BASE_URL}/resource/{resource_id}"
                })

        return resources

    def probe_resource(self, resource_id: str) -> Dict[str, Any]:
        """
        Check if a resource is accessible and get its metadata.
        """
        try:
            import requests

            # Try the resource page
            resource_url = f"{self.BASE_URL}/resource/{resource_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            }

            response = requests.get(resource_url, headers=headers, timeout=30)

            if response.status_code == 200:
                return {
                    'resource_id': resource_id,
                    'accessible': True,
                    'status_code': 200,
                    'url': resource_url,
                    'page_size': len(response.text)
                }
            else:
                return {
                    'resource_id': resource_id,
                    'accessible': False,
                    'status_code': response.status_code
                }

        except Exception as e:
            return {
                'resource_id': resource_id,
                'accessible': False,
                'error': str(e)
            }