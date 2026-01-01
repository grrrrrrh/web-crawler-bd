from __future__ import annotations

import sys

from crawl import crawl_page


def main() -> None:
    if len(sys.argv) < 2:
        print("no website provided")
        sys.exit(1)

    if len(sys.argv) > 2:
        print("too many arguments provided")
        sys.exit(1)

    base_url = sys.argv[1]
    print(f"starting crawl of: {base_url}")

    page_data = crawl_page(base_url)

    print(f"found {len(page_data)} pages")
    for data in page_data.values():
        print(data)


if __name__ == "__main__":
    main()
