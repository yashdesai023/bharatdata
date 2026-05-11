from pipeline.engine.downloaders.direct import DirectDownloader
from pipeline.engine.downloaders.browser_renderer import BrowserRenderer
from pipeline.engine.downloaders.page_scraper import PageScraper
from pipeline.engine.downloaders.api_client import ApiClient
from pipeline.engine.downloaders.manual_upload import ManualUpload
from pipeline.engine.downloaders.crawl4ai_renderer import Crawl4AIRenderer
from pipeline.engine.downloaders.ogd_downloader import OGDDownloader
from pipeline.engine.downloaders.strategy_router import MultiStrategyDownloader, StrategyRouter
from pipeline.engine.downloaders.cache_replay import CacheReplayDownloader
from pipeline.engine.downloaders.ogd_fallback import OGDFallbackDownloader


class DownloaderFactory:
    @staticmethod
    def get_downloader(method, config):
        strategies = {
            'direct_download': DirectDownloader,
            'browser_rendering': BrowserRenderer,
            'page_scraper': PageScraper,
            'api_call': ApiClient,
            'manual_upload': ManualUpload,
            'crawl4ai_rendering': Crawl4AIRenderer,
            'data_gov_api': OGDDownloader,
            'ogd_fallback': OGDFallbackDownloader,
            'cache_replay': CacheReplayDownloader,
        }
        if method not in strategies:
            raise ValueError(f"Unsupported download method: '{method}'. "
                             f"Valid options: {list(strategies.keys())}")
        return strategies[method](config)

    @staticmethod
    def get_multi_strategy_downloader(config, dataset_id):
        """
        Get a multi-strategy downloader with automatic failover.
        Use this for production deployments.
        """
        return MultiStrategyDownloader(config, dataset_id)

    @staticmethod
    def get_strategy_router(config, dataset_id):
        """
        Get a strategy router for fine-grained control.
        """
        return StrategyRouter(config, dataset_id)
