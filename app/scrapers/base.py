import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import master_config

class BaseScraper:
    """
    Base class for all portal-specific scrapers.
    Provides async HTTP capabilities with resilience (retries, rate limits).
    """
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)
        
        # Load retry settings from master config
        self.max_retries = master_config["scraping"]["max_retries"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_html(self, url: str) -> BeautifulSoup | None:
        """
        Fetches a URL asynchronously and returns a parsed BeautifulSoup object.
        Retries automatically on network failures according to Tenacity limits.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
