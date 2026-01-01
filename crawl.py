from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup


def normalize_url(url: str) -> str:
    if not isinstance(url, str):
        raise TypeError("url must be a string")

    raw = url.strip()
    if not raw:
        raise ValueError("url must be a non-empty string")

    parsed = urlparse(raw)

    # Handle schemeless URLs like "example.com/path"
    if not parsed.netloc and parsed.path and "://" not in raw and not raw.startswith("//"):
        parsed = urlparse("http://" + raw)

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"absolute URL required (missing hostname): {url!r}")

    scheme = (parsed.scheme or "").lower()
    hostname = hostname.lower()

    port = parsed.port
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    port_str = "" if (port is None or default_port) else f":{port}"

    host_needs_brackets = ":" in hostname and not hostname.startswith("[") and not hostname.endswith("]")
    host = f"[{hostname}]" if host_needs_brackets else hostname

    path = (parsed.path or "").rstrip("/")
    if path and not path.startswith("/"):
        path = "/" + path

    normalized = f"{host}{port_str}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def get_urls_from_html(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        urls.append(urljoin(base_url, href))
    return urls


def get_images_from_html(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        urls.append(urljoin(base_url, src))
    return urls


def get_h1_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if not h1:
        return ""
    return " ".join(h1.stripped_strings)


def get_first_paragraph_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    main = soup.find("main")
    if main:
        p = main.find("p")
        if p:
            return " ".join(p.stripped_strings)

    p = soup.find("p")
    if not p:
        return ""
    return " ".join(p.stripped_strings)


def extract_page_data(html: str, page_url: str) -> dict[str, Any]:
    return {
        "url": page_url,
        "h1": get_h1_from_html(html),
        "first_paragraph": get_first_paragraph_from_html(html),
        "outgoing_links": get_urls_from_html(html, page_url),
        "image_urls": get_images_from_html(html, page_url),
    }


class AsyncCrawler:
    def __init__(self, base_url: str, max_concurrency: int = 3, max_pages: int = 10):
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if not isinstance(max_concurrency, int) or max_concurrency < 1:
            raise ValueError("max_concurrency must be an int >= 1")
        if not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError("max_pages must be an int >= 1")

        parsed = urlparse(base_url)
        if not parsed.hostname:
            raise ValueError(f"base_url must be absolute and include a hostname: {base_url!r}")

        self.base_url = base_url
        self.base_domain = parsed.hostname.lower()

        self.max_concurrency = max_concurrency
        self.max_pages = max_pages

        self.should_stop = False
        self.all_tasks: set[asyncio.Task[None]] = set()

        self.page_data: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(max_concurrency)

        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "AsyncCrawler":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session is not None:
            await self.session.close()

    def _is_same_domain(self, url: str) -> bool:
        host = urlparse(url).hostname
        return bool(host) and host.lower() == self.base_domain

    async def add_page_visit(self, normalized_url: str) -> bool:
        """
        Return True if this is the first time we see normalized_url, else False.
        Also enforces max_pages and coordinates cancelling all running tasks.
        """
        async with self.lock:
            if self.should_stop:
                return False

            if normalized_url in self.page_data:
                return False

            if len(self.page_data) >= self.max_pages:
                self.should_stop = True
                print("Reached maximum number of pages to crawl.")
                for task in list(self.all_tasks):
                    task.cancel()
                return False

            # Reserve slot immediately to prevent duplicates
            self.page_data[normalized_url] = {
                "url": "",
                "h1": "",
                "first_paragraph": "",
                "outgoing_links": [],
                "image_urls": [],
            }
            return True

    async def get_html(self, url: str) -> str:
        if self.session is None:
            raise RuntimeError("session not initialized; use AsyncCrawler in an 'async with' block")

        headers = {"User-Agent": "BootCrawler/1.0"}
        timeout = aiohttp.ClientTimeout(total=10)

        async with self.session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"error fetching {url}: status {resp.status}")

            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                raise RuntimeError(
                    f"error fetching {url}: expected text/html content-type, got {content_type!r}"
                )

            return await resp.text()

    async def _run_task(self, url: str) -> None:
        task = asyncio.current_task()
        if task is not None:
            self.all_tasks.add(task)
        try:
            await self.crawl_page(url)
        finally:
            if task is not None:
                self.all_tasks.discard(task)

    async def crawl_page(self, url: str) -> None:
        if self.should_stop:
            return

        if not self._is_same_domain(url):
            return

        try:
            normalized = normalize_url(url)
        except Exception:
            return

        is_new = await self.add_page_visit(normalized)
        if not is_new:
            return

        # Print once per crawl attempt
        print(f"crawling: {url}")

        # Keep the real URL in the reserved entry
        async with self.lock:
            self.page_data[normalized]["url"] = url

        try:
            async with self.semaphore:
                html = await self.get_html(url)
        except asyncio.CancelledError:
            return
        except Exception:
            return

        data = extract_page_data(html, url)
        async with self.lock:
            self.page_data[normalized] = data

        # Spawn child tasks and track them
        tasks: list[asyncio.Task[None]] = []
        for link in data.get("outgoing_links", []):
            if self.should_stop:
                break
            if not self._is_same_domain(link):
                continue
            t = asyncio.create_task(self._run_task(link))
            tasks.append(t)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def crawl(self) -> dict[str, dict[str, Any]]:
        root = asyncio.create_task(self._run_task(self.base_url))
        await asyncio.gather(root, return_exceptions=True)

        # Ensure cancelled/remaining tasks get a chance to finish their cleanup
        while True:
            remaining = [t for t in self.all_tasks if not t.done()]
            if not remaining:
                break
            await asyncio.gather(*remaining, return_exceptions=True)

        return dict(self.page_data)


async def crawl_site_async(base_url: str, max_concurrency: int, max_pages: int) -> dict[str, dict[str, Any]]:
    async with AsyncCrawler(base_url, max_concurrency=max_concurrency, max_pages=max_pages) as crawler:
        return await crawler.crawl()
