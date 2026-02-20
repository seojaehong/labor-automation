#!/usr/bin/env python3
"""Tests for watch_inbox.py — InboxHandler event processing + cowork chain."""

from __future__ import annotations

import io
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from watch_inbox import (
    SETTLE_SECONDS,
    SUPPORTED_EXTENSIONS,
    InboxHandler,
    _find_template,
    run_cowork_chain,
)

# ── helpers ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
_FAKE_GLOBAL = Path("/nonexistent/__no_global__")  # 전역 템플릿 탐색 차단용


def make_hwpx(path: Path) -> None:
    """최소 유효한 HWPX(ZIP) 파일 생성."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("Contents/content.hpf", "<hpf/>")
        z.writestr("Contents/section0.xml", "<xml/>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.getvalue())


def ok_proc() -> MagicMock:
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


def fail_proc() -> MagicMock:
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = "mock error"
    return m


@pytest.fixture()
def matter(tmp_path: Path) -> Path:
    """기본 matter 폴더 구조 생성."""
    m = tmp_path / "CASE-001"
    for sub in ["00_inbox", "02_notes", "03_drafts", "04_final", "templates"]:
        (m / sub).mkdir(parents=True)
    return m


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


# ── _find_template ─────────────────────────────────────────────────────────────


class TestFindTemplate:
    def test_returns_none_when_empty(self, matter: Path) -> None:
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL):
            assert _find_template(matter, None) is None

    def test_finds_local_template(self, matter: Path) -> None:
        tmpl = matter / "templates/local.hwpx"
        make_hwpx(tmpl)
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL):
            assert _find_template(matter, None) == tmpl

    def test_hint_takes_priority_over_local(self, matter: Path, tmp_path: Path) -> None:
        hint = tmp_path / "custom.hwpx"
        make_hwpx(hint)
        make_hwpx(matter / "templates/local.hwpx")
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL):
            assert _find_template(matter, hint) == hint

    def test_missing_hint_returns_none(self, matter: Path, tmp_path: Path) -> None:
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL):
            assert _find_template(matter, tmp_path / "ghost.hwpx") is None

    def test_falls_back_to_global(self, matter: Path, tmp_path: Path) -> None:
        global_dir = tmp_path / "global_templates"
        global_dir.mkdir()
        tmpl = global_dir / "tmpl_test.hwpx"
        make_hwpx(tmpl)
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", global_dir):
            assert _find_template(matter, None) == tmpl

    def test_local_preferred_over_global(self, matter: Path, tmp_path: Path) -> None:
        global_dir = tmp_path / "global_templates"
        global_dir.mkdir()
        make_hwpx(global_dir / "tmpl_global.hwpx")
        local = matter / "templates/local.hwpx"
        make_hwpx(local)
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", global_dir):
            assert _find_template(matter, None) == local


# ── run_cowork_chain ───────────────────────────────────────────────────────────


class TestRunCoworkChain:
    def test_no_case_data_returns_false(self, matter: Path) -> None:
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL):
            assert run_cowork_chain(matter, SCRIPT_DIR) is False

    def test_no_template_returns_false(self, matter: Path) -> None:
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")
        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL):
            assert run_cowork_chain(matter, SCRIPT_DIR) is False

    def test_case_data_only_skips_prepare(self, matter: Path) -> None:
        """draft.md 없으면 prepare 없이 render만."""
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")
        make_hwpx(matter / "templates/tmpl.hwpx")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=ok_proc()) as mock_run:
            result = run_cowork_chain(matter, SCRIPT_DIR)

        assert result is True
        assert mock_run.call_count == 1
        assert "render_hwpx.py" in mock_run.call_args[0][0][1]

    def test_full_chain_prepare_then_render(self, matter: Path) -> None:
        """draft.md + case_data.json → prepare → render 순서."""
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")
        (matter / "03_drafts/draft.md").write_text("## IRAC\n내용", encoding="utf-8")
        make_hwpx(matter / "templates/tmpl.hwpx")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=ok_proc()) as mock_run:
            result = run_cowork_chain(matter, SCRIPT_DIR)

        assert result is True
        assert mock_run.call_count == 2
        assert "prepare_case_data.py" in mock_run.call_args_list[0][0][0][1]
        assert "render_hwpx.py" in mock_run.call_args_list[1][0][0][1]

    def test_prepare_failure_stops_chain(self, matter: Path) -> None:
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")
        (matter / "03_drafts/draft.md").write_text("## IRAC", encoding="utf-8")
        make_hwpx(matter / "templates/tmpl.hwpx")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=fail_proc()) as mock_run:
            result = run_cowork_chain(matter, SCRIPT_DIR)

        assert result is False
        assert mock_run.call_count == 1  # prepare만, render 미호출

    def test_render_failure_returns_false(self, matter: Path) -> None:
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")
        make_hwpx(matter / "templates/tmpl.hwpx")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=fail_proc()):
            result = run_cowork_chain(matter, SCRIPT_DIR)

        assert result is False

    def test_case_data_hint_used_in_render_cmd(self, matter: Path, tmp_path: Path) -> None:
        custom = tmp_path / "custom_data.json"
        custom.write_text("{}", encoding="utf-8")
        make_hwpx(matter / "templates/tmpl.hwpx")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=ok_proc()) as mock_run:
            run_cowork_chain(matter, SCRIPT_DIR, case_data_hint=custom)

        render_cmd = mock_run.call_args[0][0]
        assert str(custom) in render_cmd

    def test_template_hint_used_in_render_cmd(self, matter: Path, tmp_path: Path) -> None:
        hint = tmp_path / "hint.hwpx"
        make_hwpx(hint)
        make_hwpx(matter / "templates/local.hwpx")
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=ok_proc()) as mock_run:
            run_cowork_chain(matter, SCRIPT_DIR, template_hint=hint)

        render_cmd = mock_run.call_args[0][0]
        assert str(hint) in render_cmd

    def test_output_in_04_final(self, matter: Path) -> None:
        (matter / "02_notes/case_data.json").write_text("{}", encoding="utf-8")
        make_hwpx(matter / "templates/tmpl.hwpx")

        with patch("watch_inbox.GLOBAL_TEMPLATE_DIR", _FAKE_GLOBAL), \
             patch("watch_inbox.subprocess.run", return_value=ok_proc()) as mock_run:
            run_cowork_chain(matter, SCRIPT_DIR)

        render_cmd = mock_run.call_args[0][0]
        o_idx = render_cmd.index("-o")
        output = Path(render_cmd[o_idx + 1])
        assert output.parent == matter / "04_final"
        assert output.suffix == ".hwpx"
