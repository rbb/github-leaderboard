"""CSV output with fixed column order."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from .scorer import LeaderboardEntry

COLUMNS = ["repo", "stars", "commits", "prs_active", "prs_merged", "trend", "score"]


def _entry_to_row(entry: LeaderboardEntry) -> dict:
    return {
        "repo": entry.repo,
        "stars": "" if entry.stars is None else entry.stars,
        "commits": "" if entry.commits is None else entry.commits,
        "prs_active": "" if entry.prs_active is None else entry.prs_active,
        "prs_merged": "" if entry.prs_merged is None else entry.prs_merged,
        "trend": "" if entry.trend is None else entry.trend,
        "score": entry.score,
    }


def write_csv(entries: list[LeaderboardEntry], output: Path) -> None:
    """Write leaderboard entries to a CSV file atomically."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for entry in entries:
        writer.writerow(_entry_to_row(entry))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(buf.getvalue(), encoding="utf-8")
