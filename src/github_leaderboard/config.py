"""AppConfig and MetricWeights dataclasses with YAML config loading and validation."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import yaml

VALID_WEIGHT_KEYS = frozenset({"stars", "commits", "prs_active", "prs_merged", "trend"})


@dataclass
class MetricWeights:
    stars: float = 0.0
    commits: float = 0.0
    prs_active: float = 0.0
    prs_merged: float = 0.0
    trend: float = 0.0


@dataclass
class LookbackWindow:
    days: int
    since: datetime = field(init=False)

    def __post_init__(self) -> None:
        self.since = datetime.now(timezone.utc) - timedelta(days=self.days)


@dataclass
class AppConfig:
    topic: str | None
    target_list: Path | None
    config_file: Path
    output: Path
    top_n: int
    window: LookbackWindow
    log_format: Literal["human", "json"]
    log_level: str
    weights: MetricWeights
    token: str


def load_weights(config_file: Path) -> MetricWeights:
    """Load and validate MetricWeights from a YAML config file."""
    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with config_file.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Error: Config file is not valid YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, dict) or "weights" not in data:
        print("Error: Config validation failed — missing required 'weights:' key.", file=sys.stderr)
        sys.exit(1)

    raw_weights = data["weights"]
    if not isinstance(raw_weights, dict):
        print("Error: Config validation failed — 'weights' must be a mapping.", file=sys.stderr)
        sys.exit(1)

    # Check for unknown keys
    for key in raw_weights:
        if key not in VALID_WEIGHT_KEYS:
            print(
                f"Error: Config validation failed — unrecognised key in weights: '{key}'",
                file=sys.stderr,
            )
            sys.exit(1)

    weights = MetricWeights()
    for key in VALID_WEIGHT_KEYS:
        if key not in raw_weights:
            print(f"Notice: Weight '{key}' not specified; defaulting to 0.0")
            continue
        val = raw_weights[key]
        if not isinstance(val, (int, float)):
            print(
                f"Error: Config validation failed — weight '{key}' must be numeric, got {val!r}",
                file=sys.stderr,
            )
            sys.exit(1)
        if not (-1.0 <= float(val) <= 1.0):
            print(
                f"Error: Config validation failed — weight '{key}' = {val} is outside [-1.0, 1.0]",
                file=sys.stderr,
            )
            sys.exit(1)
        setattr(weights, key, float(val))

    return weights


def validate_config(config: AppConfig) -> None:
    """Validate AppConfig fields; exit(1) on any violation."""
    if (config.topic is None) == (config.target_list is None):
        print(
            "Error: Exactly one of --topic or --list must be provided.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not (1 <= config.top_n <= 50):
        print(
            f"Error: --top must be between 1 and 50 inclusive, got {config.top_n}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not (1 <= config.window.days <= 14):
        print(
            f"Error: --window must be between 1 and 14 inclusive, got {config.window.days}",
            file=sys.stderr,
        )
        sys.exit(1)

    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if config.log_level.upper() not in valid_levels:
        print(
            f"Error: Invalid --log-level '{config.log_level}'. "
            f"Must be one of: {', '.join(sorted(valid_levels))}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        config.output.parent.mkdir(parents=True, exist_ok=True)
        config.output.touch(exist_ok=True)
    except OSError as exc:
        print(f"Error: Output path is not writable: {exc}", file=sys.stderr)
        sys.exit(1)
    # Remove the test file we just created if it didn't exist before
    if config.output.stat().st_size == 0:
        config.output.unlink(missing_ok=True)
