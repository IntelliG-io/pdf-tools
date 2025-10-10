from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdfcompressx import CompressionResult, compress_pdf, validate_pdf
@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({
        "/Title": "Sample Document",
        "/Author": "pdfcompressx",
    })
    path = tmp_path / "sample.pdf"
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def test_compress_pdf_creates_output(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "compressed.pdf"
    result = compress_pdf(sample_pdf, output, level="medium", post_validate=False)

    assert isinstance(result, CompressionResult)
    assert output.exists()
    assert result.compressed_size > 0

    reader = PdfReader(str(output))
    assert reader.metadata.get("/Title") == "Sample Document"


def test_compress_pdf_supports_high_level(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "high.pdf"
    result = compress_pdf(sample_pdf, output, level="high", post_validate=False)
    assert result.output_path == output
    assert result.level == "high"


def test_compress_pdf_invalid_level(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        compress_pdf(sample_pdf, tmp_path / "out.pdf", level="invalid")


def test_validate_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    bogus = tmp_path / "not.pdf"
    bogus.write_text("not a pdf")
    from pdfcompressx.exceptions import InvalidPDFError

    with pytest.raises(InvalidPDFError):
        validate_pdf(bogus, use_external=False)


def test_compress_pdf_post_validate(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "validated.pdf"
    result = compress_pdf(sample_pdf, output, post_validate=True)
    assert result.output_path.exists()
    validate_pdf(result.output_path, use_external=False)


def test_compression_error_when_missing_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compress_pdf(tmp_path / "missing.pdf", tmp_path / "out.pdf")
