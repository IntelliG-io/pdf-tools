"""Utility helpers for :mod:`pdfcompressx`."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

_LOGGER = logging.getLogger("pdfcompressx")


def resolve_path(path: os.PathLike[str] | str) -> Path:
    """Resolve *path* into an absolute :class:`~pathlib.Path`."""

    resolved = Path(path).expanduser().resolve()
    _LOGGER.debug("Resolved path '%s' to '%s'", path, resolved)
    return resolved


def ensure_parent_dir(path: Path) -> None:
    """Create parent directory for *path* if it does not exist."""

    path.parent.mkdir(parents=True, exist_ok=True)


def which(executables: Sequence[str]) -> str | None:
    """Return the first executable from *executables* found on ``PATH``."""

    for candidate in executables:
        found = shutil.which(candidate)
        if found:
            _LOGGER.debug("Detected external tool: %s -> %s", candidate, found)
            return found
    return None


def run_subprocess(
    command: Sequence[str],
    *,
    env: MutableMapping[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run *command* capturing output.

    Parameters
    ----------
    command:
        Command and arguments to execute.
    env:
        Optional environment overrides.
    check:
        Whether to raise :class:`subprocess.CalledProcessError` on non-zero exit.
    """

    _LOGGER.debug("Executing command: %s", " ".join(command))
    completed = subprocess.run(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        text=True,
    )
    _LOGGER.debug(
        "Command finished with exit code %s\nstdout: %s\nstderr: %s",
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )
    return completed


def sizeof_fmt(num_bytes: int) -> str:
    """Format *num_bytes* into a human-friendly string."""

    step_unit = 1024.0
    for unit in ("bytes", "KiB", "MiB", "GiB"):
        if abs(num_bytes) < step_unit:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= step_unit
    return f"{num_bytes:.1f} TiB"


def merge_dicts(*dicts: Mapping[str, str]) -> dict[str, str]:
    """Merge mapping objects respecting right-most precedence."""

    merged: dict[str, str] = {}
    for mapping in dicts:
        merged.update(mapping)
    return merged
