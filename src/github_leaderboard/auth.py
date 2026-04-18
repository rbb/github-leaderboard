"""GitHub token loading: .github_token file → GITHUB_TOKEN env var."""

import os
from pathlib import Path


def load_token() -> str:
    """Load GitHub token from .github_token file or GITHUB_TOKEN env var.

    Returns the token string. Raises SystemExit(1) if not found.
    """
    token_file = Path(".github_token")
    if token_file.exists():
        lines = token_file.read_text().strip().splitlines()
        if lines:
            token = lines[0].strip()
            if token:
                return token

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token

    raise SystemExit(
        "Error: GitHub token not found. Create a .github_token file in the current directory\n"
        "or set the GITHUB_TOKEN environment variable."
    )
