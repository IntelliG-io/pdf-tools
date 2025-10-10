"""Compression engine for :mod:`pdfcompressx`."""

from __future__ import annotations

import dataclasses
import io
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from pypdf import PdfReader, PdfWriter

from .exceptions import CompressionError
from .optimizers import Backend, BackendType, detect_backend, run_backend
from .utils import ensure_parent_dir, resolve_path
from .validators import validate_pdf

_LOGGER = logging.getLogger("pdfcompressx")

CompressionLevelName = Literal["low", "medium", "high"]


@dataclasses.dataclass(slots=True)
class CompressionLevel:
    """Defines behavioural toggles for compression levels."""

    name: CompressionLevelName
    image_quality: int
    downsample_ratio: float
    recompress_streams: bool


@dataclasses.dataclass(slots=True)
class CompressionResult:
    """Represents the outcome of a compression run."""

    input_path: Path
    output_path: Path
    level: CompressionLevelName
    original_size: int
    compressed_size: int
    backend: BackendType | None

    @property
    def bytes_saved(self) -> int:
        return max(self.original_size - self.compressed_size, 0)

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 1.0
        return self.compressed_size / self.original_size


_LEVELS: dict[CompressionLevelName, CompressionLevel] = {
    "low": CompressionLevel("low", image_quality=95, downsample_ratio=1.0, recompress_streams=True),
    "medium": CompressionLevel("medium", image_quality=80, downsample_ratio=0.75, recompress_streams=True),
    "high": CompressionLevel("high", image_quality=65, downsample_ratio=0.5, recompress_streams=True),
}


try:  # pragma: no cover - optional dependency
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore[assignment]


def _compress_with_pypdf(source: Path, destination: Path, level: CompressionLevel) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()

    metadata = reader.metadata or {}

    for page in reader.pages:
        if level.recompress_streams:
            try:
                page.compress_content_streams()
            except Exception as exc:  # pragma: no cover - defensive
                _LOGGER.warning("Failed to compress content streams: %s", exc)
        if Image is not None and level.downsample_ratio < 0.999:
            _downsample_page_images(page, level)
        writer.add_page(page)

    if metadata:
        cleaned = {k: v for k, v in metadata.items() if v is not None}
        if cleaned:
            writer.add_metadata(cleaned)

    ensure_parent_dir(destination)
    with destination.open("wb") as target:
        writer.write(target)


def _downsample_page_images(page, level: CompressionLevel) -> None:
    try:
        images = getattr(page, "images")
    except Exception:  # pragma: no cover - best effort
        images = []
    if not images:
        return

    resources = page.get("/Resources")
    if not resources:
        return
    xobjects = resources.get("/XObject") if hasattr(resources, "get") else None
    if xobjects is None:
        return

    for image in images:
        data = getattr(image, "data", None)
        name = getattr(image, "name", None)
        if not data or not name:
            continue
        xobject = xobjects.get(name) if hasattr(xobjects, 'get') else None
        if xobject is None:
            continue
        xobject_obj = xobject.get_object() if hasattr(xobject, 'get_object') else xobject
        try:
            with Image.open(io.BytesIO(data)) as img:  # type: ignore[name-defined]
                new_size = (
                    max(1, int(img.width * level.downsample_ratio)),
                    max(1, int(img.height * level.downsample_ratio)),
                )
                if new_size == img.size:
                    continue
                resized = img.resize(new_size, Image.LANCZOS)
                output = io.BytesIO()
                format_hint = "JPEG" if img.mode in {"RGB", "L"} else "PNG"
                save_kwargs = {"quality": level.image_quality} if format_hint == "JPEG" else {}
                resized.save(output, format=format_hint, **save_kwargs)
                output.seek(0)
                if hasattr(xobject_obj, '_data'):
                    xobject_obj._data = output.read()
        except Exception as exc:  # pragma: no cover - optional path
            _LOGGER.debug("Skipping image downsampling due to error: %s", exc)


def _select_backend() -> Backend | None:
    preferred = (BackendType.QPDF, BackendType.GHOSTSCRIPT)
    return detect_backend(preferred=preferred)


def compress_pdf(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    level: CompressionLevelName = "medium",
    *,
    post_validate: bool = False,
) -> CompressionResult:
    """Compress *input_path* writing the output to *output_path*."""

    if level not in _LEVELS:
        raise ValueError(f"Unknown compression level: {level}")

    level_config = _LEVELS[level]
    source = resolve_path(input_path)
    destination = resolve_path(output_path)

    if not source.exists():
        raise FileNotFoundError(source)

    temp_dir = Path(tempfile.mkdtemp(prefix="pdfcompressx-"))
    intermediate = temp_dir / "compressed.pdf"

    backend_used: Backend | None = _select_backend()
    try:
        if backend_used:
            try:
                run_backend(backend_used, source, intermediate, level)
            except Exception as exc:  # pragma: no cover - backend failure
                _LOGGER.warning("Backend %s failed: %s", backend_used.type.value, exc)
                _compress_with_pypdf(source, intermediate, level_config)
        else:
            _compress_with_pypdf(source, intermediate, level_config)

        ensure_parent_dir(destination)
        shutil.copy2(intermediate, destination)

        original_size = source.stat().st_size
        compressed_size = destination.stat().st_size
        result = CompressionResult(
            input_path=source,
            output_path=destination,
            level=level,
            original_size=original_size,
            compressed_size=compressed_size,
            backend=backend_used.type if backend_used else None,
        )

        if post_validate:
            validate_pdf(destination)

        return result
    except Exception as exc:
        raise CompressionError(f"Compression failed: {exc}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
