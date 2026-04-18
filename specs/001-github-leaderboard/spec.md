# Feature Specification: GitHub Topic Leaderboard Generator

**Feature Branch**: `001-github-leaderboard`
**Created**: 2026-04-16
**Status**: Draft
**Input**: User description: "Python-based utility that ranks GitHub repositories based on a weighted multi-factor scoring system, outputting the results to a structured CSV file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Topic-Based Leaderboard (Priority: P1)

A user wants to discover the top repositories for a GitHub topic (e.g., "machine-learning")
and receive a ranked CSV file scored by configurable metric weights.

**Why this priority**: This is the primary use case — discovering and ranking repos by topic
is the core value proposition of the tool.

**Independent Test**: Can be fully tested by running the tool with a valid topic name and a
weight config file; the output CSV must contain ranked repositories with scores.

**Acceptance Scenarios**:

1. **Given** a valid GitHub topic string and a weight configuration file, **When** the user runs the tool, **Then** a CSV file is produced listing the top N repositories ranked by their computed scores in descending order.
2. **Given** a valid topic but the clone-traffic endpoint returns a permission error, **When** the tool fetches metrics, **Then** it logs a warning, treats clone count as zero, and still produces a complete ranked CSV.
3. **Given** the GitHub rate limit is hit during metric collection, **When** the tool receives a rate-limit response, **Then** it retries with exponential backoff and completes the run without losing any collected data.

---

### User Story 2 - Target-List Leaderboard (Priority: P2)

A user maintains a curated list of repositories (as `owner/repo` entries in a `.txt` file)
and wants to rank them using the same weighted scoring system.

**Why this priority**: Power users tracking specific repositories need this mode; it adds
significant flexibility without changing the scoring logic.

**Independent Test**: Can be fully tested by providing a `.txt` file with valid repo
identifiers and a weight config; the output CSV must rank exactly those repositories.

**Acceptance Scenarios**:

1. **Given** a `.txt` file containing valid `owner/repo` identifiers (one per line) and a weight config, **When** the user runs the tool, **Then** only those repositories are scored and the output CSV contains exactly the listed repos sorted by score descending, with ties broken by stars descending.
2. **Given** a `.txt` file where one entry is malformed (not `owner/repo` format), **When** the tool parses the file, **Then** it logs a warning for the invalid entry and continues processing the remaining valid entries.
3. **Given** both a topic argument and a target-list file are supplied simultaneously, **When** the tool starts, **Then** it exits with a clear error message explaining that the two input modes are mutually exclusive.

---

### User Story 3 - Configurable Scoring Weights (Priority: P3)

A user wants to adjust which metrics matter most for their context (e.g., prioritize
recent commit activity over historical star count) by editing a configuration file.

**Why this priority**: Without weight customization the tool is a fixed-formula calculator;
configurable weights are what make it general-purpose.

**Independent Test**: Can be fully tested by running two separate invocations with different
weight configs against the same repository set and confirming the ranked order differs.

**Acceptance Scenarios**:

1. **Given** a weight configuration where the commit-activity weight is set to zero, **When** the tool scores repositories, **Then** the commit-activity metric contributes nothing to any repository's score.
2. **Given** a malformed configuration file (invalid syntax), **When** the tool starts, **Then** it exits immediately with a human-readable error describing the problem and the expected format.
3. **Given** a valid configuration that omits an optional metric weight, **When** the tool runs, **Then** the missing weight defaults to zero and a notice is printed to the user.

---

### Edge Cases

