#!/usr/bin/env python3
"""Tests for scaffold_hub.py — matter workspace creation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scaffold_hub import FOLDERS, create_workspace, sanitize_name, write_file


# ── sanitize_name ─────────────────────────────────────────────


class TestSanitizeName:
    def test_basic_alphanumeric(self):
        assert sanitize_name("CASE-001") == "CASE-001"

    def test_spaces_become_underscores(self):
        assert sanitize_name("부당 해고") == "부당_해고"

    def test_illegal_chars_become_dash(self):
        result = sanitize_name('a/b\\c:d*e?f"g<h>i|j')
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result

    def test_empty_string_returns_matter(self):
        assert sanitize_name("") == "matter"

    def test_strips_leading_trailing_special(self):
        result = sanitize_name("...CASE-001...")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_multiple_spaces_collapsed(self):
        result = sanitize_name("a   b")
        assert "__" not in result


# ── write_file ────────────────────────────────────────────────


class TestWriteFile:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "out.txt"
        written = write_file(p, "hello")
        assert written is True
        assert p.read_text(encoding="utf-8") == "hello"

    def test_returns_false_if_exists_no_overwrite(self, tmp_path):
        p = tmp_path / "out.txt"
        p.write_text("original", encoding="utf-8")
        written = write_file(p, "new content")
        assert written is False
        assert p.read_text(encoding="utf-8") == "original"

    def test_overwrites_when_flag_set(self, tmp_path):
        p = tmp_path / "out.txt"
        p.write_text("original", encoding="utf-8")
        write_file(p, "new content", overwrite=True)
        assert p.read_text(encoding="utf-8") == "new content"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "deep" / "nested" / "file.txt"
        write_file(p, "data")
        assert p.exists()


# ── create_workspace ──────────────────────────────────────────


class TestCreateWorkspace:
    def test_creates_all_folders(self, tmp_path):
        create_workspace(tmp_path, "TEST-001", "테스트 사건", overwrite_rules=False)
        matter_dir = tmp_path / "TEST-001"
        for folder in FOLDERS:
            assert (matter_dir / folder).is_dir(), f"Missing folder: {folder}"

    def test_creates_matter_meta_json(self, tmp_path):
        create_workspace(tmp_path, "TEST-002", "메타 테스트", overwrite_rules=False)
        meta_path = tmp_path / "TEST-002" / "matter-meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["matter_id"] == "TEST-002"
        assert meta["title"] == "메타 테스트"
        assert meta["status"] == "intake"

    def test_creates_template_files(self, tmp_path):
        create_workspace(tmp_path, "TEST-003", "", overwrite_rules=False)
        d = tmp_path / "TEST-003"
        assert (d / ".cursorrules").exists()
        assert (d / "02_notes" / "matter-pack.md").exists()
        assert (d / "02_notes" / "authority-card-template.md").exists()
        assert (d / "03_drafts" / "draft.md").exists()
        assert (d / "templates" / "readme.md").exists()

    def test_sanitizes_matter_id(self, tmp_path):
        create_workspace(tmp_path, "test case/001", "", overwrite_rules=False)
        # Slashes become dashes; spaces become underscores
        found = list(tmp_path.iterdir())
        assert len(found) == 1
        assert found[0].is_dir()

    def test_returns_matter_dir_path(self, tmp_path):
        result = create_workspace(tmp_path, "RETURN-TEST", "", overwrite_rules=False)
        assert result.is_dir()
        assert result.name == "RETURN-TEST"

    def test_idempotent_second_call(self, tmp_path):
        create_workspace(tmp_path, "IDEM-001", "first", overwrite_rules=False)
        # Second call should not raise and not overwrite template files
        create_workspace(tmp_path, "IDEM-001", "second", overwrite_rules=False)
        meta = json.loads((tmp_path / "IDEM-001" / "matter-meta.json").read_text(encoding="utf-8"))
        assert meta["title"] == "first"  # not overwritten
