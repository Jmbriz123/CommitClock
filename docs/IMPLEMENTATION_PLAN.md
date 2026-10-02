# CommitClock implementation plan

## Summary

Build the Python CLI described in `docs/PROJECT_SPEC.md` through sequential,
independently verified milestones. Use `commitclock` for the package and executable.
Implement the local workflow first. Live Mattermost delivery and Gemini use require
the explicit checkpoints below; missing integration details must never be guessed.

## Implementation and Git rules

- Read the specification, this plan, and the progress log before changing code.
- Execute milestones in order. Finish and merge each branch before creating the
  next branch from updated `main`.
- Make each numbered change below a separate atomic commit, including relevant
  tests and documentation. Additional fixes get separate focused commits.
- Never combine milestones into bulk commits or squash atomic history on merge.
- Stage explicit files, inspect staged diffs for unrelated changes and secrets,
  and run relevant checks before committing. Leave existing checks passing.
- Record completed steps, verification results, commit references, blockers, and
  next steps in `docs/IMPLEMENTATION_PROGRESS.md`. Record a commit's resulting hash
  in the next progress update; do not attempt to embed its own hash.
- Stop dependent work at unresolved gates. Mocked integrations are not live
  integration completion. Pushes, PRs, and merges require session authorization.

## Ordered branches and atomic commits

### 0. Establish the implementation contract

Branch: `docs/project-specs`

1. `docs: establish CommitClock project specification`: track the existing spec
   and align README naming without changing requirements.
2. `docs: define implementation sequence and contribution rules`: preserve this
   plan, root agent instructions, and an initial progress log.

Checkpoint: map every specification requirement to a milestone or explicit gate;
merge before code.

### 1. Bootstrap the application

Branch: `chore/python-foundation`

1. `build: bootstrap CommitClock Python CLI`: Python 3.11+, src/commitclock,
   pyproject.toml, setuptools, argparse, pytest, Ruff, credential/config/state ignores.
2. `feat: add validated local configuration`: defaults, optional TOML, environment,
   then explicit CLI overrides; validate repository, IANA timezone, times, feature
   switches, templates, exclusions, model limits.
3. `ci: verify lint tests and package installation`: automated lint, tests, package
   installation and CLI smoke checks.

Checkpoint: clean checkout installs; `commitclock --help` needs no credentials.

### 2. Model shifts and persist action state

Branch: `feat/shift-state`

1. `feat: model overnight shifts and scheduled actions`: timezone-aware shifts and
   actions, previous-date midnight clock-out, clock-in before same-time opening.
2. `feat: persist action attempts and duplicate guards`: external SQLite state;
   identity includes workspace/channel, shift start and action; pending, in-flight,
   confirmed, failed, missed and unknown outcomes.
3. `feat: expose action status and redacted audit logs`: status CLI, structured
   attempts, credential redaction, concurrent-process duplicate prevention.

Checkpoint: overnight/custom schedule, restart, concurrency, duplicate tests;
interrupted in-flight attempts become unknown and are not automatically resent.

### 3. Collect committed Git evidence

Branch: `feat/git-evidence`

1. `feat: collect commits within the shift window`: Git argument arrays; commits
   reachable from current HEAD, committer timestamp in [shift start, collection time),
   capped at shift end; hashes, subjects, timestamps, paths, observed branch context.
2. `feat: filter and bound committed diff evidence`: committed patches only;
   sensitive-path exclusions, secret-like-value redaction, binary omission, input
   limits, metadata-only option.
3. `feat: retain local report evidence references`: persist report-to-commit
   references and collection context without unnecessary raw diff duplication.

Checkpoint: temporary repos prove staged/unstaged/untracked/out-of-window changes
are absent; cover empty windows, detached HEAD, merge commits, exclusions, large
patches. Never claim Git records a commit's original branch.

### 4. Generate local reports and previews

Branch: `feat/reports-preview`

1. `feat: capture opening progress and end-of-day input`: exactly three opening
   tasks; progress, next tasks, optional blockers; reuse recorded shift input for
   EOD, prompt for missing facts, never infer completion from commits.
2. `feat: render configurable evidence-backed reports`: opening/progress/EOD
   templates separate user statements from repository evidence.
3. `feat: add offline action previews`: `preview <action>` shows evidence, report
   text, and verified payload if available; until verified, label draft and delivery
   payload unavailable.

Checkpoint: rendering/missing-input/no-commit/full-shift EOD tests; no credentials
or Mattermost requests for preview.

