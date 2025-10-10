from __future__ import annotations

from datetime import datetime, timezone, timedelta

from pdf2docxplus.utils import parse_pdf_date


def test_parse_pdf_date_with_timezone():
    value = "D:20230501120000+02'30'"
    parsed = parse_pdf_date(value)
    assert parsed == datetime(2023, 5, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2, minutes=30)))


def test_parse_pdf_date_invalid():
    assert parse_pdf_date("invalid") is None
