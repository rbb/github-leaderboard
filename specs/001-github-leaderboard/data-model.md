# Data Model: GitHub Topic Leaderboard Generator

**Branch**: `001-github-leaderboard` | **Generated**: 2026-04-16

---

## Entities

### MetricWeights

User-supplied numerical multipliers loaded from the YAML config file.

| Field | Type | Validation | Default |
|-------|------|-----------|---------|
| `stars` | `float` | −1.0 ≤ value ≤ 1.0 | 0.0 |
| `commits` | `float` | −1.0 ≤ value ≤ 1.0 | 0.0 |
| `prs_active` | `float` | −1.0 ≤ value ≤ 1.0 | 0.0 |
| `prs_merged` | `float` | −1.0 ≤ value ≤ 1.0 | 0.0 |
| `trend` | `float` | −1.0 ≤ value ≤ 1.0 | 0.0 |
| `clones` | `float` | −1.0 ≤ value ≤ 1.0 | 0.0 |

**Validation rules** (all checked at startup before any API calls):
- Config file must be valid YAML syntax.
- Top-level `weights:` key must be present.
- No keys outside the six listed above are permitted in `weights:` (exit 1, name offending key).
- All present values must be numeric (int or float).
- All present values must satisfy −1.0 ≤ value ≤ 1.0.
- Missing keys default to 0.0 with a printed notice.

**State transitions**: Immutable after startup validation.

---

### LookbackWindow

The time period applied uniformly to all time-sensitive metrics.

| Field | Type | Validation |
|-------|------|-----------|
| `days` | `int` | 1 ≤ days ≤ 14 |
| `since` | `datetime` (UTC) | Computed once at startup: `datetime.now(UTC) - timedelta(days=days)` |

**Validation**: `days` checked before any API calls; values outside 1–14 exit with code 1.
**Note**: `stars` metric is NOT windowed — it reflects all-time total.

---

### RepoMetrics

Collected metric values for a single repository. `None` indicates a failed or unavailable
API call; serialized as empty string in CSV output.

| Field | Type | Source |
|-------|------|--------|
| `full_name` | `str` | `owner/repo` |
| `stars` | `int \| None` | `repo.stargazers_count` (always available) |
| `commits` | `int \| None` | `repos.list_commits(since=window.since)` — count of pages |
| `prs_active` | `int \| None` | `pulls.list(state='open')` — count with `created_at >= window.since` |
| `prs_merged` | `int \| None` | `pulls.list(state='closed')` — count with `merged_at >= window.since` |
| `trend` | `float \| None` | `(stars_in_window / total_stars)` — see note |
| `clones` | `int \| None` | `repos.get_traffic_clones()` — `None` on 403 (substituted as 0 in scoring) |

**Trend note**: `trend = stars_gained_in_window / total_stars`. If `total_stars == 0`, trend
is 0.0 (silent, no warning). If star-history pagination fails, trend is `None`.

**Clone 403 handling**: A 403 on the clone endpoint logs a WARNING and stores `None` in
`RepoMetrics.clones`; the scorer substitutes 0 for `None` when computing the weighted score
(FR-005). This is distinct from a general API failure.

---

### LeaderboardEntry

A single ranked row destined for CSV output.

| Field | Type | CSV Column | Notes |
|-------|------|-----------|-------|
| `repo` | `str` | `repo` | `owner/repo` format |
| `stars` | `int \| str` | `stars` | Empty string if unavailable |
| `commits` | `int \| str` | `commits` | Empty string if unavailable |
| `prs_active` | `int \| str` | `prs_active` | Empty string if unavailable |
| `prs_merged` | `int \| str` | `prs_merged` | Empty string if unavailable |
| `trend` | `float \| str` | `trend` | Empty string if unavailable |
| `clones` | `int \| str` | `clones` | Empty string if unavailable |
| `score` | `float` | `score` | Rounded to 2 decimal places |

**Column order** (fixed, per FR-007): `repo, stars, commits, prs_active, prs_merged, trend, clones, score`

**Sort order**: Primary: `score` descending. Secondary: `stars` descending (tie-break).

**Unavailable sentinel**: Repos where all metric calls fail still appear in the CSV with
`score = 0.0` and all metric columns as empty string. A WARNING is logged.

---

### AppConfig

Merged CLI arguments and validated weights — the single configuration object passed to
all pipeline stages.

| Field | Type | Source | Default |
|-------|------|--------|---------|
| `topic` | `str \| None` | `--topic` flag | `None` |
| `target_list` | `Path \| None` | `--list` flag | `None` |
| `config_file` | `Path` | `--config` flag | `./git-leaderboard.yml` |
| `output` | `Path` | `--output` flag | `./leaderboard.csv` |
| `top_n` | `int` | `--top` flag | `10` |
| `window` | `LookbackWindow` | `--window` flag | 7 days |
| `log_format` | `Literal['human', 'json']` | `--log-format` flag | `'human'` |
| `log_level` | `str` | `--log-level` flag | `'WARNING'` |
| `weights` | `MetricWeights` | Config file | — |
| `token` | `str` | `.git_token` → `GITHUB_TOKEN` | — |

**Validation sequence** (all before any API call):
1. Exactly one of `topic` or `target_list` is set (exit 1 otherwise).
2. `top_n` ∈ [1, 50] (exit 1 otherwise).
3. `window.days` ∈ [1, 14] (exit 1 otherwise).
4. `log_level` is one of `DEBUG/INFO/WARNING/ERROR/CRITICAL` (case-insensitive; exit 1 otherwise).
5. Config file found and parsed as YAML (exit 1 otherwise).
6. `MetricWeights` validation passes.
7. Token found (exit 1 with instructions otherwise).
8. Output path is writable (exit 1 on permission/OS error; nothing written).

---

## Entity Relationships

```
AppConfig
  ├── LookbackWindow
  └── MetricWeights

Pipeline:
  [TopicQuery | TargetList]
      → [GhApi client]
      → RepoMetrics[]
      → scorer(RepoMetrics, MetricWeights)
      → LeaderboardEntry[]
      → writer(LeaderboardEntry[], output_path)
      → CSV file
```

---

## Scoring Formula

```
score = (weights.stars    × metrics.stars    or 0)
      + (weights.commits  × metrics.commits  or 0)
      + (weights.prs_active × metrics.prs_active or 0)
      + (weights.prs_merged × metrics.prs_merged or 0)
      + (weights.trend    × metrics.trend    or 0)
      + (weights.clones   × metrics.clones   or 0)
```

`None` metric values are treated as 0 in the formula. Result is rounded to 2 decimal places.
