# Tasks: GitHub Topic Leaderboard Generator

**Input**: Design documents from `/specs/001-github-leaderboard/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD is enforced per Constitution Principle IV. Test tasks are included for each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are relative to repository root.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure (src/github_leaderboard/, tests/unit/, tests/integration/) per implementation plan
- [X] T002 Initialize pyproject.toml with dependencies (ghapi, PyYAML, pytest, pytest-recording)
- [X] T003 [P] Create .gitignore with leaderboard.csv, .github_token, *.csv, and __pycache__
- [X] T004 [P] Create README.md with installation and basic usage instructions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Implement auth.py for token loading from .github_token file or GITHUB_TOKEN env var
- [X] T006 [P] Implement client.py with GhApi wrapper and exponential backoff decorator (Decision 2)
- [X] T007 [P] Implement basic config.py for AppConfig and MetricWeights dataclasses (Data Model)
- [X] T008 [P] Setup logging infrastructure in cli.py with human/json support and log-level flags (FR-011)
- [X] T009 [P] Create tests/conftest.py for shared pytest fixtures (mocking GhApi)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Topic-Based Leaderboard (Priority: P1) 🎯 MVP

**Goal**: Discover and rank repositories for a GitHub topic and output a ranked CSV file.

**Independent Test**: Run `github-leaderboard --topic machine-learning` and verify a `leaderboard.csv` is produced with ranked repos and valid scores.

### Tests for User Story 1 (REQUIRED per TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Unit tests for scorer math and tie-breaking in tests/unit/test_scorer.py
- [X] T011 [P] [US1] Unit tests for auth token loading and precedence in tests/unit/test_auth.py
- [X] T012 [P] [US1] Integration tests for topic search and happy-path API interactions (VCR) in tests/integration/test_client.py

### Implementation for User Story 1

- [X] T013 [P] [US1] Implement scorer.py for weighted score calculation (rounded to 2 decimal places) and tie-breaking (stars descending)
- [X] T014 [P] [US1] Implement writer.py for CSV output with fixed column order and header (FR-007)
- [X] T015 [US1] Implement fetcher.py for metric collection including stars, commits (since window), PRs, trend (5-page cap), and clones (403 fallback)
- [X] T016 [US1] Implement cli.py entry point with argparse for --topic, --top, --window, --output, and execution flow
- [X] T017 [US1] Add validation for --top (1-50) and --window (1-14) in config.py or cli.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (MVP)

---

## Phase 4: User Story 2 - Target-List Leaderboard (Priority: P2)

**Goal**: Rank a curated list of repositories from a local `.txt` file using the same scoring system.

**Independent Test**: Run `github-leaderboard --list repos.txt` and verify exactly the listed repositories are ranked in the output CSV.

### Tests for User Story 2 (REQUIRED per TDD) ⚠️

- [X] T018 [P] [US2] Unit tests for target list file parsing, deduplication, and malformed entry handling in tests/unit/test_cli.py
- [X] T019 [P] [US2] Integration test for list mode API interactions (VCR) in tests/integration/test_client.py

### Implementation for User Story 2

- [X] T020 [US2] Implement target list file parsing logic in cli.py or a new utility module (support comments and blank lines)
- [X] T021 [US2] Add mutually exclusive validation for --topic and --list in cli.py (FR-001)
- [X] T022 [US2] Integrate list mode repository source into the main execution flow in cli.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Configurable Scoring Weights (Priority: P3)

**Goal**: Adjust metric weights via a YAML configuration file to customize ranking.

**Independent Test**: Run tool with two different `--config` files and verify the repository ranking order changes accordingly.

### Tests for User Story 3 (REQUIRED per TDD) ⚠️

- [X] T023 [P] [US3] Unit tests for config file validation (YAML syntax, missing weights, unknown keys, range -1 to 1) in tests/unit/test_config.py
- [X] T024 [P] [US3] Integration test for custom weight configuration impact (VCR) in tests/integration/test_client.py

### Implementation for User Story 3

- [X] T025 [US3] Implement YAML configuration loading and schema validation in config.py (FR-009)
- [X] T026 [US3] Implement default weight handling (0.0 for missing keys) and unknown key detection in config.py
- [X] T027 [US3] Integrate --config flag and weight loading into the startup sequence in cli.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T028 [P] Implement JSON log format option in cli.py (FR-011)
- [X] T029 [P] Add INFO-level progress messages (e.g., "Processing repo 3/25...") in fetcher.py
- [X] T030 [P] Create Dockerfile for the github-leaderboard console script (FR-017)
- [X] T031 Implement partial CSV write behavior when rate-limit retries are exhausted (FR-020)
- [X] T032 [P] Run all validation scenarios from quickstart.md and confirm deterministic output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1) is the MVP and should be completed first.
  - US2 (P2) and US3 (P3) can then proceed in parallel or sequentially.
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 discovery logic but uses the same scorer/fetcher.
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of input source but affects the scorer.

### Parallel Opportunities

- T003, T004 (Setup)
- T005, T006, T007, T008, T009 (Foundational)
- T010, T011, T012 (US1 Tests)
- T013, T014 (US1 Implementation)
- T018, T019 (US2 Tests)
- T023, T024 (US3 Tests)
- T028, T029, T030, T032 (Polish)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for scorer math and tie-breaking in tests/unit/test_scorer.py"
Task: "Unit tests for auth token loading and precedence in tests/unit/test_auth.py"
Task: "Integration tests for topic search and happy-path API interactions (VCR) in tests/integration/test_client.py"

# Launch independent implementation tasks for User Story 1:
Task: "Implement scorer.py for weighted score calculation (rounded to 2 decimal places) and tie-breaking (stars descending)"
Task: "Implement writer.py for CSV output with fixed column order and header (FR-007)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `github-leaderboard --topic` and verify CSV.

### Incremental Delivery

1. Foundation ready (Phase 1 + 2)
2. Add Topic Mode (US1) → MVP Release
3. Add List Mode (US2) → Version 1.1
4. Add Configurable Weights (US3) → Version 1.2
5. Polish (Phase 6) → Production Grade

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD approach: Tests MUST be written and FAIL before implementation
- All fatal errors MUST exit with code 1 (FR-020)
- Rate limits MUST be handled with exponential backoff (FR-006)
