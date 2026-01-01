from __future__ import annotations

from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """
    Normalize a URL so different forms of the "same page" compare equal.

    Normalization rules:
    - Scheme is removed (http/https)
    - Hostname is lowercased
    - Default ports are removed (:80 for http, :443 for https)
    - Fragment is removed (#...)
    - Trailing slashes are removed from the path
    - Query string is preserved (if present)

    This normalized URL is intended for comparisons, not for making requests.
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

    path = parsed.path or ""
    # Remove trailing slashes ("/" becomes "")
    path = path.rstrip("/")
    if path and not path.startswith("/"):
        path = "/" + path

    normalized = f"{host}{port_str}{path}"

    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized
