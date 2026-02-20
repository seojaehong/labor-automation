#!/usr/bin/env python3
"""Watch 00_inbox/ for new files and auto-generate authority cards.

With --cowork flag, runs the full pipeline after build_matter_pack:
  build_matter_pack → prepare_case_data → render_hwpx
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Windows cp949/cp1252 터미널에서 이모지 출력 시 UnicodeEncodeError 방지
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") not in ("utf8", "utf16"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".hwpx", ".hwp"}
SETTLE_SECONDS = 1.5

# 프로젝트 루트 templates/ (scripts/legal-hub/ 의 두 단계 위)
GLOBAL_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


def _find_template(matter_root: Path, hint: Path | None) -> Path | None:
    """HWPX 템플릿 경로를 반환한다. 우선순위: hint > matter-local > global."""
    if hint is not None:
        return hint if hint.exists() else None

    # 1. matter 폴더 내 templates/
    local = sorted((matter_root / "templates").glob("*.hwpx"))
    if local:
        return local[0]

    # 2. 프로젝트 전역 templates/
    global_tmpls = sorted(GLOBAL_TEMPLATE_DIR.glob("tmpl_*.hwpx"))
    if global_tmpls:
        return global_tmpls[0]

    return None


def run_cowork_chain(
    matter_root: Path,
    script_dir: Path,
    case_data_hint: Path | None = None,
    template_hint: Path | None = None,
) -> bool:
    """Step 2+3: prepare_case_data → render_hwpx.

    Returns True if HWPX was rendered successfully.
    """
    draft_path = matter_root / "03_drafts/draft.md"
    case_data_path = case_data_hint or (matter_root / "02_notes/case_data.json")
    merged_data_path = matter_root / "02_notes/merged_data.json"
    prepare_script = script_dir / "prepare_case_data.py"
    render_script = script_dir / "render_hwpx.py"

    # ── Step 2: prepare_case_data ────────────────────────────────────────────
    if draft_path.exists() and case_data_path.exists():
        print("   [2/3] Merging IRAC draft into case data...")
        r = subprocess.run(
            [
                sys.executable,
                str(prepare_script),
                str(case_data_path),
                str(draft_path),
                "-o",
                str(merged_data_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            print(f"   ⚠️  prepare_case_data failed: {r.stderr.strip()}")
            return False
        print(f"   ✅ Merged: {merged_data_path.name}")
        data_for_render = merged_data_path

    elif case_data_path.exists():
        print("   [2/3] No draft.md found — using case_data.json directly.")
        data_for_render = case_data_path

    else:
        print(f"   [2/3] Skipped: {case_data_path.name} not found.")
        return False

    # ── Step 3: render_hwpx ──────────────────────────────────────────────────
    template = _find_template(matter_root, template_hint)
    if not template:
        print("   [3/3] Skipped: no .hwpx template found.")
        return False

    output_path = matter_root / "04_final" / (matter_root.name + ".hwpx")
    print(f"   [3/3] Rendering {template.name} → {output_path.name}...")
    r = subprocess.run(
        [
            sys.executable,
            str(render_script),
            str(template),
            str(data_for_render),
            "-o",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"   ❌ render_hwpx failed: {r.stderr.strip()}")
        return False

    print(f"   ✅ HWPX ready: {output_path}")
    return True


class InboxHandler(FileSystemEventHandler):
    """Trigger card generation (and optional cowork chain) on new inbox files."""

    def __init__(
        self,
        matter_path: Path,
        script_dir: Path,
        cowork: bool = False,
        template_hint: Path | None = None,
        case_data_hint: Path | None = None,
    ) -> None:
        self.matter_path = matter_path
        self.script_dir = script_dir
        self.cowork = cowork
        self.template_hint = template_hint
        self.case_data_hint = case_data_hint
        self.build_script = script_dir / "build_matter_pack.py"

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        print(f"\n📥 New file detected: {path.name}")
        print(f"   Waiting {SETTLE_SECONDS}s for download to complete...")
        time.sleep(SETTLE_SECONDS)

        # ── Step 1: build_matter_pack ─────────────────────────────────────────
        print("   [1/3] Building authority cards...")
        result = subprocess.run(
            [sys.executable, str(self.build_script), str(self.matter_path), "--keep-history"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print(f"   ✅ Cards updated. {result.stdout.strip()}")
        else:
            print(f"   ❌ Card generation failed: {result.stderr.strip()}")
            return

        if not self.cowork:
            return

        # ── Step 2+3: cowork chain ────────────────────────────────────────────
        run_cowork_chain(
            matter_root=self.matter_path,
            script_dir=self.script_dir,
            case_data_hint=self.case_data_hint,
            template_hint=self.template_hint,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch inbox folder and auto-generate authority cards on new files."
    )
    parser.add_argument("matter_path", help="Matter folder path")
    parser.add_argument("--inbox", default="00_inbox", help="Inbox folder name to watch")
    parser.add_argument(
        "--cowork",
        action="store_true",
        help="Full pipeline: build_matter_pack → prepare_case_data → render_hwpx",
    )
    parser.add_argument(
        "--template",
        help="Path to .hwpx template (auto-discovered if omitted)",
    )
    parser.add_argument(
        "--case-data",
        help="Path to case_data.json (defaults to matter/02_notes/case_data.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matter_root = Path(args.matter_path)
    inbox = matter_root / args.inbox

    if not inbox.exists():
        raise SystemExit(f"Inbox path not found: {inbox}")

    script_dir = Path(__file__).resolve().parent
    handler = InboxHandler(
        matter_path=matter_root,
        script_dir=script_dir,
        cowork=args.cowork,
        template_hint=Path(args.template) if args.template else None,
        case_data_hint=Path(args.case_data) if args.case_data else None,
    )
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=False)
    observer.start()

    mode = "cowork 체인" if args.cowork else "카드 생성 전용"
    print(f"👁️  Watching: {inbox}  [{mode}]")
    print(f"   Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    if args.cowork:
        print("   Chain: build_matter_pack → prepare_case_data → render_hwpx")
    print("   Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped.")

    observer.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
