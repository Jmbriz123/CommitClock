from pathlib import Path

import pytest

from commitclock.config import ConfigError, load_config


def test_precedence_and_secret_repr(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('timezone = "UTC"\nmax_input_chars = 20\n')
    config = load_config(
        config_file,
        {"max_input_chars": 40},
        {
            "COMMITCLOCK_MAX_INPUT_CHARS": "30",
            "GEMINI_API_KEY": "private-value",
        },
    )
    assert config.max_input_chars == 40
    assert config.timezone == "UTC"
    assert config.gemini_api_key == "private-value"
    assert "private-value" not in repr(config)


@pytest.mark.parametrize(
    "overrides",
    [
        {"timezone": "Invalid/Zone"},
        {"start": "25:00"},
        {"eod": "20:00"},
        {"inspect_diffs": "maybe"},
        {"max_input_chars": 0},
        {"max_output_tokens": True},
        {"repository": "/does/not/exist"},
        {"state_dir": Path.cwd()},
        {"templates": {"opening": "{tasks.__class__}"}},
        {"templates": {"opening": "{tasks!r}"}},
        {"sensitive_paths": [1]},
        {"model": 12},
        {"mattermost_url": "https://[invalid"},
        {"mattermost_url": "https://example.com:abc"},
        {"mattermost_url": "https://example.com?token=private"},
        {"mattermost_url": "https://user:password@example.com"},
    ],
)
def test_invalid_configuration_is_actionable(overrides):
    with pytest.raises(ConfigError):
        load_config(overrides=overrides, environ={})


def test_defaults_and_env_booleans():
    config = load_config(environ={"COMMITCLOCK_INSPECT_DIFFS": "false"})
    assert config.timezone == "Asia/Manila"
    assert not config.inspect_diffs
    assert not config.submission_enabled
    assert config.start.hour == 17


def test_bad_toml_does_not_echo_secret(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("gemini_api_key = secret-value")
    with pytest.raises(ConfigError) as error:
        load_config(path, environ={})
    assert "secret-value" not in str(error.value)


@pytest.mark.parametrize("value", ["²", "9" * 5000], ids=["superscript", "oversized"])
@pytest.mark.parametrize("key", ["max_input_chars", "max_output_tokens", "max_requests_per_shift"])
def test_invalid_integer_conversion_produces_safe_config_error(key, value):
    with pytest.raises(ConfigError) as error:
        load_config(overrides={key: value}, environ={})
    assert str(error.value) == f"{key} must be a positive integer"
