# Web Crawler (boot.dev)

A small async web crawler that:
- Crawls pages on a single domain
- Respects `robots.txt` (best-effort)
- Avoids re-crawling pages via URL normalization + canonicalization
- Limits concurrency and total pages crawled (`max_concurrency`, `max_pages`)
- Exports results to:
  - `report.csv` (page content + internal/external link stats)
  - `site.dot` (Graphviz DOT graph of internal links)

## Requirements
- Python (managed via `uv`)
- `uv` installed
