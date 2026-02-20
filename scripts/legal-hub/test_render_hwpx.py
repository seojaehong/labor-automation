#!/usr/bin/env python3
"""Tests for render_hwpx.py — hwpx template placeholder replacement."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from render_hwpx import render_hwpx, replace_placeholders


# ── Fixture: minimal hwpx (ZIP with XML) ─────────────────────


def _make_test_hwpx(tmp_path: Path, xml_content: str, filename: str = "Contents/section0.xml") -> Path:
    """Create a minimal hwpx file (ZIP) with one XML file."""
    hwpx_path = tmp_path / "test_template.hwpx"
    with zipfile.ZipFile(hwpx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, xml_content)
        # Add a non-XML file to test passthrough
        zf.writestr("mimetype", "application/hwp+zip")
    return hwpx_path


# ── replace_placeholders ─────────────────────────────────────


class TestReplacePlaceholders:
    def test_basic_replacement(self):
        result = replace_placeholders("이름: {{신청인_성명}}", {"신청인_성명": "홍길동"})
        assert result == "이름: 홍길동"

    def test_multiple_placeholders(self):
        text = "{{신청인_성명}}은 {{피신청인_상호}}를 상대로"
        data = {"신청인_성명": "홍길동", "피신청인_상호": "주식회사 OO운수"}
        result = replace_placeholders(text, data)
        assert result == "홍길동은 주식회사 OO운수를 상대로"

    def test_missing_key_keeps_original(self):
        result = replace_placeholders("{{없는키}}", {})
        assert result == "{{없는키}}"

    def test_whitespace_in_key(self):
        result = replace_placeholders("{{ 신청인_성명 }}", {"신청인_성명": "홍길동"})
        assert result == "홍길동"

    def test_no_placeholders(self):
        result = replace_placeholders("일반 텍스트입니다.", {"키": "값"})
        assert result == "일반 텍스트입니다."

    def test_multiline_replacement(self):
        text = "제1항: {{청구취지}}\n제2항: {{신청이유_IRAC}}"
        data = {"청구취지": "복직을 구합니다.", "신청이유_IRAC": "IRAC 분석 결과"}
        result = replace_placeholders(text, data)
        assert "복직을 구합니다." in result
        assert "IRAC 분석 결과" in result

    def test_newlines_in_value(self):
        data = {"첨부서류_목록": "1. 근로계약서\n2. 해고통보서"}
        result = replace_placeholders("첨부: {{첨부서류_목록}}", data)
        assert "1. 근로계약서\n2. 해고통보서" in result


# ── render_hwpx (ZIP processing) ─────────────────────────────


class TestRenderHwpx:
    def test_basic_render(self, tmp_path):
        xml = '<text>신청인: {{신청인_성명}}</text>'
        template = _make_test_hwpx(tmp_path, xml)
        output = tmp_path / "output.hwpx"
        data = {"신청인_성명": "홍길동"}

        replaced = render_hwpx(template, data, output)

        assert output.exists()
        assert len(replaced) == 1
        assert "Contents/section0.xml" in replaced[0]

        # Verify content inside output ZIP
        with zipfile.ZipFile(output, "r") as zf:
            result_xml = zf.read("Contents/section0.xml").decode("utf-8")
            assert "홍길동" in result_xml
            assert "{{신청인_성명}}" not in result_xml

    def test_non_xml_files_passthrough(self, tmp_path):
        xml = '<text>{{신청인_성명}}</text>'
        template = _make_test_hwpx(tmp_path, xml)
        output = tmp_path / "output.hwpx"

        render_hwpx(template, {"신청인_성명": "홍길동"}, output)

        with zipfile.ZipFile(output, "r") as zf:
            mimetype = zf.read("mimetype").decode("utf-8")
            assert mimetype == "application/hwp+zip"

    def test_no_replacements_returns_empty_list(self, tmp_path):
        xml = '<text>고정 텍스트</text>'
        template = _make_test_hwpx(tmp_path, xml)
        output = tmp_path / "output.hwpx"

        replaced = render_hwpx(template, {"신청인_성명": "홍길동"}, output)

        assert replaced == []
        assert output.exists()

    def test_multiple_xml_files(self, tmp_path):
        hwpx_path = tmp_path / "multi.hwpx"
        with zipfile.ZipFile(hwpx_path, "w") as zf:
            zf.writestr("Contents/section0.xml", "<a>{{신청인_성명}}</a>")
            zf.writestr("Contents/section1.xml", "<b>{{해고일자}}</b>")
            zf.writestr("Contents/header.xml", "<c>고정</c>")
        output = tmp_path / "out.hwpx"
        data = {"신청인_성명": "홍길동", "해고일자": "2026. 1. 15."}

        replaced = render_hwpx(hwpx_path, data, output)

        assert len(replaced) == 2
        with zipfile.ZipFile(output, "r") as zf:
            s0 = zf.read("Contents/section0.xml").decode("utf-8")
            s1 = zf.read("Contents/section1.xml").decode("utf-8")
            assert "홍길동" in s0
            assert "2026. 1. 15." in s1

    def test_output_parent_auto_created(self, tmp_path):
        xml = '<text>{{신청인_성명}}</text>'
        template = _make_test_hwpx(tmp_path, xml)
        output = tmp_path / "deep" / "nested" / "output.hwpx"

        render_hwpx(template, {"신청인_성명": "홍길동"}, output)

        assert output.exists()

    def test_xml_special_chars_in_value(self, tmp_path):
        xml = '<text>{{청구취지}}</text>'
        template = _make_test_hwpx(tmp_path, xml)
        output = tmp_path / "output.hwpx"
        data = {"청구취지": "A & B < C > D"}

        render_hwpx(template, data, output)

        with zipfile.ZipFile(output, "r") as zf:
            result = zf.read("Contents/section0.xml").decode("utf-8")
            assert "A & B < C > D" in result

    def test_all_example_placeholders(self, tmp_path):
        """Test with the actual example data file placeholders."""
        placeholders = [
            "신청인_성명", "신청인_주소", "신청인_연락처",
            "피신청인_상호", "피신청인_대표자", "피신청인_주소",
            "해고일자", "청구취지", "신청이유_IRAC",
            "첨부서류_목록", "신청일자", "노동위원회_명칭",
        ]
        xml_parts = [f"<field name='{p}'>{{{{ {p} }}}}</field>" for p in placeholders]
        xml = "<root>" + "".join(xml_parts) + "</root>"
        template = _make_test_hwpx(tmp_path, xml)
        output = tmp_path / "output.hwpx"

        data = {p: f"값_{p}" for p in placeholders}
        replaced = render_hwpx(template, data, output)

        assert len(replaced) == 1
        with zipfile.ZipFile(output, "r") as zf:
            result = zf.read("Contents/section0.xml").decode("utf-8")
            for p in placeholders:
                assert f"값_{p}" in result
                assert f"{{{{{p}}}}}" not in result  # no leftover tokens
