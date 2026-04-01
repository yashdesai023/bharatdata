from pipeline.engine.downloaders.direct import DirectDownloader
from pipeline.engine.downloaders.browser_renderer import BrowserRenderer
from pipeline.engine.downloaders.page_scraper import PageScraper
from pipeline.engine.downloaders.api_client import ApiClient
from pipeline.engine.downloaders.manual_upload import ManualUpload


class DownloaderFactory:
    @staticmethod
    def get_downloader(method, config):
        strategies = {
            'direct_download': DirectDownloader,
            'browser_rendering': BrowserRenderer,
            'page_scraper': PageScraper,
            'api_call': ApiClient,
            'manual_upload': ManualUpload,
        }
        if method not in strategies:
            raise ValueError(f"Unsupported download method: '{method}'. "
                             f"Valid options: {list(strategies.keys())}")
        return strategies[method](config)
