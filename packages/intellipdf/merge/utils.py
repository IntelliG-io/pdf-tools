"""Utility helpers for :mod:`intellipdf.merge`."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

PathLike = Union[str, Path]


def ensure_path(path: PathLike) -> Path:
    """Return a :class:`~pathlib.Path` instance for *path*."""

    resolved = Path(path).expanduser()
    try:
        return resolved.resolve(strict=False)
    except FileNotFoundError:  # pragma: no cover - defensive
        return resolved


def ensure_iterable(paths: Iterable[PathLike]) -> list[Path]:
    """Validate and convert an iterable of paths to :class:`Path` objects."""

    return [ensure_path(path) for path in paths]


__all__ = ["PathLike", "ensure_path", "ensure_iterable"]
