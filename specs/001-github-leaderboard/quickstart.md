# Quickstart: github-leaderboard

**Branch**: `001-github-leaderboard` | **Generated**: 2026-04-16

---

## Prerequisites

- Python ≥ 3.12
- A GitHub Personal Access Token with at minimum `public_repo` read scope
  (add `repo` scope to include clone-traffic data)

---

## Installation

```bash
# From the project root
pip install .

# Or with pipx (recommended for CLI tools)
pipx install .

# Or in Docker
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install .
```

---

## Authentication

Create a `.github_token` file in your working directory (it's in `.gitignore`):

```bash
echo "ghp_yourPersonalAccessTokenHere" > .github_token
```

Or export the environment variable:

```bash
export GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere
```

---

## Configuration

Create a `git-leaderboard.yml` in your working directory:

```yaml
weights:
  stars: 1.0       # All-time star count
  commits: 0.5     # Commits in window
  prs_active: 0.3  # Open PRs created in window
  prs_merged: 0.4  # PRs merged in window
  trend: 0.2       # Star velocity (stars gained / total stars)
  clones: 0.1      # Clone count in window (requires repo scope)
```

Weights must be in the range −1.0 to 1.0. Missing weights default to 0.0.

---

## Usage

### Rank repositories by topic

```bash
# Default: top 10, 7-day window
github-leaderboard --topic machine-learning

# Custom settings
github-leaderboard --topic python --top 25 --window 14 --output results.csv

# With explicit config file
github-leaderboard --topic rust --config my-weights.yml
```

### Rank a curated list of repositories

```bash
# Create a list file
cat > repos.txt << EOF
torvalds/linux
microsoft/vscode
facebook/react
EOF

github-leaderboard --list repos.txt --output my-leaderboard.csv
```

### Adjust logging verbosity

```bash
# See all debug output
github-leaderboard --topic python --log-level DEBUG

# JSON output for structured log ingestion
github-leaderboard --topic python --log-format json --log-level INFO
```

---

## Output

The tool writes a CSV file (default: `leaderboard.csv`) sorted by score descending:

```csv
repo,stars,commits,prs_active,prs_merged,trend,clones,score
owner/top-repo,45230,312,8,22,0.0034,156,87.42
owner/second-repo,12100,89,3,11,0.0012,43,31.17
owner/no-clones,8900,201,5,9,0.0008,,29.15
```

Repositories with unavailable metrics appear with empty fields. Score is rounded to
2 decimal places.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (or zero results — no CSV written) |
| `1` | Fatal error (see stderr for details) |

---

## Common Errors

**Missing token**
```
Error: GitHub token not found. Create a .github_token file in the current directory
or set the GITHUB_TOKEN environment variable.
```
→ Create `.github_token` or `export GITHUB_TOKEN=...`

**Invalid config**
```
Error: Config validation failed — unrecognised key in weights: 'forks'
```
→ Remove unrecognised keys from the `weights:` block.

**Rate limit exhausted**
```
Error: GitHub REST API rate limit retries exhausted after 5 attempts.
```
→ Wait for rate limit to reset (check `https://api.github.com/rate_limit`) and retry.

**Clone traffic 403 (warning, not fatal)**
```
WARNING: Clone traffic endpoint returned 403 for owner/repo — token lacks repo scope.
         Substituting clone count = 0.
```
→ Add `repo` scope to your token for clone data, or set `clones: 0` in your config.

---

## Development Setup

```bash
git clone <repo>
cd github_leaderboard
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with local changes
python -m github_leaderboard --topic python
```
