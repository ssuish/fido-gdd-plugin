"""JSON command-line adapter for the detector engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import ScanConfig, ScanFailure
from .scanner import scan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--gdd", required=True, action="append", type=Path)
    parser.add_argument("--source", required=True, action="append", type=Path)
    parser.add_argument("--json", required=True, action="store_true")
    args = parser.parse_args()
    try:
        result = scan(
            args.project_root, ScanConfig(tuple(args.gdd), tuple(args.source))
        )
    except ScanFailure as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
