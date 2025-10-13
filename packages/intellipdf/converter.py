"""Unified conversion pipeline orchestrating parser, interpreter, layout, and DOCX export."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Sequence
from zipfile import ZipFile, BadZipFile

from .core.parser import PDFParser, ParsedDocument
from .exporters.docx.generator import DocxGenerator
from .tools.common.interfaces import ConversionContext
from .tools.converter.pdf_to_docx.converter.types import (
    ConversionMetadata,
    ConversionOptions,
    ConversionResult,
)
from .tools.converter.pdf_to_docx.converter.pipeline import PipelineLogger
from .tools.converter.pdf_to_docx.interpreter import PDFContentInterpreter, PageContent
from .tools.converter.pdf_to_docx.layout_analyzer import LayoutAnalyzer
from .tools.converter.pdf_to_docx.converter.metadata import merge_metadata as _merge_metadata

__all__ = ["ConversionPipeline", "convert_pdf_to_docx"]


LOGGER = logging.getLogger("intellipdf.converter")


@dataclass(slots=True)
class _StageTimings:
    parse_ms: float = 0.0
    interpret_ms: float = 0.0
    analyse_ms: float = 0.0
    export_ms: float = 0.0

    def per_page(self, pages: int) -> dict[str, float]:
        safe = max(1, pages)
        return {
            "parse_ms_per_page": self.parse_ms / safe,
            "interpret_ms_per_page": self.interpret_ms / safe,
            "analyse_ms_per_page": self.analyse_ms / safe,
            "export_ms_per_page": self.export_ms / safe,
        }


class ConversionPipeline:
    """Run the end-to-end PDF → DOCX conversion using discrete stages."""

    def __init__(
        self,
        *,
        options: ConversionOptions | None = None,
        metadata: ConversionMetadata | None = None,
        parser_factory: type[PDFParser] = PDFParser,
        interpreter_factory: type[PDFContentInterpreter] = PDFContentInterpreter,
        analyzer_factory: type[LayoutAnalyzer] = LayoutAnalyzer,
        docx_generator: DocxGenerator | None = None,
    ) -> None:
        self.options = options or ConversionOptions()
        self.metadata = metadata
        self._parser_factory = parser_factory
        self._interpreter_factory = interpreter_factory
        self._analyzer_factory = analyzer_factory
        self._generator = docx_generator or DocxGenerator()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run(
        self,
        input_document: str | Path,
        output_path: str | Path | None = None,
        *,
        context: ConversionContext | None = None,
    ) -> ConversionResult:
        """Convert *input_document* into DOCX stored at *output_path*."""

        source_path = Path(input_document)
        if not source_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {source_path}")
        destination = self._resolve_output_path(source_path, output_path)
        self._validate_io(source_path, destination)
        LOGGER.debug("Validated input PDF %s and output destination %s", source_path, destination)

        resources: dict[str, Any] = context.resources if context is not None else {}
        logger = self._initialise_environment(source_path, resources, context)
        LOGGER.info("Starting PDF → DOCX conversion for %s", source_path)
        timings = _StageTimings()

        # -- Stage 1: Parse -------------------------------------------------
        parser = self._parser_factory(source_path)
        self._open_pdf_document(parser, logger, resources)
        parse_start = perf_counter()
        parsed = parser.parse()
        timings.parse_ms = (perf_counter() - parse_start) * 1000.0
        page_numbers = self._resolve_page_numbers(parsed.page_count, self.options.page_numbers)
        self._advance_logger(
            logger,
            f"Parsed '{source_path.name}' ({parsed.page_count} pages) in {timings.parse_ms:.1f} ms.",
        )
        resources["parsed_document"] = parsed

        # -- Stage 2: Interpret content streams -----------------------------
        interpret_start = perf_counter()
        interpreter = self._interpreter_factory(parsed)
        page_contents = self._interpret_pages(interpreter, page_numbers)
        timings.interpret_ms = (perf_counter() - interpret_start) * 1000.0
        glyphs_total = sum(len(content.glyphs) for content in page_contents)
        images_total = sum(len(content.images) for content in page_contents)
        self._advance_logger(
            logger,
            f"Decoded {len(page_numbers)} selected pages -> glyphs={glyphs_total}, images={images_total} "
            f"in {timings.interpret_ms:.1f} ms.",
        )
        resources["page_contents"] = page_contents

        # -- Stage 3: Layout analysis --------------------------------------
        analyse_start = perf_counter()
        analyzer = self._analyzer_factory(self.options)
        ir = analyzer.analyse(parsed, contents=page_contents)
        if self.metadata is not None:
            ir.document.metadata = _merge_metadata(ir.document.metadata, self.metadata)
            self._advance_logger(
                logger,
                "Applied metadata overrides to IR document metadata.",
            )
        timings.analyse_ms = (perf_counter() - analyse_start) * 1000.0
        self._advance_logger(
            logger,
            f"Extracted layout into {ir.document.page_count} section(s) with "
            f"{sum(len(section.elements) for section in ir.document.sections)} elements "
            f"in {timings.analyse_ms:.1f} ms.",
        )
        resources["intermediate_representation"] = ir

        # -- Stage 4: Export DOCX ------------------------------------------
        export_start = perf_counter()
        generation_result = self._generator.generate(ir, destination)
        timings.export_ms = (perf_counter() - export_start) * 1000.0
        self._basic_validation(generation_result.output_path)
        self._advance_logger(
            logger,
            f"Generated DOCX '{generation_result.output_path.name}' "
            f"in {timings.export_ms:.1f} ms (paragraphs={generation_result.stats.paragraphs}, "
            f"words={generation_result.stats.words}).",
        )

        # -- Stage 5: Summary & metrics ------------------------------------
        total_duration = timings.parse_ms + timings.interpret_ms + timings.analyse_ms + timings.export_ms
        self._advance_logger(
            logger,
            f"Conversion complete in {total_duration:.1f} ms "
            f"(pages={len(page_numbers)}, tagged={ir.tagged_pdf}).",
        )

        while logger.remaining():
            self._advance_logger(logger)

        metrics = {
            "parse_ms": timings.parse_ms,
            "interpret_ms": timings.interpret_ms,
            "analyse_ms": timings.analyse_ms,
            "export_ms": timings.export_ms,
            "total_ms": total_duration,
            **timings.per_page(len(page_numbers)),
        }
        resources["conversion_metrics"] = metrics
        resources["docx_generation_metadata"] = generation_result.metadata
        log_records = tuple(logger.records)
        resources["conversion_log"] = log_records

        stats = generation_result.stats
        LOGGER.info(
            "Finished conversion for %s (pages=%d, paragraphs=%d, words=%d)",
            source_path,
            len(page_numbers),
            stats.paragraphs,
            stats.words,
        )
        return ConversionResult(
            output_path=generation_result.output_path.resolve(),
            page_count=len(page_numbers),
            paragraph_count=stats.paragraphs,
            word_count=stats.words,
            line_count=stats.lines,
            tagged_pdf=ir.tagged_pdf,
            log=log_records,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_output_path(source: Path, destination: str | Path | None) -> Path:
        if destination is None:
            return source.with_suffix(".docx")
        resolved = Path(destination)
        if resolved.suffix.lower() != ".docx":
            resolved = resolved.with_suffix(".docx")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    @staticmethod
    def _resolve_page_numbers(total_pages: int, requested: Sequence[int] | None) -> list[int]:
        if requested is None:
            return list(range(total_pages))
        page_numbers: list[int] = []
        for index in requested:
            if index < 0 or index >= total_pages:
                raise ValueError(f"Page index {index} out of bounds for document with {total_pages} pages")
            page_numbers.append(index)
        return page_numbers

    def _interpret_pages(
        self,
        interpreter: PDFContentInterpreter,
        page_numbers: Iterable[int],
    ) -> list[PageContent]:
        contents: list[PageContent] = []
        for index in page_numbers:
            contents.append(interpreter.interpret_page(index))
        return contents

    def _initialise_environment(
        self,
        source_path: Path,
        resources: dict[str, Any],
        context: ConversionContext | None,
    ) -> PipelineLogger:
        logger = PipelineLogger()
        configuration = self._build_default_configuration()
        existing_resources = resources.get("configuration")
        if isinstance(existing_resources, dict):
            existing_resources.update(configuration)
            configuration_map = existing_resources
        else:
            resources["configuration"] = configuration
            configuration_map = configuration
        resources["controller"] = self
        resources["pipeline_logger"] = logger
        if context is not None:
            existing_config = context.config.get("converter")
            if isinstance(existing_config, dict):
                existing_config.update(configuration)
            else:
                context.config["converter"] = configuration_map
        self._advance_logger(
            logger,
            f"Loaded input document '{source_path.name}' into converter controller.",
        )
        self._advance_logger(
            logger,
            "Converter configuration initialised "
            f"(default_styles={len(configuration['default_styles'])}, "
            f"font_mappings={len(configuration['font_mappings'])}).",
        )
        self._advance_logger(
            logger,
            "Prepared conversion workspace for pages, fonts, images, and metadata caches.",
        )
        return logger

    def _build_default_configuration(self) -> dict[str, Any]:
        options_snapshot = asdict(self.options)
        default_styles_attr = getattr(self._generator, "DEFAULT_STYLES", ())
        if isinstance(default_styles_attr, dict):
            default_styles: Any = dict(default_styles_attr)
        elif isinstance(default_styles_attr, (list, tuple, set)):
            default_styles = tuple(default_styles_attr)
        else:
            default_styles = default_styles_attr
        font_mappings_attr = getattr(self._analyzer_factory, "DEFAULT_FONT_MAPPINGS", {})
        font_mappings = dict(font_mappings_attr) if isinstance(font_mappings_attr, dict) else {}
        return {
            "options": options_snapshot,
            "default_styles": default_styles,
            "font_mappings": font_mappings,
        }

    def _advance_logger(self, logger: PipelineLogger, detail: str | None = None) -> None:
        logger.advance(detail)
        LOGGER.debug(logger.records[-1])

    @staticmethod
    def _basic_validation(output_path: Path) -> None:
        try:
            with ZipFile(output_path, "r") as archive:
                # Ensure mandatory parts exist.
                archive.getinfo("word/document.xml")
                archive.getinfo("[Content_Types].xml")
        except (BadZipFile, KeyError) as exc:
            raise RuntimeError(f"Generated DOCX appears invalid: {exc}") from exc

    def _validate_io(self, source_path: Path, destination: Path) -> None:
        """Ensure the PDF source and DOCX destination satisfy IO expectations."""

        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Input document must be a PDF file with '.pdf' extension: {source_path}"
            )

        try:
            with source_path.open("rb") as stream:
                header = stream.read(5)
        except OSError as exc:  # pragma: no cover - filesystem level failure
            raise RuntimeError(f"Unable to read input PDF '{source_path}': {exc}") from exc

        if not header.startswith(b"%PDF"):
            raise ValueError(
                "Input document does not appear to be a valid PDF (missing '%PDF' header)."
            )

        target_dir = destination.parent
        if not target_dir.exists():
            raise FileNotFoundError(f"Output directory does not exist: {target_dir}")
        if not os.access(target_dir, os.W_OK):
            raise PermissionError(f"Output directory is not writable: {target_dir}")

        if destination.exists() and not os.access(destination, os.W_OK):
            raise PermissionError(f"Output file is not writable: {destination}")

    def _open_pdf_document(
        self,
        parser: PDFParser,
        logger: PipelineLogger,
        resources: dict[str, Any],
    ) -> None:
        """Open the PDF resource in binary mode via the parser and record it."""

        try:
            reader = parser.load()
        except Exception as exc:  # pragma: no cover - delegated to parser/lib
            message = f"Unable to open input PDF '{parser.source}': {exc}"
            raise RuntimeError(message) from exc

        resources["pdf_reader"] = reader
        stream = getattr(reader, "stream", None)
        if stream is not None:
            resources["pdf_stream"] = stream

        page_hint = 0
        try:
            page_hint = len(getattr(reader, "pages", []) or [])
        except Exception:  # pragma: no cover - defensive for exotic readers
            page_hint = 0

        detail = "Opened input PDF in binary mode via parser backend."
        if page_hint:
            detail = (
                f"Opened input PDF in binary mode via parser backend "
                f"(page_hint={page_hint})."
            )
        self._advance_logger(logger, detail)


# ---------------------------------------------------------------------- #
# Public convenience function
# ---------------------------------------------------------------------- #


def convert_pdf_to_docx(
    input_document: str | Path,
    output_path: str | Path | None = None,
    *,
    options: ConversionOptions | None = None,
    metadata: ConversionMetadata | None = None,
    context: ConversionContext | None = None,
) -> ConversionResult:
    """High level helper that converts *input_document* into a DOCX package."""

    pipeline = ConversionPipeline(options=options, metadata=metadata)
    return pipeline.run(input_document, output_path, context=context)
