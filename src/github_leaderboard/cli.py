"""CLI entry point for github-leaderboard."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .auth import load_token
from .config import AppConfig, LookbackWindow, MetricWeights, load_weights, validate_config


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "level": record.levelname,
                "message": record.getMessage(),
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            }
        )


def _setup_logging(log_level: str, log_format: str) -> None:
    level = getattr(logging, log_level.upper(), logging.WARNING)
    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s:%(lineno)d: %(message)s"))

    # Mirror ERROR+ to stderr as well
    err_handler = logging.StreamHandler(sys.stderr)
    err_handler.setLevel(logging.ERROR)
    if log_format == "json":
        err_handler.setFormatter(_JsonFormatter())
    else:
        err_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    root.addHandler(err_handler)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-leaderboard",
        description="Rank GitHub repositories by topic or curated list using weighted metrics.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "-t", "--topic",
        metavar="TOPIC",
        help="GitHub topic string",
        )
    mode.add_argument(
        "-l", "--list",
        dest="target_list",
        metavar="FILE",
        type=Path,
        help="Path to .txt file; one owner/repo per line",
        )
    parser.add_argument(
        "-c", "--config",
        metavar="FILE",
        type=Path,
        default=Path("./git-leaderboard.yml"),
        help="YAML config file (default: ./git-leaderboard.yml)",
        )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        type=Path,
        default=Path("./leaderboard.csv"),
        help="Output CSV path (default: ./leaderboard.csv)",
        )
    parser.add_argument(
        "-n", "--top",
        type=int,
        default=10,
        metavar="N",
        help="Number of repos to rank (1-50, default: 10)",
        )
    parser.add_argument(
        "-w", "--window",
        type=int, default=7,
        metavar="DAYS",
        help="Lookback window in days (1-14, default: 7)",
        )
    parser.add_argument(
        "-f", "--log-format",
        choices=["human", "json"],
        default="human",
        help="Log output format (default: human)",
        )
    parser.add_argument(
        "-v", "--log-level",
        default="WARNING",
        help="Log level (default: WARNING)",
        )
    return parser


def parse_target_list(path: Path) -> list[str]:
    """Parse owner/repo entries from a text file, skipping comments and blank lines.

    Accepts either 'owner/repo' or full GitHub URLs like 'https://github.com/owner/repo'.
    """
    import re
    slug_pattern = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")
    github_url_pattern = re.compile(
        r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+?)(?:\.git|/.*)?$"
    )
    seen: set[str] = set()
    repos: list[str] = []
    logger = logging.getLogger(__name__)

    lines = path.read_text(encoding="utf-8").splitlines()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # Normalise GitHub URLs to owner/repo
        url_match = github_url_pattern.match(line)
        if url_match:
            line = url_match.group(1)

        if not slug_pattern.match(line):
            logger.warning("Malformed entry in list file, skipping: %r", raw.strip())
            continue
        if line in seen:
            logger.warning("Duplicate entry in list file, skipping: %r", line)
            continue
        seen.add(line)
        repos.append(line)

    return repos


def main(args: list[str] | None = None) -> None:
    parser = _build_parser()
    ns = parser.parse_args(args)

    # Validate mutual exclusion manually (argparse handles it but we need custom messages)
    if ns.topic is None and ns.target_list is None:
        print("Error: Exactly one of --topic or --list must be provided.", file=sys.stderr)
        sys.exit(1)

    _setup_logging(ns.log_level, ns.log_format)

    # Load weights (uses default config file if it doesn't exist, defaults all to 0.0)
    if ns.config.exists():
        weights = load_weights(ns.config)
    else:
        weights = MetricWeights()

    token = load_token()

    config = AppConfig(
        topic=ns.topic,
        target_list=ns.target_list,
        config_file=ns.config,
        output=ns.output,
        top_n=ns.top,
        window=LookbackWindow(days=ns.window),
        log_format=ns.log_format,
        log_level=ns.log_level.upper(),
        weights=weights,
        token=token,
    )

    validate_config(config)

    # Defer import to avoid circular at module level
    from .runner import run

    run(config)


if __name__ == "__main__":
    main()
