# CLI Contract: github-leaderboard

**Branch**: `001-github-leaderboard` | **Generated**: 2026-04-16

This document defines the complete command-line interface contract for the
`github-leaderboard` console script. It is the authoritative reference for
what the tool accepts and produces.

---

## Synopsis

```
github-leaderboard (-t TOPIC | -l FILE) [-c CONFIG] [-o OUTPUT]
                   [-n TOP] [-w WINDOW] [-f FORMAT] [-v LEVEL]
                   [-h]
```

---

## Input Modes (mutually exclusive, exactly one required)

| Flag | Short | Argument | Description |
|------|-------|----------|-------------|
| `--topic` | `-t` | `TOPIC` | GitHub topic string (e.g. `machine-learning`) |
| `--list` | `-l` | `FILE` | Path to `.txt` file; one `owner/repo` per line |

Providing both or neither exits with code 1 and a message naming the conflict.

---

## Options

| Flag | Short | Argument | Default | Valid Range |
|------|-------|----------|---------|-------------|
| `--config` | `-c` | `FILE` | `./git-leaderboard.yml` | Must be valid YAML |
| `--output` | `-o` | `FILE` | `./leaderboard.csv` | Must be writable |
| `--top` | `-n` | `N` | `10` | 1–50 inclusive |
| `--window` | `-w` | `DAYS` | `7` | 1–14 inclusive |
| `--log-format` | `-f` | `FORMAT` | `human` | `human` \| `json` |
| `--log-level` | `-v` | `LEVEL` | `WARNING` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL` (case-insensitive) |
| `--help` | `-h` | — | — | — |

All flags that accept an argument support both the short single-character form and the
long form. Boolean on/off flags use `--flag`/`--no-flag` style. Help text shows the
default value for every flag.

---

## Authentication

The tool reads the GitHub token from (in order):

1. `.git_token` file in the current working directory (plain text; first line used)
2. `GITHUB_TOKEN` environment variable

If neither is present, the tool exits with code 1 and prints:

```
Error: GitHub token not found. Create a .git_token file in the current directory
or set the GITHUB_TOKEN environment variable.
```

The token is **never** accepted as a CLI argument.

---

## Configuration File Format

YAML only; always parsed as YAML regardless of extension.

```yaml
weights:
  stars: 1.0
  commits: 0.5
  prs_active: 0.3
  prs_merged: 0.4
  trend: 0.2
  clones: 0.1
```

**Rules**:
- `weights:` key is required.
- Recognised keys: `stars`, `commits`, `prs_active`, `prs_merged`, `trend`, `clones`.
- Any unrecognised key in `weights:` causes exit code 1, naming the offending key.
- Values must be numeric and in the range −1.0 to 1.0 inclusive.
- Missing keys default to 0.0 with a notice printed to stdout.

---

## Target List File Format (for `--list`)

Plain text file, UTF-8 encoding:

```
# Comments (lines starting with #) are allowed
torvalds/linux
microsoft/vscode
owner/repo
```

- One `owner/repo` entry per line.
- Blank lines and comment lines (`#`) are ignored.
- Malformed entries (not matching `owner/repo`) log a WARNING and are skipped.
- Duplicate entries are deduplicated; each duplicate logs a WARNING.
- If no valid entries remain: exit code 0, notice to stderr, no CSV written.

---

## Output CSV

Written to the path specified by `--output` (default: `./leaderboard.csv`).

**Column order** (fixed):
```
repo,stars,commits,prs_active,prs_merged,trend,clones,score
```

**Details**:
- `repo`: `owner/repo` string
- `stars`: all-time star count (integer)
- `commits`, `prs_active`, `prs_merged`, `clones`: windowed integer counts
- `trend`: `stars_in_window / total_stars` (float)
- `score`: weighted sum, rounded to 2 decimal places
- Unavailable metric values → empty string
- Sort: `score` descending; ties broken by `stars` descending
- Output is atomic: file is not written at all if an error occurs mid-run

---

## Logging

| Destination | Content |
|-------------|---------|
| stdout | All log output (DEBUG through CRITICAL) |
| stderr | ERROR and CRITICAL messages additionally mirrored here |

`--log-format human` (default): human-readable text lines
`--log-format json`: newline-delimited JSON objects with `level`, `message`, `timestamp`

---

## Exit Codes

| Code | Condition |
|------|-----------|
| `0` | Successful run |
| `0` | Zero topic results (no CSV written; notice to stderr) |
| `0` | Empty/all-invalid target list (no CSV written; notice to stderr) |
| `1` | Invalid config (bad YAML, missing `weights:`, unrecognised key, out-of-range value) |
| `1` | Missing GitHub token |
| `1` | Invalid `--top` value (outside 1–50) |
| `1` | Invalid `--window` value (outside 1–14) |
| `1` | Invalid `--log-level` value |
| `1` | Output path not writable |
| `1` | Rate-limit retries exhausted |
| `1` | Both `--topic` and `--list` supplied, or neither supplied |

---

## Rate-Limit Behaviour

- **REST API** (5,000 req/hr): exponential backoff — delays 1s, 2s, 4s, 8s, 16s (5 attempts).
- **Search API** (30 req/min): same backoff; detected separately by endpoint or header.
- A WARNING is logged for each retry, identifying which limit was hit.
- After 5 exhausted retries: exit code 1.

---

## Known Limitations

- Trend metric is approximated for repos with > 500 stars gained in the window period
  (capped at 5 pages / 500 most-recent stargazers; see `research.md` Decision 1).
- Clone traffic requires the token to have `repo` scope (admin/push access). Without
  this scope, clone counts are substituted as 0 with a WARNING per FR-005.
