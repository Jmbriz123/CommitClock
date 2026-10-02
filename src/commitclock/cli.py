"""Command-line interface; importing this module performs no I/O."""

import argparse
import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from commitclock import __version__
from commitclock.audit import audit_snapshot
from commitclock.config import ConfigError, load_config
from commitclock.state import StateError, StateStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="commitclock", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="Explicit local TOML configuration")
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--timezone")
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument(
        "--no-scheduling", dest="scheduling_enabled", action="store_false", default=None
    )
    parser.add_argument(
        "--no-submission", dest="submission_enabled", action="store_false", default=None
    )
    parser.add_argument("--no-diffs", dest="inspect_diffs", action="store_false", default=None)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "check-config", help="Validate local configuration without service requests"
    )
    status_parser = subparsers.add_parser("status", help="Show local action and attempt status")
    status_parser.add_argument(
        "--recover-interrupted",
        action="store_true",
        help="Mark abandoned attempts unknown under the submission lock",
    )
    args = parser.parse_args(argv)
    if args.command:
        try:
            config = load_config(
                args.config,
                {
                    key: getattr(args, key)
                    for key in (
                        "repository",
                        "timezone",
                        "state_dir",
                        "scheduling_enabled",
                        "submission_enabled",
                        "inspect_diffs",
                    )
                },
            )
            if args.command == "status":
                with StateStore(config.state_dir) as state:
                    if args.recover_interrupted:
                        with state.submission_lock():
                            state.recover_interrupted()
                    print(
                        json.dumps(
                            audit_snapshot(
                                state, (config.gemini_api_key, config.mattermost_access_token)
                            ),
                            indent=2,
                        )
                    )
                return 0
        except (ConfigError, StateError) as error:
            parser.error(str(error))
        except (OSError, sqlite3.Error):
            parser.error("Cannot access local state; check its directory and permissions")
        print("Configuration is valid. Live integrations remain gated.")
        return 0
    parser.print_help()
    return 0
