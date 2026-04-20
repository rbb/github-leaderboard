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

# Example data pipeline
```bash
#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Leaderboard Pipeline..."

# 1. Generate initial leaderboard
github-leaderboard -n 50 -l websites.txt -o websites.csv

# 2. Get existing projects
gh-projects -o gh_projects.txt

# 3. Compare and find new projects
gh-new-proj -a websites.txt -b gh_projects.txt -o new_projects.txt

# 4. Generate leaderboard for new projects
github-leaderboard -n 10 -l new_projects.txt -o new_projects.csv

# 5. Convert results to HTML
csv-html -i websites.csv new_projects.csv -o leaderboard.html

echo "Pipeline complete! Output generated in leaderboard.html"

# scp leaderboard.html somewhere.
```
