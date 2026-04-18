# github-leaderboard

Rank GitHub repositories by topic or curated list using weighted metrics.

## Installation

```bash
pip install .
# or
pipx install .
```

## Authentication

```bash
echo "ghp_yourtoken" > .github_token
# or
export GITHUB_TOKEN=ghp_yourtoken
```

## Usage

```bash
# Rank by topic (default: top 10, 7-day window)
github-leaderboard --topic machine-learning

# Rank curated list
github-leaderboard --list repos.txt --output my-leaderboard.csv

# Custom scoring weights
github-leaderboard --topic python --config my-weights.yml --top 25 --window 14
```

## Configuration

Create `git-leaderboard.yml`:

```yaml
weights:
  stars: 1.0
  commits: 0.5
  prs_active: 0.3
  prs_merged: 0.4
  trend: 0.2
  clones: 0.1
```

Weights must be in the range −1.0 to 1.0. Missing weights default to 0.0.

## Output

CSV file (`leaderboard.csv` by default) sorted by score descending:

```
repo,stars,commits,prs_active,prs_merged,trend,clones,score
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
ruff check src/
```
