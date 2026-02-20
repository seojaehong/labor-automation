#!/usr/bin/env python3
"""Append /chrome session activity records to cases/{ID}/07_audit/chrome-session-log.csv."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path

FIELDNAMES = [
    "timestamp_utc",
    "platform",
    "action",
    "url",
    "query",
    "result_count",
    "extracted_chars",
    "saved_file",
    "sha256",
    "note",
]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def append_log(
    case_path: Path,
    platform: str,
    action: str,
    *,
    url: str = "",
    query: str = "",
    result_count: int = 0,
    extracted_chars: int = 0,
    saved_file: str = "",
    content_for_hash: str = "",
    note: str = "",
) -> Path:
    """Append one row to chrome-session-log.csv and return the log path."""
    audit_dir = case_path / "07_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_path = audit_dir / "chrome-session-log.csv"

    row = {
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "platform": platform,
        "action": action,
        "url": url,
        "query": query,
        "result_count": result_count,
        "extracted_chars": extracted_chars,
        "saved_file": saved_file,
        "sha256": _sha256(content_for_hash) if content_for_hash else "",
        "note": note,
    }

    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return log_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Log a /chrome session activity to chrome-session-log.csv."
    )
    parser.add_argument("case_path", help="Path to the case folder (e.g. cases/2026-LA-001)")
    parser.add_argument("platform", choices=["lbox", "superlawyer", "bigcase", "other"])
    parser.add_argument("action", help="Action performed (e.g. search, ai_query, extract, save)")
    parser.add_argument("--url", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--result-count", type=int, default=0)
    parser.add_argument("--extracted-chars", type=int, default=0)
    parser.add_argument("--saved-file", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    log_path = append_log(
        case_path=Path(args.case_path),
        platform=args.platform,
        action=args.action,
        url=args.url,
        query=args.query,
        result_count=args.result_count,
        extracted_chars=args.extracted_chars,
        saved_file=args.saved_file,
        note=args.note,
    )
    print(f"Logged to: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
