import asyncio
import hashlib
from pathlib import Path
from urllib import robotparser
import httpx
from app.ingestion.parser import extract_category_links, extract_fatwa_links
from app.ingestion.adapters import DORAR_URL_RE


class ConservativeCrawler:
    def __init__(self, cache_dir: Path, user_agent: str, delay_seconds: float = 2.5):
        self.cache_dir = cache_dir
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._robots: robotparser.RobotFileParser | None = None

    def cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.html"

    async def prepare(self, client: httpx.AsyncClient) -> None:
        response = await client.get("https://binbaz.org.sa/robots.txt", headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        parser = robotparser.RobotFileParser("https://binbaz.org.sa/robots.txt")
        parser.parse(response.text.splitlines())
        self._robots = parser

    async def fetch(self, client: httpx.AsyncClient, url: str) -> str:
        if not url.startswith("https://binbaz.org.sa/"):
            raise ValueError("Crawler is restricted to binbaz.org.sa")
        if self._robots is None:
            await self.prepare(client)
        if self._robots and not self._robots.can_fetch(self.user_agent, url):
            raise PermissionError(f"robots.txt disallows {url}")
        cache_file = self.cache_path(url)
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        response = await client.get(url, headers={"User-Agent": self.user_agent}, follow_redirects=True, timeout=30)
        response.raise_for_status()
        cache_file.write_text(response.text, encoding="utf-8")
        await asyncio.sleep(self.delay_seconds)
        return response.text

    async def discover(self, seed_urls: list[str], max_categories: int | None = None) -> dict[int, str]:
        queue = list(seed_urls)
        seen: set[str] = set()
        fatwas: dict[int, str] = {}
        async with httpx.AsyncClient() as client:
            while queue and (max_categories is None or len(seen) < max_categories):
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                html = await self.fetch(client, url)
                fatwas.update(extract_fatwa_links(html, url))
                for category in extract_category_links(html, url):
                    if category not in seen:
                        queue.append(category)
        return fatwas

    async def fetch_documents(self, urls: list[str]) -> None:
        """Cache detail pages as a separate, resumable step after discovery."""
        async with httpx.AsyncClient() as client:
            for url in urls:
                await self.fetch(client, url)


class ApprovedReferenceCrawler:
    """Conservative detail-page fetcher for explicitly approved Dorar URLs.

    Discovery is intentionally not automated. The source currently presents a
    Cloudflare challenge to non-browser clients, so callers receive the error
    rather than bypassing the site's controls or falling back to another source.
    """

    def __init__(self, cache_dir: Path, user_agent: str, delay_seconds: float = 2.5):
        self.cache_dir = cache_dir
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._robots: robotparser.RobotFileParser | None = None

    def cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.html"

    async def prepare(self, client: httpx.AsyncClient) -> None:
        robots_url = "https://dorar.net/robots.txt"
        response = await client.get(robots_url, headers={"User-Agent": self.user_agent}, follow_redirects=True)
        response.raise_for_status()
        parser = robotparser.RobotFileParser(robots_url)
        parser.parse(response.text.splitlines())
        self._robots = parser

    async def fetch(self, client: httpx.AsyncClient, url: str) -> str:
        normalized = url.split("?")[0].split("#")[0].rstrip("/")
        if not DORAR_URL_RE.match(normalized):
            raise ValueError("Approved crawler is restricted to canonical dorar.net/feqhia detail pages")
        if self._robots is None:
            await self.prepare(client)
        if self._robots and not self._robots.can_fetch(self.user_agent, normalized):
            raise PermissionError(f"robots.txt disallows {normalized}")
        cache_file = self.cache_path(normalized)
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        response = await client.get(normalized, headers={"User-Agent": self.user_agent}, follow_redirects=True, timeout=30)
        response.raise_for_status()
        if "Attention Required! | Cloudflare" in response.text:
            raise PermissionError("Dorar blocked non-browser retrieval; no bypass was attempted")
        cache_file.write_text(response.text, encoding="utf-8")
        await asyncio.sleep(self.delay_seconds)
        return response.text

    async def fetch_documents(self, urls: list[str]) -> dict[str, Path]:
        cached: dict[str, Path] = {}
        async with httpx.AsyncClient() as client:
            for url in urls:
                await self.fetch(client, url)
                cached[url] = self.cache_path(url.split("?")[0].split("#")[0].rstrip("/"))
        return cached
