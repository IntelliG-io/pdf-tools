"""Adapters bridging the shared PDF parser with the DOCX conversion pipeline."""

from __future__ import annotations

from ....core.parser import PDFParser
from ....pdf2docx.primitives import PdfDocument, Page


class PdfToDocxParserAdapter:
    """Wrap a :class:`PDFParser` to expose high level primitives."""

    def __init__(self, parser: PDFParser) -> None:
        self.parser = parser

    def as_reader(self):
        return self.parser.reader

    def metadata(self) -> dict[str, str]:
        return self.parser.metadata()

    def to_pdf_document(self) -> PdfDocument:
        """Create a minimal :class:`PdfDocument` compatible with the converter."""

        reader = self.parser.reader
        pages = []
        for index, page in enumerate(reader.pages):
            pages.append(
                Page(
                    number=index,
                    width=float(page.mediabox.width),
                    height=float(page.mediabox.height),
                    text_blocks=[],
                    images=[],
                    lines=[],
                )
            )
        return PdfDocument(pages=pages, metadata=self.metadata(), tagged=False)
