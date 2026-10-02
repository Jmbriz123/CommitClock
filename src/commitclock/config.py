"""Validated configuration. Credentials are deliberately excluded from repr output."""

import os
import string
import subprocess
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(ValueError):
    """An actionable, credential-free configuration error."""


ACTIONS = ("clkin", "opening", "progress", "eod", "clkout")
REPORT_FIELDS = {"tasks", "completed", "in_progress", "next_tasks", "blockers", "evidence"}
DEFAULT_TEMPLATES = {
    "opening": "Planned tasks (user supplied):\n{tasks}",
    "progress": (
        "User update\nCompleted: {completed}\nIn progress: {in_progress}\n"
        "Next: {next_tasks}\nBlockers: {blockers}\n\nRepository evidence:\n{evidence}"
    ),
    "eod": (
        "End of shift — user update\nCompleted: {completed}\nIn progress: {in_progress}\n"
        "Next shift: {next_tasks}\nBlockers: {blockers}\n\n"
        "Full-shift repository evidence:\n{evidence}"
    ),
}


@dataclass(frozen=True)
class Config:
    repository: Path
    state_dir: Path
    timezone: str = "Asia/Manila"
    start: time = time(17)
    progress: time = time(20, 30)
    eod: time = time(23, 30)
    end: time = time(0)
    scheduling_enabled: bool = True
    submission_enabled: bool = False
    inspect_diffs: bool = True
    sensitive_paths: tuple[str, ...] = (".env*", "*.pem", "*.key", "credentials*", "secrets/**")
    max_input_chars: int = 16000
    max_output_tokens: int = 600
    max_requests_per_shift: int = 2
    model: str = ""
    mattermost_url: str = ""
    mattermost_channel: str = ""
    mattermost_access_token: str = field(default="", repr=False)
    gemini_api_key: str = field(default="", repr=False)
    templates: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TEMPLATES))


def _base(env: Mapping[str, str], variable: str, default: Path) -> Path:
    value = Path(env.get(variable, str(default))).expanduser()
    if not value.is_absolute():
        raise ConfigError(f"{variable} must be an absolute path")
    return value


def _bool(value: object, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false", "1", "0"}:
        return value.lower() in {"true", "1"}
    raise ConfigError(f"{key} must be true or false")


def _time(value: object, key: str) -> time:
    try:
        result = time.fromisoformat(str(value))
    except ValueError:
        raise ConfigError(f"{key} must be HH:MM") from None
    if result.tzinfo or result.second or result.microsecond:
        raise ConfigError(f"{key} must be a local HH:MM time")
    return result


def validate_templates(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) - set(DEFAULT_TEMPLATES):
        raise ConfigError("templates must contain opening, progress, or eod strings")
    result = dict(DEFAULT_TEMPLATES)
    for name, template in value.items():
        if not isinstance(template, str) or not template.strip():
            raise ConfigError(f"templates.{name} must be a nonempty string")
        try:
            fields = list(string.Formatter().parse(template))
        except ValueError:
            raise ConfigError(f"templates.{name} has invalid braces") from None
        if any(
            f is not None and (f not in REPORT_FIELDS or spec or conv)
            for _, f, spec, conv in fields
        ):
            raise ConfigError(f"templates.{name} has an unsupported placeholder")
        result[name] = template
    return result


def load_config(
    path: Path | None = None,
    overrides: Mapping[str, object] | None = None,
    environ: Mapping[str, str] | None = None,
) -> Config:
    env = os.environ if environ is None else environ
    home = Path.home()
    config_path = (
        path or _base(env, "XDG_CONFIG_HOME", home / ".config") / "commitclock/config.toml"
    )
    values: dict = {}
    if path is not None or config_path.exists():
        try:
            with config_path.open("rb") as handle:
                values = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            raise ConfigError("Cannot read configuration as TOML; check file and syntax") from None
    known = set(Config.__dataclass_fields__)
    if set(values) - known:
        raise ConfigError("Configuration contains unsupported keys")
    for key in known - {"templates"}:
        name = (
            key.upper()
            if key.startswith(("mattermost_", "gemini_"))
            else f"COMMITCLOCK_{key.upper()}"
        )
        if name in env:
            values[key] = env[name]
    values.update({k: v for k, v in (overrides or {}).items() if v is not None})
    if set(values) - known:
        raise ConfigError("CLI configuration contains unsupported keys")
    for key in ("scheduling_enabled", "submission_enabled", "inspect_diffs"):
        if key in values:
            values[key] = _bool(values[key], key)
    for key in ("start", "progress", "eod", "end"):
        if key in values:
            values[key] = _time(values[key], key)
    for key in ("max_input_chars", "max_output_tokens", "max_requests_per_shift"):
        if key in values:
            raw = values[key]
            if isinstance(raw, bool) or not str(raw).isdigit() or int(raw) <= 0:
                raise ConfigError(f"{key} must be a positive integer")
            values[key] = int(raw)
    for key in (
        "timezone",
        "model",
        "mattermost_url",
        "mattermost_channel",
        "mattermost_access_token",
        "gemini_api_key",
    ):
        if key in values and not isinstance(values[key], str):
            raise ConfigError(f"{key} must be a string")
    try:
        ZoneInfo(values.get("timezone", "Asia/Manila"))
    except (ValueError, ZoneInfoNotFoundError):
        raise ConfigError("timezone must be a valid IANA timezone") from None
    exclusions = values.get(
        "sensitive_paths", Config.__dataclass_fields__["sensitive_paths"].default
    )
    if isinstance(exclusions, str):
        exclusions = exclusions.split(",")
    if not isinstance(exclusions, (list, tuple)) or any(
        not isinstance(p, str) or not p.strip() for p in exclusions
    ):
        raise ConfigError("sensitive_paths must be a list of nonempty glob patterns")
    values["sensitive_paths"] = tuple(exclusions)
    values["templates"] = validate_templates(values.get("templates", {}))
    try:
        repo = Path(values.get("repository", Path.cwd())).expanduser().resolve()
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        values["repository"] = Path(result.stdout.strip()).resolve()
    except (OSError, TypeError, ValueError, subprocess.CalledProcessError):
        raise ConfigError(
            "repository must be inside an accessible Git working repository"
        ) from None
    try:
        state = (
            Path(
                values.get(
                    "state_dir", _base(env, "XDG_STATE_HOME", home / ".local/state") / "commitclock"
                )
            )
            .expanduser()
            .resolve()
        )
    except (TypeError, ValueError):
        raise ConfigError("state_dir must be a filesystem path") from None
    if state.is_relative_to(values["repository"]):
        raise ConfigError("state_dir must be outside the repository")
    values["state_dir"] = state
    config = Config(**values)

    def minute(t: time) -> int:
        return t.hour * 60 + t.minute

    offsets = [
        (minute(t) - minute(config.start)) % 1440 for t in (config.progress, config.eod, config.end)
    ]
    if not 0 < offsets[0] < offsets[1] < offsets[2]:
        raise ConfigError("schedule must order start, progress, eod, end within one day")
    if config.mattermost_url:
        from urllib.parse import urlsplit

        try:
            url = urlsplit(config.mattermost_url)
            port = url.port
        except ValueError:
            raise ConfigError("mattermost_url has an invalid hostname or port") from None
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or port == 0
        ):
            raise ConfigError("mattermost_url must be HTTPS without credentials, query or fragment")
    return config
