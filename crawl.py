from __future__ import annotations

from urllib.parse import urlparse
from bs4 import BeautifulSoup


def normalize_url(url: str) -> str:
    """
    Normalize a URL so different forms of the "same page" compare equal.

    Rules:
    - Scheme removed (http/https)
    - Hostname lowercased
    - Default ports removed (:80 for http, :443 for https)
    - Fragment removed (#...)
    - Trailing slashes removed from path
    - Query preserved (if present)

    Intended for comparisons, not for making requests.
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


def get_h1_from_html(html: str) -> str:
    """
    Return the text content of the first <h1> tag in the given HTML.
    Returns "" if no <h1> exists.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    h1 = soup.find("h1")
    if h1 is None:
        return ""
    return h1.get_text(" ", strip=True)


def get_first_paragraph_from_html(html: str) -> str:
    """
    Return the text content of the first <p> tag.
    If a <main> tag exists, prefer the first <p> within <main>.
    Returns "" if no <p> exists.
    """
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
