"""
Strategy Router
---------------
Production-ready downloader that implements failover logic.
Priority: 1. OGD API → 2. Crawl4AI → 3. Direct URL → 4. Cache Replay
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from pipeline.engine.downloaders.ogd_downloader import OGDDownloader
from pipeline.engine.downloaders.crawl4ai_renderer import Crawl4AIRenderer
from pipeline.engine.downloaders.direct import DirectDownloader
from pipeline.engine.downloaders.base import BaseDownloader


class DownloadStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"


@dataclass
class DownloadResult:
    resource_id: str
    strategy: str
    status: DownloadStatus
    file_path: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False


class StrategyRouter:
    """
    Routes download requests through multiple strategies with automatic failover.
    Designed for production use - never fails completely if any strategy works.
    """

    DEFAULT_STRATEGIES = [
        {'name': 'ogd_api', 'enabled': True, 'priority': 1},
        {'name': 'crawl4ai', 'enabled': True, 'priority': 2},
        {'name': 'direct_url', 'enabled': True, 'priority': 3},
        {'name': 'cache_replay', 'enabled': True, 'priority': 4},
    ]

    def __init__(self, config: Dict[str, Any], dataset_id: str):
        self.config = config
        self.dataset_id = dataset_id
        self.logger = logging.getLogger("StrategyRouter")
        self.strategies = config.get('strategies', self.DEFAULT_STRATEGIES)
        self.fallback_enabled = config.get('fallback_enabled', True)
        self.cache_dir = Path(config.get('cache_dir', f'data/cache/{dataset_id}'))
        self.results: List[DownloadResult] = []

    def download(self, resource_id: str, urls: Dict[str, str] = None) -> Optional[str]:
        """
        Try each strategy in priority order until one succeeds.
        Returns file path on success, None on complete failure.
        """
        urls = urls or {'ogd_api': None}  # Default: use manifest

        # Sort strategies by priority
        sorted_strategies = sorted(
            [s for s in self.strategies if s.get('enabled', True)],
            key=lambda x: x.get('priority', 99)
        )

        last_error = None

        for strategy_config in sorted_strategies:
            strategy_name = strategy_config['name']
            self.logger.info(f"Trying strategy: {strategy_name} for {resource_id}")

            try:
                file_path = self._try_strategy(strategy_name, resource_id, urls, strategy_config)

                if file_path:
                    result = DownloadResult(
                        resource_id=resource_id,
                        strategy=strategy_name,
                        status=DownloadStatus.SUCCESS,
                        file_path=file_path
                    )
                    self.results.append(result)
                    self.logger.success(f"[{strategy_name}] Successfully downloaded {resource_id}")
                    return file_path

            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"[{strategy_name}] Failed for {resource_id}: {e}")
                result = DownloadResult(
                    resource_id=resource_id,
                    strategy=strategy_name,
                    status=DownloadStatus.FAILED,
                    error=last_error
                )
                self.results.append(result)

                if not self.fallback_enabled:
                    break
                continue

        # All strategies failed
        self.logger.error(f"All strategies failed for {resource_id}. Last error: {last_error}")
        return None

    def _try_strategy(self, strategy_name: str, resource_id: str, urls: Dict, config: Dict) -> Optional[str]:
        """Execute a specific download strategy."""

        if strategy_name == 'ogd_api':
            return self._ogd_api_download(resource_id, config)
        elif strategy_name == 'crawl4ai':
            return self._crawl4ai_download(resource_id, urls.get('crawl4ai'), config)
        elif strategy_name == 'direct_url':
            return self._direct_url_download(urls.get('direct_url'), config)
        elif strategy_name == 'cache_replay':
            return self._cache_replay_download(resource_id)
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")

    def _ogd_api_download(self, resource_id: str, config: Dict) -> Optional[str]:
        """Download using OGD API."""
        ogd_config = self.config.copy()
        ogd_config['source_name'] = self.dataset_id

        downloader = OGDDownloader(ogd_config)
        # OGDDownloader handles manifest internally
        files = downloader.download()

        if files:
            # Find the file for this resource_id
            for f in files:
                if resource_id in f or resource_id.replace('-', '') in f:
                    return f
            return files[0] if files else None

        return None

    def _crawl4ai_download(self, resource_id: str, url: str, config: Dict) -> Optional[str]:
        """Download using Crawl4AI web scraping."""
        if not url:
            # Generate URL from pattern
            url = f"https://data.gov.in/resource/{resource_id}"

        crawl_config = {
            **config,
            'url': url,
            'source_name': self.dataset_id,
            'output_dir': f'data/raw/{self.dataset_id}'
        }

        downloader = Crawl4AIRenderer(crawl_config)
        files = downloader.download(url)

        return files[0] if files else None

    def _direct_url_download(self, url: str, config: Dict) -> Optional[str]:
        """Download directly from a URL."""
        if not url:
            return None

        direct_config = {
            'url': url,
            'source_name': self.dataset_id,
            'output_dir': f'data/raw/{self.dataset_id}'
        }

        downloader = DirectDownloader(direct_config)
        return downloader.download(url)

    def _cache_replay_download(self, resource_id: str) -> Optional[str]:
        """Replay from cached file when all sources fail."""
        cache_path = self.cache_dir / f"{resource_id}.json"

        if cache_path.exists() and cache_path.stat().st_size > 100:
            self.logger.info(f"Cache hit for {resource_id}: {cache_path}")
            return str(cache_path)

        # Also try without dashes
        cache_path_alt = self.cache_dir / f"{resource_id.replace('-', '')}.json"
        if cache_path_alt.exists():
            return str(cache_path_alt)

        return None

    def get_results_summary(self) -> Dict[str, Any]:
        """Get summary of all download attempts."""
        total = len(self.results)
        success = len([r for r in self.results if r.status == DownloadStatus.SUCCESS])
        failed = len([r for r in self.results if r.status == DownloadStatus.FAILED])
        cached = len([r for r in self.results if r.cached])

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'cached': cached,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'results': [
                {
                    'resource_id': r.resource_id,
                    'strategy': r.strategy,
                    'status': r.status.value,
                    'file_path': r.file_path,
                    'error': r.error
                }
                for r in self.results
            ]
        }


class MultiStrategyDownloader:
    """
    High-level interface for multi-strategy downloading.
    Use this in the orchestrator instead of single downloader.
    """

    def __init__(self, config: Dict[str, Any], dataset_id: str):
        self.router = StrategyRouter(config, dataset_id)
        self.logger = logging.getLogger("MultiStrategyDownloader")

    def download_all(self, manifest_entries: List[Dict]) -> List[str]:
        """
        Download all resources from manifest using strategy router.
        Returns list of successfully downloaded file paths.
        """
        downloaded_files = []
        failed_resources = []

        for entry in manifest_entries:
            resource_id = entry.get('resource_id')
            urls = entry.get('urls', {})

            self.logger.info(f"Processing resource: {resource_id}")

            file_path = self.router.download(resource_id, urls)

            if file_path:
                downloaded_files.append(file_path)
                # Cache successful downloads for offline replay
                self._cache_download(file_path, resource_id)
            else:
                failed_resources.append(resource_id)

        # Log summary
        summary = self.router.get_results_summary()
        self.logger.info(f"Download complete: {summary['success']}/{summary['total']} successful")

        if failed_resources:
            self.logger.warning(f"Failed resources ({len(failed_resources)}): {failed_resources[:5]}...")

        return downloaded_files

    def _cache_download(self, file_path: str, resource_id: str):
        """Cache successful downloads for offline replay."""
        try:
            import shutil
            cache_dir = Path(f'data/cache/{self.router.dataset_id}')
            cache_dir.mkdir(parents=True, exist_ok=True)

            cache_path = cache_dir / f"{resource_id}.json"
            shutil.copy2(file_path, cache_path)
            self.logger.debug(f"Cached: {file_path} -> {cache_path}")
        except Exception as e:
            self.logger.warning(f"Failed to cache {resource_id}: {e}")