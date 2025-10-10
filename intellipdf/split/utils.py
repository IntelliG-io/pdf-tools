"""Utility helpers for the :mod:`intellipdf.split` package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence

from .exceptions import InvalidPageRangeError


@dataclass(frozen=True)
class PageRange:
    """Represents an inclusive page range."""

    start: int
    end: int

    def __post_init__(self) -> None:  # pragma: no cover - dataclass validation
        if self.start < 1 or self.end < 1:
            raise ValueError("Page numbers must be positive integers")
        if self.start > self.end:
            raise ValueError("Page range start must be less than or equal to end")

    def label(self) -> str:
        """Return a human-readable label for the range."""

        if self.start == self.end:
            return f"page_{self.start}"
        return f"pages_{self.start}-{self.end}"


def coerce_path(path: str | Path) -> Path:
    """Return a :class:`~pathlib.Path` object for ``path``."""

    return Path(path).expanduser().resolve()


def _range_tokens_from_iterable(ranges: Iterable[object]) -> Iterator[str]:
    for item in ranges:
        if isinstance(item, str):
            yield from (token.strip() for token in item.split(",") if token.strip())
        elif isinstance(item, Sequence) and len(item) == 2:
            yield f"{item[0]}-{item[1]}"
        elif isinstance(item, (int,)):
            yield str(item)
        else:
            raise InvalidPageRangeError(ranges)


def parse_page_ranges(
    ranges: str | Sequence[object] | None,
    *,
    total_pages: int,
) -> List[PageRange]:
    """Parse ``ranges`` into a list of :class:`PageRange` instances.

    Args:
        ranges: Page range specification expressed as a comma-separated string,
            a sequence of strings, integers or pairs, or ``None``.
        total_pages: Total number of pages in the source PDF, used to validate
            the resulting ranges.

    Raises:
        InvalidPageRangeError: If the ranges cannot be parsed or validate.

    Returns:
        A list of :class:`PageRange` objects sorted in the order they were
        supplied.
    """

    if ranges is None:
        raise InvalidPageRangeError([ranges])

    if isinstance(ranges, str):
        tokens = [token.strip() for token in ranges.split(",") if token.strip()]
    elif isinstance(ranges, Sequence):
        tokens = list(_range_tokens_from_iterable(ranges))
    else:
        raise InvalidPageRangeError([ranges])

    parsed: List[PageRange] = []
    for token in tokens:
        if "-" in token:
            start_str, end_str = token.split("-", 1)
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError as exc:  # pragma: no cover - defensive programming
                raise InvalidPageRangeError(ranges) from exc
        else:
            try:
                start = end = int(token)
            except ValueError as exc:
                raise InvalidPageRangeError(ranges) from exc

        if start < 1 or end < 1 or end > total_pages:
            raise InvalidPageRangeError([token])
        if start > end:
            raise InvalidPageRangeError([token])
        parsed.append(PageRange(start, end))

    if not parsed:
        raise InvalidPageRangeError(ranges)

    return parsed


def normalize_pages(pages: Iterable[int | str], *, total_pages: int) -> List[int]:
    """Normalise ``pages`` into a sorted list of unique page numbers."""

    normalised: List[int] = []
    for page in pages:
        if isinstance(page, str):
            if not page.strip():
                continue
            try:
                number = int(page)
            except ValueError as exc:  # pragma: no cover - defensive programming
                raise InvalidPageRangeError([page]) from exc
        else:
            number = int(page)
        if number < 1 or number > total_pages:
            raise InvalidPageRangeError([number])
        if number not in normalised:
            normalised.append(number)

    if not normalised:
        raise InvalidPageRangeError(pages)

    normalised.sort()
    return normalised


def build_output_filename(base_name: str, part: PageRange | int) -> str:
    """Construct a filename component for a split PDF output."""

    safe_base = base_name.replace(" ", "_")
    if isinstance(part, PageRange):
        suffix = part.label()
    else:
        suffix = f"page_{part}"
    return f"{safe_base}_{suffix}.pdf"
