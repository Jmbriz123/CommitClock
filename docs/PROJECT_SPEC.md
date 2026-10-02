# CommitClock — Project Specification

## Project summary

CommitClock is a personal internship assistant that inspects real progress in a Git repository and automates Mattermost clock-in, check-ins, EOD reporting, and clock-out.

## Goal

Turn repository work into accurate, concise internship updates and submit the configured Mattermost commands on the user's work schedule.

## Target user

One intern using CommitClock locally for their own repository and Mattermost account.

## Confirmed choices

- **Runtime:** Python command-line application.
- **Progress evidence:** Read Git commit metadata and committed diffs; do not include uncommitted changes.
- **Mattermost behavior:** Automatically submit configured slash commands.
- **`/ck` interaction:** Submitting `/ck` opens a prompt/form; CommitClock must complete that flow with the generated report.
- **Scheduled user input:** Ask the user for planned tasks/progress through terminal prompts while the scheduler is running.
- **Summary generation:** An external LLM may summarize committed diffs; provider/API remains to be selected.
- **LLM provider:** Gemini API, using a currently available free-tier model where possible; do not enable paid billing by default.
- **Mattermost identity:** Operate through the user's own Mattermost account, not a separate bot identity, if the workspace supports it.
- **Shift:** 5:00 PM–12:00 AM Asia/Manila, crossing midnight.
- **Daily sequence:** `/clkin` at 5:00 PM; opening `/ck` at 5:00 PM with three planned tasks; progress `/ck` at 8:30 PM; EOD `/ck` at 11:30 PM; `/clkout` at 12:00 AM.
- **Progress `/ck`:** Ask what was done and what the user plans next.
- **EOD `/ck`:** Summarize all work accomplished during the full shift.

## Scheduled workflow

The scheduled runner should treat the shift as one workday anchored to its 5:00 PM start, even though it ends on the next calendar date.

| Asia/Manila time | Action | Information needed |
| --- | --- | --- |
| 5:00 PM | Submit `/clkin` | No report text unless the command requires it. |
| 5:00 PM | Submit opening `/ck` | Ask for three planned tasks and include them in the check-in. |
| 8:30 PM | Submit progress `/ck` | Ask what tasks are done/in progress and what comes next; add committed repo evidence. |
| 11:30 PM | Submit EOD `/ck` | Summarize the full shift's completed work, current status, blockers, and next steps. |
| 12:00 AM | Submit `/clkout` | Record the clock-out time after the EOD submission. |

The exact form fields, form submission behavior, and `/clkin` and `/clkout` response behavior remain to be confirmed. The scheduler must not invent or send an unverified command format.

## Runtime behavior

- Provide a foreground scheduler mode that remains running during the shift and triggers actions at the configured times.
- Also provide manual commands for previewing and running an action on demand.
- Require the user to start the scheduler; do not run as a hidden background process by default.
- If the scheduler is offline at a scheduled time, record the missed action and notify the user when available. Do not silently backfill clock-in or clock-out events at a later time.
- Require terminal input for planned tasks and progress updates. If the user does not provide required input, report the pending action and do not send an incomplete or fabricated check-in.
- Log each attempted action, timestamp, payload type, and success/failure without logging credentials.

## Repository evidence

- Default to the configured repository or the current Git repository.
- For each shift, collect commit hashes, timestamps, subjects, branch names, changed file paths, and committed diff content within the shift window.
- Keep the overnight reporting window attached to the date on which the shift began.
- Ignore uncommitted, staged, and unstaged working-tree changes.
- Exclude configured sensitive paths and allow diff inspection to be disabled per repository.
- Treat commits as evidence of changes only. Do not infer that work is complete, tested, merged, or deployed without explicit user input.
- Preserve evidence references locally so a report can be traced to the commits that informed it.

## Reports

Templates must be configurable. The following fields are provisional until the user supplies exact examples.

### Opening check-in — 5:00 PM

