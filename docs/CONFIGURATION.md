# Local configuration

Install with `python -m pip install -e '.[dev]'`. Python 3.11+ and Git are required.
`commitclock --help` works without credentials. Integration commands are added in
later milestones; live service access remains gated.

Configuration precedence is defaults < TOML < environment < explicit CLI options.
The optional default TOML file is `$XDG_CONFIG_HOME/commitclock/config.toml` (or
`~/.config/commitclock/config.toml`). Keep private configuration outside Git;
`*.local.toml` and `.env*` are ignored for explicit local configurations.

```toml
repository = "/absolute/path/to/your/repository"
timezone = "Asia/Manila"
start = "17:00"
progress = "20:30"
eod = "23:30"
end = "00:00"
scheduling_enabled = true
submission_enabled = false
inspect_diffs = true
sensitive_paths = [".env*", "*.pem", "*.key", "credentials*", "secrets/**"]
max_input_chars = 16000
max_output_tokens = 600
max_requests_per_shift = 2

[templates]
opening = "Planned tasks (user supplied):\n{tasks}"
```

Environment names use `COMMITCLOCK_` plus the upper-case field name, except
`MATTERMOST_URL`, `MATTERMOST_CHANNEL`, `MATTERMOST_ACCESS_TOKEN`, and
`GEMINI_API_KEY`. Boolean environment values accept true/false or 1/0.
`COMMITCLOCK_SENSITIVE_PATHS` accepts comma-separated patterns. Templates are TOML
only and support plain named placeholders: tasks, completed, in_progress,
next_tasks, blockers, evidence. Format specs/conversions/attribute access are rejected.

State defaults to `$XDG_STATE_HOME/commitclock` or `~/.local/state/commitclock`;
`state_dir` must be outside the inspected repository. Credentials are never included
in configuration repr. Diff redaction and provider consent are separate gates;
setting an API key alone never authorizes transmission.

Run `commitclock --config /path/to/config.toml check-config` to validate. Global
options go before the subcommand: `--repository`, `--timezone`, `--state-dir`,
`--no-diffs`, `--no-submission`, and `--no-scheduling`.

## Shift dates and daylight saving time

A shift belongs to the local date on which it starts. Under the default schedule,
clock-out at exactly midnight on October 3 belongs to the October 2 shift. Manual
selection uses the most recently started shift, including the time between its
end and the next start. Clock-in precedes opening when both share the same time.
Evidence includes timestamps at shift start and excludes its collection-time upper
bound, capped at shift end; before a shift begins its evidence window is empty.

Configured times are local wall-clock times in the configured IANA timezone. For a
repeated daylight-saving time, use the first occurrence. A scheduled time skipped
by a daylight-saving transition causes an explicit error for that dated schedule;
adjust the schedule instead of silently moving an attendance event. Action ordering,
evidence boundaries, and stored shift identities use UTC instants. Elapsed shift
duration can therefore change across daylight-saving transitions. IANA timezone
data must be available on the host for the configured zone.
