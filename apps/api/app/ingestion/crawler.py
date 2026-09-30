import asyncio
import hashlib
import os
from pathlib import Path
import subprocess
from urllib import robotparser
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
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
        response = await self._get(client, robots_url)
        parser = robotparser.RobotFileParser(robots_url)
        parser.parse(response.splitlines())
        self._robots = parser

    async def _get(self, client: httpx.AsyncClient, url: str) -> str:
        """Fetch a public page without weakening TLS validation.

        Python's bundled CA store is not always connected to the Windows trust
        store.  On Windows we therefore use the system curl (Schannel).  Other
        platforms use httpx.  Both paths send the declared crawler user agent.
        """
        if os.name == "nt":
            completed = await asyncio.to_thread(
                subprocess.run,
                ["curl.exe", "--fail", "--silent", "--show-error", "--location", "--max-time", "45", "--user-agent", self.user_agent, url],
                capture_output=True,
                check=False,
            )
            if completed.returncode:
                message = completed.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"curl failed for {url}: {message}")
            return completed.stdout.decode("utf-8", errors="strict")
        response = await client.get(url, headers={"User-Agent": self.user_agent}, follow_redirects=True, timeout=45)
        response.raise_for_status()
        return response.text

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
        html = await self._get(client, normalized)
        if "Attention Required! | Cloudflare" in html:
            raise PermissionError("Dorar blocked non-browser retrieval; no bypass was attempted")
        cache_file.write_text(html, encoding="utf-8")
        await asyncio.sleep(self.delay_seconds)
        return html

    async def discover(self, index_url: str = "https://dorar.net/feqhia?l=1") -> list[str]:
        """Discover canonical detail links from Dorar's public Fiqh index."""
        async with httpx.AsyncClient() as client:
            if self._robots is None:
                await self.prepare(client)
            if self._robots and not self._robots.can_fetch(self.user_agent, index_url):
                raise PermissionError(f"robots.txt disallows {index_url}")
            html = await self._get(client, index_url)
        soup = BeautifulSoup(html, "html.parser")
        discovered: dict[int, str] = {}
        leaf_discovered: dict[int, str] = {}
        for anchor in soup.select('a[href*="/feqhia/"]'):
            href = urljoin(index_url, str(anchor.get("href", ""))).split("?")[0].split("#")[0].rstrip("/")
            match = DORAR_URL_RE.match(href)
            if match:
                discovered[int(match.group(1))] = href
                title = " ".join(anchor.get_text(" ", strip=True).split())
                if title.startswith(("المطلب", "المَطلب", "المَطلَب", "الفرع", "فَرع", "المسألة", "مسألة")):
                    leaf_discovered[int(match.group(1))] = href
        selected = leaf_discovered or discovered
        return [selected[key] for key in sorted(selected)]

    async def discover_content_sequence(self, start_url: str, limit: int) -> list[str]:
        """Follow the site's visible next-page relation and keep content pages."""
        current = start_url
        seen: set[str] = set()
        content_urls: list[str] = []
        async with httpx.AsyncClient() as client:
            while current and current not in seen and len(content_urls) < limit:
                seen.add(current)
                html = await self.fetch(client, current)
                soup = BeautifulSoup(html, "html.parser")
                if any(node.select_one("h1") and node.select_one(".w-100.mt-4") for node in soup.select(".amiri_custom_content")):
                    content_urls.append(current)
                next_anchor = next((a for a in soup.find_all("a", href=True) if "التالي" in a.get_text(" ", strip=True)), None)
                if next_anchor is None:
                    break
                candidate = urljoin(current, str(next_anchor.get("href"))).split("?")[0].split("#")[0].rstrip("/")
                current = candidate if DORAR_URL_RE.match(candidate) else ""
        return content_urls

    async def fetch_documents(self, urls: list[str]) -> dict[str, Path]:
        cached: dict[str, Path] = {}
        async with httpx.AsyncClient() as client:
            for url in urls:
                await self.fetch(client, url)
                cached[url] = self.cache_path(url.split("?")[0].split("#")[0].rstrip("/"))
        return cached
