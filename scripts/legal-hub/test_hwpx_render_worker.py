#!/usr/bin/env python3
"""Tests for hwpx_render_worker.py — 24 scenarios (TDD).

check_structure    5개
check_placeholders 4개
load_job           4개
write_result       3개
mark_job           2개
emit_hwpx_job      6개
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hwpx_render_worker import (
    DONE_SUFFIX,
    FAIL_SUFFIX,
    JOB_SUFFIX,
    check_placeholders,
    check_structure,
    emit_hwpx_job,
    load_job,
    mark_job,
    write_result,
)

# ── helpers ────────────────────────────────────────────────────────────────────


def make_hwpx(path: Path, *, section_xml: str = "<root/>", mimetype: str = "application/hwp+zip") -> None:
    """최소 유효 HWPX(ZIP) 생성."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", mimetype)
        z.writestr("Contents/content.hpf", "<hpf/>")
        z.writestr("Contents/section0.xml", section_xml)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.getvalue())


def make_hwpx_no_section(path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("Contents/content.hpf", "<hpf/>")
    path.write_bytes(buf.getvalue())


def make_job_dict(tmp_path: Path, job_id: str = "TEST-001") -> dict:
    tmpl = tmp_path / "tmpl.hwpx"
    data = tmp_path / "data.json"
    make_hwpx(tmpl)
    data.write_text("{}", encoding="utf-8")
    return {
        "job_id":        job_id,
        "created_at":    "2026-02-20T00:00:00+00:00",
        "template_path": str(tmpl),
        "data_path":     str(data),
        "status":        "pending",
    }


# ── check_structure (5개) ──────────────────────────────────────────────────────


class TestCheckStructure:
    def test_valid_hwpx_returns_true(self, tmp_path: Path) -> None:
        p = tmp_path / "ok.hwpx"
        make_hwpx(p)
        ok, msg = check_structure(p)
        assert ok is True
        assert msg == "ok"

    def test_missing_mimetype_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.hwpx"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Contents/section0.xml", "<x/>")
        p.write_bytes(buf.getvalue())
        ok, msg = check_structure(p)
        assert ok is False
        assert "mimetype" in msg

    def test_wrong_mimetype_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.hwpx"
        make_hwpx(p, mimetype="application/pdf")
        ok, msg = check_structure(p)
        assert ok is False
        assert "mimetype" in msg

    def test_missing_section_xml_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "nosec.hwpx"
        make_hwpx_no_section(p)
        ok, msg = check_structure(p)
        assert ok is False
        assert "section" in msg

    def test_not_a_zip_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "notzip.hwpx"
        p.write_bytes(b"this is not a zip file")
        ok, msg = check_structure(p)
        assert ok is False
        assert "ZIP" in msg or "zip" in msg.lower()


# ── check_placeholders (4개) ──────────────────────────────────────────────────


class TestCheckPlaceholders:
    def test_no_placeholders_returns_true(self, tmp_path: Path) -> None:
        p = tmp_path / "clean.hwpx"
        make_hwpx(p, section_xml="<root><t>홍길동</t></root>")
        ok, msg = check_placeholders(p)
        assert ok is True

    def test_leftover_token_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "dirty.hwpx"
        make_hwpx(p, section_xml="<root><t>{{신청인_성명}}</t></root>")
        ok, msg = check_placeholders(p)
        assert ok is False
        assert "신청인_성명" in msg

    def test_multiple_tokens_all_reported(self, tmp_path: Path) -> None:
        p = tmp_path / "multi.hwpx"
        make_hwpx(p, section_xml="<t>{{A}}</t><t>{{B}}</t>")
        ok, msg = check_placeholders(p)
        assert ok is False
        assert "A" in msg and "B" in msg

    def test_partial_braces_not_flagged(self, tmp_path: Path) -> None:
        """단일 중괄호는 placeholder가 아님."""
        p = tmp_path / "partial.hwpx"
        make_hwpx(p, section_xml="<t>{not a token}</t>")
        ok, msg = check_placeholders(p)
        assert ok is True


# ── load_job (4개) ────────────────────────────────────────────────────────────


class TestLoadJob:
    def test_returns_dict(self, tmp_path: Path) -> None:
        job = make_job_dict(tmp_path)
        p = tmp_path / "job.json"
        p.write_text(json.dumps(job), encoding="utf-8")
        result = load_job(p)
        assert isinstance(result, dict)

    def test_job_id_preserved(self, tmp_path: Path) -> None:
        job = make_job_dict(tmp_path, job_id="MY-JOB-42")
        p = tmp_path / "j.json"
        p.write_text(json.dumps(job), encoding="utf-8")
        assert load_job(p)["job_id"] == "MY-JOB-42"

    def test_template_path_preserved(self, tmp_path: Path) -> None:
        job = make_job_dict(tmp_path)
        p = tmp_path / "j.json"
        p.write_text(json.dumps(job), encoding="utf-8")
        loaded = load_job(p)
        assert "template_path" in loaded

    def test_unicode_fields_preserved(self, tmp_path: Path) -> None:
        job = {"job_id": "K-001", "title": "부당해고 사건"}
        p = tmp_path / "k.json"
        p.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        assert load_job(p)["title"] == "부당해고 사건"