- **Zero topic results**: When a topic search returns no repositories, the tool prints a notice to stderr and exits with code 0; no output CSV is written.
- **Deleted or private repository**: When a target-list entry resolves to a deleted or private repository, the tool includes it in the CSV with score = 0 and all metrics marked as unavailable, and logs a warning — consistent with the all-metrics-unavailable behavior.
- **Duplicate target-list entries**: When the same `owner/repo` appears more than once in the target list, the tool deduplicates (scores it once), logs a warning identifying the duplicate entries, and continues.
- **Output not writable**: When the output file path is not writable, the tool exits immediately with a non-zero error code and prints a message to stderr identifying the path and OS error; no partial output is written.
- **All metrics unavailable**: When all metric API calls fail for a single repository, the tool includes it in the CSV with score = 0 and all metric columns marked as unavailable (empty string), and logs a warning.
- **Month boundary**: The lookback window is a UTC timestamp computed at startup; month/year boundaries require no special handling.
- **Zero-star trend**: When a repository has zero total stars, the trend metric is treated as 0 silently (no warning logged); zero stars means no trend signal.
- **Empty target list**: When the target list file contains no valid `owner/repo` entries (all lines blank, malformed, or commented), the tool prints a notice to stderr, exits with code 0, and writes no output CSV — consistent with zero-topic-results behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept either `-t`/`--topic <string>` or `-l`/`--list <file>` as the repository source; both flags MUST be mutually exclusive. Providing both or neither MUST produce a clear error message.
- **FR-002**: The tool MUST read metric weights from a configuration file in YAML format only (JSON is not supported). The config file is optional; if `-c`/`--config <file>` is not provided, the tool looks for `git-leaderboard.yml` in the working directory. If neither exists, the tool exits with a clear error. The file is always parsed as YAML regardless of its extension. The config file MUST contain a `weights:` block with keys matching the CSV column names: `stars`, `commits`, `prs_active`, `prs_merged`, `trend`, `clones`. Example: `weights: {stars: 1.0, commits: 0.5, prs_active: 0.3, prs_merged: 0.4, trend: 0.2, clones: 0.1}`.
- **FR-003**: The tool MUST collect the following metrics for each repository: star count, commit activity (window-day), active pull requests (window-day), merged pull requests (window-day), trending bonus (star velocity: stars gained in last N days ÷ total stars), and clone count (window-day). All time-windowed metrics share a single lookback window set by `-w`/`--window` (default: 7 days), computed once at startup. For clone count specifically, the GitHub Traffic API returns up to 14 daily buckets; the tool MUST sum only the buckets whose date falls within the last `window` days.
- **FR-004**: The tool MUST compute a weighted score per repository using the formula: `Score = (W_star × Stars) + (W_com × Commits) + (W_pra × PR_active) + (W_prm × PR_merged) + (W_trn × Trend) + (W_cln × Clones)`.
- **FR-005**: When the clone-traffic endpoint returns a 403 error, the tool MUST log a warning and substitute a clone count of zero for that repository rather than aborting.
- **FR-006**: The tool MUST handle GitHub API rate limits by retrying with exponential backoff: maximum 5 retries, initial delay 1 second, doubling each attempt (1s → 2s → 4s → 8s → 16s). The REST API (5,000 req/hour) and the Search API (30 req/minute) have separate rate limits; both MUST be handled independently. The tool MUST log a warning when a rate-limit retry is triggered, identifying which limit was hit.
- **FR-007**: The tool MUST output results to a CSV file sorted by score descending; ties are broken by stars descending (applies to both topic mode and list mode). The output path is set via `-o`/`--output <file>` (default: `leaderboard.csv` in the working directory). Column order and names MUST be: `repo, stars, commits, prs_active, prs_merged, trend, clones, score`. The `score` column MUST be rounded to 2 decimal places. If the output file already exists and is writable, the tool MUST print a notice to stdout (e.g., `Overwriting existing file: <path>`) before overwriting it.
- **FR-008**: The tool MUST load the GitHub authentication token by checking, in order: (1) a `.github_token` file in the working directory (plain text, first line used); (2) the `GITHUB_TOKEN` environment variable. If neither is present, the tool MUST exit with code 1 and a message instructing the user to create `.github_token` or set `GITHUB_TOKEN`. The token MUST NOT be accepted as a CLI argument. The `.github_token` file MUST be listed in `.gitignore`.
- **FR-009**: The configuration file MUST be validated at startup; the tool MUST exit with code 1 and a clear error before making any API calls. Validation MUST reject: invalid YAML syntax, missing `weights:` block, unrecognised keys in `weights:` (naming the offending key), non-numeric weight values, and weight values outside the range −1 to 1 inclusive.
- **FR-010**: For topic-based discovery, `-n`/`--top N` (default: 10) controls how many repositories are retrieved and ranked. Valid range is 1–50 inclusive; values outside this range MUST cause the tool to exit with code 1 and a message identifying the valid range before making any API calls. When `--list` mode is used, `--top` is silently ignored; all valid entries in the target list are scored and ranked.
- **FR-011**: All log and warning messages MUST be written to stdout; error-level messages MUST additionally be written to stderr. The tool MUST support a `--log-format` flag accepting `human` (default) or `json`. The tool MUST support a `--log-level` flag accepting `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (case-insensitive; default: `WARNING`); invalid values MUST exit with code 1. Both flags support short forms: `-f`/`--log-format` and `-v`/`--log-level`. The tool MUST emit INFO-level progress messages during multi-repo metric collection (e.g., `Processing repo 3/25: owner/name`); these are visible only when `--log-level INFO` or lower is set.
- **FR-012**: All flags that accept an argument MUST support both a short single-character form and a long form (e.g., `-t`/`--topic`). Boolean on/off flags MUST support `--flag`/`--no-flag` pairs. Help output MUST display the default value for every flag.
- **FR-013**: The tool MUST support `-w`/`--window <days>` (default: 7) to set the lookback period in days, with a maximum of 14. Values outside the range 1–14 MUST cause the tool to exit with a non-zero error code and a message identifying the valid range before making any API calls. This cap aligns with the GitHub Traffic API's maximum clone data window, ensuring all metrics reflect the same period. The window is computed as a UTC timestamp at startup.
- **FR-014**: When the output file path is not writable (permission error, disk full, or other OS error), the tool MUST exit immediately with a non-zero error code and print a message to stderr identifying the path and the OS error. No partial output is written.
- **FR-015**: The CLI MUST be implemented using Python's `argparse` standard library module (no third-party CLI framework).
- **FR-016**: The tool MUST require Python ≥ 3.12.
- **FR-017**: The tool MUST be packaged as a `pyproject.toml` project with a console script entry point, installable via `pip install .` or `pipx install .`, and usable as a Docker base image install target.
- **FR-018**: The tool MUST use the `ghapi` library (fastai) as the GitHub API client.
- **FR-019**: The installed console script entry point MUST be named `github-leaderboard`.
- **FR-020**: All fatal errors (invalid config, unwritable output, exhausted retries, missing `GITHUB_TOKEN`) MUST exit with code 1. Successful runs and zero-topic-results MUST exit with code 0. When retries are exhausted for a single API call during a multi-repo metric collection run, the tool MUST write a partial CSV containing all repositories whose metrics were fully collected before the failure, print an error to stderr identifying the failed repository and the exhausted-retry condition, and exit with code 1. Repositories not yet processed and the repository that triggered exhaustion are excluded from the partial CSV.

### Key Entities

- **Repository**: A GitHub repository identified by `owner/repo`; carries all collected metric values and a computed leaderboard score.
- **MetricWeights**: User-defined numerical multipliers for each scoring metric, loaded from a config file.
- **LeaderboardEntry**: A ranked row in the output CSV with fixed columns: `repo` (owner/repo), `stars`, `commits`, `prs_active`, `prs_merged`, `trend`, `clones`, `score`. Unavailable metric values are represented as empty strings.
- **TopicQuery**: A GitHub topic string used to discover repositories via search.
- **TargetList**: A local file containing explicit `owner/repo` identifiers to score.
- **LookbackWindow**: The time period (in days, set by `-w`/`--window`, min 1, default 7, max 14) applied uniformly to all time-sensitive metrics: commit activity, active PRs, merged PRs, trending bonus (ΔStars), and clone count. The 14-day cap matches the GitHub Traffic API's clone data limit. Star count is the only metric that is not windowed — it reflects the repository's all-time total.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a topic with at least 10 repositories at default settings (`--top 10`, `--window 7`), the tool produces a complete ranked CSV within 5 minutes on a standard internet connection. Runtime for larger `--top` values is bounded by the Search API rate limit (30 req/min); no SLA is defined beyond the default.
- **SC-002**: 100% of repositories in the target list appear in the output CSV (excluding explicitly logged invalid/unreachable entries).
- **SC-003**: A repository with a 403 clone-traffic error is still included in the output CSV with a score computed from the remaining metrics.
- **SC-004**: An invalid configuration file causes the tool to exit before contacting GitHub, with an error message that identifies the offending field.
- **SC-005**: Two runs with identical inputs and weights produce identical output CSV files (deterministic scoring).
- **SC-006**: A change to a single weight in the configuration file causes a measurable change in the ranked order when metric values differ across repositories.

## Clarifications

### Session 2026-04-16 (fourth pass)

- Q: When rate-limit retries are exhausted for a single API call during a multi-repo run, what happens? → A: Write a partial CSV with all repos whose metrics were fully collected before the failure, then exit 1. The repo that triggered exhaustion and any unprocessed repos are excluded from the partial CSV.
- Q: What should happen when `--top N` is passed with `--list`? → A: Silently ignored; all valid entries in the target list are scored and ranked.
- Q: For the clone metric, which Traffic API daily buckets are summed when `--window N` is set? → A: Sum only the daily buckets that fall within the last N days. GitHub returns up to 14 daily values; use the most recent N of them.
- Q: When the output file already exists and is writable, should the tool overwrite it? → A: Yes, overwrite — but print a notice to stdout before doing so.
- Q: Should the tool provide progress feedback during long multi-repo runs? → A: Yes — emit INFO-level progress messages per repo (e.g., "Processing repo 3/25..."); visible when the user passes `-v INFO`.

### Session 2026-04-16 (third pass)

- Q: Trend metric when total stars = 0 (division by zero)? → A: Treat trend = 0 silently; zero stars means no trend signal.
- Q: What if the target list file has no valid entries? → A: Exit code 0, print notice to stderr, write no CSV (same as zero-topic-results).
- Q: Should `--top N` be validated? → A: Valid range 1–50 inclusive; values outside range exit with code 1 before any API calls.
- Q: Are negative weight values allowed? → A: Yes; valid range is −1 to 1 inclusive. Values outside this range exit with code 1.
- Q: Should the score column be rounded in the CSV? → A: Round to 2 decimal places.

### Session 2026-04-16 (second pass)

- Q: Tie-breaking sort order for identical scores? → A: Secondary sort by stars descending in both topic mode and list mode.
- Q: Valid values for `--log-level`? → A: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (Python logging standard, case-insensitive; default `WARNING`).
- Q: How should the config file format be determined? → A: YAML only; always parsed as YAML regardless of filename or extension.
- Q: Should unknown keys in `weights:` block cause an error or be ignored? → A: Exit with code 1, naming the unrecognised key(s).
- Q: Are all 6 weight keys required, or can they be omitted? → A: Missing keys default to zero with a printed notice (partial configs are valid).

### Session 2026-04-16 (continued)

- Q: What time window does the trending bonus (ΔStars) use, and is it configurable? → A: All time-windowed metrics share a single `-w`/`--window <days>` CLI flag (default: 7); window is computed as a UTC timestamp at startup.
- Q: What are the CSV output column names and order? → A: `repo, stars, commits, prs_active, prs_merged, trend, clones, score`; unavailable values are empty strings.
- Q: Does the tool hammer the GitHub API? → A: Search API (30 req/min) is the binding constraint at ~2 calls/repo; SC-001 SLA scoped to default --top 10. Trend pagination strategy deferred to planning. Both rate limits handled separately per FR-006.
- Q: What is the valid range for `--window`? → A: 1–14 days (max 14 matches GitHub Traffic API clone data limit); values outside range exit with error before any API calls.
- Q: What happens when the output CSV file path is not writable? → A: Exit immediately with non-zero error code; print path and OS error to stderr; write nothing.
- Q: What happens when a target list contains duplicate `owner/repo` entries? → A: Deduplicate (score once) and log a warning identifying the duplicates.
- Q: Short flag for `--top` and `--window`? → A: `-n`/`--top` (Unix count convention, cf. `head -n`); `-w`/`--window`.
- Q: What happens when a topic search returns zero repositories? → A: Exit code 0, print notice to stderr, write no output file.
- Q: How does the tool behave when all metric API calls return errors for a single repository? → A: Include in CSV with score=0 and all metrics marked unavailable (empty string); log a warning.
- Q: What happens when a target-list repository is deleted or private? → A: Include in CSV with score=0 and metrics unavailable; log a warning (same as all-metrics-fail behavior).
- Q: Where do log/warning messages go, given the tool may run as a systemd service or Docker container? → A: All log output goes to stdout; errors are additionally mirrored to stderr. A `--log-format human|json` flag controls structure (default: human-readable). A `--log-level` flag controls verbosity (default: WARNING for service use).
- Q: How are the two input modes and other options specified on the CLI? → A: Named flags (`--topic`/`--list`). Config file optional, defaults to `git-leaderboard.yml`. Result limit via `--top N` (default 10, no hard cap). Flags that take arguments support short and long forms. Boolean flags use `--flag`/`--no-flag` style. Help text shows default values for all flags.
- Q: What environment variable name does the tool use for the GitHub authentication token? → A: `GITHUB_TOKEN` (aligns with ghapi default, GitHub Actions, and gh CLI convention).
- Q: Which Python CLI framework should the tool use? → A: `argparse` (stdlib only, no extra dependency).
- Q: What is the minimum Python version the tool must support? → A: Python 3.12.
- Q: What are the exponential backoff parameters for rate-limit retries? → A: 5 retries, 1s initial delay, doubling each attempt (max ~31s total wait).
- Q: How should the tool be packaged/distributed? → A: `pyproject.toml` package with console script entry point; supports both `pip install .` / `pipx` and Docker (`pip install .` inside image).
- Q: What is the config file schema? → A: `weights:` block with keys matching CSV column names: `stars`, `commits`, `prs_active`, `prs_merged`, `trend`, `clones`.
- Q: Which Python library should be used to call the GitHub API? → A: `ghapi` (fastai) — auto-generated from GitHub OpenAPI spec, native `GITHUB_TOKEN` support.
- Q: What should the installed console script command be named? → A: `github-leaderboard`.
- Q: What exit code for fatal errors? → A: Exit code 1 for all fatal errors (bad config, unwritable output, exhausted retries); exit code 0 for success and graceful no-results termination.
- Q: What should the tool do when `GITHUB_TOKEN` is not set? → A: Read token from `.github_token` file first (working directory, plain text first line), fall back to `GITHUB_TOKEN` env var; exit code 1 with instructions if neither present. `.github_token` added to `.gitignore`.

## Assumptions

- The user has a valid GitHub Personal Access Token available either in a `.github_token` file (working directory) or the `GITHUB_TOKEN` environment variable before running the tool. `.github_token` takes precedence; the file is listed in `.gitignore` to prevent accidental commits.
- The token has at minimum `public_repo` read scope; clone-traffic data requires `repo` scope (admin/push access) — its absence is an expected and handled condition.
- The lookback window (min 1, default 7, max 14 days, configurable via `-w`/`--window`) is always computed in UTC relative to the moment the tool is invoked; no historical backfill is required. The 14-day cap is driven by the GitHub Traffic API's clone data limit.
- The output CSV file is written to the current working directory as `leaderboard.csv` unless the user specifies an alternative path via `-o`/`--output`.
- The default configuration file is `git-leaderboard.yml` in the working directory; the `-c`/`--config` flag overrides this.
- Concurrent API fetching is a performance enhancement, not a v1 requirement; sequential fetching is acceptable for the initial release.
- The GitHub Search API is rate-limited to 30 requests/minute independently of the REST API limit (5,000 req/hour). At 2 search calls per repository (active PRs + merged PRs), the practical throughput ceiling for PR metrics is ~15 repositories/minute. Runtime for large `--top` values is dominated by this limit.
- The trend (ΔStars) calculation requires paginating star history; the implementation strategy (pagination depth, approximation approach) is a planning concern.
- The tool targets single-user or small-team local execution; no multi-user access control or web interface is required.
- Topic discovery returns GitHub's default ordering (typically by best-match/stars); the tool re-ranks the fetched set by the weighted score.
