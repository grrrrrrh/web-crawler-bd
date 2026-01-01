from __future__ import annotations

import sys


def main() -> None:
    argv = sys.argv

    if len(argv) < 2:
        print("no website provided")
        sys.exit(1)

    if len(argv) > 2:
        print("too many arguments provided")
        sys.exit(1)

    base_url = argv[1]
    print(f"starting crawl of: {base_url}")


if __name__ == "__main__":
    main()
