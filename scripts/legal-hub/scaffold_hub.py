#!/usr/bin/env python3
"""Create a local legal hub workspace for one matter."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


FOLDERS = [
    "00_inbox",
    "01_sources",
    "02_notes",
    "02_notes/cards",
    "03_drafts",
    "04_final",
    "templates",
]


CURSOR_RULES_TEMPLATE = """# Role
You are a senior Korean legal drafting copilot.

# Non-Negotiable Rules
1. Use only files under this matter folder as evidence.
2. Do not invent facts, case numbers, or holdings.
3. Mark uncertain statements as [CHECK_NEEDED].
4. Keep the section order: Issue, Rule, Application, Conclusion, Relief.
5. Keep heading structure unchanged unless explicitly instructed.
6. When citing a case, include court, decision date, and case number.

# Output Policy
- Draft output target file: 03_drafts/draft.md
- Keep legal tone direct, concise, and formal.
"""


MATTER_PACK_TEMPLATE = """# Matter Pack

## Matter Metadata
- matter_id: {matter_id}
- title: {title}
- created_at_utc: {created_at}
- status: intake

## Core Facts
- claimant:
- respondent:
- timeline:
- objective:

## Issues
1.
2.
3.

## Authority Card Index
| card | source_file | case_numbers | courts |
|---|---|---|---|
| (pending) | - | - | - |

## Drafting Constraints
- No fabricated authority.
- Mark unknown fact as [CHECK_NEEDED].
- Keep IRAC structure.
"""


CARD_TEMPLATE = """# Authority Card Template

## Metadata
- source_file:
- extracted_at_utc:
- extracted_chars:
- case_numbers:
- courts:
- dates:

## Holding Summary
- 

## Application Point
- 

## Reliability
- high | medium | low
"""


DRAFT_TEMPLATE = """# Draft

## Issue

## Rule

## Application

## Conclusion

## Relief
"""


def sanitize_name(value: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|]+', "-", value)
    clean = re.sub(r"\s+", "_", clean).strip("._-")
    return clean or "matter"


def write_file(path: Path, content: str, overwrite: bool = False) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def create_workspace(root: Path, matter_id: str, title: str, overwrite_rules: bool) -> Path:
    safe_id = sanitize_name(matter_id)
    matter_dir = root / safe_id
    matter_dir.mkdir(parents=True, exist_ok=True)

    for folder in FOLDERS:
        (matter_dir / folder).mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    meta = {
        "matter_id": safe_id,
        "title": title or "TBD",
        "created_at_utc": created_at,
        "status": "intake",
    }
    write_file(matter_dir / "matter-meta.json", json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    write_file(matter_dir / ".cursorrules", CURSOR_RULES_TEMPLATE, overwrite=overwrite_rules)
    write_file(
        matter_dir / "02_notes/matter-pack.md",
        MATTER_PACK_TEMPLATE.format(matter_id=safe_id, title=title or "TBD", created_at=created_at),
    )
    write_file(matter_dir / "02_notes/authority-card-template.md", CARD_TEMPLATE)
    write_file(matter_dir / "03_drafts/draft.md", DRAFT_TEMPLATE)
    write_file(
        matter_dir / "templates/readme.md",
        "# Templates\n\nStore your standard filing templates here (opinion, petition, response).\n",
    )

    return matter_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a legal hub workspace for one matter.")
    parser.add_argument("matter_id", help="Matter identifier (e.g., 2026-ga-1234)")
    parser.add_argument("--title", default="", help="Human-readable title")
    parser.add_argument("--root", default="MATTERS", help="Workspace root directory")
    parser.add_argument(
        "--overwrite-rules",
        action="store_true",
        help="Overwrite existing .cursorrules file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matter_dir = create_workspace(
        root=Path(args.root),
        matter_id=args.matter_id,
        title=args.title,
        overwrite_rules=args.overwrite_rules,
    )

    print(f"Workspace ready: {matter_dir}")
    print("Next:")
    print(f"1) Put exports into: {matter_dir / '00_inbox'}")
    print(f"2) Build cards: python scripts/legal-hub/build_matter_pack.py \"{matter_dir}\"")
    print(f"3) Render docx: python scripts/legal-hub/render_docx.py \"{matter_dir}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
