"""
Cache Replay Downloader
-----------------------
Offline mode: Replays from cached files when all network sources fail.
Cache location: data/cache/{dataset_id}/{resource_id}.json
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from pipeline.engine.downloaders.base import BaseDownloader


class CacheReplayDownloader(BaseDownloader):
    """
    Replays downloads from cached files.
    Used as last resort when all network-based strategies fail.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.cache_dir = Path(config.get('cache_dir', 'data/cache'))
        self.dataset_id = config.get('source_name', config.get('dataset_id', 'unknown'))
        self.logger = logging.getLogger("CacheReplayDownloader")

        # Dataset-specific cache directory
        if self.dataset_id:
            self.cache_dir = self.cache_dir / self.dataset_id

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download(self, resource_id: str = None, dest_folder: str = None) -> List[str]:
        """
        Replay from cached file(s).
        Returns list of file paths (cached files).
        """
        downloaded_files = []

        # If specific resource_id provided
        if resource_id:
            file_path = self._find_cache(resource_id)
            if file_path:
                downloaded_files.append(file_path)
            else:
                self.logger.warning(f"No cache found for resource: {resource_id}")
            return downloaded_files

        # Otherwise, return all cached files for this dataset
        for cache_file in self.cache_dir.glob("*.json"):
            downloaded_files.append(str(cache_file))

        self.logger.info(f"Cache replay: found {len(downloaded_files)} cached files")
        return downloaded_files

    def _find_cache(self, resource_id: str) -> Optional[str]:
        """Find cache file for a resource."""
        # Try exact match
        cache_path = self.cache_dir / f"{resource_id}.json"
        if cache_path.exists():
            return str(cache_path)

        # Try without dashes
        cache_path = self.cache_dir / f"{resource_id.replace('-', '')}.json"
        if cache_path.exists():
            return str(cache_path)

        # Try glob pattern
        matches = list(self.cache_dir.glob(f"*{resource_id.replace('-', '')}*.json"))
        if matches:
            return str(matches[0])

        return None

    def is_available(self, resource_id: str = None) -> bool:
        """Check if cache is available for a resource."""
        if resource_id:
            return self._find_cache(resource_id) is not None
        else:
            # Check if any cache exists
            return len(list(self.cache_dir.glob("*.json"))) > 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        cache_files = list(self.cache_dir.glob("*.json"))

        total_size = sum(f.stat().st_size for f in cache_files)
        total_records = 0

        for f in cache_files:
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    total_records += data.get('total', data.get('records', [])).__len__()
            except Exception:
                pass

        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'estimated_records': total_records
        }


class ManifestRegistry:
    """
    Registry for tracking download status across strategies.
    JSON-based manifest with multi-URL support per resource.
    """

    def __init__(self, dataset_id: str, registry_path: str = None):
        self.dataset_id = dataset_id
        self.registry_path = Path(registry_path or f"pipeline/manifests/{dataset_id}_registry.json")
        self.logger = logging.getLogger("ManifestRegistry")
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load registry from file."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load registry: {e}")

        # Initialize empty registry
        return {
            'dataset_id': self.dataset_id,
            'strategies': ['ogd_api', 'crawl4ai', 'direct_url', 'cache_replay'],
            'resources': {}
        }

    def save(self):
        """Save registry to file."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def add_resource(self, entity_name: str, resource_id: str, urls: Dict[str, str] = None):
        """Add a resource to the registry."""
        self.data['resources'][resource_id] = {
            'entity_name': entity_name,
            'resource_id': resource_id,
            'urls': urls or {},
            'status': 'pending',
            'last_tried': None,
            'last_success': None,
            'strategies_tried': [],
            'current_strategy': None,
            'file_path': None,
            'error': None,
            'cache_available': False,
            'record_count': 0
        }

    def update_status(self, resource_id: str, strategy: str, status: str,
                      file_path: str = None, error: str = None, record_count: int = 0):
        """Update the status of a resource after download attempt."""
        if resource_id not in self.data['resources']:
            self.logger.warning(f"Resource {resource_id} not in registry")
            return

        from datetime import datetime
        now = datetime.now().isoformat()

        resource = self.data['resources'][resource_id]

        if strategy not in resource['strategies_tried']:
            resource['strategies_tried'].append(strategy)

        resource['current_strategy'] = strategy
        resource['last_tried'] = now

        if status == 'success':
            resource['status'] = 'completed'
            resource['last_success'] = now
            resource['file_path'] = file_path
            resource['record_count'] = record_count
            resource['error'] = None
            resource['cache_available'] = os.path.exists(file_path) if file_path else False

        elif status == 'failed':
            if resource['status'] != 'completed':
                resource['status'] = 'failed'
            resource['error'] = error

        self.save()

    def get_pending_resources(self) -> List[Dict]:
        """Get all pending resources."""
        return [
            {'resource_id': rid, 'entity_name': r['entity_name'], 'urls': r['urls']}
            for rid, r in self.data['resources'].items()
            if r['status'] in ('pending', 'failed')
        ]

    def get_completed_count(self) -> int:
        """Get count of successfully completed resources."""
        return len([r for r in self.data['resources'].values() if r['status'] == 'completed'])

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of registry status."""
        resources = self.data['resources']
        total = len(resources)
        completed = len([r for r in resources.values() if r['status'] == 'completed'])
        failed = len([r for r in resources.values() if r['status'] == 'failed'])
        pending = len([r for r in resources.values() if r['status'] == 'pending'])

        return {
            'dataset_id': self.dataset_id,
            'total_resources': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 2)
        }