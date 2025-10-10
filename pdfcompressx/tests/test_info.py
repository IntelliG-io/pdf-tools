from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from pdfcompressx import get_compression_info


def test_get_compression_info_reports_metrics(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    pdf_path = tmp_path / "info.pdf"
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    info = get_compression_info(pdf_path)

    assert info.file_size_bytes == pdf_path.stat().st_size
    assert info.image_count == 0
    assert info.potential_savings_bytes >= 0
