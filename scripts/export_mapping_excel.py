#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.curam_tables_parser import json_to_excel


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the current multi-agent tables_json.json result to Excel."
    )
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.mapping.exists():
        parser.error(f"Mapping file not found: {args.mapping}")

    json_to_excel(args.mapping, args.output, sheet_name="results")
    print(f"[OK] Excel mapping exported to: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())