"""pypdf backend implementation for PDF Splitter."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import IndirectObject, NameObject

from ..exceptions import EncryptedPDFError, InvalidPDFError
from .base import BackendDocument, PDFBackend


@dataclass
class PypdfDocument(BackendDocument):
    reader: PdfReader
    raw_bytes: bytes

    def iter_pages(self) -> Iterable[object]:
        return iter(self.reader.pages)

    def get_page(self, index: int) -> object:
        return self.reader.pages[index]

    def copy_metadata(self, writer: PdfWriter, *, title_suffix: str = "", pages_label: str | None = None) -> None:
        metadata_dict = {}
        metadata = self.reader.metadata

        if metadata and metadata.title:
            title = metadata.title
            if title_suffix:
                title = f"{title}{title_suffix}"
            metadata_dict['/Title'] = title
        if metadata and metadata.author:
            metadata_dict['/Author'] = metadata.author
        if metadata and metadata.subject:
            metadata_dict['/Subject'] = metadata.subject
        if metadata and metadata.creator:
            metadata_dict['/Creator'] = metadata.creator

        if pages_label:
            metadata_dict['/Keywords'] = pages_label

        metadata_dict.setdefault('/Producer', 'PDF Splitter CLI')

        if metadata_dict:
            writer.add_metadata(metadata_dict)

        metadata_ref = self._metadata_reference()
        if metadata_ref is not None:
            writer._root_object[NameObject('/Metadata')] = metadata_ref  # type: ignore[attr-defined]

    def _metadata_reference(self) -> IndirectObject | None:
        try:
            catalog = self.reader.trailer.get("/Root")
            metadata_ref = catalog.get("/Metadata") if catalog else None
            if isinstance(metadata_ref, IndirectObject):
                return metadata_ref
        except Exception:
            return None
        return None


class PypdfBackend(PDFBackend):
    """Backend implementation that uses `pypdf` under the hood."""

    def load(self, pdf_path: str, password: str | None = None) -> PypdfDocument:
        path = Path(pdf_path)
        if not path.exists() or not path.is_file():
            raise InvalidPDFError(f"PDF file not found: {pdf_path}")

        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            raise InvalidPDFError(f"Unable to read PDF file: {pdf_path}. Error: {exc}") from exc

        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
        except PdfReadError as exc:
            raise InvalidPDFError(f"Corrupted or invalid PDF file: {pdf_path}. Error: {exc}") from exc
        except Exception as exc:
            raise InvalidPDFError(f"Unexpected error reading PDF: {pdf_path}. Error: {exc}") from exc

        if reader.is_encrypted:
            if password:
                if reader.decrypt(password) == 0:
                    raise EncryptedPDFError("Failed to decrypt PDF with supplied password.")
            else:
                raise EncryptedPDFError("PDF is encrypted. Supply a password to process this file.")

        num_pages = len(reader.pages)
        if num_pages == 0:
            raise InvalidPDFError(f"PDF has no pages: {pdf_path}")

        return PypdfDocument(num_pages=num_pages, file_size=len(raw_bytes), reader=reader, raw_bytes=raw_bytes)

    def new_writer(self) -> PdfWriter:
        return PdfWriter()

    def write(self, writer: PdfWriter, destination: str) -> None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as handle:
            writer.write(handle)
