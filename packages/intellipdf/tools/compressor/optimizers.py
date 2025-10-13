"""External optimization backend integration for :mod:`intellipdf.tools.compressor`."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from .utils import run_subprocess, which

_LOGGER = logging.getLogger("intellipdf.compress")


class BackendType(str, Enum):
    """Enumeration of supported optimization backends."""

    QPDF = "qpdf"
    GHOSTSCRIPT = "ghostscript"


@dataclass(frozen=True)
class Backend:
    """Represents an optimization backend and its executable."""

    type: BackendType
    executable: str


_BACKEND_CANDIDATES: list[tuple[BackendType, Sequence[str]]] = [
    (BackendType.QPDF, ("qpdf",)),
    (BackendType.GHOSTSCRIPT, ("gs", "gswin64c", "gswin32c")),
]


def detect_backend(preferred: Iterable[BackendType] | None = None) -> Backend | None:
    """Detect the first available backend from *preferred* order."""

    order = list(preferred) if preferred else [candidate for candidate, _ in _BACKEND_CANDIDATES]
    for backend_type in order:
        for candidate_type, executables in _BACKEND_CANDIDATES:
            if backend_type is not candidate_type:
                continue
            executable = which(executables)
            if executable:
                return Backend(candidate_type, executable)
    return None


def build_qpdf_command(executable: str, source: Path, output: Path, level: str) -> list[str]:
    """Construct the qpdf command according to *level*."""

    stream_setting = {
        "low": "compress",
        "medium": "compress",
        "high": "compress",
    }[level]
    object_streams = "generate" if level != "low" else "preserve"
    return [
        executable,
        "--linearize",
        f"--stream-data={stream_setting}",
        f"--object-streams={object_streams}",
        "--recompress-flate",
        str(source),
        str(output),
    ]


def build_ghostscript_command(executable: str, source: Path, output: Path, level: str) -> list[str]:
    """Construct the Ghostscript command according to *level*."""

    pdf_settings = {
        "low": "/prepress",
        "medium": "/printer",
        "high": "/ebook",
    }[level]
    return [
        executable,
        "-sDEVICE=pdfwrite",
        "-dNOPAUSE",
        "-dBATCH",
        "-dSAFER",
        "-dCompatibilityLevel=1.5",
        f"-dPDFSETTINGS={pdf_settings}",
        f"-sOutputFile={output}",
        str(source),
    ]


def run_backend(backend: Backend, source: Path, output: Path, level: str) -> None:
    """Execute *backend* to optimise the document."""

    if backend.type is BackendType.QPDF:
        command = build_qpdf_command(backend.executable, source, output, level)
    elif backend.type is BackendType.GHOSTSCRIPT:
        command = build_ghostscript_command(backend.executable, source, output, level)
    else:
        raise ValueError(f"Unsupported backend: {backend.type}")

    _LOGGER.info("Running %s backend for compression", backend.type.value)
    run_subprocess(command)
