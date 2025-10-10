"""Information utilities for the :mod:`intellipdf.compress` package."""

from __future__ import annotations

import dataclasses
import logging
import os

from pypdf import PdfReader

from .utils import resolve_path

_LOGGER = logging.getLogger("intellipdf.compress")


@dataclasses.dataclass(slots=True)
class CompressionInfo:
    """Describes metrics about a PDF file relevant for compression."""

    file_size_bytes: int
    image_count: int
    average_image_dpi: float | None
    potential_savings_bytes: int


def _estimate_image_dpi(reader: PdfReader) -> tuple[int, float | None]:
    image_count = 0
    dpi_values: list[float] = []

    for page in reader.pages:
        page_width_inch = float(page.mediabox.width) / 72.0
        page_height_inch = float(page.mediabox.height) / 72.0
        try:
            images = getattr(page, "images", [])
        except Exception:  # pragma: no cover - attribute access guard
            images = []
        for image in images:
            image_count += 1
            width_px = getattr(image, "width", None)
            height_px = getattr(image, "height", None)
            if not width_px or not height_px:
                continue
            dpi_x = width_px / max(page_width_inch, 1e-6)
            dpi_y = height_px / max(page_height_inch, 1e-6)
            dpi_values.append((dpi_x + dpi_y) / 2.0)

    average_dpi = sum(dpi_values) / len(dpi_values) if dpi_values else None
    return image_count, average_dpi


def _estimate_potential_savings(file_size_bytes: int, image_count: int) -> int:
    if image_count == 0:
        return int(file_size_bytes * 0.05)
    weight = min(0.35 + image_count * 0.02, 0.6)
    return int(file_size_bytes * weight)


def get_compression_info(path: str | os.PathLike[str]) -> CompressionInfo:
    """Return :class:`CompressionInfo` for the PDF located at *path*."""

    pdf_path = resolve_path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    file_size = pdf_path.stat().st_size
    reader = PdfReader(str(pdf_path))
    image_count, average_dpi = _estimate_image_dpi(reader)
    savings = _estimate_potential_savings(file_size, image_count)

    info = CompressionInfo(
        file_size_bytes=file_size,
        image_count=image_count,
        average_image_dpi=average_dpi,
        potential_savings_bytes=savings,
    )
    _LOGGER.debug("Compression info for %s: %s", pdf_path, info)
    return info
