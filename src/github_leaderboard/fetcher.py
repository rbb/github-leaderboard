"""Per-repo metric collection: stars, commits, PRs, trend."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone

from ghapi.all import GhApi, paged

from .client import retry_with_backoff
from .config import LookbackWindow
from .scorer import RepoMetrics

logger = logging.getLogger(__name__)

_TREND_STARS_PER_PAGE = 100
_TREND_MAX_PAGES = 100  # cap at 10,000 recent stars per repo
_GRAPHQL_URL = "https://api.github.com/graphql"


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


_TREND_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    stargazers(first: 100, orderBy: {field: STARRED_AT, direction: DESC}, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      edges { starredAt }
    }
  }
}
"""


@retry_with_backoff
def _graphql(auth_header: str, variables: dict) -> dict:
    req = urllib.request.Request(
        _GRAPHQL_URL,
        data=json.dumps({"query": _TREND_QUERY, "variables": variables}).encode(),
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _fetch_trend(api: GhApi, owner: str, repo: str, since: datetime, total_stars: int) -> float | None:
    """Count stars gained in the window via GraphQL (newest-first, pagination not capped at 40k)."""
    if total_stars == 0:
        return 0.0
    auth_header = api.headers.get("Authorization", "")
    gained = 0
    cursor: str | None = None
    try:
        for page in range(1, _TREND_MAX_PAGES + 1):
            variables: dict = {"owner": owner, "repo": repo, "cursor": cursor}
            payload = _graphql(auth_header, variables)
            if "errors" in payload:
                logger.warning("GraphQL errors for %s/%s: %s", owner, repo, payload["errors"])
                return None
            sg = payload["data"]["repository"]["stargazers"]
            edges = sg["edges"]
            if not edges:
                break
            for edge in edges:
                starred_at_str = edge.get("starredAt")
                if not isinstance(starred_at_str, str):
                    continue
                if _parse_dt(starred_at_str) < since:
                    return float(gained)
                gained += 1
            if not sg["pageInfo"]["hasNextPage"]:
                break
            cursor = sg["pageInfo"]["endCursor"]
            logger.debug("stargazer trend page %d for %s/%s (gained=%d)", page, owner, repo, gained)
        else:
            logger.info(
                "Trend page cap (%d) reached for %s/%s; reported count is a lower bound",
                _TREND_MAX_PAGES, owner, repo,
            )
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
