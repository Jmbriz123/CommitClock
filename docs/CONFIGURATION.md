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