- Three tasks planned for the shift

### Progress check-in — 8:30 PM

- Tasks completed so far
- Work in progress
- Next tasks/plans
- Blockers or help needed
- Relevant committed repo activity

### EOD check-in — 11:30 PM

- All work completed during the shift
- Work still in progress
- Blockers
- Next shift's plan
- Relevant committed repo activity across the whole shift

## Mattermost integration

The tool must use the existing `/clkin`, `/ck`, and `/clkout` commands and post or act as the user's own account. Prefer a user-created personal access token (PAT) when the workspace allows it. PATs use the account's Mattermost API permissions, may require an administrator to enable token creation, and do not expire by default. Store the token securely outside the repository and provide instructions to revoke it. Do not require or store the user's raw Mattermost password.

A PAT can authenticate Mattermost REST API requests, but does not by itself reproduce a slash-command interaction or open the `/ck` form. Slash commands are sent to their configured integration endpoint when submitted in the Mattermost client; interactive dialogs are opened from a slash-command trigger. Therefore, use the workspace's supported command integration or an authenticated Mattermost UI session to invoke and complete the form. Confirm which method the workspace permits before building the delivery adapter. Keep report generation separate from delivery and provide preview mode without Mattermost credentials.

Configuration must use environment variables or a local ignored config file. Suggested variables are `MATTERMOST_URL`, `MATTERMOST_ACCESS_TOKEN`, and `GEMINI_API_KEY`. Never commit credentials or log secrets. Use the least-privileged account that still performs the required actions.

## Privacy and model use

- Diff inspection is enabled because the user selected it.
- Use the Gemini API through Google's official Python SDK, with a model name configured rather than permanently hard-coded.
- Prefer a free-tier model and enforce a local request/input-size limit. Do not enable paid billing or fall back to a paid model automatically; stop and report when free quota is unavailable.
- Send only the minimum relevant diff snippets and commit metadata needed for the report; do not send the full repository.
- Exclude configured sensitive paths and secret-like values before sending diff snippets. Explain that Gemini receives the remaining snippets and verify current data-use terms for the selected tier/model during setup.
- Keep API credentials out of source control and logs.
- Do not upload the full repository.

## Functional requirements

- Provide scheduled shift workflow and manual preview/action commands.
- Support configurable shift times, timezone, repository path, and report templates.
- Provide a preview command that shows the evidence and exact payloads without sending any Mattermost request.
- Prevent duplicate submissions where possible using a local action log and idempotency checks.
- Show success only when Mattermost confirms submission; surface failures and unknown outcomes clearly.
- Give useful setup and runtime errors for invalid repositories, missing configuration, missing user input, authentication issues, and failed delivery.
- Include an option to disable scheduling and an option to disable Mattermost submission.

## Non-goals for the MVP

- Hidden background scheduling or automatic startup on boot.
- Backfilling missed clock events.
- Inferring completion, testing, deployment, or merge status solely from commits.
- Multi-user or team-wide reporting.
- Reading or uploading the full repository by default.

## Quality and security requirements

- Separate scheduling, Git evidence collection, report generation, user prompts, and Mattermost delivery into distinct modules.
- Keep credentials out of source control and logs.
- Test overnight shift-window selection, scheduled action times, committed diff selection, report formatting, payload construction, duplicate prevention, and failed submission handling.
- Verify preview mode never sends a Mattermost request.
- Document setup, supported Mattermost configuration, privacy behavior, and how to disable the integration.

## Open questions before implementation

1. What are the exact fields in the `/ck` form, and what happens after it is submitted?
2. Does your workspace allow personal access tokens, and can you use the existing Mattermost UI session if PAT access cannot invoke `/ck` and its form?
3. Please share redacted examples of your opening, progress, and EOD check-ins if the provisional fields need to match an existing format.
4. Is it acceptable for sanitized committed diff snippets to be sent to Gemini's free tier, subject to the provider's current data-use terms?
