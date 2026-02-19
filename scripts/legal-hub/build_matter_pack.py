#!/usr/bin/env python3
"""Build authority cards and a matter pack index from inbox files."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".hwpx", ".hwp"}
COURT_PATTERNS = [
    "대법원",
    "고등법원",
    "지방법원",
    "가정법원",
    "행정법원",
    "헌법재판소",
    "중앙노동위원회",
    "지방노동위원회",
]


@dataclass
class SourceCard:
    source_path: Path
    card_path: Path
    text_len: int
    case_numbers: list[str]
    courts: list[str]
    dates: list[str]
    summary: str
    warnings: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create authority cards from inbox files.")
    parser.add_argument("matter_path", help="Matter folder path")
    parser.add_argument("--inbox", default="00_inbox", help="Inbox folder name")
    parser.add_argument("--cards", default="02_notes/cards", help="Output cards folder")
    parser.add_argument("--matter-pack", default="02_notes/matter-pack.md", help="Matter pack output file")
    parser.add_argument("--max-summary-chars", type=int, default=900, help="Summary max chars per card")
    parser.add_argument(
        "--keep-history",
        action="store_true",
        help="Keep existing cards and append numeric suffix for new runs",
    )
    return parser.parse_args()


def strip_xml_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    parts: list[str] = []
    for node in root.iter():
        if node.text:
            text = node.text.strip()
            if text:
                parts.append(text)
    return "\n".join(parts)


def read_text_file(path: Path) -> tuple[str, list[str]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore"), ["utf8 decode fallback used"]


def read_docx(path: Path) -> tuple[str, list[str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
        text = strip_xml_text(xml)
        if not text.strip():
            return "", ["docx extracted but empty text"]
        return text, []
    except Exception as exc:  # noqa: BLE001
        return "", [f"docx extract failed: {exc}"]


def read_hwpx(path: Path) -> tuple[str, list[str]]:
    try:
        chunks: list[str] = []
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                low = name.lower()
                if not low.endswith(".xml"):
                    continue
                if "contents/" not in low and "content/" not in low:
                    continue
                chunks.append(strip_xml_text(archive.read(name)))
        text = "\n".join(filter(None, chunks))
        if not text.strip():
            return "", ["hwpx extracted but empty text"]
        return text, []
    except Exception as exc:  # noqa: BLE001
        return "", [f"hwpx extract failed: {exc}"]


def read_pdf(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        chunks = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(chunks).strip()
        if text:
            return text, warnings
        warnings.append("pypdf returned empty text")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"pypdf unavailable/failed: {exc}")

    try:
        import fitz  # type: ignore

        with fitz.open(path) as doc:
            text = "\n".join((page.get_text() or "") for page in doc).strip()
        if text:
            return text, warnings
        warnings.append("pymupdf returned empty text")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"pymupdf unavailable/failed: {exc}")

    return "", warnings + ["pdf extraction failed; OCR may be required"]


def read_hwp(path: Path) -> tuple[str, list[str]]:
    cmd = shutil.which("hwp5txt")
    if not cmd:
        return "", ["hwp extraction skipped; convert to hwpx/docx or install hwp5txt (pyhwp)"]
    try:
        proc = subprocess.run([cmd, str(path)], capture_output=True, text=True, check=False)
        text = proc.stdout.strip()
        if text:
            return text, []
        return "", ["hwp5txt returned empty text"]
    except Exception as exc:  # noqa: BLE001
        return "", [f"hwp5txt failed: {exc}"]


def extract_text(path: Path) -> tuple[str, list[str]]:
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return read_text_file(path)
    if ext == ".docx":
        return read_docx(path)
    if ext == ".hwpx":
        return read_hwpx(path)
    if ext == ".pdf":
        return read_pdf(path)
    if ext == ".hwp":
        return read_hwp(path)
    return "", [f"unsupported extension: {ext}"]


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def detect_case_numbers(text: str) -> list[str]:
    patterns = [
        r"\b\d{4}\s*[가-힣A-Za-z]{1,4}\s*\d{1,8}\b",
        r"\b\d{2}\s*[가-힣A-Za-z]{1,4}\s*\d{1,8}\b",
    ]
    hits: list[str] = []
    for pattern in patterns:
        hits.extend(re.findall(pattern, text))
    return unique([re.sub(r"\s+", "", hit) for hit in hits])[:10]


def detect_dates(text: str) -> list[str]:
    hits = re.findall(r"\b(19|20)\d{2}\.\s*\d{1,2}\.\s*\d{1,2}\.\b", text)
    # re.findall with groups returns only group 1; run full pattern capture below.
    full_hits = re.findall(r"\b(?:19|20)\d{2}\.\s*\d{1,2}\.\s*\d{1,2}\.\b", text)
    normalized = [re.sub(r"\s+", "", hit) for hit in full_hits]
    return unique(normalized)[:10]


def detect_courts(text: str) -> list[str]:
    return [name for name in COURT_PATTERNS if name in text]


def summarize_text(text: str, max_chars: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "(no text extracted)"

    block = " ".join(lines[:30])
    block = re.sub(r"\s+", " ", block).strip()
    if len(block) > max_chars:
        return block[:max_chars].rstrip() + " ..."
    return block


def sanitize_stem(path: Path) -> str:
    stem = re.sub(r"[^\w.-]+", "_", path.stem, flags=re.UNICODE)
    stem = re.sub(r"_+", "_", stem).strip("._")
    return stem or "source"


def render_card(card: SourceCard, matter_root: Path) -> str:
    source_rel = card.source_path.relative_to(matter_root).as_posix()
    extracted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    warnings_block = (
        "\n".join(f"- {item}" for item in card.warnings) if card.warnings else "- none"
    )
    return f"""# Authority Card: {card.source_path.name}

