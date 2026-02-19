#!/usr/bin/env python3
"""Render an hwpx template by replacing {{placeholder}} tokens with case data.

hwpx is a ZIP archive containing OWPML XML files. This script:
1. Opens the template hwpx (ZIP)
2. Finds all XML files under Contents/
3. Replaces {{placeholder}} tokens with provided values
4. Saves the result as a new hwpx file
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render hwpx from template + data.")
    parser.add_argument("template", help="Path to template .hwpx file")
    parser.add_argument("data", help="Path to JSON data file with placeholder values")
    parser.add_argument("--output", "-o", required=True, help="Output .hwpx path")
    return parser.parse_args()


def replace_placeholders(xml_text: str, data: dict[str, str]) -> str:
    """Replace {{key}} tokens in XML text with values from data dict."""
    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        return data.get(key, match.group(0))  # keep original if key not found

    return re.sub(r"\{\{([^}]+)\}\}", replacer, xml_text)


def render_hwpx(template_path: Path, data: dict[str, str], output_path: Path) -> list[str]:
    """Open template hwpx, replace placeholders, save as new hwpx.

    Returns list of replaced file names for logging.
    """
    replaced_files: list[str] = []

    buf = BytesIO()
    with zipfile.ZipFile(template_path, "r") as src, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            raw = src.read(item.filename)
            lower = item.filename.lower()

            if lower.endswith(".xml") and ("contents/" in lower or "content/" in lower):
                try:
                    xml_text = raw.decode("utf-8")
                    new_text = replace_placeholders(xml_text, data)
                    if new_text != xml_text:
                        replaced_files.append(item.filename)
                    dst.writestr(item, new_text.encode("utf-8"))
                except UnicodeDecodeError:
                    dst.writestr(item, raw)
            else:
                dst.writestr(item, raw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buf.getvalue())
    return replaced_files


def main() -> int:
    args = parse_args()
    template_path = Path(args.template)
    data_path = Path(args.data)
    output_path = Path(args.output)

    if not template_path.exists():
        raise SystemExit(f"Template not found: {template_path}")
    if not data_path.exists():
        raise SystemExit(f"Data file not found: {data_path}")

    data = json.loads(data_path.read_text(encoding="utf-8"))
    replaced = render_hwpx(template_path, data, output_path)

    print(f"hwpx generated: {output_path}")
    if replaced:
        print(f"Placeholders replaced in: {', '.join(replaced)}")
    else:
        print("Warning: No placeholders were replaced. Check template tokens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
