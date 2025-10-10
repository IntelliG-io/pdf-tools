from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest
from pypdf import PdfWriter


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
