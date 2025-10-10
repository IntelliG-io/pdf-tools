"""Backend abstractions for PDF Splitter."""

from .base import BackendDocument, PDFBackend
from .pypdf_backend import PypdfBackend

__all__ = [
    "BackendDocument",
    "PDFBackend",
    "PypdfBackend",
]
