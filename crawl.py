from __future__ import annotations

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def _ensure_absolute_http_url(url: str) -> str:
    """
    Ensure a URL is parseable as an absolute http(s) URL when possible.

    - If already has a scheme, return as-is.
    - If schemeless like "example.com/path", treat as http://example.com/path
    """
    u = url.strip()
    if "://" in u or u.startswith("//"):
        return u
    return "http://" + u


def _get_hostname(url: str) -> str | None:
    parsed = urlparse(_ensure_absolute_http_url(url))
    return parsed.hostname.lower() if parsed.hostname else None


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


def get_h1_from_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    h1 = soup.find("h1")
    if h1 is None:
        return ""
    return h1.get_text(" ", strip=True)


def get_first_paragraph_from_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    main = soup.find("main")
    if main is not None:
        p = main.find("p")
        if p is not None:
            return p.get_text(" ", strip=True)

    p = soup.find("p")
    if p is None:
        return ""
    return p.get_text(" ", strip=True)


def get_urls_from_html(html: str, base_url: str) -> list[str]:
    if not isinstance(html, str):
        raise TypeError("html must be a string")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be a non-empty string")

    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        urls.append(urljoin(base_url, href))

    return urls


def get_images_from_html(html: str, base_url: str) -> list[str]:
    if not isinstance(html, str):
        raise TypeError("html must be a string")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be a non-empty string")

    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        urls.append(urljoin(base_url, src))

    return urls


def extract_page_data(html: str, page_url: str) -> dict:
    if not isinstance(html, str):
        raise TypeError("html must be a string")
    if not isinstance(page_url, str) or not page_url.strip():
        raise ValueError("page_url must be a non-empty string")

    return {
        "url": page_url,
        "h1": get_h1_from_html(html),
        "first_paragraph": get_first_paragraph_from_html(html),
        "outgoing_links": get_urls_from_html(html, page_url),
        "image_urls": get_images_from_html(html, page_url),
    }


def get_html(url: str) -> str:
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    if not url.strip():
        raise ValueError("url must be a non-empty string")

    headers = {"User-Agent": "BootCrawler/1.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    mime_type = content_type.split(";", 1)[0].strip().lower()
    if mime_type != "text/html":
        raise ValueError(f"expected text/html content-type, got {content_type!r}")

    return resp.text


def crawl_page(base_url: str, current_url: str | None = None, page_data: dict | None = None) -> dict:
    """
    Recursively crawl pages starting from base_url and return page_data.

    page_data is keyed by normalized URL to avoid crawling the same page twice.
    Only URLs on the same hostname as base_url are crawled.
    """
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be a non-empty string")

    if current_url is None:
        current_url = base_url

    if page_data is None:
        page_data = {}

    # Skip non-http(s) schemes (mailto:, javascript:, etc.)
    parsed_current = urlparse(_ensure_absolute_http_url(current_url))
    if parsed_current.scheme and parsed_current.scheme not in ("http", "https"):
        return page_data

    base_host = _get_hostname(base_url)
    current_host = parsed_current.hostname.lower() if parsed_current.hostname else None
    if base_host is None or current_host is None:
        return page_data

    # Same-domain guard
    if current_host != base_host:
        return page_data

    # De-dupe by normalized URL
    try:
        normalized = normalize_url(current_url)
    except Exception:
        return page_data

    if normalized in page_data:
        return page_data

    print(f"crawling: {current_url}")

    try:
        html = get_html(current_url)
    except Exception as e:
        print(f"error fetching {current_url}: {e}")
        return page_data

    page_data[normalized] = extract_page_data(html, current_url)

    # Crawl outgoing links
    for url in get_urls_from_html(html, current_url):
        crawl_page(base_url, url, page_data)

    return page_data
