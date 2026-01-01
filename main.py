from __future__ import annotations

import asyncio
import sys

from crawl import crawl_site_async
from csv_report import write_csv_report

DEFAULT_MAX_CONCURRENCY = 3
DEFAULT_MAX_PAGES = 10


def parse_args(argv: list[str]) -> tuple[str, int, int]:
    if len(argv) < 2:
        print("no website provided")
        raise SystemExit(1)

    # allow either: main.py URL  OR  main.py URL max_concurrency max_pages
    if len(argv) not in (2, 4):
        print("too many arguments provided")
        raise SystemExit(1)

    base_url = argv[1]

    if len(argv) == 2:
        return base_url, DEFAULT_MAX_CONCURRENCY, DEFAULT_MAX_PAGES

    try:
        max_concurrency = int(argv[2])
        max_pages = int(argv[3])
    except ValueError:
        print("max_concurrency and max_pages must be integers")
        raise SystemExit(1)

    if max_concurrency < 1 or max_pages < 1:
        print("max_concurrency and max_pages must be >= 1")
        raise SystemExit(1)

    return base_url, max_concurrency, max_pages


async def main_async(base_url: str, max_concurrency: int, max_pages: int) -> int:
    print(f"starting crawl of: {base_url}")

    page_data = await crawl_site_async(
        base_url,
        max_concurrency=max_concurrency,
        max_pages=max_pages,
    )

    write_csv_report(page_data, filename="report.csv")
    print(f"wrote report.csv with {len(page_data)} pages")
    return 0


if __name__ == "__main__":
    base_url, max_concurrency, max_pages = parse_args(sys.argv)
    raise SystemExit(asyncio.run(main_async(base_url, max_concurrency, max_pages)))
