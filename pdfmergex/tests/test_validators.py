from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from pdfmergex.validators import PDFInfo, get_pdf_info, validate_pdf


def test_validate_pdf_success(
    pdf_factory: Callable[[str, str | None], Path]
) -> None:
    pdf_path = pdf_factory("doc.pdf")
    assert validate_pdf(pdf_path)


def test_validate_pdf_failure(tmp_path: Path) -> None:
    invalid_path = tmp_path / "not.pdf"
    invalid_path.write_text("not a pdf")
    with pytest.raises(Exception):
        validate_pdf(invalid_path)


def test_get_pdf_info(
    pdf_factory: Callable[[str, str | None], Path]
) -> None:
    pdf_path = pdf_factory("info.pdf")
    info = get_pdf_info(pdf_path)
    assert isinstance(info, PDFInfo)
    assert info.num_pages == 1
    assert info.metadata.get("/Title") is None
    assert "/Producer" in info.metadata
