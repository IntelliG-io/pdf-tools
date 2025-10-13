"""Translate the IntelliPDF intermediate representation into DOCX packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from ...tools.converter.pdf_to_docx.docx.types import DocumentStatistics
from ...tools.converter.pdf_to_docx.docx.writer import write_docx
from ...tools.converter.pdf_to_docx.layout_analyzer import IntermediateRepresentation

__all__ = [
    "DocxGenerationStats",
    "DocxGenerationResult",
    "DocxGenerator",
    "generate_docx",
]


@dataclass(slots=True)
class DocxGenerationStats:
    """Aggregated statistics describing the generated DOCX package."""

    pages: int
    paragraphs: int
    words: int
    lines: int
    characters: int
    characters_with_spaces: int

    @classmethod
    def from_document_statistics(cls, stats: DocumentStatistics) -> "DocxGenerationStats":
        return cls(
            pages=stats.pages,
            paragraphs=stats.paragraphs,
            words=stats.words,
            lines=stats.lines,
            characters=stats.characters,
            characters_with_spaces=stats.characters_with_spaces,
        )


@dataclass(slots=True)
class DocxGenerationResult:
    """Outcome returned by :class:`DocxGenerator`."""

    output_path: Path
    stats: DocxGenerationStats
    metadata: dict[str, str]


class DocxGenerator:
    """Materialise a DOCX package from an :class:`IntermediateRepresentation`."""

    def __init__(
        self,
        *,
        writer: Callable[[IntermediateRepresentation, Path], DocumentStatistics] | None = None,
    ) -> None:
        self._writer = writer or self._default_writer

    @staticmethod
    def _default_writer(ir: IntermediateRepresentation, destination: Path) -> DocumentStatistics:
        destination.parent.mkdir(parents=True, exist_ok=True)
        return write_docx(ir.document, destination)

    def generate(
        self,
        ir: IntermediateRepresentation,
        destination: str | Path,
    ) -> DocxGenerationResult:
        """Persist *ir* as a DOCX package written to *destination*."""

        output_path = Path(destination).resolve()
        if output_path.suffix.lower() != ".docx":
            output_path = output_path.with_suffix(".docx")

        stats = self._writer(ir, output_path)
        metadata_map: dict[str, str] = {}
        for key, value in asdict(ir.metadata).items():
            if value is None:
                continue
            if isinstance(value, list):
                if not value:
                    continue
                metadata_map[key] = ", ".join(str(item) for item in value)
            else:
                metadata_map[key] = str(value)
        return DocxGenerationResult(
            output_path=output_path,
            stats=DocxGenerationStats.from_document_statistics(stats),
            metadata=metadata_map,
        )


def generate_docx(
    ir: IntermediateRepresentation,
    destination: str | Path,
    *,
    generator: DocxGenerator | None = None,
) -> DocxGenerationResult:
    """Convenience helper creating a DOCX package from *ir* at *destination*."""

    engine = generator or DocxGenerator()
    return engine.generate(ir, destination)