# ── write_result (3개) ────────────────────────────────────────────────────────


class TestWriteResult:
    def _gates(self, overall: bool = True) -> dict:
        return {
            "gate1_structure":    {"passed": True,  "detail": "ok"},
            "gate2_placeholders": {"passed": True,  "detail": "ok"},
            "gate3_roundtrip":    {"passed": None,  "detail": "skipped"},
            "overall":            overall,
        }

    def test_creates_result_json(self, tmp_path: Path) -> None:
        job = make_job_dict(tmp_path, "W-001")
        output = tmp_path / "W-001.hwpx"
        make_hwpx(output)
        result_path = write_result(job, output, self._gates(), tmp_path)
        assert result_path.exists()
        assert result_path.name == "W-001.result.json"

    def test_result_contains_overall(self, tmp_path: Path) -> None:
        job = make_job_dict(tmp_path, "W-002")
        output = tmp_path / "W-002.hwpx"
        make_hwpx(output)
        result_path = write_result(job, output, self._gates(overall=False), tmp_path)
        data = json.loads(result_path.read_text("utf-8"))
        assert data["overall"] is False

    def test_result_output_path_none_when_missing(self, tmp_path: Path) -> None:
        job = make_job_dict(tmp_path, "W-003")
        missing = tmp_path / "ghost.hwpx"  # 존재하지 않음
        result_path = write_result(job, missing, self._gates(), tmp_path)
        data = json.loads(result_path.read_text("utf-8"))
        assert data["output_path"] is None


# ── mark_job (2개) ────────────────────────────────────────────────────────────


class TestMarkJob:
    def test_success_creates_done(self, tmp_path: Path) -> None:
        job_path = tmp_path / f"J-001{JOB_SUFFIX}"
        job_path.write_text("{}", encoding="utf-8")
        marked = mark_job(job_path, success=True)
        assert marked.suffix == ".done"
        assert marked.exists()
        assert not job_path.exists()

    def test_failure_creates_fail(self, tmp_path: Path) -> None:
        job_path = tmp_path / f"J-002{JOB_SUFFIX}"
        job_path.write_text("{}", encoding="utf-8")
        marked = mark_job(job_path, success=False)
        assert marked.suffix == ".fail"
        assert marked.exists()
        assert not job_path.exists()


# ── emit_hwpx_job (6개) ───────────────────────────────────────────────────────


class TestEmitHwpxJob:
    def test_creates_job_file(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "t.hwpx"
        data = tmp_path / "d.json"
        make_hwpx(tmpl)
        data.write_text("{}", encoding="utf-8")
        jobs_dir = tmp_path / "jobs"
        path = emit_hwpx_job(tmpl, data, jobs_dir)
        assert path.exists()
        assert path.suffix == ".json"

    def test_job_file_has_pending_status(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "t.hwpx"
        data = tmp_path / "d.json"
        make_hwpx(tmpl)
        data.write_text("{}", encoding="utf-8")
        path = emit_hwpx_job(tmpl, data, tmp_path / "jobs")
        job = json.loads(path.read_text("utf-8"))
        assert job["status"] == "pending"

    def test_custom_job_id_used(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "t.hwpx"
        data = tmp_path / "d.json"
        make_hwpx(tmpl)
        data.write_text("{}", encoding="utf-8")
        path = emit_hwpx_job(tmpl, data, tmp_path / "jobs", job_id="CUSTOM-99")
        assert "CUSTOM-99" in path.name
        job = json.loads(path.read_text("utf-8"))
        assert job["job_id"] == "CUSTOM-99"

    def test_template_path_absolute_in_job(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "t.hwpx"
        data = tmp_path / "d.json"
        make_hwpx(tmpl)
        data.write_text("{}", encoding="utf-8")
        path = emit_hwpx_job(tmpl, data, tmp_path / "jobs")
        job = json.loads(path.read_text("utf-8"))
        assert Path(job["template_path"]).is_absolute()

    def test_jobs_dir_created_if_missing(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "t.hwpx"
        data = tmp_path / "d.json"
        make_hwpx(tmpl)
        data.write_text("{}", encoding="utf-8")
        new_dir = tmp_path / "new" / "jobs"
        assert not new_dir.exists()
        emit_hwpx_job(tmpl, data, new_dir)
        assert new_dir.exists()

    def test_auto_job_id_is_unique(self, tmp_path: Path) -> None:
        tmpl = tmp_path / "t.hwpx"
        data = tmp_path / "d.json"
        make_hwpx(tmpl)
        data.write_text("{}", encoding="utf-8")
        jobs_dir = tmp_path / "jobs"
        p1 = emit_hwpx_job(tmpl, data, jobs_dir)
        p2 = emit_hwpx_job(tmpl, data, jobs_dir)
        assert p1 != p2
