from __future__ import annotations

from pathlib import Path
from typing import Callable
import sys

import pytest
from pypdf import PdfWriter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    for _ in range(5):
        writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Producer": "pdfsplitx-tests", "/Title": "Sample"})
    with pdf_path.open("wb") as stream:
        writer.write(stream)
    return pdf_path


@pytest.fixture()
def empty_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    with pdf_path.open("wb") as stream:
        writer.write(stream)
    return pdf_path


@pytest.fixture()
def pdf_factory(tmp_path: Path) -> Callable[[str, str | None], Path]:
    def _create(filename: str, title: str | None = None) -> Path:
        path = tmp_path / filename
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        if title is not None:
            writer.add_metadata({"/Title": title})
        with path.open("wb") as handle:
            writer.write(handle)
        return path

    return _create


@pytest.fixture()
def sample_pdfs(pdf_factory: Callable[[str, str | None], Path]) -> list[Path]:
    pdf1 = pdf_factory("one.pdf", title="Document One")
    pdf2 = pdf_factory("two.pdf")
    return [pdf1, pdf2]
