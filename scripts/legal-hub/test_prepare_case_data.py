#!/usr/bin/env python3
"""Tests for prepare_case_data.py — IRAC injection into case data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prepare_case_data import merge_irac_into_data, prepare_case_data


SAMPLE_IRAC = """\
# IRAC 분석: 부당해고 구제신청

## Issue (쟁점)
구제신청 기간은 제척기간이다[^1].

## Rule (법규)
| 법령 | 조문 |
|------|------|
| 근로기준법 제28조 | 구제신청권 |

[^1]: 대법원 96누5926 판결
"""

SAMPLE_DATA = {
    "신청인_성명": "홍길동",
    "신청인_주소": "서울시",
    "신청이유_IRAC": "(자동 삽입 예정)",
}


class TestMergeIracIntoData:
    def test_irac_injected(self):
        result = merge_irac_into_data(SAMPLE_DATA.copy(), SAMPLE_IRAC)
        assert "제척기간" in result["신청이유_IRAC"]
        assert "96누5926" in result["신청이유_IRAC"]

    def test_other_fields_preserved(self):
        result = merge_irac_into_data(SAMPLE_DATA.copy(), SAMPLE_IRAC)
        assert result["신청인_성명"] == "홍길동"
        assert result["신청인_주소"] == "서울시"

    def test_empty_irac(self):
        result = merge_irac_into_data(SAMPLE_DATA.copy(), "")
        assert result["신청이유_IRAC"] == ""

    def test_no_irac_field_in_data(self):
        data = {"신청인_성명": "홍길동"}
        result = merge_irac_into_data(data, SAMPLE_IRAC)
        assert "신청이유_IRAC" in result
        assert "제척기간" in result["신청이유_IRAC"]


class TestPrepareCaseData:
    def test_file_based_merge(self, tmp_path):
        irac_path = tmp_path / "irac.md"
        irac_path.write_text(SAMPLE_IRAC, encoding="utf-8")

        data_path = tmp_path / "data.json"
        data_path.write_text(json.dumps(SAMPLE_DATA, ensure_ascii=False), encoding="utf-8")

        output_path = tmp_path / "merged.json"
        result = prepare_case_data(data_path, irac_path, output_path)

        assert output_path.exists()
        merged = json.loads(output_path.read_text(encoding="utf-8"))
        assert "제척기간" in merged["신청이유_IRAC"]
        assert merged["신청인_성명"] == "홍길동"

    def test_output_is_valid_json(self, tmp_path):
        irac_path = tmp_path / "irac.md"
        irac_path.write_text(SAMPLE_IRAC, encoding="utf-8")

        data_path = tmp_path / "data.json"
        data_path.write_text(json.dumps(SAMPLE_DATA, ensure_ascii=False), encoding="utf-8")

        output_path = tmp_path / "merged.json"
        prepare_case_data(data_path, irac_path, output_path)

        # Should be parseable as JSON
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)

    def test_output_parent_auto_created(self, tmp_path):
        irac_path = tmp_path / "irac.md"
        irac_path.write_text(SAMPLE_IRAC, encoding="utf-8")

        data_path = tmp_path / "data.json"
        data_path.write_text(json.dumps(SAMPLE_DATA, ensure_ascii=False), encoding="utf-8")

        output_path = tmp_path / "deep" / "nested" / "merged.json"
        prepare_case_data(data_path, irac_path, output_path)
        assert output_path.exists()
