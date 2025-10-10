"""Utility helpers for the :mod:`intellipdf.merge` package."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

PathLike = Union[str, Path]


def ensure_path(path: PathLike) -> Path:
    """Return a :class:`~pathlib.Path` instance for *path*.

    This helper normalises any string-like path and expands user-home
    references. Relative paths are resolved relative to the current
    working directory to avoid surprises when running in subprocesses or
    CI environments.
    """

    resolved = Path(path).expanduser()
    try:
        return resolved.resolve(strict=False)
    except FileNotFoundError:
        # Should not happen with strict=False, but keep for completeness.
        return resolved


def ensure_iterable(paths: Iterable[PathLike]) -> list[Path]:
    """Validate and convert an iterable of paths to :class:`Path` objects."""

    return [ensure_path(path) for path in paths]


__all__ = ["PathLike", "ensure_path", "ensure_iterable"]
