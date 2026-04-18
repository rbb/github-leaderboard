"""Per-repo metric collection: stars, commits, PRs, trend."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from ghapi.all import GhApi, paged

from .client import retry_with_backoff
from .config import LookbackWindow
from .scorer import RepoMetrics

logger = logging.getLogger(__name__)

_TREND_PAGE_CAP = 5
_STARS_PER_PAGE = 100


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.rstrip("Z")).replace(tzinfo=timezone.utc)


@retry_with_backoff
def _search_topic_repos(api: GhApi, topic: str, top_n: int) -> list[str]:
    """Return list of 'owner/repo' strings for the given topic, up to top_n."""
    results: list[str] = []
    per_page = min(top_n, 100)
    page = 1
    while len(results) < top_n:
        resp = api.search.repos(
            q=f"topic:{topic}",
            sort="stars",
            order="desc",
            per_page=per_page,
            page=page,
        )
        items = resp["items"] or []
        for item in items:
            results.append(item.full_name)
            if len(results) >= top_n:
                break
        if len(items) < per_page:
            break
        page += 1
    return results[:top_n]


def _fetch_commits(api: GhApi, owner: str, repo: str, since: datetime) -> int | None:
    try:
        count = 0
        for page in paged(
            api.repos.list_commits,
            owner=owner,
            repo=repo,
            since=_iso(since),
            per_page=100,
        ):
            logger.debug("commits page (%d so far) %s/%s since=%s", count + len(page), owner, repo, _iso(since))
            count += len(page)
        return count
    except Exception as exc:
        logger.warning("Failed to fetch commits for %s/%s: %s", owner, repo, exc)
        return None


def _fetch_prs(api: GhApi, owner: str, repo: str, since: datetime) -> tuple[int | None, int | None]:
    """Return (active_count, merged_count) for PRs within the window."""
    try:
        active = 0
        for page in paged(api.pulls.list, owner=owner, repo=repo, state="open", per_page=100):
            logger.debug("prs open page (%d so far) %s/%s", active + len(page), owner, repo)
            early_stop = False
            for pr in page:
                created = _parse_dt(pr.created_at)
                if created >= since:
                    active += 1
                else:
                    early_stop = True
                    break
            if early_stop:
                break
    except Exception as exc:
        logger.warning("Failed to fetch open PRs for %s/%s: %s", owner, repo, exc)
        active = None

    try:
        merged = 0
        for page in paged(api.pulls.list, owner=owner, repo=repo, state="closed", per_page=100):
            logger.debug("prs closed page (%d so far) %s/%s", merged + len(page), owner, repo)
            early_stop = False
            for pr in page:
                # merged_at is an empty AttrDict (not None) for unmerged closed PRs
                merged_at_val = getattr(pr, "merged_at", None)
                if not isinstance(merged_at_val, str) or not merged_at_val:
                    continue
                merged_at = _parse_dt(merged_at_val)
                if merged_at >= since:
                    merged += 1
                else:
                    early_stop = True
                    break
            if early_stop:
                break
    except Exception as exc:
        logger.warning("Failed to fetch closed PRs for %s/%s: %s", owner, repo, exc)
        merged = None

    return active, merged


def _fetch_trend(api: GhApi, owner: str, repo: str, since: datetime, total_stars: int) -> float | None:
    """Compute trend = stars_gained_in_window (capped at 5 pages)."""
    if total_stars == 0:
        return 0.0
    try:
        last_page = max(1, math.ceil(total_stars / _STARS_PER_PAGE))
        start_page = max(1, last_page - _TREND_PAGE_CAP + 1)

        gained = 0
        for p in range(last_page, start_page - 1, -1):
            try:
                logger.debug("stars page %d/%d %s/%s", p, last_page, owner, repo)
                resp = api.activity.list_stargazers_for_repo(
                    owner=owner,
                    repo=repo,
                    per_page=_STARS_PER_PAGE,
                    page=p,
                    headers={"Accept": "application/vnd.github.star+json"},
                )
            except Exception as page_exc:
                code = getattr(page_exc, "status", None) or getattr(page_exc, "code", None)
                if str(code) == "422" or "422" in str(page_exc):
                    # Pagination limit hit; try an earlier page
                    last_page = max(1, p - 1)
                    continue
                raise
            if not resp:
                break
            all_before = True
            for star in resp:
                starred_at_str = (
                    star.get("starred_at") if isinstance(star, dict)
                    else getattr(star, "starred_at", None)
                )
                if isinstance(starred_at_str, str) and starred_at_str:
                    starred_at = _parse_dt(starred_at_str)
                    if starred_at >= since:
                        gained += 1
                        all_before = False
            if all_before:
                break

        return float(gained)
    except Exception as exc:
        logger.warning("Failed to fetch stargazer trend for %s/%s: %s", owner, repo, exc)
        return None



def fetch_metrics(
    api: GhApi,
    full_name: str,
    window: LookbackWindow,
    index: int,
    total: int,
) -> RepoMetrics:
    owner, repo = full_name.split("/", 1)
    logger.info("Processing repo %d/%d: %s", index, total, full_name)

    # Get basic repo info (stars)
    try:
        logger.debug("repo info %s", full_name)
        repo_info = api.repos.get(owner=owner, repo=repo)
        stars: int | None = repo_info.stargazers_count
    except Exception as exc:
        logger.warning("Failed to fetch repo info for %s: %s", full_name, exc)
        stars = None

    commits = _fetch_commits(api, owner, repo, window.since)
    prs_active, prs_merged = _fetch_prs(api, owner, repo, window.since)
    trend = _fetch_trend(api, owner, repo, window.since, stars or 0)

    if all(v is None for v in (stars, commits, prs_active, prs_merged, trend)):
        logger.warning("All metric calls failed for %s; will appear with score=0.0", full_name)

    return RepoMetrics(
        full_name=full_name,
        stars=stars,
        commits=commits,
        prs_active=prs_active,
        prs_merged=prs_merged,
        trend=trend,
    )


def fetch_all(
    api: GhApi,
    repos: list[str],
    window: LookbackWindow,
) -> list[RepoMetrics]:
    results: list[RepoMetrics] = []
    total = len(repos)
    for i, full_name in enumerate(repos, start=1):
        results.append(fetch_metrics(api, full_name, window, i, total))
    return results
