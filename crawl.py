from __future__ import annotations

import asyncio
import random
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse, urlunparse, parse_qsl
from urllib.robotparser import RobotFileParser

import aiohttp
from bs4 import BeautifulSoup

USER_AGENT = "BootCrawler/1.0"

SKIP_SCHEMES = {"mailto", "tel", "javascript"}
SKIP_EXTENSIONS = {
    ".pdf", ".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".mp3", ".wav", ".ogg", ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".exe", ".dmg", ".iso",
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
}

RETRYABLE_STATUS = {429, 503}


def canonicalize_url(url: str) -> str:
    """
    Canonicalize a URL to reduce duplicates:
    - Remove fragment (#...)
    - Remove utm_* query parameters
    Preserves all other query params and their order.
    """
    parsed = urlparse(url)
    q = parse_qsl(parsed.query, keep_blank_values=True)
    q = [(k, v) for (k, v) in q if not k.lower().startswith("utm_")]
    new_query = urlencode(q, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))


def is_crawlable_url(url: str) -> bool:
    """
    Return False for schemes we should never crawl (mailto:, tel:, javascript:)
    or non-http(s) schemes.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    if scheme in SKIP_SCHEMES:
        return False
    if scheme and scheme not in ("http", "https"):
        return False
    return True


def has_skipped_extension(url: str) -> bool:
    """
    Return True if the URL path ends with a common non-HTML extension.
    """
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in SKIP_EXTENSIONS)


def normalize_url(url: str) -> str:
    """
    Normalize a URL so different forms of the "same page" compare equal.

    Rules:
    - Scheme removed (http/https)
    - Hostname lowercased
    - Default ports removed (:80 for http, :443 for https)
    - Fragment removed (#...) (already removed by canonicalize_url, but safe)
    - Trailing slashes removed from path
    - Query preserved (after canonicalization)
    """
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

    # Bracket IPv6 literals when reconstructing host:port
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
    outgoing_raw = get_urls_from_html(html, page_url)
    outgoing: list[str] = []
    seen: set[str] = set()

    for u in outgoing_raw:
        u = canonicalize_url(u)
        if u in seen:
            continue
        seen.add(u)
        outgoing.append(u)

    return {
        "url": page_url,
        "h1": get_h1_from_html(html),
        "first_paragraph": get_first_paragraph_from_html(html),
        "outgoing_links": outgoing,
        "image_urls": [canonicalize_url(u) for u in get_images_from_html(html, page_url)],
    }


class AsyncCrawler:
    def __init__(
        self,
        base_url: str,
        max_concurrency: int = 3,
        max_pages: int = 10,
        max_retries: int = 3,
    ):
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if not isinstance(max_concurrency, int) or max_concurrency < 1:
            raise ValueError("max_concurrency must be an int >= 1")
        if not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError("max_pages must be an int >= 1")
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be an int >= 0")

        parsed = urlparse(base_url)
        if not parsed.hostname:
            raise ValueError(f"base_url must be absolute and include a hostname: {base_url!r}")

        self.base_url = canonicalize_url(base_url)
        self.base_domain = parsed.hostname.lower()

        self.max_concurrency = max_concurrency
        self.max_pages = max_pages
        self.max_retries = max_retries

        self.should_stop = False
        self.all_tasks: set[asyncio.Task[None]] = set()

        self.page_data: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(max_concurrency)

        self.session: aiohttp.ClientSession | None = None
        self.robots: RobotFileParser | None = None

    async def __aenter__(self) -> "AsyncCrawler":
        self.session = aiohttp.ClientSession()
        await self._load_robots()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session is not None:
            await self.session.close()

    def _is_same_domain(self, url: str) -> bool:
        host = urlparse(url).hostname
        return bool(host) and host.lower() == self.base_domain

    async def _load_robots(self) -> None:
        """
        Best-effort robots.txt loader. If it fails, we default to allowing crawl.
        """
        if self.session is None:
            return

        robots_url = urljoin(self.base_url, "/robots.txt")
        headers = {"User-Agent": USER_AGENT}
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with self.session.get(robots_url, headers=headers, timeout=timeout) as resp:
                if resp.status >= 400:
                    return
                text = await resp.text()
        except Exception:
            return

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(text.splitlines())
        self.robots = rp

    def _allowed_by_robots(self, url: str) -> bool:
        if self.robots is None:
            return True
        try:
            return self.robots.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    async def add_page_visit(self, normalized_url: str) -> bool:
        """
        Return True if this is the first time we see normalized_url, else False.
        Enforces max_pages and coordinates cancelling all concurrent tasks.
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

    async def _sleep_backoff(self, attempt: int) -> None:
        # exponential backoff with jitter
        base = 0.5 * (2**attempt)
        jitter = random.uniform(0.0, 0.25)
        await asyncio.sleep(base + jitter)

    async def get_html(self, url: str) -> str:
        """
        Fetch a URL and return HTML with retries + backoff for transient failures.
        """
        if self.session is None:
            raise RuntimeError("session not initialized; use AsyncCrawler in an 'async with' block")

        headers = {"User-Agent": USER_AGENT}
        timeout = aiohttp.ClientTimeout(total=10)

        last_err: Exception | None = None

        for attempt in range(self.max_retries + 1):
            if self.should_stop:
                raise asyncio.CancelledError()

            try:
                async with self.semaphore:
                    async with self.session.get(url, headers=headers, timeout=timeout) as resp:
                        status = resp.status

                        if status in RETRYABLE_STATUS:
                            if attempt == self.max_retries:
                                raise RuntimeError(f"retryable status {status} fetching {url}")
                            await resp.release()
                            await self._sleep_backoff(attempt)
                            continue

                        if status >= 400:
                            raise RuntimeError(f"error fetching {url}: status {status}")

                        content_type = resp.headers.get("Content-Type", "")
                        if "text/html" not in content_type.lower():
                            raise RuntimeError(
                                f"error fetching {url}: expected text/html content-type, got {content_type!r}"
                            )

                        return await resp.text()

            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
                last_err = e
                # Retry only transient errors; RuntimeError here might be from retryable status.
                if attempt < self.max_retries:
                    await self._sleep_backoff(attempt)
                    continue
                break

        raise last_err or RuntimeError(f"error fetching {url}")

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

        url = canonicalize_url(url)

        if not is_crawlable_url(url):
            return
        if has_skipped_extension(url):
            return
        if not self._is_same_domain(url):
            return
        if not self._allowed_by_robots(url):
            return

        try:
            normalized = normalize_url(url)
        except Exception:
            return

        is_new = await self.add_page_visit(normalized)
        if not is_new:
            return

        print(f"crawling: {url}")

        async with self.lock:
            self.page_data[normalized]["url"] = url

        try:
            html = await self.get_html(url)
        except asyncio.CancelledError:
            return
        except Exception:
            return

        data = extract_page_data(html, url)

        async with self.lock:
            self.page_data[normalized] = data

        tasks: list[asyncio.Task[None]] = []
        for link in data.get("outgoing_links", []):
            if self.should_stop:
                break
            link = canonicalize_url(link)
            if not is_crawlable_url(link):
                continue
            if has_skipped_extension(link):
                continue
            if not self._is_same_domain(link):
                continue
            t = asyncio.create_task(self._run_task(link))
            tasks.append(t)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def crawl(self) -> dict[str, dict[str, Any]]:
        root = asyncio.create_task(self._run_task(self.base_url))
        await asyncio.gather(root, return_exceptions=True)

        while True:
            remaining = [t for t in self.all_tasks if not t.done()]
            if not remaining:
                break
            await asyncio.gather(*remaining, return_exceptions=True)

        return dict(self.page_data)


async def crawl_site_async(base_url: str, max_concurrency: int, max_pages: int) -> dict[str, dict[str, Any]]:
    async with AsyncCrawler(base_url, max_concurrency=max_concurrency, max_pages=max_pages) as crawler:
        return await crawler.crawl()
