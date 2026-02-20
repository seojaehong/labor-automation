#!/usr/bin/env python3
"""Merge IRAC markdown into case data JSON for template rendering.

Usage:
    python prepare_case_data.py data.json irac.md -o merged.json

The merged JSON can then be fed to render_hwpx.py or used standalone.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def merge_irac_into_data(data: dict[str, str], irac_text: str) -> dict[str, str]:
    """Inject IRAC markdown text into the 신청이유_IRAC field."""
    data["신청이유_IRAC"] = irac_text
    return data


def prepare_case_data(data_path: Path, irac_path: Path, output_path: Path) -> dict[str, str]:
    """Read data JSON + IRAC markdown, merge, and write output JSON."""
    data = json.loads(data_path.read_text(encoding="utf-8"))
    irac_text = irac_path.read_text(encoding="utf-8")

    merged = merge_irac_into_data(data, irac_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge IRAC into case data JSON.")
    parser.add_argument("data", help="Path to case data JSON")
    parser.add_argument("irac", help="Path to IRAC markdown file")
    parser.add_argument("--output", "-o", required=True, help="Output merged JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_path = Path(args.data)
    irac_path = Path(args.irac)
    output_path = Path(args.output)

    if not data_path.exists():
        raise SystemExit(f"Data file not found: {data_path}")
    if not irac_path.exists():
        raise SystemExit(f"IRAC file not found: {irac_path}")

    merged = prepare_case_data(data_path, irac_path, output_path)
    print(f"Merged JSON: {output_path}")
    print(f"IRAC length: {len(merged.get('신청이유_IRAC', ''))} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
