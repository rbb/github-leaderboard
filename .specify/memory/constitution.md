<!--
SYNC IMPACT REPORT
==================
Version change: [unversioned template] → 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - Core Principles (I–V)
  - Technical Stack & Constraints
  - Development Workflow
  - Governance
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ Constitution Check section references these principles
  - .specify/templates/spec-template.md ✅ No changes required; FR/SC patterns align
  - .specify/templates/tasks-template.md ✅ Phase structure aligns with TDD principle
Follow-up TODOs: None — all placeholders resolved.
-->

# GitHub Leaderboard Constitution

## Core Principles

### I. CLI-First Design

The tool MUST operate entirely from the command line. All inputs are provided via
CLI arguments or environment variables; all primary output goes to stdout or a
named CSV file. No interactive prompts are permitted in normal operation. Error
messages MUST go to stderr. Human-readable and machine-parseable (CSV) output
formats are both supported.

**Rationale**: Enables scripting, CI/CD integration, and reproducible runs without
a GUI or web server dependency.

### II. Configuration-Driven Scoring

Metric weights MUST be externalized to a user-supplied JSON or YAML configuration
file; no weights are hard-coded. Adding or reweighting a metric MUST NOT require
a code change. The config schema MUST be validated at startup with clear error
messages on malformed input.

**Rationale**: Different users rank repositories differently; hard-coded weights
would make the tool unfit for diverse use cases.

### III. Resilient API Access

Every GitHub API call MUST handle rate-limit responses (HTTP 429 / 403 secondary
limit) via exponential backoff with jitter. Endpoints that return 403 due to
insufficient permissions (e.g., `traffic/clones`) MUST log a warning and
substitute a zero value rather than aborting the run. The tool MUST surface the
token scopes required for full fidelity so users can act on warnings.

**Rationale**: GitHub's API limits are unavoidable; silent failures or hard crashes
produce unreliable leaderboards and poor user experience.

### IV. Test-First Development

Tests MUST be written and confirmed to fail before any implementation code is
written (Red-Green-Refactor). Unit tests cover individual metric calculators and
scoring logic. Integration tests (using recorded VCR cassettes or mocks) cover
API interaction paths. No PR may be merged with failing tests or without test
coverage for new logic paths.

**Rationale**: The scoring algorithm is numerically sensitive; regressions are
invisible without automated verification.

### V. Simplicity & Minimal Dependencies

The implementation MUST use Python 3.9+ with the fewest third-party libraries
that satisfy requirements (`ghapi`, `pandas` or `csv`, `PyYAML`/`json`). New
dependencies require explicit justification. YAGNI applies: features not listed
in the specification MUST NOT be added speculatively.

**Rationale**: A small dependency surface reduces installation friction, security
exposure, and maintenance burden for a utility tool.

## Technical Stack & Constraints

- **Language**: Python 3.9+
- **GitHub Client**: `ghapi` (wraps GitHub REST API v3)
- **Authentication**: GitHub Personal Access Token via `GITHUB_TOKEN` environment variable;
  token MUST NOT be accepted as a CLI argument to prevent accidental leakage in
  shell history.
- **Output**: `pandas` or stdlib `csv`; output file defaults to `leaderboard.csv`
  in the working directory unless overridden by CLI flag.
- **Date arithmetic**: All timestamp windows (e.g., 7-day lookback) MUST be
  computed in UTC ISO-8601 format at runtime; no hard-coded date strings.
- **Concurrency**: Sequential API calls are acceptable for MVP; concurrent fetching
  is a performance improvement that MUST NOT compromise error-handling guarantees.

## Development Workflow

- Feature branches follow the naming convention `###-short-description`.
- All changes to scoring logic or CLI interface MUST update `requirements.md` or
  the relevant spec if behavior changes.
- Every commit touching `src/` MUST leave the test suite green.
- The `leaderboard.csv` output file MUST be listed in `.gitignore`; API tokens
  and config files containing secrets MUST never be committed.
- Code review MUST verify compliance with Principles I–V before merge.

## Governance

This constitution supersedes all ad-hoc conventions. Amendments require:
1. A written rationale describing the change and its impact.
2. A version bump following semantic versioning (MAJOR for breaking principle
   changes, MINOR for additions, PATCH for clarifications).
3. Propagation of any affected template updates before the amendment is merged.

All PRs and design reviews MUST include a "Constitution Check" section confirming
no principles are violated. Complexity beyond what the specification requires MUST
be explicitly justified in the plan's Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-04-16 | **Last Amended**: 2026-04-16
