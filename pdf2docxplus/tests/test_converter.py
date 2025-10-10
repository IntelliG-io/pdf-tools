from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from docx import Document

from pdf2docxplus import convert_pdf_to_docx
from pdf2docxplus.metadata import PDFMetadata


@patch("pdf2docxplus.converter.validate_conversion")
@patch("pdf2docxplus.converter.apply_metadata_to_docx")
@patch("pdf2docxplus.converter.extract_metadata")
@patch("pdf2docxplus.converter.Converter")
@patch("pdf2docxplus.converter.validate_pdf")
def test_convert_pdf_to_docx_pipeline(
    mock_validate_pdf: MagicMock,
    mock_converter_cls: MagicMock,
    mock_extract_metadata: MagicMock,
    mock_apply_metadata: MagicMock,
    mock_validate_conversion: MagicMock,
    tmp_path: Path,
):
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF-1.5")
    docx_path = tmp_path / "output.docx"
    Document().save(docx_path)

    mock_converter = MagicMock()
    mock_converter.__enter__.return_value = mock_converter
    mock_converter_cls.return_value = mock_converter

    sample_metadata = PDFMetadata(title="Test")
    mock_extract_metadata.return_value = sample_metadata

    result = convert_pdf_to_docx(pdf_path, docx_path)

    mock_validate_pdf.assert_called_once_with(pdf_path.resolve())
    mock_converter_cls.assert_called_once()
    mock_converter.convert.assert_called_once()
    mock_extract_metadata.assert_called_once()
    mock_apply_metadata.assert_called_once_with(docx_path.resolve(), sample_metadata)
    mock_validate_conversion.assert_called_once_with(docx_path.resolve(), sample_metadata)
    assert result == docx_path.resolve()


@patch("pdf2docxplus.converter.Converter")
def test_convert_pdf_to_docx_handles_conversion_error(mock_converter_cls: MagicMock, tmp_path: Path):
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF-1.5")
    docx_path = tmp_path / "output.docx"

    mock_converter = MagicMock()
    mock_converter.__enter__.side_effect = RuntimeError("boom")
    mock_converter_cls.return_value = mock_converter

    from pdf2docxplus.exceptions import ConversionError

    with patch("pdf2docxplus.converter.validate_pdf"), patch(
        "pdf2docxplus.converter.extract_metadata", return_value=None
    ), patch("pdf2docxplus.converter.ensure_output_directory"), patch(
        "pdf2docxplus.converter.validate_conversion"
    ):
        try:
            convert_pdf_to_docx(pdf_path, docx_path)
        except ConversionError:
            pass
        else:
            raise AssertionError("ConversionError was not raised")
