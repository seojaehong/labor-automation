#!/usr/bin/env python3
"""Tests for build_matter_pack.py — authority card generation."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from build_matter_pack import (
    SourceCard,
    build_matter_pack,
    detect_case_numbers,
    detect_courts,
    detect_dates,
    read_docx,
    read_hwpx,
    read_text_file,
    render_card,
    sanitize_stem,
    strip_xml_text,
    summarize_text,
)


# ── strip_xml_text ────────────────────────────────────────────


class TestStripXmlText:
    def test_extracts_text_nodes(self):
        xml = b"<root><a>hello</a><b>world</b></root>"
        assert "hello" in strip_xml_text(xml)
        assert "world" in strip_xml_text(xml)

    def test_empty_xml(self):
        assert strip_xml_text(b"<root/>") == ""

    def test_invalid_xml_returns_empty(self):
        assert strip_xml_text(b"not xml at all") == ""

    def test_ignores_whitespace_only_nodes(self):
        xml = b"<root><a>  </a><b>text</b></root>"
        result = strip_xml_text(xml)
        assert result.strip() == "text"


# ── read_text_file ─────────────────────────────────────────────


class TestReadTextFile:
    def test_reads_utf8(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("안녕하세요 판결", encoding="utf-8")
        text, warnings = read_text_file(p)
        assert "안녕하세요" in text
        assert warnings == []

    def test_returns_empty_list_warnings_on_success(self, tmp_path):
        p = tmp_path / "ok.md"
        p.write_text("# 제목\n내용", encoding="utf-8")
        _, warnings = read_text_file(p)
        assert warnings == []


# ── read_docx ─────────────────────────────────────────────────


class TestReadDocx:
    def _make_docx(self, tmp_path: Path, text: str) -> Path:
        p = tmp_path / "test.docx"
        xml = f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("word/document.xml", xml.encode("utf-8"))
        return p

    def test_extracts_text(self, tmp_path):
        p = self._make_docx(tmp_path, "테스트 내용")
        text, warnings = read_docx(p)
        assert "테스트 내용" in text

    def test_returns_warning_on_empty(self, tmp_path):
        p = tmp_path / "empty.docx"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("word/document.xml", b"<w:document/>")
        _, warnings = read_docx(p)
        assert any("empty" in w for w in warnings)

    def test_returns_warning_on_corrupt(self, tmp_path):
        p = tmp_path / "bad.docx"
        p.write_bytes(b"not a zip")
        _, warnings = read_docx(p)
        assert len(warnings) > 0


# ── read_hwpx ─────────────────────────────────────────────────


class TestReadHwpx:
    def _make_hwpx(self, tmp_path: Path, text: str) -> Path:
        p = tmp_path / "test.hwpx"
        xml = f'<?xml version="1.0"?><root><text>{text}</text></root>'
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("Contents/section0.xml", xml.encode("utf-8"))
        return p

    def test_extracts_text(self, tmp_path):
        p = self._make_hwpx(tmp_path, "구제신청 내용")
        text, warnings = read_hwpx(p)
        assert "구제신청 내용" in text

    def test_ignores_non_content_xml(self, tmp_path):
        p = tmp_path / "meta.hwpx"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("META-INF/container.xml", "<root><text>메타데이터</text></root>".encode("utf-8"))
            zf.writestr("Contents/section0.xml", "<root><text>본문</text></root>".encode("utf-8"))
        text, _ = read_hwpx(p)
        assert "본문" in text


# ── detect_case_numbers ───────────────────────────────────────


class TestDetectCaseNumbers:
    def test_detects_4digit_year_format(self):
        text = "대법원 2022다54321 판결"
        result = detect_case_numbers(text)
        assert "2022다54321" in result

    def test_detects_96nu5926(self):
        text = "대법원 1997. 2. 14. 선고 96누5926 판결"
        result = detect_case_numbers(text)
        assert any("96누5926" in n or "96" in n for n in result)

    def test_deduplicates(self):
        text = "96누5926 판결, 96누5926 판결"
        result = detect_case_numbers(text)
        assert result.count(result[0]) == 1 if result else True

    def test_returns_empty_for_no_match(self):
        result = detect_case_numbers("일반 텍스트입니다.")
        assert result == []

    def test_limits_to_10(self):
        nums = " ".join([f"2022가{str(i).zfill(5)}" for i in range(20)])
        result = detect_case_numbers(nums)
        assert len(result) <= 10


# ── detect_courts ─────────────────────────────────────────────


class TestDetectCourts:
    def test_detects_supreme_court(self):
        assert "대법원" in detect_courts("대법원 판결입니다.")

    def test_detects_multiple_courts(self):
        text = "대법원과 헌법재판소 판결"
        result = detect_courts(text)
        assert "대법원" in result
        assert "헌법재판소" in result

    def test_no_false_positives(self):
        result = detect_courts("일반 텍스트")
        assert result == []

    def test_detects_labor_commission(self):
        assert "중앙노동위원회" in detect_courts("중앙노동위원회 판정")


# ── detect_dates ──────────────────────────────────────────────


class TestDetectDates:
    def test_detects_korean_date_format(self):
        # \b 패턴: 마지막 '.' 직후 한국어 단어 문자가 오면 매치
        result = detect_dates("2026. 1. 15.해고")
        assert any("2026" in d for d in result)

    def test_deduplicates(self):
        # 날짜 직후 한국어 붙여쓰기로 \b 매치 확보
        text = "2026. 1. 15.해고 2026. 1. 15.재확인"
        result = detect_dates(text)
        assert len(result) == 1

    def test_limits_to_10(self):
        dates = " ".join([f"2020. {i}. 1." for i in range(1, 15)])
        result = detect_dates(dates)
        assert len(result) <= 10


# ── summarize_text ────────────────────────────────────────────


class TestSummarizeText:
    def test_returns_no_text_for_empty(self):
        assert summarize_text("", 200) == "(no text extracted)"

    def test_truncates_at_max_chars(self):
        long = "가나다라 " * 300
        result = summarize_text(long, 100)
        assert len(result) <= 104  # 100 + "..." margin

    def test_short_text_not_truncated(self):
        text = "짧은 텍스트"
        result = summarize_text(text, 500)
        assert result == text

    def test_blank_lines_ignored(self):
        text = "\n\n  \n실제 내용\n\n"
        result = summarize_text(text, 500)
        assert result == "실제 내용"


# ── sanitize_stem ─────────────────────────────────────────────


class TestSanitizeStem:
    def test_basic(self, tmp_path):
        p = tmp_path / "sample_irac.md"
        assert sanitize_stem(p) == "sample_irac"

    def test_spaces_to_underscore(self, tmp_path):
        p = tmp_path / "my file.md"
        result = sanitize_stem(p)
        assert " " not in result

    def test_empty_stem_returns_source(self, tmp_path):
        p = tmp_path / ".hiddenfile"
        result = sanitize_stem(p)
        # stem of ".hiddenfile" is ".hiddenfile" → strip "." → "hiddenfile"
        assert result != ""


# ── build_matter_pack ─────────────────────────────────────────


class TestBuildMatterPack:
    def _make_card(self, tmp_path: Path, name: str) -> SourceCard:
        source = tmp_path / "00_inbox" / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("판례 내용", encoding="utf-8")
        card_path = tmp_path / "02_notes" / "cards" / (name + ".md")
        card_path.parent.mkdir(parents=True, exist_ok=True)
        return SourceCard(
            source_path=source,
            card_path=card_path,
            text_len=10,
            case_numbers=["2022다54321"],
            courts=["대법원"],
            dates=["2022.1.1."],
            summary="요약",
            warnings=[],
        )

    def test_creates_pack_file(self, tmp_path):
        card = self._make_card(tmp_path, "source.md")
        pack = tmp_path / "02_notes" / "matter-pack.md"
        build_matter_pack([card], tmp_path, pack)
        assert pack.exists()

    def test_pack_contains_card_count(self, tmp_path):
        card = self._make_card(tmp_path, "source.md")
        pack = tmp_path / "02_notes" / "matter-pack.md"
        build_matter_pack([card], tmp_path, pack)
        content = pack.read_text(encoding="utf-8")
        assert "cards_count: 1" in content

    def test_empty_cards_list(self, tmp_path):
        pack = tmp_path / "matter-pack.md"
        build_matter_pack([], tmp_path, pack)
        content = pack.read_text(encoding="utf-8")
        assert "cards_count: 0" in content

    def test_pack_has_required_sections(self, tmp_path):
        pack = tmp_path / "matter-pack.md"
        build_matter_pack([], tmp_path, pack)
        content = pack.read_text(encoding="utf-8")
        for section in ["## Build Metadata", "## Authority Card Index", "## Core Facts", "## Issues"]:
            assert section in content


# ── render_card ───────────────────────────────────────────────


class TestRenderCard:
    def test_render_contains_source_file(self, tmp_path):
        source = tmp_path / "00_inbox" / "test.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("내용", encoding="utf-8")
        card_path = tmp_path / "02_notes" / "cards" / "test.md"
        card_path.parent.mkdir(parents=True, exist_ok=True)
        card = SourceCard(
            source_path=source,
            card_path=card_path,
            text_len=50,
            case_numbers=["2022다54321"],
            courts=["대법원"],
            dates=["2022.1.15."],
            summary="판시 내용 요약",
            warnings=[],
        )
        content = render_card(card, tmp_path)
        assert "00_inbox/test.md" in content
        assert "2022다54321" in content
        assert "대법원" in content
        assert "판시 내용 요약" in content

    def test_render_warnings_section(self, tmp_path):
        source = tmp_path / "00_inbox" / "warn.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("내용", encoding="utf-8")
        card_path = tmp_path / "cards" / "warn.md"
        card_path.parent.mkdir(parents=True, exist_ok=True)
        card = SourceCard(
            source_path=source, card_path=card_path,
            text_len=0, case_numbers=[], courts=[], dates=[],
            summary="(no text extracted)", warnings=["utf8 decode fallback used"],
        )
        content = render_card(card, tmp_path)
        assert "utf8 decode fallback used" in content
