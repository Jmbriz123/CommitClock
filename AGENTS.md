# CommitClock contributor instructions

Before changing code, read docs/PROJECT_SPEC.md, docs/IMPLEMENTATION_PLAN.md,
and docs/IMPLEMENTATION_PROGRESS.md.

Follow the numbered milestones and atomic commit boundaries in the plan. Complete
and merge a milestone branch before branching from updated main for the next one.
Never squash milestone history or combine numbered changes in bulk commits. Include
relevant tests/docs with each change and use the specified conventional messages.
Stage explicit paths, inspect the staged diff for unrelated changes and secrets,
and run relevant checks before each commit. Additional fixes are separate commits.

Update the progress log with completed steps, verification, blockers, and next step.
Record resulting commit hashes in the next update, never self-reference a commit.
Stop dependent work at unresolved gates. Never guess a live command contract or
claim mocked integrations prove live completion. Preserve credentials outside Git.
Pushing, PRs and merging follow the authorization of the current user session.
