"""Command line entry point: ``python -m src.task_parser <task_spec.md>``."""

from __future__ import annotations

import argparse
import sys

from .parser import TaskParser, to_json


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(
        description="Parse a task_spec.md file into a TaskRequirement JSON object."
    )
    cli.add_argument("task_spec", help="Path to task_spec.md")
    cli.add_argument(
        "--limitations",
        default=None,
        help="Optional path to limitations.md for conflict checking",
    )
    cli.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation width (default: 2)",
    )
    args = cli.parse_args(argv)

    requirement = TaskParser().parse_file(
        args.task_spec, limitations_path=args.limitations
    )
    print(to_json(requirement, indent=args.indent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
