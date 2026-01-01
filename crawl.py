from __future__ import annotations

from urllib.parse import urljoin, urlparse
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
    """
    Extract structured information from a page's HTML.

    Returns a dict with keys:
    - url
    - h1
    - first_paragraph
    - outgoing_links
    - image_urls
    """
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
