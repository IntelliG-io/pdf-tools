"""Optional optimization helpers for merged PDF documents."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .exceptions import PdfOptimizationError
from .utils import PathLike, ensure_path
from .validators import validate_pdf

LOGGER = logging.getLogger("intellipdf.merge")


def _qpdf_available() -> str | None:
    return shutil.which("qpdf")


def optimize_pdf(input: PathLike, output: PathLike) -> Path:
    """Optimize a PDF using ``qpdf`` when available."""

    input_path = ensure_path(input)
    output_path = ensure_path(output)

    validate_pdf(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qpdf_executable = _qpdf_available()
    if not qpdf_executable:
        LOGGER.debug("qpdf not available; copying %s to %s", input_path, output_path)
        try:
            shutil.copyfile(input_path, output_path)
        except Exception as exc:  # pragma: no cover - IO errors vary
            LOGGER.error("Failed to copy PDF during optimization: %s", exc)
            raise PdfOptimizationError("Failed to copy PDF during optimization") from exc
        return output_path

    command = [
        qpdf_executable,
        "--linearize",
        str(input_path),
        str(output_path),
    ]
    LOGGER.debug("Running qpdf command: %s", command)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - OS errors vary
        LOGGER.error("Failed to execute qpdf: %s", exc)
        raise PdfOptimizationError("Failed to execute qpdf") from exc

    if result.returncode != 0:
        LOGGER.error(
            "qpdf failed with code %s: %s", result.returncode, result.stderr
        )
        raise PdfOptimizationError(f"qpdf failed: {result.stderr.strip()}")

    LOGGER.info("Optimized PDF %s into %s", input_path, output_path)
    return output_path


__all__ = ["optimize_pdf"]