## Metadata
- source_file: {source_rel}
- extracted_at_utc: {extracted_at}
- extracted_chars: {card.text_len}
- case_numbers: {", ".join(card.case_numbers) if card.case_numbers else "-"}
- courts: {", ".join(card.courts) if card.courts else "-"}
- dates: {", ".join(card.dates) if card.dates else "-"}

## Holding Summary (Draft)
{card.summary}

## Application Point (Draft)
- [CHECK_NEEDED] Fill legal application point.

## Extraction Warnings
{warnings_block}
"""


def build_matter_pack(cards: list[SourceCard], matter_root: Path, pack_path: Path) -> None:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        "# Matter Pack",
        "",
        "## Build Metadata",
        f"- generated_at_utc: {generated}",
        f"- cards_count: {len(cards)}",
        "",
        "## Authority Card Index",
        "| card | source_file | chars | case_numbers | courts |",
        "|---|---|---:|---|---|",
    ]

    for card in cards:
        card_rel = card.card_path.relative_to(matter_root).as_posix()
        source_rel = card.source_path.relative_to(matter_root).as_posix()
        case_numbers = ", ".join(card.case_numbers) if card.case_numbers else "-"
        courts = ", ".join(card.courts) if card.courts else "-"
        lines.append(f"| {card_rel} | {source_rel} | {card.text_len} | {case_numbers} | {courts} |")

    if not cards:
        lines.append("| - | - | 0 | - | - |")

    lines.extend(
        [
            "",
            "## Core Facts",
            "- claimant:",
            "- respondent:",
            "- timeline:",
            "- objective:",
            "",
            "## Issues",
            "1.",
            "2.",
            "3.",
            "",
            "## Drafting Constraints",
            "- No fabricated authorities or facts.",
            "- Mark missing evidence as [CHECK_NEEDED].",
            "- Keep IRAC structure.",
            "",
        ]
    )

    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    matter_root = Path(args.matter_path)
    inbox = matter_root / args.inbox
    cards_dir = matter_root / args.cards
    pack_path = matter_root / args.matter_pack

    if not matter_root.exists():
        raise SystemExit(f"Matter path not found: {matter_root}")
    if not inbox.exists():
        raise SystemExit(f"Inbox path not found: {inbox}")

    cards_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(
        (path for path in inbox.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda p: p.name.lower(),
    )

    cards: list[SourceCard] = []
    for source in sources:
        text, warnings = extract_text(source)
        case_numbers = detect_case_numbers(text)
        courts = detect_courts(text)
        dates = detect_dates(text)
        summary = summarize_text(text, args.max_summary_chars)

        card_name = sanitize_stem(source) + ".md"
        card_path = cards_dir / card_name
        if args.keep_history:
            idx = 1
            while card_path.exists() and card_path.stat().st_size > 0:
                card_path = cards_dir / f"{sanitize_stem(source)}_{idx}.md"
                idx += 1

        card = SourceCard(
            source_path=source,
            card_path=card_path,
            text_len=len(text),
            case_numbers=case_numbers,
            courts=courts,
            dates=dates,
            summary=summary,
            warnings=warnings,
        )
        card_path.write_text(render_card(card, matter_root), encoding="utf-8")
        cards.append(card)

    build_matter_pack(cards, matter_root, pack_path)
    print(f"Cards generated: {len(cards)}")
    print(f"Matter pack written: {pack_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
