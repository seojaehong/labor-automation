#!/usr/bin/env python3
"""Watch 00_inbox/ for new files and auto-generate authority cards."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".hwpx", ".hwp"}
SETTLE_SECONDS = 1.5


class InboxHandler(FileSystemEventHandler):
    """Trigger card generation when a supported file lands in the inbox."""

    def __init__(self, matter_path: Path, script_dir: Path) -> None:
        self.matter_path = matter_path
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

        print("   Building authority cards...")
        result = subprocess.run(
            [sys.executable, str(self.build_script), str(self.matter_path), "--keep-history"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print(f"   ✅ Authority cards updated. {result.stdout.strip()}")
        else:
            print(f"   ❌ Card generation failed: {result.stderr.strip()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch inbox folder and auto-generate authority cards on new files."
    )
    parser.add_argument("matter_path", help="Matter folder path")
    parser.add_argument("--inbox", default="00_inbox", help="Inbox folder name to watch")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matter_root = Path(args.matter_path)
    inbox = matter_root / args.inbox

    if not inbox.exists():
        raise SystemExit(f"Inbox path not found: {inbox}")

    script_dir = Path(__file__).resolve().parent
    handler = InboxHandler(matter_root, script_dir)
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=False)
    observer.start()

    print(f"👁️  Watching: {inbox}")
    print(f"   Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
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
