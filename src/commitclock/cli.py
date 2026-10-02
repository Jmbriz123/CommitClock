"""Command-line interface; importing this module performs no I/O."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from commitclock import __version__
from commitclock.config import ConfigError, load_config


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
    args = parser.parse_args(argv)
    if args.command:
        try:
            load_config(
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
        except ConfigError as error:
            parser.error(str(error))
        print("Configuration is valid. Live integrations remain gated.")
        return 0
    parser.print_help()
    return 0
