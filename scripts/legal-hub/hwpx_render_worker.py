#!/usr/bin/env python3
"""HWPX Render Worker — 방안 C (Job Queue 폴링 방식).

흐름:
  emit_hwpx_job()  →  hwpx-jobs/<id>.job.json
  worker (2초 폴링) →  render_hwpx.py 실행
                    →  검증 게이트 3단계
                    →  hwpx-output/<id>.hwpx  +  <id>.result.json
  job.json  →  <id>.job.done  (or .fail)

Usage:
    # 워커 실행
    python hwpx_render_worker.py --jobs-dir hwpx-jobs --output-dir hwpx-output

    # job 생성 (Python에서)
    from hwpx_render_worker import emit_hwpx_job
    job_path = emit_hwpx_job(template, data, jobs_dir)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLL_INTERVAL = 2  # seconds
JOB_SUFFIX    = ".job.json"
DONE_SUFFIX   = ".job.done"
FAIL_SUFFIX   = ".job.fail"


# ── Job 생성 ──────────────────────────────────────────────────────────────────

def emit_hwpx_job(
    template_path: Path,
    data_path: Path,
    jobs_dir: Path,
    job_id: str | None = None,
) -> Path:
    """job.json 파일을 생성하고 경로를 반환한다.

    Args:
        template_path: .hwpx 템플릿 경로
        data_path: JSON 데이터 파일 경로
        jobs_dir: job 파일 저장 디렉터리
        job_id: 명시적 job ID (미지정 시 타임스탬프 자동 생성)

    Returns:
        생성된 .job.json 파일 경로
    """
    jobs_dir.mkdir(parents=True, exist_ok=True)
    if job_id is None:
        job_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")[:21]

    job: dict[str, Any] = {
        "job_id":        job_id,
        "created_at":    datetime.now(timezone.utc).isoformat(),
        "template_path": str(template_path.resolve()),
        "data_path":     str(data_path.resolve()),
        "status":        "pending",
    }
    job_path = jobs_dir / f"{job_id}{JOB_SUFFIX}"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return job_path


# ── 검증 게이트 ───────────────────────────────────────────────────────────────

def check_structure(hwpx_path: Path) -> tuple[bool, str]:
    """게이트 ①: ZIP 구조 검증 (mimetype + section*.xml 존재)."""
    try:
        with zipfile.ZipFile(hwpx_path) as z:
            names = z.namelist()
            if "mimetype" not in names:
                return False, "mimetype entry missing"
            mime = z.read("mimetype").decode("utf-8", errors="ignore").strip()
            if "hwp" not in mime.lower():
                return False, f"invalid mimetype: {mime!r}"
            has_section = any(
                n.lower().startswith("contents/section") and n.lower().endswith(".xml")
                for n in names
            )
            if not has_section:
                return False, "no Contents/section*.xml found"
        return True, "ok"
    except zipfile.BadZipFile as exc:
        return False, f"not a valid ZIP: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"structure check error: {exc}"


def check_placeholders(hwpx_path: Path) -> tuple[bool, str]:
    """게이트 ②: 미치환 {{token}} 잔존 여부 검사."""
    try:
        leftover: list[str] = []
        with zipfile.ZipFile(hwpx_path) as z:
            for name in z.namelist():
                if name.lower().endswith(".xml") and "contents/" in name.lower():
                    txt = z.read(name).decode("utf-8", errors="ignore")
                    leftover += re.findall(r"\{\{[^}]+\}\}", txt)
        if leftover:
            unique = list(dict.fromkeys(leftover))
            return False, f"leftover tokens: {unique}"
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"placeholder check error: {exc}"


def check_hwp_roundtrip(hwpx_path: Path) -> tuple[bool | None, str]:
    """게이트 ③: 한글 COM round-trip (pywin32 + Windows 전용).

    Returns:
        (True, "ok")     — 한글이 정상적으로 열고 닫음
        (False, reason)  — 한글이 오류 반환
        (None, reason)   — pywin32 미설치 or 비-Windows → 게이트 스킵
    """
    if sys.platform != "win32":
        return None, "non-Windows: skipped"
    try:
        import win32com.client  # type: ignore
    except ImportError:
        return None, "pywin32 not installed: skipped"

    hwp = None
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModuleExample")
        ok = hwp.Open(str(hwpx_path.resolve()), "HWP", "forceopen:true")
        if not ok:
            return False, "hwp.Open returned False"
        hwp.Quit()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"COM error: {exc}"
    finally:
        if hwp is not None:
            try:
                hwp.Quit()
            except Exception:  # noqa: BLE001
                pass


def run_gates(hwpx_path: Path) -> dict[str, Any]:
    """세 게이트를 순서대로 실행하고 결과 dict를 반환한다."""
    g1_ok, g1_msg = check_structure(hwpx_path)
    g2_ok, g2_msg = check_placeholders(hwpx_path)
    g3_ok, g3_msg = check_hwp_roundtrip(hwpx_path)

    # 전체 통과: g1 AND g2 AND (g3 is None OR g3 is True)
    overall = g1_ok and g2_ok and (g3_ok is None or g3_ok is True)

    return {
        "gate1_structure":    {"passed": g1_ok,  "detail": g1_msg},
        "gate2_placeholders": {"passed": g2_ok,  "detail": g2_msg},
        "gate3_roundtrip":    {"passed": g3_ok,  "detail": g3_msg},
        "overall":            overall,
    }


# ── Job 처리 ──────────────────────────────────────────────────────────────────

def load_job(job_path: Path) -> dict[str, Any]:
    """job.json을 읽어 dict로 반환한다."""
    return json.loads(job_path.read_text(encoding="utf-8"))


def write_result(
    job: dict[str, Any],
    output_path: Path,
    gates: dict[str, Any],
    output_dir: Path,
) -> Path:
    """<job_id>.result.json을 output_dir에 기록하고 경로를 반환한다."""
    result = {
        "job_id":      job["job_id"],
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output_path) if output_path.exists() else None,
        "gates":       gates,
        "overall":     gates["overall"],
    }
    result_path = output_dir / f"{job['job_id']}.result.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result_path


def mark_job(job_path: Path, success: bool) -> Path:
    """job.json을 .done 또는 .fail로 이름 변경한다."""
    suffix = DONE_SUFFIX if success else FAIL_SUFFIX
    dest = job_path.with_suffix("").with_suffix(suffix)
    job_path.rename(dest)
    return dest


def process_job(job_path: Path, output_dir: Path, script_dir: Path) -> bool:
    """단일 job을 처리한다. 성공 시 True 반환."""
    job = load_job(job_path)
    job_id = job["job_id"]
    template = Path(job["template_path"])
    data     = Path(job["data_path"])
    output   = output_dir / f"{job_id}.hwpx"

    print(f"  [job] {job_id}")

    # render_hwpx.py 호출
    output_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, str(script_dir / "render_hwpx.py"),
         str(template), str(data), "-o", str(output)],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        print(f"  ❌ render failed: {r.stderr.strip()}")
        gates = {"gate1_structure":    {"passed": False, "detail": "render failed"},
                 "gate2_placeholders": {"passed": False, "detail": "render failed"},
                 "gate3_roundtrip":    {"passed": None,  "detail": "render failed"},
                 "overall": False}
        write_result(job, output, gates, output_dir)
        mark_job(job_path, success=False)
        return False

    # 검증 게이트
    gates = run_gates(output)
    result_path = write_result(job, output, gates, output_dir)
    success = gates["overall"]
    marked = mark_job(job_path, success=success)

    mark = "✅" if success else "❌"
    print(f"  {mark} gates={'PASS' if success else 'FAIL'}  "
          f"→ {output.name}  ({output.stat().st_size if output.exists() else 0}B)")
    print(f"     result: {result_path.name}  marker: {marked.name}")
    return success


# ── 워커 루프 ─────────────────────────────────────────────────────────────────

def watch_jobs(jobs_dir: Path, output_dir: Path, script_dir: Path, once: bool = False) -> None:
    """jobs_dir를 폴링하며 .job.json을 순서대로 처리한다."""
    print(f"👷 HWPX Render Worker")
    print(f"   jobs_dir  : {jobs_dir}")
    print(f"   output_dir: {output_dir}")
    print(f"   poll      : {POLL_INTERVAL}s  (Ctrl+C to stop)\n")

    try:
        while True:
            pending = sorted(jobs_dir.glob(f"*{JOB_SUFFIX}"))
            for job_path in pending:
                process_job(job_path, output_dir, script_dir)
            if once and not pending:
                break
            if once and pending:
                continue
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HWPX Render Worker (job queue polling).")
    parser.add_argument("--jobs-dir",    default="hwpx-jobs",   help="Job queue directory")
    parser.add_argument("--output-dir",  default="hwpx-output", help="Output directory")
    parser.add_argument("--once",        action="store_true",   help="Process once then exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    watch_jobs(
        jobs_dir   = Path(args.jobs_dir),
        output_dir = Path(args.output_dir),
        script_dir = script_dir,
        once       = args.once,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
