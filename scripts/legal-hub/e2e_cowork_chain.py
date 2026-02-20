#!/usr/bin/env python3
"""E2E test: full cowork chain for all 3 document types.

build_matter_pack → prepare_case_data → render_hwpx

Usage:
    python scripts/legal-hub/e2e_cowork_chain.py
    python scripts/legal-hub/e2e_cowork_chain.py --output-dir C:/dev/output/labor-automation-e2e
    python scripts/legal-hub/e2e_cowork_chain.py --output-dir ./e2e_output --keep-matter
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES  = REPO_ROOT / "templates"

CASES: list[dict] = [
    {
        "id":       "E2E-RESCUE",
        "label":    "부당해고 구제신청서",
        "template": "tmpl_rescue_application.hwpx",
        "data":     "rescue_application_data.example.json",
        "irac_key": "신청이유_IRAC",
    },
    {
        "id":       "E2E-CONTRACT",
        "label":    "근로계약서",
        "template": "tmpl_employment_contract.hwpx",
        "data":     "employment_contract_data.example.json",
        "irac_key": None,
    },
    {
        "id":       "E2E-WAGE",
        "label":    "임금체불 진정서",
        "template": "tmpl_wage_complaint.hwpx",
        "data":     "wage_complaint_data.example.json",
        "irac_key": "법적검토_IRAC",
    },
]

IRAC_DRAFT = (
    "## Issue\n법적 쟁점\n\n"
    "## Rule\n관련 법령\n\n"
    "## Application\n사실관계 적용\n\n"
    "## Conclusion\n결론\n"
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def leftover_tokens(hwpx_path: Path) -> list[str]:
    """HWPX ZIP 안의 XML에서 미치환 {{token}} 목록 반환."""
    tokens: list[str] = []
    with zipfile.ZipFile(hwpx_path) as z:
        for fname in z.namelist():
            if fname.lower().endswith(".xml") and "contents/" in fname.lower():
                txt = z.read(fname).decode("utf-8", errors="ignore")
                tokens += re.findall(r"\{\{[^}]+\}\}", txt)
    return tokens


def setup_matter(matter_root: Path, cid: str, case: dict) -> Path:
    """임시 matter 폴더 생성 및 픽스처 배치."""
    r = run([
        sys.executable, str(SCRIPT_DIR / "scaffold_hub.py"),
        cid, "--title", cid, "--root", str(matter_root),
    ])
    if r.returncode != 0:
        raise RuntimeError(f"scaffold_hub failed: {r.stderr}")

    matter = matter_root / cid

    # template
    shutil.copy2(TEMPLATES / case["template"], matter / "templates" / case["template"])

    # case_data.json
    case_data = json.loads((TEMPLATES / case["data"]).read_text("utf-8"))
    (matter / "02_notes" / "case_data.json").write_text(
        json.dumps(case_data, ensure_ascii=False, indent=2), "utf-8"
    )

    # draft.md (IRAC 자동 주입 대상만)
    if case["irac_key"] == "신청이유_IRAC":
        (matter / "03_drafts" / "draft.md").write_text(IRAC_DRAFT, "utf-8")

    # inbox 트리거 파일
    (matter / "00_inbox" / "trigger.md").write_text("# E2E trigger\n", "utf-8")

    return matter


# ── 메인 로직 ─────────────────────────────────────────────────────────────────

def run_case(case: dict, matter_root: Path) -> dict:
    cid = case["id"]
    print(f"\n{'─'*50}")
    print(f"▶ {cid}  ({case['label']})")

    result: dict = {"id": cid, "label": case["label"], "status": "FAIL", "size": 0, "leftover": []}

    matter = setup_matter(matter_root, cid, case)

    # Step 1: build_matter_pack
    r = run([sys.executable, str(SCRIPT_DIR / "build_matter_pack.py"), str(matter), "--keep-history"])
    if r.returncode != 0:
        print(f"  ❌ build_matter_pack failed: {r.stderr.strip()}")
        return result
    print(f"  [1] build_matter_pack: {r.stdout.strip().splitlines()[0]}")

    # Step 2+3: cowork chain
    sys.path.insert(0, str(SCRIPT_DIR))
    from watch_inbox import run_cowork_chain
    ok = run_cowork_chain(matter, SCRIPT_DIR)
    if not ok:
        print("  ❌ run_cowork_chain returned False")
        return result

    # 검증
    output = matter / "04_final" / f"{cid}.hwpx"
    if not output.exists():
        print(f"  ❌ output not found: {output}")
        return result

    tokens = leftover_tokens(output)
    result["size"]     = output.stat().st_size
    result["leftover"] = tokens
    result["status"]   = "PASS" if not tokens else "FAIL"
    result["output"]   = output

    mark = "✅" if result["status"] == "PASS" else "❌"
    print(f"  {mark} output: {output.name} ({result['size']}B)  미치환={len(tokens)}개")
    return result


def save_artifacts(results: list[dict], matter_root: Path, output_dir: Path) -> None:
    """HWPX + merged_data.json + 리포트를 output_dir에 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# E2E Cowork Chain Test Results",
        f"- run_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- output_dir: {output_dir}",
        "",
        "## Results",
        "| case | label | status | hwpx_size | leftover |",
        "|------|-------|--------|-----------|----------|",
    ]

    for r in results:
        cid   = r["id"]
        mark  = "PASS" if r["status"] == "PASS" else "FAIL"
        report_lines.append(
            f"| {cid} | {r['label']} | {mark} | {r['size']}B | {len(r['leftover'])}개 |"
        )

        # HWPX 복사
        if "output" in r and r["output"].exists():
            shutil.copy2(r["output"], output_dir / r["output"].name)

        # merged_data.json 복사
        merged = matter_root / cid / "02_notes" / "merged_data.json"
        if merged.exists():
            shutil.copy2(merged, output_dir / f"{cid}_merged_data.json")

    report_lines += ["", "## Output Files"]
    for f in sorted(output_dir.iterdir()):
        report_lines.append(f"- {f.name} ({f.stat().st_size}B)")

    (output_dir / "README_E2E.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E2E cowork chain test for all 3 document types.")
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Artifact output directory (default: _e2e_output/<timestamp>)",
    )
    parser.add_argument(
        "--keep-matter",
        action="store_true",
        help="Keep temporary matter folders after test (for inspection)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / timestamp if args.output_dir else \
                 REPO_ROOT / "_e2e_output" / timestamp
    matter_root = REPO_ROOT / f"_e2e_matter_{timestamp}"

    print(f"E2E Cowork Chain  [{timestamp}]")
    print(f"output → {output_dir}")

    results: list[dict] = []
    try:
        for case in CASES:
            results.append(run_case(case, matter_root))
    finally:
        save_artifacts(results, matter_root, output_dir)
        if not args.keep_matter and matter_root.exists():
            shutil.rmtree(matter_root)

    # 최종 요약
    print(f"\n{'='*50}")
    print("E2E 결과 요약")
    print(f"{'='*50}")
    all_pass = True
    for r in results:
        mark = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {mark} {r['id']}: {r['status']} ({r['size']}B)")
        if r["status"] != "PASS":
            all_pass = False

    print(f"\n📁 {output_dir}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
