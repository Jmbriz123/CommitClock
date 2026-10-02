# Implementation progress

## Current status

Milestones 0–2 complete. Next: merge feat/shift-state and begin milestone 3.
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
- 2.2: bd2c541; independent review found no state/locking correctness blockers.
- 2.3: structured status/audit output and credential redaction added. Explicit
  status recovery shares the submission lock. Validation: 41 tests pass, Ruff
  passes. Review found malformed URL validation needs a focused fix before merge.

- 2.3: 57221fd.
- Focused fix: malformed Mattermost hostnames/ports now produce ConfigError; URL
  queries/fragments are rejected to avoid credentials in action identity. Validation:
  44 tests and Ruff pass. Milestone 2 complete.

## Milestone 3

- Milestone 2 fix: 895b52c; merged as 1c4a28e. Existing upstream documentation
  history retained via 6525289 before creating feat/git-evidence.
- Focused configuration fix: invalid Unicode/oversized integer values now produce
  credential-free ConfigError messages. Validation: 25 configuration tests pass.
  Committed-evidence collector and privacy regression tests are in progress.
