from abc import ABC, abstractmethod
import os
import requests
import hashlib
import time

class BaseDownloader(ABC):
    def __init__(self, config):
        self.config = config
        self.rate_limit = config.get('rate_limit', 1)
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    @abstractmethod
    def download(self, url=None, dest_folder=None):
        """Downloads a single file or a set of binary data to the destination folder."""
        pass

    def get_file_hash(self, file_path):
        """Calculates SHA-256 hash of a file for change detection."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
