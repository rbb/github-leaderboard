# Research: GitHub Topic Leaderboard Generator

**Branch**: `001-github-leaderboard` | **Generated**: 2026-04-16

---

## Decision 1: Star Trend (ΔStars) Pagination Strategy

**Decision**: Backward-page approach — fetch the most recent stargazer pages only, stopping
when all entries on a page predate the window.

**Rationale**: Stars are returned chronologically oldest-first. Starting from the last page
(most recent) and working backwards minimises API calls for the common case where only a
small fraction of total stars fall within the window. Capped at 5 pages maximum (500 recent
stargazers) per repository — accurate for repos gaining < 500 stars per 14-day window;
documented approximation for repos with higher velocity.

**Alternatives considered**:
- *Full pagination*: Correct but unbounded API cost for popular repos (e.g., 40,000-star
  repo = 400 pages per run). Rejected — violates Constitution V (minimal, bounded API use).
- *GitHub Events API*: Watch events include starring, but only covers last 90 days and
  returns at most 300 events. Rejected — insufficient window coverage and undocumented cap.
- *GraphQL `starredAt`*: GitHub GraphQL API supports timestamped star queries with cursor
  pagination. Rejected — would require adding `gql`/`httpx` dependency; spec mandates `ghapi`.

**Implementation note**: Use `Accept: application/vnd.github.star+json` header to get
`starred_at` timestamps. Compute last page index from `stargazers_count`:
`last_page = max(1, ceil(stargazers_count / 100))`. Fetch pages from `last_page` down to
`max(1, last_page - 4)` (5 pages). Count entries where `starred_at >= window_since`.

---

## Decision 2: Rate-Limit Handling Architecture

**Decision**: Implement a custom `retry_with_backoff()` decorator in `client.py` that wraps
`ghapi` calls. Detect rate-limit exhaustion from HTTP 429 and 403 responses (both used by
GitHub). Separately detect Search API limits by checking response headers or catching
`github.GithubException` with status 403 and message matching `"rate limit"`.

**Rationale**: `ghapi` provides no built-in retry. It does provide a `limit_cb` callback
and `api.limit_rem` to monitor remaining quota, but these are informational only.

**Handling strategy**:
- REST API (5,000 req/hr): retry up to 5 times with delays 1s, 2s, 4s, 8s, 16s. Log
  `WARNING` on each retry identifying which limit was hit.
- Search API (30 req/min): same backoff parameters; distinguished by endpoint path
  (`/search/`) in the request or by `X-RateLimit-Resource: search` response header.
- After 5 retries: raise `RateLimitExhaustedError` → caught by caller → exit code 1.

**Alternatives considered**:
- *`tenacity` library*: elegant retry decorator, but adds a dependency. Rejected per
  Constitution V.
- *Sleep until `X-RateLimit-Reset`*: More efficient but complex; the reset time can be
  far in the future. Exponential backoff with 5 retries is simpler and sufficient.

---

## Decision 3: Commit Count in Window

**Decision**: Use `api.repos.list_commits(owner, repo, since=window_since, per_page=100)`
with `paged()` iteration, counting all returned commits.

**Rationale**: The REST commits endpoint natively supports `since` date filtering. This
avoids the Search API (more rate-limited) and gives an exact count rather than an
approximation.

**Alternatives considered**:
- *Search API (`q=repo:owner/repo+committer-date:>DATE`)*: Uses the 30-req/min Search
  quota. Rejected — PR metric collection already uses this quota heavily.
- *GraphQL `defaultBranchRef.target.history`*: Not available via `ghapi`; requires
  separate HTTP client.

---

## Decision 4: Active and Merged PR Count in Window

**Decision**: Use `api.pulls.list(owner, repo, state='open', per_page=100)` for active PRs
(filter `created_at >= window_since`), and `api.pulls.list(owner, repo, state='closed',
per_page=100)` for merged PRs (filter `merged_at >= window_since`, `merged_at is not None`).

**Rationale**: The PR list endpoint returns timestamps; application-side date filtering is
simpler than constructing search queries. Using `pulls.list` avoids the Search API.

**Note**: Repos with many PRs may require paging. Stop pagination early once all entries on
a page predate the window (PRs are returned newest-first).

**Alternatives considered**:
- *Search API `is:pr is:merged merged:>DATE`*: Uses Search quota. Rejected for same reason
  as commits.

---

## Decision 5: CSV Output — stdlib csv vs pandas

**Decision**: Use Python stdlib `csv.DictWriter` for all CSV output.

**Rationale**: The output is a fixed 8-column file; no pivot, aggregation, or DataFrame
operations are needed. Adding `pandas` would be ~10 MB of wheel for zero gain.

**Alternatives considered**:
- *pandas*: Constitution V explicitly lists it as optional ("pandas or csv"). For this
  use case, it's overengineered.

---

## Decision 6: Testing Strategy

**Decision**: `pytest` with two layers:
1. **Unit tests** (`tests/unit/`): Pure Python; mock `GhApi` at the class level with
   `unittest.mock.patch`. Cover config validation, scorer math, auth token loading, and
   metric edge cases (zero stars, 403 clone, all-metrics-unavailable).
2. **Integration tests** (`tests/integration/`): `pytest-recording` (VCR) cassettes for
   happy-path API interactions. Record once against GitHub sandbox; replay in CI.

**Rationale**: VCR cassettes test the real API contract (response shape, pagination);
`unittest.mock` is easier for error injection (rate limits, 403, network timeout).

**Alternatives considered**:
- *`responses` library*: Good for `requests`-based clients; `ghapi` uses `httpcore`
  internally, making `responses` less reliable. Rejected.
- *All mocks*: Loses API contract coverage. Rejected per Constitution IV.

---

## Resolved Clarifications (from spec)

All NEEDS CLARIFICATION items resolved:

| Item | Resolution |
|------|------------|
| Trend pagination strategy | Backward 5-page cap (Decision 1 above) |
| pandas vs stdlib csv | stdlib csv (Decision 5 above) |
| Test approach | pytest + VCR + unittest.mock (Decision 6 above) |
| Rate-limit separate handling | Custom decorator, endpoint-path detection (Decision 2) |
