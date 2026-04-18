#!/usr/bin/env python3
"""Convert a leaderboard CSV to a styled HTML file.

Usage:
    python csv_html.py leaderboard.csv
    python csv_html.py leaderboard.csv -o report.html
    python csv_html.py leaderboard.csv --title "My Leaderboard"
"""

from __future__ import annotations

import argparse
from argparse import ArgumentDefaultsHelpFormatter
import csv
import html
from datetime import datetime, timezone
from pathlib import Path


def convert(src: Path, dst: Path, title: str) -> None:
    rows = list(csv.DictReader(src.read_text(encoding="utf-8").splitlines()))
    if not rows:
        dst.write_text("<p>No data.</p>", encoding="utf-8")
        return

    columns = list(rows[0].keys())
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    BAR_COLS = {"score", "trend", "commits"}

    def _top(col: str) -> float:
        try:
            return max((float(r[col]) for r in rows if r.get(col)), default=0.0)
        except ValueError:
            return 0.0

    col_max = {col: _top(col) for col in BAR_COLS if col in columns}

    def cell(col: str, val: str, rank: int) -> str:
        v = html.escape(val)
        if col == "repo":
            return f"<td class='repo'><a href='https://github.com/{v}' target='_blank' rel='noopener'>{v}</a></td>"
        if col in col_max and col_max[col]:
            try:
                pct = float(val) / col_max[col] * 100
                return (
                    f"<td class='{col}'>"
                    f"<div class='bar-wrap'>"
                    f"<div class='bar' style='width:{pct:.1f}%'></div>"
                    f"<span>{v}</span>"
                    f"</div></td>"
                )
            except ValueError:
                pass
        return f"<td>{v}</td>"

    header_html = "<th>#</th>" + "".join(f"<th>{html.escape(c)}</th>" for c in columns)

    body_rows = []
    for i, row in enumerate(rows, start=1):
        cells = f"<td class='rank'>{i}</td>" + "".join(cell(c, row.get(c, ""), i) for c in columns)
        body_rows.append(f"<tr>{cells}</tr>")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;padding:2rem}}
  h1{{font-size:1.5rem;margin-bottom:.4rem;color:#58a6ff}}
  .meta{{font-size:.8rem;color:#8b949e;margin-bottom:1.5rem}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  th{{background:#161b22;color:#8b949e;text-align:left;padding:.5rem .75rem;
      border-bottom:1px solid #30363d;font-weight:600;white-space:nowrap}}
  td{{padding:.45rem .75rem;border-bottom:1px solid #21262d;vertical-align:middle}}
  tr:hover td{{background:#161b22}}
  td.rank{{color:#8b949e;width:2.5rem;text-align:right}}
  td.repo a{{color:#58a6ff;text-decoration:none}}
  td.repo a:hover{{text-decoration:underline}}
  td.score,td.trend,td.commits{{min-width:160px}}
  .bar-wrap{{display:flex;align-items:center;gap:.5rem}}
  .bar{{height:8px;background:#238636;border-radius:4px;min-width:2px}}
  .bar-wrap span{{white-space:nowrap;font-weight:600;color:#3fb950}}
  @media(max-width:700px){{td.score .bar,td.trend .bar,td.commits .bar{{display:none}}}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">Generated {generated} &middot; {len(rows)} repositories</p>
<table>
<thead><tr>{header_html}</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
</body>
</html>
"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(page, encoding="utf-8")
    print(f"Wrote {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a leaderboard CSV to HTML.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input",
        default='leaderboard.csv',
        type=Path, help="Input CSV file",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default='leaderboard.html',
        help="Output HTML file (default: <input>.html)",
        )
    parser.add_argument("--title", default="GitHub Leaderboard", help="Page title")
    ns = parser.parse_args()

    src: Path = ns.input
    dst: Path = ns.output

    if not src.exists():
        parser.error(f"File not found: {src}")

    convert(src, dst, ns.title)


if __name__ == "__main__":
    main()
