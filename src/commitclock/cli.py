"""Command-line interface; importing this module performs no I/O."""

import argparse
from collections.abc import Sequence

from commitclock import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="commitclock", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args(argv)
    parser.print_help()
    return 0