### 5. Add Gemini summarization behind a setup gate

Branch: `feat/gemini-summaries`

1. `feat: add summarizer interface and local fallback`: deterministic independent
   local reports; commit content is untrusted data, never instructions.
2. `docs: establish Gemini privacy and model setup gate`: verify current official
   SDK guidance, model availability, free limits, data terms; record configurable
   selected model and obtain explicit consent for sanitized snippet transmission.
3. `feat: integrate bounded Gemini summarization`: only after gate; official Google
   Python SDK, input/output/request limits, filtered evidence, quota errors, no
   automatic model switch or billing enablement.

Checkpoint: mock redaction/truncation/quota/auth/unsupported-claim/fallback tests.
Local limits cannot guarantee free billing; verify user's free-tier configuration
before enabling requests.

### 6. Verify and implement Mattermost delivery

Branch: `feat/mattermost-delivery`

1. `feat: define delivery contracts and disabled adapter`: separate construction,
   submission, confirmation; `run <action>` blocked until live setup is verified.
2. `docs: record verified Mattermost command contracts`: obtain redacted examples,
   fields, permitted access, command/form sequence, responses, confirmation signals,
   PAT/UI availability; verify official docs and actual workspace behavior.
3. `feat: implement verified Mattermost delivery adapter`: only verified route;
   prefer supported authenticated API, UI only if required/permitted; external
   tokens/session data, no raw password, actual /ck form completion.
4. `feat: handle delivery confirmation and uncertain outcomes`: success only with
   confirmation; distinguish failure/unknown, reconcile before possible duplicates.

Checkpoint: fixtures for exact fields/order/expired auth/form changes/rejection/
timeout/confirmation. Real submissions only in explicitly authorized test context.
Keep milestone blocked if access/form details unavailable.

### 7. Run the foreground scheduler

Branch: `feat/foreground-scheduler`

1. `feat: schedule ordered foreground shift actions`: injectable clock/persisted
   actions, 17:00 clock-in/opening, 20:30 progress, 23:30 EOD, next-day 00:00 clock-out,
   Asia/Manila; `schedule` command.
2. `feat: coordinate terminal prompts and pending actions`: input separate from
   loop, unanswered prompts don't freeze later events, incomplete input stays pending.
3. `feat: record missed events and recover safely`: downtime/interruption detection,
   missed notifications without backfill, disable flags, shutdown, duplicate guards,
   confirmed EOD before clock-out.

Checkpoint: simulated complete overnight sequence, unanswered prompts, restart
post-midnight, missed actions, failed EOD, unknown delivery; no real-time waits.

### 8. Complete operational documentation and acceptance

Branch: `docs/mvp-acceptance`

1. `docs: document setup privacy and recovery procedures`: installation, config,
   supported transport, consent, revocation, session protection, retention, manual
   commands, missed/unknown actions, disabling integrations.
2. `test: verify complete CommitClock shift workflow`: temporary Git repo, fake
   clock, terminal input, mocked Gemini, verified delivery fixtures.
3. `docs: record MVP acceptance and remaining limitations`: actual verification
   results, requirements checklist, external blockers.

Checkpoint: clean install, lint, unit/end-to-end tests; no tracked/logged secrets;
no Mattermost preview requests; uncertain submissions never appear successful.

## Interfaces and defaults

- Actions: clkin, opening, progress, eod, clkout, shared by preview/run.
- Separate configuration, shift, state, evidence, prompt, report, summarization,
  delivery, and scheduling modules.
- Shared types: shift window, action identity, commit evidence, user input, report
  draft, delivery payload, delivery result.
- External private config/application-data directories for SQLite and config.
- Explicit foreground scheduling only; no daemon or auto-start.
- Provisional report fields until verified examples require changes.
- Record verified live adapter contracts before coding; never guess transport.

## Requirement coverage

| Specification area | Milestones |
| --- | --- |
| CLI/configuration/disable switches | 1, 4, 6, 7 |
| Overnight sequence/manual/scheduled workflow | 2, 4, 6, 7 |
| Committed evidence/exclusions/traceability | 3 |
| Prompts/templates/factual reports | 4, 5 |
| Gemini privacy/model/quota | 5 (explicit setup gate) |
| Own-account commands/forms/confirmation | 6 (workspace gate) |
| Logs/duplicates/failure/missed events | 2, 6, 7 |
| Documentation/security/acceptance | Every milestone, final acceptance in 8 |
