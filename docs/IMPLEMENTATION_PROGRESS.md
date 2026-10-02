# Implementation progress

## Current status

Milestones 0–1 complete and merged locally. Milestone 2 underway on feat/shift-state.
The user requested implementation of sequential branches and merges; local merges
are authorized for this session. No remote push or real service submission planned.

## Completed changes

- Existing specification was already tracked by e631304 before implementation.
- 0.1: e8f71c3 aligned README naming; reviewed specification unchanged.
- 0.2: preserved implementation sequence, contributor instructions, and requirement
  coverage; verified all specification areas map to milestones or explicit gates.

## External gates

- 5.2: verify provider terms/model/free-tier configuration and explicit user consent
  before implementing Gemini transmission.
- 6.2: actual Mattermost fields, permitted access and confirmation contract required.

## Milestone 1

- 0.2: bb4fe2c; milestone 0 merged locally as b467148.
- 1.1: Python package, argparse entry point, dev dependencies and ignore rules added.
  Validation: CLI help and initial pytest smoke test. Next: validated configuration.
- 1.1: f3b5169.
- 1.2: validated configuration and check-config command added; 17 tests pass and
  Ruff passes. Dependency installation succeeded in the isolated .venv after the
  sandbox's network restriction required an approved download. Next: CI/install checks.
- 1.2: 60fdd15.
- 1.3: CI matrix for Python 3.11–3.13; lint/format/17 tests, CLI help/check-config,
  editable install, wheel build and fresh-environment wheel installation passed
  locally on Python 3.12. CI execution on other versions awaits a remote run.
  Milestone 1 complete; next: shift model and state persistence.

## Milestone 2

- 1.3: b028590; milestone 1 merged before this branch.
- 2.1: dated shifts, ordered actions, UTC identities, midnight anchoring and DST
  handling implemented. Validation: 17 shift tests plus 17 prior tests pass; Ruff
  passes. Next: action journal and duplicate guards.
- 2.1: 0ecef06.
- 2.2: private SQLite action/attempt journal, exclusive submission lock, duplicate
  guards, attempt ownership and interrupted recovery added. Validation: 38 tests
  pass, including a real subprocess killed during a claim and recovery blocked by
  a live sender; Ruff passes. Next: redacted audit/status output.
