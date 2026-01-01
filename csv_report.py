from __future__ import annotations

import csv
from typing import Any


def write_csv_report(page_data: dict[str, dict[str, Any]], filename: str = "report.csv") -> None:
    """
    Write the crawler's page_data dict to a CSV file.

    Columns:
      - page_url
      - h1
      - first_paragraph
      - outgoing_link_urls (semicolon-separated)
      - image_urls (semicolon-separated)
    """
    fieldnames = ["page_url", "h1", "first_paragraph", "outgoing_link_urls", "image_urls"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for page in page_data.values():
            outgoing_links = page.get("outgoing_links") or []
            image_urls = page.get("image_urls") or []

            writer.writerow(
                {
                    "page_url": page.get("url", ""),
                    "h1": page.get("h1", ""),
                    "first_paragraph": page.get("first_paragraph", ""),
                    "outgoing_link_urls": ";".join(outgoing_links),
                    "image_urls": ";".join(image_urls),
                }
            )
