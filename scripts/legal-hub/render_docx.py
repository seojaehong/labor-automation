#!/usr/bin/env python3
"""Render markdown draft into court-style DOCX."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "python-docx is required. Install with: pip install python-docx"
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a markdown draft to DOCX.")
    parser.add_argument("matter_path", help="Matter folder path")
    parser.add_argument("--input", default="03_drafts/draft.md", help="Markdown input path (relative to matter)")
    parser.add_argument("--output", default="04_final/final.docx", help="DOCX output path (relative to matter)")
    parser.add_argument("--font", default="Malgun Gothic", help="Main document font")
    parser.add_argument("--font-size", type=float, default=12.0, help="Main font size (pt)")
    parser.add_argument("--line-spacing", type=float, default=1.6, help="Line spacing multiplier")
    parser.add_argument("--top-cm", type=float, default=4.5, help="Top margin in cm")
    parser.add_argument("--bottom-cm", type=float, default=3.0, help="Bottom margin in cm")
    parser.add_argument("--left-cm", type=float, default=2.0, help="Left margin in cm")
    parser.add_argument("--right-cm", type=float, default=2.0, help="Right margin in cm")
    return parser.parse_args()


def configure_document(doc: Document, font_name: str, font_size: float, line_spacing: float, margins: dict[str, float]) -> None:
    for section in doc.sections:
        section.top_margin = Cm(margins["top"])
        section.bottom_margin = Cm(margins["bottom"])
        section.left_margin = Cm(margins["left"])
        section.right_margin = Cm(margins["right"])

    style = doc.styles["Normal"]
    style.font.name = font_name
    style.font.size = Pt(font_size)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    style.paragraph_format.line_spacing = line_spacing
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)


def add_heading(doc: Document, text: str, level: int) -> None:
    size_map = {1: 16, 2: 14, 3: 13}
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text.strip())
    run.bold = True
    run.font.size = Pt(size_map.get(level, 12))
    if level == 1:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def add_runs_with_bold(paragraph, text: str) -> None:
    """Parse **bold** markers and add runs with appropriate formatting."""
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            if part:
                paragraph.add_run(part)


def add_plain_paragraph(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_runs_with_bold(paragraph, text.strip())


def add_list_item(doc: Document, text: str, numbered: bool) -> None:
    style_name = "List Number" if numbered else "List Bullet"
    paragraph = doc.add_paragraph(style=style_name)
    add_runs_with_bold(paragraph, text.strip())


def render_markdown(doc: Document, markdown_text: str) -> None:
    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            doc.add_paragraph()
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            add_heading(doc, heading_match.group(2), level)
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            add_list_item(doc, bullet_match.group(1), numbered=False)
            continue

        number_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if number_match:
            add_list_item(doc, number_match.group(1), numbered=True)
            continue

        add_plain_paragraph(doc, stripped)


def main() -> int:
    args = parse_args()
    matter_root = Path(args.matter_path)
    input_path = matter_root / args.input
    output_path = matter_root / args.output

    if not input_path.exists():
        raise SystemExit(f"Input markdown not found: {input_path}")

    markdown_text = input_path.read_text(encoding="utf-8")
    doc = Document()
    configure_document(
        doc=doc,
        font_name=args.font,
        font_size=args.font_size,
        line_spacing=args.line_spacing,
        margins={
            "top": args.top_cm,
            "bottom": args.bottom_cm,
            "left": args.left_cm,
            "right": args.right_cm,
        },
    )
    render_markdown(doc, markdown_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    print(f"DOCX generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
