"""High level helpers that expose layout analysis routines."""

from __future__ import annotations

from typing import Any, Iterable

from .converter.layout import collect_page_placements


class LayoutAnalyzer:
    """Utility that reuses the legacy layout analysis pipeline."""

    def analyse(self, document: Any) -> Iterable[Any]:
        return collect_page_placements(document)
