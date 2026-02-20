#!/usr/bin/env python3
"""Generate template-based test documents for labor automation."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from render_hwpx import render_hwpx

PLACEHOLDER_RE = re.compile(r"\{\{([^}]+)\}\}")

MD_PAIRS = [
    (
        "sample_rescue_application.md",
        "rescue_application_data.example.json",
        "test_rescue_application_rendered.md",
    ),
    (
        "sample_employment_contract.md",
        "employment_contract_data.example.json",
        "test_employment_contract_rendered.md",
    ),
    (
        "sample_wage_complaint.md",
        "wage_complaint_data.example.json",
        "test_wage_complaint_rendered.md",
    ),
]

HWPX_CASES = [
    (
        "tmpl_rescue_application.hwpx",
        "rescue_application_data.example.json",
        "test_rescue_application.hwpx",
    ),
    (
        "tmpl_employment_contract.hwpx",
        "employment_contract_data.example.json",
        "test_employment_contract.hwpx",
    ),
    (
        "tmpl_wage_complaint.hwpx",
        "wage_complaint_data.example.json",
        "test_wage_complaint.hwpx",
    ),
]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    parser = argparse.ArgumentParser(
        description="Generate rendered markdown + hwpx test outputs.",
    )
    parser.add_argument(
        "--templates",
        default=str(project_root / "templates"),
        help="templates directory path",
    )
    parser.add_argument(
        "--output",
        default=r"C:\dev\output\labor-automation-template-tests",
        help="output directory path",
    )
    return parser.parse_args()


def replace_placeholders(text: str, data: dict[str, str]) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1).strip()
        return str(data.get(key, match.group(0)))

    rendered = PLACEHOLDER_RE.sub(repl, text)
    return rendered.replace("{{토큰명}}", "토큰명")


def count_leftovers(text: str) -> int:
    return len(PLACEHOLDER_RE.findall(text))


def render_markdown_files(
    template_dir: Path,
    output_dir: Path,
) -> list[tuple[Path, int]]:
    results: list[tuple[Path, int]] = []
    for md_name, json_name, output_name in MD_PAIRS:
        md_text = (template_dir / md_name).read_text(encoding="utf-8")
        data = json.loads((template_dir / json_name).read_text(encoding="utf-8"))

        rendered = replace_placeholders(md_text, data)
        output_path = output_dir / output_name
        output_path.write_text(rendered, encoding="utf-8")

        results.append((output_path, count_leftovers(rendered)))
    return results


def count_hwpx_leftovers(hwpx_path: Path) -> int:
    section_xml = ""
    with zipfile.ZipFile(hwpx_path, "r") as zf:
        if "Contents/section0.xml" in zf.namelist():
            section_xml = zf.read("Contents/section0.xml").decode("utf-8", errors="ignore")
    return count_leftovers(section_xml)


def render_hwpx_files(
    template_dir: Path,
    output_dir: Path,
) -> list[tuple[Path, list[str], int]]:
    results: list[tuple[Path, list[str], int]] = []
    for template_name, data_name, output_name in HWPX_CASES:
        template_path = template_dir / template_name
        data_path = template_dir / data_name
        output_path = output_dir / output_name

        data = json.loads(data_path.read_text(encoding="utf-8"))
        # sample_* specs include a literal {{토큰명}} example in guidance text.
        data.setdefault("토큰명", "토큰명")
        replaced_files = render_hwpx(template_path, data, output_path)
        leftover_count = count_hwpx_leftovers(output_path)
        results.append((output_path, replaced_files, leftover_count))

    return results


def write_report(
    output_dir: Path,
    md_results: list[tuple[Path, int]],
    hwpx_results: list[tuple[Path, list[str], int]],
) -> Path:
    report_path = output_dir / "README_TEST_RESULTS.md"
    lines = [
        "# Labor Automation Template Test Results",
        "",
        "## Markdown Render Results",
    ]

    for path, leftovers in md_results:
        lines.append(f"- {path.name}: leftover_tokens={leftovers}")

    lines.append("")
    lines.append("## HWPX Render Results")
    for path, replaced_files, leftovers in hwpx_results:
        replaced = ", ".join(replaced_files) if replaced_files else "<none>"
        lines.append(f"- {path.name}: leftover_tokens={leftovers}, replaced_files={replaced}")

    lines.extend(
        [
            "",
            "## Output Files",
        ]
    )

    for path, _ in md_results:
        lines.append(f"- {path}")
    for path, _, _ in hwpx_results:
        lines.append(f"- {path}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    args = parse_args()
    template_dir = Path(args.templates)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_results = render_markdown_files(template_dir, output_dir)
    hwpx_results = render_hwpx_files(template_dir, output_dir)
    report_path = write_report(output_dir, md_results, hwpx_results)

    print(f"Generated output directory: {output_dir}")
    for path, leftovers in md_results:
        print(f"MD: {path} (leftover_tokens={leftovers})")
    for path, _, leftovers in hwpx_results:
        print(f"HWPX: {path} (leftover_tokens={leftovers})")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
