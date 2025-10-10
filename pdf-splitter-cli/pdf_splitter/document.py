"""Adapter utilities for interacting with PDF files via pluggable backends."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Optional, Union

from .backends import BackendDocument, PypdfBackend
from .backends.base import PDFBackend
from .exceptions import (
    InvalidPDFError,
    InsufficientDiskSpaceError,
    PDFSplitterException,
)
from .types import PDFInfo


class PDFDocumentAdapter:
    """High level helper around a backend-specific PDF document."""

    def __init__(
        self,
        pdf_path: str,
        password: Optional[str] = None,
        *,
        backend: Optional[PDFBackend] = None,
    ) -> None:
        self.path = Path(pdf_path)
        self.backend: PDFBackend = backend or PypdfBackend()
        self._document: BackendDocument = self.backend.load(pdf_path, password=password)

        self._fonts_cache: Optional[List[str]] = None
        self._attachments_cache: Optional[int] = None
        self._xmp_cache: Optional[str] = None
        self._has_outlines_cache: Optional[bool] = None
        self._linearized_cache: Optional[bool] = None

    # ------------------------------------------------------------------
    # Basic document information helpers
    # ------------------------------------------------------------------
    @property
    def document(self) -> BackendDocument:
        return self._document

    @property
    def num_pages(self) -> int:
        return self._document.num_pages

    @property
    def file_size(self) -> int:
        return self._document.file_size

    @property
    def metadata(self) -> Any:
        metadata = getattr(self._document, "metadata", None)
        if metadata is not None:
            return metadata
        reader = getattr(self._document, "reader", None)
        return getattr(reader, "metadata", None)

    @property
    def is_encrypted(self) -> bool:
        encrypted = getattr(self._document, "is_encrypted", None)
        if encrypted is not None:
            return bool(encrypted)
        reader = getattr(self._document, "reader", None)
        return bool(getattr(reader, "is_encrypted", False))

    @property
    def has_outlines(self) -> bool:
        if self._has_outlines_cache is None:
            reader = getattr(self._document, "reader", None)
            outlines = getattr(reader, "outlines", None)
            self._has_outlines_cache = bool(outlines)
        return self._has_outlines_cache

    @property
    def linearized(self) -> bool:
        if self._linearized_cache is None:
            raw_bytes = getattr(self._document, "raw_bytes", b"")
            head = raw_bytes[:1024].decode(errors="ignore") if raw_bytes else ""
            self._linearized_cache = "/Linearized" in head
        return self._linearized_cache

    @property
    def xmp_metadata(self) -> Optional[str]:
        if self._xmp_cache is not None:
            return self._xmp_cache

        xmp = getattr(self._document, "xmp_metadata", None)
        if xmp is None:
            reader = getattr(self._document, "reader", None)
            xmp = getattr(reader, "xmp_metadata", None)

        if xmp is None:
            self._xmp_cache = None
        else:
            xml = getattr(xmp, "xmp_data", None) or getattr(xmp, "xml", None)
            if isinstance(xml, bytes):
                self._xmp_cache = xml.decode("utf-8", errors="ignore")
            elif isinstance(xml, str):
                self._xmp_cache = xml
            else:
                self._xmp_cache = None
        return self._xmp_cache

    @property
    def fonts(self) -> List[str]:
        if self._fonts_cache is None:
            fonts: set[str] = set()
            for page in self.iter_pages():
                resources = page.get("/Resources") if hasattr(page, "get") else None
                if resources is None:
                    continue
                font_dict = resources.get("/Font") if hasattr(resources, "get") else None
                if font_dict is None:
                    continue
                values = font_dict.values() if hasattr(font_dict, "values") else []
                for font in values:
                    try:
                        font_obj = font.get_object() if hasattr(font, "get_object") else font
                        base_font = font_obj.get("/BaseFont") if hasattr(font_obj, "get") else None
                        if base_font:
                            fonts.add(str(base_font))
                    except Exception:  # pragma: no cover - defensive
                        continue
            self._fonts_cache = sorted(fonts)
        return self._fonts_cache

    @property
    def attachment_count(self) -> int:
        if self._attachments_cache is not None:
            return self._attachments_cache

        count = 0
        try:
            reader = getattr(self._document, "reader", None)
            trailer = getattr(reader, "trailer", None)
            catalog = trailer.get("/Root") if trailer else None
            if catalog and "/Names" in catalog:
                names = catalog["/Names"]
                if "/EmbeddedFiles" in names:
                    embedded = names["/EmbeddedFiles"]
                    file_names = embedded.get("/Names", [])
                    count = len(file_names) // 2
        except Exception:  # pragma: no cover - defensive
            count = 0

        self._attachments_cache = count
        return count

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    def get_page(self, page_number_zero_indexed: int):
        return self._document.get_page(page_number_zero_indexed)

    def iter_pages(self) -> Iterable[Any]:
        return self._document.iter_pages()

    def new_writer(self) -> Any:
        return self.backend.new_writer()

    def write(self, writer: Any, destination: Union[str, Path]) -> None:
        self.backend.write(writer, str(destination))

    def copy_metadata(
        self,
        writer: Any,
        *,
        title_suffix: str = "",
        pages_label: Optional[str] = None,
    ) -> None:
        """Copy core metadata and optional suffixes to ``writer``."""

        self._document.copy_metadata(writer, title_suffix=title_suffix, pages_label=pages_label)

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def to_pdf_info(self) -> PDFInfo:
        return PDFInfo(
            num_pages=self.num_pages,
            file_size=self.file_size,
            title=getattr(self.metadata, "title", None),
            author=getattr(self.metadata, "author", None),
            subject=getattr(self.metadata, "subject", None),
            creator=getattr(self.metadata, "creator", None),
            producer=getattr(self.metadata, "producer", None),
            is_encrypted=self.is_encrypted,
            linearized=self.linearized,
            has_outlines=self.has_outlines,
            fonts=self.fonts,
            attachments=self.attachment_count,
            xmp_metadata=self.xmp_metadata,
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_access(self) -> None:
        """Perform lightweight validation ensuring all pages are readable."""
        try:
            for page in self.iter_pages():
                _ = getattr(page, "mediabox", None)
        except Exception as exc:  # pragma: no cover - defensive
            raise InvalidPDFError(f"Unexpected error validating PDF pages: {exc}") from exc

    # ------------------------------------------------------------------
    @staticmethod
    def ensure_directory_writable(directory: str, required_mb: int = 10) -> Path:
        path = Path(directory)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise InsufficientDiskSpaceError(
                f"Permission denied while creating directory: {directory}."
            ) from exc

        try:
            usage = path.stat()
        except Exception:  # pragma: no cover - fallback
            usage = None

        # Fallback: attempt to write temp file if stat missing free space info
        try:
            with (path / ".pdf_splitter_probe").open("wb") as handle:
                handle.write(b"0")
            (path / ".pdf_splitter_probe").unlink(missing_ok=True)
        except OSError as exc:
            raise InsufficientDiskSpaceError(
                f"Cannot write to directory: {directory}. Error: {exc}"
            ) from exc

        # Additional free-space heuristic if supported by platform
        try:
            import shutil

            total, used, free = shutil.disk_usage(str(path))
            if free / (1024 * 1024) < required_mb:
                raise InsufficientDiskSpaceError(
                    "Insufficient disk space in {directory}. Available {available:.1f} MB, required {required} MB.".format(
                        directory=directory,
                        available=free / (1024 * 1024),
                        required=required_mb,
                    )
                )
        except InsufficientDiskSpaceError:
            raise
        except Exception:
            # If disk usage retrieval fails, continue silently
            pass

        return path


__all__ = ["PDFDocumentAdapter"]
