import os
import asyncio
import logging
import time
import re
import ssl
from urllib.parse import urlparse, quote, urljoin
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from pipeline.engine.downloaders.base import BaseDownloader

class Crawl4AIRenderer(BaseDownloader):
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger("Crawl4AIRenderer")
        self.magic = config.get('magic', True)
        self.concurrency = config.get('concurrency', 1)
        self.jitter = config.get('jitter', 3)
        self.ssl_verify = config.get('ssl_verify', True)
        # Resolve 'verify' used by requests: prefer explicit env bundle (REQUESTS_CA_BUNDLE/SSL_CERT_FILE) if set,
        # otherwise prefer certifi when ssl_verify is True.
        try:
            env_cafile = os.environ.get('REQUESTS_CA_BUNDLE') or os.environ.get('SSL_CERT_FILE')
            if env_cafile and os.path.exists(env_cafile):
                self.verify = env_cafile
                self.logger.info(f"Using CA bundle from env: {env_cafile}")
            elif self.ssl_verify:
                try:
                    import certifi
                    self.verify = certifi.where()
                    self.logger.info(f"Using CA bundle from: {self.verify}")
                except Exception:
                    # fallback to system store; recommend installing certifi for robustness
                    self.logger.warning("certifi not available; using system cert store. For reliable TLS, install certifi (pip install certifi).")
                    self.verify = True
            else:
                self.verify = False
        except Exception:
            # last-resort: use system verification
            self.verify = True

        # If verify is a path (certifi), expose it via env vars so other libraries (and requests) pick it up
        self.allow_insecure_fallback = config.get('allow_insecure_fallback', False)
        try:
            if isinstance(self.verify, str):
                os.environ.setdefault('REQUESTS_CA_BUNDLE', self.verify)
                os.environ.setdefault('SSL_CERT_FILE', self.verify)
                self.logger.info(f"Using CA bundle from: {self.verify}")
        except Exception:
            pass

        # Directory to persist per-host cert bundles if verification fails; useful for environments missing intermediate CAs
        output_dir = config.get('output_dir', 'data/raw')
        self.cert_dir = config.get('cert_dir', os.path.join(output_dir, '..', 'certs'))
        os.makedirs(self.cert_dir, exist_ok=True)
        self._host_cert_map = {}  # cache host->pem path
    def download(self, url=None, dest_folder=None):
        """Renders a page using Crawl4AI and extracts links."""
        target_url = url or self.config.get('url')
        output_dir = dest_folder or self.config.get('output_dir', "data/raw")
        link_selector = self.config.get('link_selector', "a")
        filters = self.config.get('filters', {})
        
        if not target_url:
            raise ValueError("Crawl4AIRenderer requires a URL.")
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Run the async crawler in a synchronous context
        return asyncio.run(self._async_download(target_url, output_dir, link_selector, filters))

    async def _async_download(self, url, output_dir, selector, filters):
        downloaded_files = []
        
        # Professional naming for artifacts
        timestamp = int(time.time())
        artifacts_base = self.config.get('artifacts_dir', os.path.join(output_dir, 'artifacts'))
        source_name = self.config.get('source_name', 'default')
        artifact_path = os.path.join(artifacts_base, f"{source_name}_{timestamp}")
        os.makedirs(artifact_path, exist_ok=True)
        # Use the selector from config, or None for automatic link discovery
        selector = self.config.get('link_selector')
        click_selector = self.config.get('click_selector')
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            magic=self.magic,
            wait_until="domcontentloaded",
            page_timeout=60000,
            screenshot=True,
            markdown_generator=None 
        )
        
        if selector:
            config.wait_for = selector
            
        if click_selector:
             # If we need to click, we might need a session or specialized config
             # In Crawl4AI 0.4.x, we can use js_code to click if needed
             self.logger.info(f"Will attempt to click {click_selector} before extraction.")
             # Use backticks for the selector to avoid quote nesting issues
             config.js_code = [f"const el = document.querySelector(`{click_selector}`); if(el) el.click();"]

        async with AsyncWebCrawler() as crawler:
            self.logger.info(f"Crawling {url} with Magic Mode: {self.magic}")
            
            result = None
            try:
                result = await crawler.arun(url=url, config=config)
            except Exception as e:
                self.logger.error(f"Crawl execution error for {url}: {str(e)}")
            
            # Save Accuracy Artifacts (Save if result exists, regardless of success flag)
            if result and self.config.get('artifact_preservation', True):
                md_path = os.path.join(artifact_path, f"metadata_{timestamp}.md")
                img_path = os.path.join(artifact_path, f"page_view_{timestamp}.png")
                
                try:
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(result.markdown or "No content extracted.")
                    
                    if result.screenshot:
                        import base64
                        with open(img_path, 'wb') as f:
                            f.write(base64.b64decode(result.screenshot))
                    self.logger.info(f"Artifacts preserved at {artifact_path}")
                except Exception as save_err:
                    self.logger.warning(f"Could not save artifacts: {save_err}")

            if not result or not result.success:
                err_msg = result.error_message if result else "No result returned"
                self.logger.error(f"Failed to crawl {url}: {err_msg}")
                return []

            # Extract links using Crawl4AI's parsed content
            all_links = result.links.get('internal', []) + result.links.get('external', [])
            
            self.logger.info(f"Found {len(all_links)} raw links on page.")

            for link in all_links:
                href = link.get('href')
                if not href:
                    continue

                # URL-encode href to handle Unicode characters (fixes charmap errors)
                try:
                    encoded_href = quote(href, safe=':/?#[]@!$&\'()*+,;=%')
                except Exception:
                    encoded_href = href  # Fallback to original if encoding fails

                # Resolve relative URLs
                full_url = encoded_href if encoded_href.startswith("http") else f"{url.rstrip('/')}/{encoded_href.lstrip('/')}"
                filename = os.path.basename(encoded_href).split('?')[0]

                # Filtering logic (Same as BrowserRenderer for consistency)
                include_list = filters.get('include', [])
                exclude_list = filters.get('exclude', [])
                filter_mode = filters.get('mode', 'all')

                if include_list:
                    if filter_mode == 'any':
                        if not any(inc.lower() in filename.lower() for inc in include_list):
                            continue
                    else:
                        if not all(inc.lower() in filename.lower() for inc in include_list):
                            continue

                if any(exc.lower() in filename.lower() for exc in exclude_list):
                    continue

                # Process discovered link: follow HTML pages to embedded xlsx/csv links and download binaries
                file_path = os.path.join(output_dir, filename)
                self.logger.info(f"Processing discovered link: {filename} -> {full_url}")

                self._wait_for_rate_limit()
                if self.jitter:
                    time.sleep(self.jitter) # Extra delay for Census portal safety

                try:
                    import requests
                    session = requests.Session()
                    # Set browser-like headers to avoid bot detection
                    ua = self.config.get('user_agent') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
                    session.headers.update({
                        'User-Agent': ua,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': url
                    })
                    # Mount retry adapter to handle transient network errors
                    try:
                        from requests.adapters import HTTPAdapter
                        from urllib3.util.retry import Retry
                        # Try modern Retry API, fall back silently if incompatible
                        try:
                            retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=frozenset(['GET','POST']))
                        except Exception:
                            retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429,500,502,503,504])
                        adapter = HTTPAdapter(max_retries=retry_strategy)
                        session.mount('https://', adapter)
                        session.mount('http://', adapter)
                    except Exception:
                        pass
                    # Allow redirects and check content-type
                    try:
                        resp = session.get(full_url, timeout=30, verify=self.verify, allow_redirects=True)
                    except requests.exceptions.SSLError as ssl_e:
                        # Try bootstrapping a per-host cert bundle and retry
                        host = urlparse(full_url).hostname
                        self.logger.warning(f"SSL verification failed for {host}. Attempting to bootstrap certificate: {ssl_e}")
                        try:
                            pem = self._bootstrap_cert(host)
                            if pem:
                                resp = session.get(full_url, timeout=30, verify=pem, allow_redirects=True)
                            else:
                                if self.allow_insecure_fallback:
                                    self.logger.warning(f"Bootstrapping failed; falling back to insecure download for {full_url} due to allow_insecure_fallback=True")
                                    try:
                                        import urllib3
                                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                                    except Exception:
                                        pass
                                    resp = session.get(full_url, timeout=30, verify=False, allow_redirects=True)
                                else:
                                    raise
                        except requests.exceptions.SSLError as e2:
                            if self.allow_insecure_fallback:
                                self.logger.warning(f"Bootstrapped cert verify failed; falling back insecure for {full_url}: {e2}")
                                try:
                                    import urllib3
                                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                                except Exception:
                                    pass
                                resp = session.get(full_url, timeout=30, verify=False, allow_redirects=True)
                            else:
                                self.logger.error(f"Retry with bootstrapped cert failed for {full_url}: {e2}")
                                raise
                        except Exception as e:
                            self.logger.error(f"Retry with bootstrapped cert failed for {full_url}: {e}")
                            raise

                    ctype = resp.headers.get('content-type', '').lower()

                    if 'text/html' in ctype or 'application/xhtml+xml' in ctype:
                        # parse HTML for .xlsx/.xls/.csv links
                        html = resp.text
                        hrefs = re.findall(r'href=[\'\"]([^\'\"]+\\.(?:xlsx|xls|csv))(?:\?[^\'\"]*)?[\'\"]', html, flags=re.IGNORECASE)
                        if not hrefs:
                            # loose search fallback
                            hrefs = re.findall(r'([^\s\'\"]+\\.(?:xlsx|xls|csv))', html, flags=re.IGNORECASE)

                        # If still none, ask Crawl4AI to render this subpage (handles JS-generated links)
                        if not hrefs:
                            try:
                                self.logger.info(f"No direct file links found in HTML; rendering subpage: {full_url}")
                                result2 = await crawler.arun(url=full_url, config=config)
                                if result2 and result2.success:
                                    sub_links = result2.links.get('internal', []) + result2.links.get('external', [])
                                    for l in sub_links:
                                        h2 = l.get('href')
                                        if h2 and re.search(r'\\.(xlsx|xls|csv)$', h2, re.IGNORECASE):
                                            hrefs.append(h2)
                            except Exception as e:
                                self.logger.warning(f"Renderer failed for {full_url}: {e}")

                        for href in hrefs:
                            # URL-encode href to handle Unicode characters
                            try:
                                encoded_href = quote(href, safe=':/?#[]@!$&\'()*+,;=%')
                            except Exception:
                                encoded_href = href

                            sub_url = encoded_href if encoded_href.startswith('http') else urljoin(full_url, encoded_href)
                            sub_name = os.path.basename(sub_url).split('?')[0]
                            # Sanitize filename to remove any remaining Unicode
                            sub_name = ''.join(c if ord(c) < 128 else '_' for c in sub_name)
                            sub_path = os.path.join(output_dir, sub_name)
                            try:
                                self.logger.info(f"Found embedded file link: {sub_name} -> {sub_url}")
                                try:
                                    r2 = session.get(sub_url, stream=True, timeout=30, verify=self.verify)
                                except requests.exceptions.SSLError:
                                    # attempt per-host cert for embedded link
                                    host2 = urlparse(sub_url).hostname
                                    pem2 = self._host_cert_map.get(host2)
                                    if pem2:
                                        r2 = session.get(sub_url, stream=True, timeout=30, verify=pem2)
                                    elif self.allow_insecure_fallback:
                                        self.logger.warning(f"Embedded link SSL failed; falling back to insecure download for {sub_url}")
                                        try:
                                            import urllib3
                                            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                                        except Exception:
                                            pass
                                        r2 = session.get(sub_url, stream=True, timeout=30, verify=False)
                                    else:
                                        raise

                                if r2.status_code == 200:
                                    with open(sub_path, 'wb') as f:
                                        for chunk in r2.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    downloaded_files.append(sub_path)
                                else:
                                    self.logger.warning(f"Failed to download embedded {sub_url}: Status {r2.status_code}")
                            except Exception as e:
                                self.logger.error(f"Error downloading embedded {sub_url}: {e}")
                    else:
                        # Direct binary download
                        try:
                            r2 = resp if resp.status_code == 200 else session.get(full_url, stream=True, timeout=30, verify=self.verify)
                        except requests.exceptions.SSLError:
                            host2 = urlparse(full_url).hostname
                            pem2 = self._host_cert_map.get(host2)
                            if pem2:
                                r2 = session.get(full_url, stream=True, timeout=30, verify=pem2)
                            elif self.allow_insecure_fallback:
                                self.logger.warning(f"SSL failed for {full_url}; falling back to insecure download")
                                try:
                                    import urllib3
                                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                                except Exception:
                                    pass
                                r2 = session.get(full_url, stream=True, timeout=30, verify=False)
                            else:
                                raise

                        if r2.status_code == 200:
                            with open(file_path, 'wb') as f:
                                for chunk in r2.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            downloaded_files.append(file_path)
                        else:
                            self.logger.warning(f"Failed to download {full_url}: Status {r2.status_code}")
                except Exception as e:
                    self.logger.error(f"Error downloading {full_url}: {e}")

        return downloaded_files

    def _bootstrap_cert(self, host):
        """Fetch server certificate for host and persist a combined trust bundle (certifi + server cert).
        This creates a bundle that contains the system/mozila CA bundle followed by the server's leaf
        certificate so requests can verify the host even when intermediate CAs are missing from the OS.
        """
        try:
            if host in self._host_cert_map:
                return self._host_cert_map[host]

            pem_path = os.path.join(self.cert_dir, f"{host}.pem")
            bundle_path = os.path.join(self.cert_dir, f"{host}_bundle.pem")

            try:
                # Prefer certifi bundle if available
                try:
                    import certifi
                    cafile = certifi.where()
                except Exception:
                    cafile = None

                # Fetch server certificate (PEM)
                server_pem = ssl.get_server_certificate((host, 443))

                # Write the raw server PEM for diagnostics
                with open(pem_path, 'w') as f:
                    f.write(server_pem)

                # Create a combined bundle: certifi CA bundle (if present) + server pem
                if cafile and os.path.exists(cafile):
                    with open(bundle_path, 'w') as out:
                        with open(cafile, 'r') as cf:
                            out.write(cf.read())
                        out.write("\n")
                        out.write(server_pem)
                else:
                    # Fallback: use only the server pem as the bundle
                    with open(bundle_path, 'w') as out:
                        out.write(server_pem)

                # Cache mapping to use this bundle for subsequent requests to the host
                self._host_cert_map[host] = bundle_path
                self.logger.info(f"Created trust bundle for {host} at {bundle_path}")
                return bundle_path
            except Exception as e:
                self.logger.error(f"Failed to bootstrap certificate for {host}: {e}")
                return None
        except Exception as e:
            self.logger.error(f"_bootstrap_cert unexpected error: {e}")
            return None
