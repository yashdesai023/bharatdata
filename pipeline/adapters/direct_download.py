import os
import time
from pathlib import Path
import requests
import pandas as pd
import json
from loguru import logger

class DirectDownloadError(Exception):
    pass

class DirectDownloadAdapter:
    def __init__(self, max_retries: int = 3, retry_delay: int = 5, timeout: int = 120):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.session = requests.Session()

    def _verify_integrity(self, file_path: Path) -> bool:
        """Perform a quick format sanity check to catch HTML error pages masquerading as data files."""
        if not file_path.exists():
            return False
            
        if file_path.stat().st_size < 1024:
            return False
            
        try:
            suffix = file_path.suffix.lower()
            if suffix in (".xls", ".xlsx"):
                pd.read_excel(file_path, nrows=1)
            elif suffix == ".csv":
                pd.read_csv(file_path, nrows=1)
            elif suffix == ".json":
                with open(file_path) as f:
                    json.load(f)
            return True
        except Exception as e:
            logger.warning(f"Integrity check failed for {file_path}: {e}")
            return False

    def download(self, url: str, dest_path: Path, force_redownload: bool = False, check_etag: bool = True) -> tuple[Path, str]:
        """
        Download a file with exponential backoff and chunking.
        Saves the file to dest_path.
        Returns (Path, content_type)
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        etag_path = dest_path.with_suffix(dest_path.suffix + ".etag")

        current_etag = None
        if etag_path.exists():
            current_etag = etag_path.read_text().strip()

        if not force_redownload and dest_path.exists() and not check_etag:
            logger.info(f"File already exists, reusing: {dest_path}")
            return dest_path, ""

        delay = self.retry_delay
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Downloading {url} -> {dest_path} (Attempt {attempt})")
                
                # Check ETag first if requested
                if check_etag and current_etag and not force_redownload:
                    head = self.session.head(url, timeout=self.timeout)
                    new_etag = head.headers.get("ETag")
                    if new_etag == current_etag:
                        # Verify file is not empty and at least minimally valid
                        if self._verify_integrity(dest_path):
                            logger.info(f"ETag matches, cache is valid: {dest_path}")
                            return dest_path, head.headers.get("Content-Type", "")
                        else:
                            logger.warning(f"Cached file looks corrupt or invalid, re-downloading")
                            if dest_path.exists():
                                dest_path.unlink()

                with self.session.get(url, timeout=self.timeout, stream=True) as resp:
                    resp.raise_for_status()
                    content_type = resp.headers.get("Content-Type", "")
                    new_etag = resp.headers.get("ETag")
                    
                    with dest_path.open("wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    
                    if new_etag:
                        etag_path.write_text(new_etag)
                        
                logger.success(f"Downloaded {dest_path.stat().st_size} bytes from {url}")
                return dest_path, content_type
            except Exception as e:
                logger.warning(f"Download failed ({e}), attempt {attempt}")
                if attempt == self.max_retries:
                    raise DirectDownloadError(f"Failed to download {url}") from e
                time.sleep(delay)
                delay *= 2  # exponential backoff
