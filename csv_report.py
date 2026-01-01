from __future__ import annotations

import csv
from typing import Any
from urllib.parse import urlparse


def write_csv_report(
    page_data: dict[str, dict[str, Any]],
    base_url: str,
    filename: str = "report.csv",
) -> None:
    """
    Write crawler page_data to CSV.

    Includes link stats:
    - internal_links_count
    - external_links_count
    - external_domains (semicolon-separated unique hostnames)
    """
    base_host = urlparse(base_url).hostname
    base_domain = base_host.lower() if base_host else ""

    fieldnames = [
        "page_url",
        "h1",
        "first_paragraph",
        "internal_links_count",
        "external_links_count",
        "external_domains",
        "outgoing_link_urls",
        "image_urls",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for page in page_data.values():
            outgoing_links: list[str] = page.get("outgoing_links") or []
            image_urls: list[str] = page.get("image_urls") or []

            internal = 0
            external = 0
            external_domains: set[str] = set()

            for u in outgoing_links:
                host = urlparse(u).hostname
                if not host:
                    continue
                h = host.lower()
                if base_domain and h == base_domain:
                    internal += 1
                else:
                    external += 1
                    external_domains.add(h)

            writer.writerow(
                {
                    "page_url": page.get("url", ""),
                    "h1": page.get("h1", ""),
                    "first_paragraph": page.get("first_paragraph", ""),
                    "internal_links_count": internal,
                    "external_links_count": external,
                    "external_domains": ";".join(sorted(external_domains)),
                    "outgoing_link_urls": ";".join(outgoing_links),
                    "image_urls": ";".join(image_urls),
                }
            )
