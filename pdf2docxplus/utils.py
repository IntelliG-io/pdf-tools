"""Utility helpers for pdf2docxplus."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterator, Union

PathLike = Union[str, os.PathLike[str]]


def configure_logging() -> None:
    """Configure package-wide logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def to_path(path: PathLike) -> Path:
    """Normalize an input path to :class:`Path`."""
    return Path(path).expanduser().resolve()


def ensure_output_directory(path: Path) -> None:
    """Ensure the parent directory of ``path`` exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def time_block(logger: logging.Logger, message: str) -> Iterator[None]:
    """Context manager that logs the execution time of a code block."""
    start = datetime.now(tz=timezone.utc)
    logger.debug("Starting %s", message)
    try:
        yield
    finally:
        end = datetime.now(tz=timezone.utc)
        elapsed = (end - start).total_seconds()
        logger.info("%s completed in %.2fs", message, elapsed)


def parse_pdf_date(raw: str | None) -> datetime | None:
    """Parse a PDF date string into a timezone-aware :class:`datetime`."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("D:"):
        text = text[2:]
    try:
        base = datetime.strptime(text[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None
    tz_sign = text[14:15]
    if tz_sign in {"+", "-"}:
        try:
            hours = int(text[15:17])
            minutes = int(text[18:20]) if len(text) >= 20 else 0
        except ValueError:
            hours = minutes = 0
        delta = timedelta(hours=hours, minutes=minutes)
        if tz_sign == "-":
            delta = -delta
        tz = timezone(delta)
    else:
        tz = timezone.utc
    return base.replace(tzinfo=tz)
