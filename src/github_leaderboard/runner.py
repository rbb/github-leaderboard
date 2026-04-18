"""Main execution pipeline: fetch → score → write."""

from __future__ import annotations

import logging
import sys

from .client import RateLimitExhaustedError, make_api
from .config import AppConfig
from .fetcher import _search_topic_repos, fetch_metrics
from .scorer import RepoMetrics, score_repos
from .writer import write_csv

logger = logging.getLogger(__name__)


def run(config: AppConfig) -> None:
    api = make_api(config.token)

    # Determine repo list
    if config.topic:
        try:
            repos = _search_topic_repos(api, config.topic, config.top_n)
        except RateLimitExhaustedError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        if not repos:
            print(f"No repositories found for topic '{config.topic}'.", file=sys.stderr)
            sys.exit(0)
    else:
        from .cli import parse_target_list

        repos = parse_target_list(config.target_list)
        if not repos:
            print("No valid repositories found in list file.", file=sys.stderr)
            sys.exit(0)
        repos = repos[: config.top_n]

    # Fetch metrics per repo; on rate-limit exhaustion write partial CSV and exit 1
    collected: list[RepoMetrics] = []
    total = len(repos)
    rate_limit_error: RateLimitExhaustedError | None = None

    for i, full_name in enumerate(repos, start=1):
        try:
            collected.append(fetch_metrics(api, full_name, config.window, i, total))
        except RateLimitExhaustedError as exc:
            rate_limit_error = exc
            break

    # Score and sort whatever we have
    entries = score_repos(collected, config.weights)

    if entries:
        write_csv(entries, config.output)
        logger.info("Wrote %d entries to %s", len(entries), config.output)

    if rate_limit_error is not None:
        if entries:
            print(
                f"Warning: Rate limit exhausted after {len(entries)} repo(s). "
                f"Partial results written to {config.output}.",
                file=sys.stderr,
            )
        print(f"Error: {rate_limit_error}", file=sys.stderr)
        sys.exit(1)
