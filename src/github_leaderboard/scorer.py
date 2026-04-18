"""Weighted score calculation and tie-breaking sort."""

from __future__ import annotations

from dataclasses import dataclass

from .config import MetricWeights


@dataclass
class RepoMetrics:
    full_name: str
    stars: int | None
    commits: int | None
    prs_active: int | None
    prs_merged: int | None
    trend: float | None


@dataclass
class LeaderboardEntry:
    repo: str
    stars: int | None
    commits: int | None
    prs_active: int | None
    prs_merged: int | None
    trend: float | None
    score: float


def _compute_score(m: RepoMetrics, w: MetricWeights) -> float:
    return round(
        w.stars * (m.stars or 0)
        + w.commits * (m.commits or 0)
        + w.prs_active * (m.prs_active or 0)
        + w.prs_merged * (m.prs_merged or 0)
        + w.trend * (m.trend or 0.0),
        2,
    )


def score_repos(metrics: list[RepoMetrics], weights: MetricWeights) -> list[LeaderboardEntry]:
    entries = [
        LeaderboardEntry(
            repo=m.full_name,
            stars=m.stars,
            commits=m.commits,
            prs_active=m.prs_active,
            prs_merged=m.prs_merged,
            trend=m.trend,
            score=_compute_score(m, weights),
        )
        for m in metrics
    ]
    entries.sort(key=lambda e: (e.score, e.stars or 0), reverse=True)
    return entries
