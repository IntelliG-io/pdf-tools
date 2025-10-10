from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest
from pypdf import PdfWriter


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
