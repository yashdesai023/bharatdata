import time
from urllib.parse import urlparse
from threading import Lock

# Get the pipeline logger
import os
import sys

# Ensure pipeline root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.logger_config import pipeline_logger as logger

class RateLimiter:
    """
    Ensures that HTTP requests to external servers (specifically NCRB)
    do not exceed the configured rate limit (default 1 req/sec).
    Tracks rate limits per hostname independently.
    Thread-safe for parallel ingestion.
    """
    def __init__(self, requests_per_second: float = 1.0):
        self.requests_per_second = requests_per_second
        self.min_gap = 1.0 / requests_per_second
        self._last_request_times = {}
        self._lock = Lock()

    def wait(self, url: str):
        """
        Wait if necessary to enforce the rate limit for the given URL's hostname.
        """
        hostname = urlparse(url).hostname
        if not hostname:
            return  # Invalid URL, assume no rate limiting needed

        with self._lock:
            now = time.monotonic()
            last_request = self._last_request_times.get(hostname, 0.0)
            elapsed = now - last_request
            
            if elapsed < self.min_gap:
                sleep_time = self.min_gap - elapsed
                logger.debug(f"Rate limiting active for {hostname}. Sleeping for {sleep_time:.3f}s")
                time.sleep(sleep_time)
                # After sleeping, record the new monotonic time
                self._last_request_times[hostname] = time.monotonic()
            else:
                self._last_request_times[hostname] = now

# Provide a standard singleton instance for the entire pipeline
default_rate_limiter = RateLimiter(requests_per_second=1.0)


if __name__ == "__main__":
    # Test block
    print("Testing Rate Limiter...")
    limiter = RateLimiter(requests_per_second=1.0)
    
    test_urls = [
        "https://www.ncrb.gov.in/page1",
        "https://www.ncrb.gov.in/page2",
        "https://www.ncrb.gov.in/page3",
        "https://www.ncrb.gov.in/page4",
        "https://www.ncrb.gov.in/page5"
    ]
    
    other_urls = [
        "https://api.github.com/endpoint1",
        "https://api.github.com/endpoint2"
    ]
    
    # Test 1: 5 rapid requests to the same host
    print("\nExecuting Test 1: 5 rapid requests to the same host")
    last_t = None
    for idx, url in enumerate(test_urls):
        limiter.wait(url)
        t = time.monotonic()
        if last_t is not None:
            gap = t - last_t
            print(f"[{idx+1}/5] Request to {url} - Gap: {gap:.3f}s")
            assert gap >= 1.0, f"Rate limit failed! Gap was {gap:.3f}s"
        else:
            print(f"[{idx+1}/5] First request to {url}")
        last_t = t
        
    # Test 2: Requests to a different host should not be throttled by the first host
    print("\nExecuting Test 2: Requests to a different host")
    print("Immediately requesting from GitHub right after an NCRB request...")
    limiter.wait("https://www.ncrb.gov.in/page6")
    t1 = time.monotonic()
    
    # Should not wait because it's a different host
    limiter.wait("https://api.github.com/endpoint1")
    t2 = time.monotonic()
    
    gap_diff_host = t2 - t1
    print(f"Gap between NCRB and GitHub request: {gap_diff_host:.3f}s")
    assert gap_diff_host < 0.1, f"Different hosts incorrectly throttled! Gap was {gap_diff_host:.3f}s"

    print("\n✅ All Rate Limiter tests passed!")
    
