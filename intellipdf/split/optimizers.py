"""Optional optimisation helpers for :mod:`intellipdf.split`."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .utils import coerce_path

LOGGER = logging.getLogger("intellipdf.split")


def optimize_pdf(source: str | Path, destination: str | Path) -> bool:
    """Optimise a PDF using :command:`qpdf` if it is available.

    Args:
        source: Path to the input PDF file.
        destination: Path to write the optimised PDF to.

    Returns:
        ``True`` if optimisation was performed, otherwise ``False`` when qpdf is
        not available.
    """

    qpdf_executable = shutil.which("qpdf")
    if not qpdf_executable:
        LOGGER.info("qpdf not available - skipping optimisation")
        return False

    src_path = coerce_path(source)
    dst_path = coerce_path(destination)

    command = [
        qpdf_executable,
        "--linearize",
        str(src_path),
        str(dst_path),
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - depends on env
        LOGGER.warning("qpdf optimisation failed: %s", exc)
        return False

    return True
