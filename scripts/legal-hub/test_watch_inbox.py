#!/usr/bin/env python3
"""Tests for watch_inbox.py — InboxHandler event processing."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from watch_inbox import SETTLE_SECONDS, SUPPORTED_EXTENSIONS, InboxHandler


# ── InboxHandler.on_created ───────────────────────────────────


class TestInboxHandlerOnCreated:
    def _make_handler(self, tmp_path: Path) -> InboxHandler:
        script_dir = Path(__file__).resolve().parent
        return InboxHandler(matter_path=tmp_path, script_dir=script_dir)

    def _make_event(self, path: str, is_directory: bool = False) -> MagicMock:
        event = MagicMock()
        event.is_directory = is_directory
        event.src_path = path
        return event

    def test_ignores_directory_events(self, tmp_path):
        handler = self._make_handler(tmp_path)
        event = self._make_event(str(tmp_path / "subdir"), is_directory=True)
        with patch("watch_inbox.time.sleep") as mock_sleep, \
             patch("watch_inbox.subprocess.run") as mock_run:
            handler.on_created(event)
            mock_run.assert_not_called()

    def test_ignores_unsupported_extension(self, tmp_path):
        handler = self._make_handler(tmp_path)
        event = self._make_event(str(tmp_path / "file.xlsx"))
        with patch("watch_inbox.time.sleep"), \
             patch("watch_inbox.subprocess.run") as mock_run:
            handler.on_created(event)
            mock_run.assert_not_called()

    @pytest.mark.parametrize("ext", [".md", ".txt", ".pdf", ".docx", ".hwpx", ".hwp"])
    def test_triggers_on_supported_extensions(self, tmp_path, ext):
        handler = self._make_handler(tmp_path)
        event = self._make_event(str(tmp_path / f"file{ext}"))
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Cards generated: 1"
        with patch("watch_inbox.time.sleep"), \
             patch("watch_inbox.subprocess.run", return_value=mock_result) as mock_run:
            handler.on_created(event)
            mock_run.assert_called_once()

    def test_calls_build_matter_pack_script(self, tmp_path):
        handler = self._make_handler(tmp_path)
        event = self._make_event(str(tmp_path / "doc.md"))
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("watch_inbox.time.sleep"), \
             patch("watch_inbox.subprocess.run", return_value=mock_result) as mock_run:
            handler.on_created(event)
            args = mock_run.call_args[0][0]  # list of strings
            assert any("build_matter_pack.py" in str(a) for a in args)
            assert any(str(tmp_path) == a for a in args)

    def test_passes_keep_history_flag(self, tmp_path):
        handler = self._make_handler(tmp_path)
        event = self._make_event(str(tmp_path / "doc.md"))
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("watch_inbox.time.sleep"), \
             patch("watch_inbox.subprocess.run", return_value=mock_result) as mock_run:
            handler.on_created(event)
            args = mock_run.call_args[0][0]
            assert "--keep-history" in args

    def test_settle_sleep_is_called(self, tmp_path):
        handler = self._make_handler(tmp_path)
        event = self._make_event(str(tmp_path / "doc.md"))
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("watch_inbox.time.sleep") as mock_sleep, \
             patch("watch_inbox.subprocess.run", return_value=mock_result):
            handler.on_created(event)
            mock_sleep.assert_called_once_with(SETTLE_SECONDS)


# ── Constants ─────────────────────────────────────────────────


class TestConstants:
    def test_supported_extensions_set(self):
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".hwpx" in SUPPORTED_EXTENSIONS
        assert ".hwp" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS

    def test_settle_seconds_positive(self):
        assert SETTLE_SECONDS > 0
