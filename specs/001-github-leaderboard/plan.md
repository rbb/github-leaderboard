# Implementation Plan: GitHub Topic Leaderboard Generator

**Branch**: `001-github-leaderboard` | **Date**: 2026-04-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-github-leaderboard/spec.md`

## Summary

A Python 3.12 CLI tool that queries GitHub repositories (by topic or explicit list), collects
six time-windowed metrics via the `ghapi` library, applies user-configured YAML weights to
compute a weighted score, and writes a ranked CSV. Rate-limit handling, graceful 403 fallback
for clone traffic, and startup config validation are core resilience requirements.

## Technical Context

**Language/Version**: Python 3.12 (spec FR-016; constitution says 3.9+, spec overrides)
**Primary Dependencies**: `ghapi` (GitHub API client), `PyYAML` (config parsing), stdlib
`csv`/`argparse`/`logging` (no third-party CLI or CSV framework needed)
**Storage**: Single CSV output file; no database
**Testing**: `pytest` + `unittest.mock` for error/edge paths; `pytest-recording` (VCR
cassettes) for happy-path API integration tests
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows); primary target is
Linux/macOS for scripting and Docker use
**Project Type**: CLI tool / console script
**Performance Goals**: Top-10 topic run completes within 5 minutes on standard internet
(SC-001); no SLA for larger `--top` values due to Search API rate limit (30 req/min)
**Constraints**: Search API (30 req/min) is the binding throughput ceiling at ~2 calls/repo
for PR metrics; 14-day window cap driven by GitHub Traffic API clone data limit
**Scale/Scope**: Single-user / small-team local execution; no web interface or concurrency
required for MVP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CLI-First Design | ✅ PASS | `argparse` for all inputs; no interactive prompts; stdout for logs, stderr for errors; CSV file output |
| II. Configuration-Driven Scoring | ✅ PASS | YAML-only config with `weights:` block; validated at startup before any API calls |
| III. Resilient API Access | ✅ PASS | Manual exponential backoff (5 retries, 1s→16s); 403 on clone-traffic → zero substitution; token scope surfaced in warning |
| IV. Test-First Development | ✅ PASS | TDD enforced; unit tests for scorer/config/fetcher; VCR cassettes for API paths |
| V. Simplicity & Minimal Dependencies | ✅ PASS | `ghapi` + `PyYAML` + stdlib only; no pandas (stdlib `csv` is sufficient for 8 fixed columns) |

**Post-design re-check**: See Phase 1 section below — no new violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-github-leaderboard/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli.md
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
src/
└── github_leaderboard/
    ├── __init__.py
    ├── cli.py           # argparse setup; main() entry point; accepts args=None for testability
    ├── auth.py          # Token loading: .git_token file → GITHUB_TOKEN env var
    ├── config.py        # YAML config loading, schema validation, MetricWeights dataclass
    ├── client.py        # GhApi wrapper: exponential backoff decorator, Search/REST rate-limit detection
    ├── fetcher.py       # Per-repo metric collection (stars, commits, PRs, trend, clones)
    ├── scorer.py        # Weighted score calculation; tie-breaking sort
    └── writer.py        # CSV output with column ordering and score rounding

tests/
├── unit/
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_scorer.py
│   └── test_fetcher.py
├── integration/
│   ├── cassettes/       # VCR recorded HTTP cassettes
│   └── test_client.py
└── conftest.py

pyproject.toml
README.md
git-leaderboard.yml      # Example config (committed; user copies and edits)
.gitignore               # Includes: leaderboard.csv, .git_token, *.csv
```

**Structure Decision**: Single-project layout under `src/` (Python packaging best practice
for installable packages; prevents import-without-install bugs). No monorepo or multi-package
split needed for a single CLI tool.

## Complexity Tracking

> No Constitution Check violations requiring justification.

---

## Phase 1: Design & Contracts

*See generated artifacts: `research.md`, `data-model.md`, `contracts/cli.md`, `quickstart.md`*

**Post-design Constitution Check**: All five principles still satisfied. The backward
stargazer pagination strategy (see `research.md`) adds one extra API call type per repo but
stays within the "sequential API calls acceptable for MVP" allowance (Constitution §Technical
Stack). No new dependencies introduced.
