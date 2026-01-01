from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _q(s: str) -> str:
    # Quote for DOT
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_dot_report(
    page_data: dict[str, dict[str, Any]],
    base_url: str,
    filename: str = "site.dot",
    internal_only: bool = True,
) -> None:
    """
    Write a Graphviz DOT directed graph of page link relationships.
    By default, includes only links within base_url's domain.
    """
    base_host = urlparse(base_url).hostname
    base_domain = base_host.lower() if base_host else ""

    with open(filename, "w", encoding="utf-8") as f:
        f.write("digraph site {\n")
        f.write("  rankdir=LR;\n")

        for page in page_data.values():
            src = page.get("url") or ""
            if not src:
                continue

            for dst in page.get("outgoing_links", []) or []:
                if internal_only and base_domain:
                    host = urlparse(dst).hostname
                    if not host or host.lower() != base_domain:
                        continue
                f.write(f"  {_q(src)} -> {_q(dst)};\n")

        f.write("}\n")
