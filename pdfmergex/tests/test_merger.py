from __future__ import annotations

from pathlib import Path

import pytest

from pdfmergex.merger import merge_pdfs
from pdfmergex.validators import get_pdf_info


def test_merge_pdfs_creates_output(
    tmp_path: Path, sample_pdfs: list[Path]
) -> None:
    output = tmp_path / "merged.pdf"

    result = merge_pdfs(sample_pdfs, output)

    assert result == output
    assert output.exists()

    info = get_pdf_info(output)
    assert info.num_pages == 2
    assert info.metadata.get("/Title") == "Document One"


def test_merge_pdfs_no_inputs(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        merge_pdfs([], tmp_path / "out.pdf")
