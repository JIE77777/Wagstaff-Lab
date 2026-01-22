#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worldgen tools: build index + topology skeleton."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from devtools.build_worldgen_index import main as build_main  # noqa: E402
from devtools.worldgen_topology import main as topo_main  # noqa: E402


def main(argv: list | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wagstaff worldgen", description="Worldgen tools")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("build", help="Build worldgen structure index")
    sub.add_parser("topo", help="Build S3 topology skeleton")

    args, rest = parser.parse_known_args(argv)
    if args.cmd == "build":
        build_main(rest)
        return
    if args.cmd == "topo":
        topo_main(rest)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
