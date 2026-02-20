#!/usr/bin/env python3
"""Tests for chrome_log.py — /chrome session audit logger."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from chrome_log import FIELDNAMES, _sha256, append_log


# ── _sha256 ───────────────────────────────────────────────────


class TestSha256:
    def test_known_hash(self):
        expected = hashlib.sha256("hello".encode("utf-8")).hexdigest()
        assert _sha256("hello") == expected

    def test_empty_string(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert _sha256("") == expected

    def test_korean_text(self):
        text = "안녕하세요"
        result = _sha256(text)
        assert len(result) == 64  # hex digest length


# ── append_log ────────────────────────────────────────────────


class TestAppendLog:
    def test_creates_audit_dir_and_csv(self, tmp_path):
        log_path = append_log(tmp_path, "lbox", "search", query="부당해고")
        assert log_path.exists()
        assert log_path.parent.name == "07_audit"
        assert log_path.name == "chrome-session-log.csv"

    def test_csv_has_header_on_first_write(self, tmp_path):
        append_log(tmp_path, "lbox", "search")
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == FIELDNAMES

    def test_appends_multiple_rows(self, tmp_path):
        append_log(tmp_path, "lbox", "search", query="q1")
        append_log(tmp_path, "bigcase", "ai_query", query="q2")
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["platform"] == "lbox"
        assert rows[1]["platform"] == "bigcase"

    def test_no_duplicate_header_on_second_write(self, tmp_path):
        append_log(tmp_path, "lbox", "search")
        append_log(tmp_path, "lbox", "search")
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2  # 2 data rows, not 1 data + 1 misread header

    def test_query_field_recorded(self, tmp_path):
        append_log(tmp_path, "lbox", "search", query="부당해고 제척기간")
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        assert row["query"] == "부당해고 제척기간"

    def test_sha256_recorded_when_content_provided(self, tmp_path):
        content = "판결문 내용"
        append_log(tmp_path, "bigcase", "extract", content_for_hash=content)
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert row["sha256"] == expected

    def test_sha256_empty_when_no_content(self, tmp_path):
        append_log(tmp_path, "lbox", "search")
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        assert row["sha256"] == ""

    def test_result_count_field(self, tmp_path):
        append_log(tmp_path, "bigcase", "search", result_count=3508)
        log_path = tmp_path / "07_audit" / "chrome-session-log.csv"
        with log_path.open(encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        assert row["result_count"] == "3508"

    def test_returns_log_path(self, tmp_path):
        result = append_log(tmp_path, "superlawyer", "ai_query")
        assert isinstance(result, Path)
        assert result.exists()
