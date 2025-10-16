"""Unified conversion pipeline orchestrating parser, interpreter, layout, and DOCX export."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Literal, Sequence
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
        pdf_version = self._validate_io(source_path, destination)
        LOGGER.debug(
            "Validated input PDF %s (version=%s) and output destination %s",
            source_path,
            pdf_version,
            destination,
        )

        resources: dict[str, Any] = context.resources if context is not None else {}
        logger = self._initialise_environment(source_path, resources, context)
        LOGGER.info("Starting PDF → DOCX conversion for %s", source_path)
        timings = _StageTimings()

        resources["pdf_version"] = pdf_version
        self._advance_logger(
            logger,
            f"Detected PDF header version {pdf_version}.",
        )

        # -- Stage 1: Parse -------------------------------------------------
        parser = self._parser_factory(source_path)
        self._open_pdf_document(parser, logger, resources, context)
        startxref, xref_kind = self._locate_cross_reference(parser, logger, resources)
        trailer_info = self._read_trailer(parser, logger, resources)
        self._load_document_catalog(parser, logger, resources, trailer_info)
        parse_start = perf_counter()
        parsed = parser.parse()
        timings.parse_ms = (perf_counter() - parse_start) * 1000.0
        page_numbers = self._resolve_page_numbers(parsed.page_count, self.options.page_numbers)
        self._advance_logger(
            logger,
            f"Parsed '{source_path.name}' ({parsed.page_count} pages) in {timings.parse_ms:.1f} ms.",
        )
        resources["parsed_document"] = parsed
        resources.setdefault("pdf_startxref", startxref)
        resources.setdefault("pdf_cross_reference_kind", xref_kind)

        self._iterate_page_dictionaries(
            parsed,
            page_numbers,
            logger=logger,
            resources=resources,
        )
        self._collect_page_content_streams(
            parsed,
            page_numbers,
            logger=logger,
            resources=resources,
        )

        # -- Stage 2: Interpret content streams -----------------------------
        page_buffers = self._prepare_page_content_buffers(page_numbers, resources)
        if page_buffers:
            detail = f"Prepared page content buffers for {len(page_buffers)} page(s)."
        else:
            detail = "No pages selected; prepared empty page content buffers."
        self._advance_logger(logger, detail)
        interpret_start = perf_counter()
        interpreter = self._interpreter_factory(parsed)
        page_contents = self._interpret_pages(
            interpreter,
            page_numbers,
            resources=resources,
            buffers=page_buffers,
        )
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
        *,
        resources: dict[str, Any] | None = None,
        buffers: Sequence[dict[str, Any]] | None = None,
    ) -> list[PageContent]:
        contents: list[PageContent] = []
        buffer_lookup: dict[int, dict[str, Any]] | None = None
        if buffers is not None:
            buffer_lookup = {}
            for buffer in buffers:
                page_number = buffer.get("page_number") if isinstance(buffer, dict) else None
                if isinstance(page_number, int):
                    buffer_lookup[page_number] = buffer
        for position, index in enumerate(page_numbers):
            content = interpreter.interpret_page(index)
            contents.append(content)
            if buffers is None:
                continue
            target_buffer = None
            if buffer_lookup is not None:
                target_buffer = buffer_lookup.get(index)
            if target_buffer is None and position < len(buffers):
                target_buffer = buffers[position]
                if buffer_lookup is not None:
                    buffer_lookup[index] = target_buffer
            if not isinstance(target_buffer, dict):
                continue
            target_buffer["page_number"] = content.page_number
            target_buffer["ordinal"] = position
            target_buffer["glyphs"] = list(content.glyphs)
            target_buffer["images"] = list(content.images)
            target_buffer["lines"] = list(content.lines)
            target_buffer["paths"] = list(content.paths)
            target_buffer["resources"] = content.resources
            existing_dimensions = {}
            if isinstance(target_buffer.get("dimensions"), dict):
                existing_dimensions = dict(target_buffer["dimensions"])
            existing_dimensions.update({
                "width": content.width,
                "height": content.height,
            })
            target_buffer["dimensions"] = existing_dimensions
            target_buffer["glyph_count"] = len(content.glyphs)
            target_buffer["image_count"] = len(content.images)
            target_buffer["line_count"] = len(content.lines)
            target_buffer["path_count"] = len(content.paths)
        if resources is not None and buffers is not None:
            resources["page_content_summary"] = [
                {
                    "page_number": buffer.get("page_number"),
                    "glyphs": buffer.get("glyph_count", len(buffer.get("glyphs", ()))),
                    "images": buffer.get("image_count", len(buffer.get("images", ()))),
                    "lines": buffer.get("line_count", len(buffer.get("lines", ()))),
                    "paths": buffer.get("path_count", len(buffer.get("paths", ()))),
                }
                for buffer in buffers
                if isinstance(buffer, dict)
            ]
        return contents

    def _prepare_page_content_buffers(
        self,
        page_numbers: Sequence[int],
        resources: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Initialise storage containers for page content extraction."""

        plan = list(page_numbers)
        raw_dimensions = resources.get("page_dimensions")
        dimensions_map: dict[int, dict[str, Any]] = {}
        if isinstance(raw_dimensions, dict):
            for key, value in raw_dimensions.items():
                if isinstance(key, int) and isinstance(value, dict):
                    dimensions_map[key] = dict(value)

        stream_summaries_lookup: dict[int, dict[str, Any]] = {}
        stream_summaries = resources.get("page_content_stream_summaries")
        if isinstance(stream_summaries, list):
            for entry in stream_summaries:
                if not isinstance(entry, dict):
                    continue
                page_number = entry.get("page_number")
                if isinstance(page_number, int):
                    stream_summaries_lookup[page_number] = dict(entry)

        buffers: list[dict[str, Any]] = []
        for index, page_number in enumerate(plan):
            summary = stream_summaries_lookup.get(page_number, {})
            raw_lengths = summary.get("stream_lengths")
            stream_lengths: list[int] = []
            if isinstance(raw_lengths, list):
                for length in raw_lengths:
                    if isinstance(length, (int, float)):
                        stream_lengths.append(int(length))
            stream_count_raw = summary.get("stream_count")
            stream_count = int(stream_count_raw) if isinstance(stream_count_raw, (int, float)) else len(stream_lengths)
            content_length_raw = summary.get("bytes")
            content_length = (
                int(content_length_raw)
                if isinstance(content_length_raw, (int, float))
                else 0
            )
            has_content = bool(summary.get("has_content", bool(stream_lengths) or content_length > 0))

            buffer: dict[str, Any] = {
                "page_number": page_number,
                "ordinal": index,
                "glyphs": [],
                "images": [],
                "lines": [],
                "paths": [],
                "resources": None,
                "dimensions": (
                    dict(dimensions_map.get(page_number, {}))
                    if page_number in dimensions_map
                    else None
                ),
                "glyph_count": 0,
                "image_count": 0,
                "line_count": 0,
                "path_count": 0,
                "content_stream_count": stream_count,
                "content_stream_lengths": stream_lengths,
                "content_length": content_length,
                "has_content": has_content,
            }
            buffers.append(buffer)
        resources["page_content_plan"] = plan
        resources["page_content_buffers"] = buffers
        return buffers

    def _iterate_page_dictionaries(
        self,
        parsed: ParsedDocument,
        page_numbers: Sequence[int],
        *,
        logger: PipelineLogger,
        resources: dict[str, Any],
    ) -> list[Any]:
        """Enumerate each selected page dictionary before interpretation."""

        plan = list(page_numbers)
        resources["page_iteration_plan"] = plan

        pages = parsed.pages
        reader = parsed.resolver.reader
        details: list[dict[str, Any]] = []
        dictionaries: list[Any] = []
        descriptors: list[str] = []
        geometry_summaries: list[dict[str, Any]] = []
        dimension_lookup: dict[int, dict[str, Any]] = {}
        resource_lookup: dict[int, dict[str, Any]] = {}
        resource_summaries: list[dict[str, Any]] = []

        def _summarise_named_resources(values: Any) -> list[dict[str, Any]]:
            entries: list[dict[str, Any]] = []
            if not isinstance(values, dict):
                return entries
            for raw_name, candidate in values.items():
                name = str(raw_name)
                entry: dict[str, Any] = {"name": name}
                if isinstance(candidate, dict):
                    ref = candidate.get("$ref")
                    if isinstance(ref, (list, tuple)) and len(ref) == 2:
                        try:
                            entry["ref"] = (int(ref[0]), int(ref[1]))
                        except Exception:
                            entry["ref"] = tuple(ref)  # pragma: no cover - defensive fallback
                    subtype = candidate.get("/Subtype")
                    if isinstance(subtype, str):
                        entry["subtype"] = subtype
                    base_font = candidate.get("/BaseFont")
                    if isinstance(base_font, str):
                        entry["base_font"] = base_font
                    length = candidate.get("__stream_length__")
                    if isinstance(length, (int, float)):
                        entry["length"] = float(length)
                entries.append(entry)
            return entries

        for ordinal, index in enumerate(plan):
            if index < 0 or index >= len(pages):
                raise ValueError(
                    f"Page index {index} out of bounds for document with {len(pages)} pages",
                )

            parsed_page = pages[index]

            try:
                page_dict = reader.pages[parsed_page.number]  # type: ignore[index]
            except Exception as exc:  # pragma: no cover - delegated to parser/lib
                message = f"Unable to load page {parsed_page.number + 1} dictionary: {exc}"
                raise RuntimeError(message) from exc

            dictionaries.append(page_dict)

            media_left, media_bottom, media_right, media_top = parsed_page.geometry.media_box
            unit = parsed_page.geometry.user_unit or 1.0
            media_width = float((media_right - media_left) * unit)
            media_height = float((media_top - media_bottom) * unit)
            crop_box = parsed_page.geometry.crop_box
            if crop_box is not None:
                crop_left, crop_bottom, crop_right, crop_top = crop_box
                crop_width = float((crop_right - crop_left) * unit)
                crop_height = float((crop_top - crop_bottom) * unit)
            else:
                crop_width = crop_height = None
            width = crop_width if crop_width is not None else media_width
            height = crop_height if crop_height is not None else media_height
            rotation_raw = parsed_page.geometry.rotate
            rotation = int(rotation_raw) if rotation_raw is not None else 0
            ref = parsed_page.object_ref

            dictionary_type: str | None = None
            if hasattr(page_dict, "get"):
                try:
                    raw_type = page_dict.get("/Type")
                except Exception:
                    raw_type = None
                if raw_type is not None:
                    dictionary_type = str(raw_type)

            descriptor = f"p{parsed_page.number + 1}"
            if rotation:
                descriptor += f"@{rotation}°"
            if isinstance(ref, tuple):
                descriptor += f"[{ref[0]} {ref[1]}]"
            descriptors.append(descriptor)

            page_resources = (
                parsed_page.resources if isinstance(parsed_page.resources, dict) else {}
            )
            resource_lookup[parsed_page.number] = page_resources
            fonts_summary = _summarise_named_resources(page_resources.get("/Font"))
            xobject_summary = _summarise_named_resources(page_resources.get("/XObject"))
            extgstate_summary = _summarise_named_resources(page_resources.get("/ExtGState"))
            properties_summary = _summarise_named_resources(page_resources.get("/Properties"))
            color_space_summary = _summarise_named_resources(page_resources.get("/ColorSpace"))

            entry: dict[str, Any] = {
                "page_number": parsed_page.number,
                "ordinal": ordinal,
                "object_ref": ref,
                "rotation": rotation,
                "width": width,
                "height": height,
                "user_unit": float(unit),
                "dictionary_type": dictionary_type,
                "media_box": (
                    float(media_left),
                    float(media_bottom),
                    float(media_right),
                    float(media_top),
                ),
                "media_width": media_width,
                "media_height": media_height,
            }
            if crop_box is not None:
                entry["crop_box"] = tuple(float(value) for value in crop_box)
                entry["crop_width"] = crop_width
                entry["crop_height"] = crop_height
            details.append(entry)

            geometry_summary: dict[str, Any] = {
                "page_number": parsed_page.number,
                "ordinal": ordinal,
                "width": width,
                "height": height,
                "rotation": rotation,
                "media_box": entry["media_box"],
                "media_width": media_width,
                "media_height": media_height,
                "user_unit": float(unit),
            }
            if crop_box is not None:
                geometry_summary["crop_box"] = entry["crop_box"]
                geometry_summary["crop_width"] = crop_width
                geometry_summary["crop_height"] = crop_height
            geometry_summaries.append(geometry_summary)
            resource_summary: dict[str, Any] = {
                "page_number": parsed_page.number,
                "ordinal": ordinal,
                "keys": sorted(page_resources.keys()),
                "font_count": len(fonts_summary),
                "fonts": fonts_summary,
                "xobject_count": len(xobject_summary),
                "xobjects": xobject_summary,
                "ext_gstate_count": len(extgstate_summary),
                "ext_gstate": extgstate_summary,
                "property_count": len(properties_summary),
                "properties": properties_summary,
                "color_space_count": len(color_space_summary),
                "color_spaces": color_space_summary,
            }
            resource_summaries.append(resource_summary)
            dimension_lookup[parsed_page.number] = {
                "width": width,
                "height": height,
                "rotation": rotation,
                "media_box": entry["media_box"],
                "user_unit": float(unit),
                "media_width": media_width,
                "media_height": media_height,
            }
            if crop_box is not None:
                dimension_lookup[parsed_page.number]["crop_box"] = entry["crop_box"]
                dimension_lookup[parsed_page.number]["crop_width"] = crop_width
                dimension_lookup[parsed_page.number]["crop_height"] = crop_height

        resources["page_iteration_details"] = details
        resources["page_dictionaries"] = dictionaries
        resources["page_dictionary_refs"] = [entry.get("object_ref") for entry in details]
        resources["page_geometry_summaries"] = geometry_summaries
        resources["page_dimensions"] = dimension_lookup
        resources["page_resources"] = resource_lookup
        resources["page_resource_summaries"] = resource_summaries

        if descriptors:
            geometry_descriptions: list[str] = []
            for summary in geometry_summaries[:3]:
                dims = f"{summary['width']:.1f}x{summary['height']:.1f}pt"
                if summary["rotation"]:
                    dims += f"@{summary['rotation']}°"
                geometry_descriptions.append(
                    f"p{summary['page_number'] + 1}={dims}"
                )
            if len(geometry_summaries) > 3:
                geometry_descriptions.append("…")
            geometry_clause = (
                f" captured geometry ({', '.join(geometry_descriptions)})"
                if geometry_descriptions
                else ""
            )
            resource_descriptions: list[str] = []
            for summary in resource_summaries[:3]:
                resource_descriptions.append(
                    "p"
                    f"{summary['page_number'] + 1}="
                    f"fonts:{summary['font_count']},xobj:{summary['xobject_count']}"
                )
            if len(resource_summaries) > 3:
                resource_descriptions.append("…")
            resource_clause = (
                f" resources ({', '.join(resource_descriptions)})"
                if resource_descriptions
                else ""
            )
            detail = (
                "Enumerated "
                f"{len(descriptors)} page dictionaries ({', '.join(descriptors)}) before interpretation;"
                f"{geometry_clause}{resource_clause}."
            )
            detail = detail.replace(";.", ".")
        else:
            detail = "No page dictionaries selected for iteration; skipping enumeration."

        self._advance_logger(logger, detail)
        return dictionaries

    def _collect_page_content_streams(
        self,
        parsed: ParsedDocument,
        page_numbers: Sequence[int],
        *,
        logger: PipelineLogger,
        resources: dict[str, Any],
    ) -> None:
        """Collect and summarise raw page content streams."""

        plan = list(page_numbers)
        pages = parsed.pages
        stream_lookup: dict[int, list[bytes]] = {}
        concatenated_lookup: dict[int, bytes] = {}
        summaries: list[dict[str, Any]] = []

        for ordinal, index in enumerate(plan):
            if index < 0 or index >= len(pages):
                raise ValueError(
                    f"Page index {index} out of bounds for document with {len(pages)} pages",
                )

            parsed_page = pages[index]
            raw_streams = []
            for stream in parsed_page.content_streams or ():
                if isinstance(stream, bytes):
                    raw_streams.append(stream)
                elif isinstance(stream, bytearray):
                    raw_streams.append(bytes(stream))
                elif isinstance(stream, str):
                    raw_streams.append(stream.encode("latin-1", "ignore"))
                elif stream is None:
                    continue
                else:
                    try:
                        raw_streams.append(bytes(stream))  # type: ignore[arg-type]
                    except Exception:
                        raw_streams.append(str(stream).encode("latin-1", "ignore"))

            concatenated = parsed_page.contents or b""
            if isinstance(concatenated, bytearray):
                concatenated = bytes(concatenated)
            elif isinstance(concatenated, str):
                concatenated = concatenated.encode("latin-1", "ignore")

            stream_lookup[parsed_page.number] = list(raw_streams)
            concatenated_lookup[parsed_page.number] = concatenated
            stream_lengths = [len(chunk) for chunk in raw_streams]
            summary: dict[str, Any] = {
                "page_number": parsed_page.number,
                "ordinal": ordinal,
                "stream_count": len(raw_streams),
                "stream_lengths": stream_lengths,
                "bytes": len(concatenated),
                "has_content": bool(raw_streams) or bool(concatenated),
            }
            summaries.append(summary)

        resources["page_content_streams"] = stream_lookup
        resources["page_content_bytes"] = concatenated_lookup
        resources["page_content_stream_summaries"] = summaries

        if summaries:
            preview: list[str] = []
            for summary in summaries[:3]:
                preview.append(
                    "p"
                    f"{summary['page_number'] + 1}="
                    f"streams:{summary['stream_count']},bytes:{summary['bytes']}"
                )
            if len(summaries) > 3:
                preview.append("…")
            detail = (
                "Decoded page content streams for "
                f"{len(summaries)} page(s) ({', '.join(preview)})."
            )
        else:
            detail = "No page content streams found for selected pages."

        self._advance_logger(logger, detail)

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
        if "password" in options_snapshot and options_snapshot["password"]:
            options_snapshot["password"] = "***"
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

    def _validate_io(self, source_path: Path, destination: Path) -> str:
        """Ensure the PDF source and DOCX destination satisfy IO expectations.

        Returns the declared PDF version from the file header when validation
        succeeds.
        """

        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Input document must be a PDF file with '.pdf' extension: {source_path}"
            )

        try:
            with source_path.open("rb") as stream:
                header_line = stream.readline(32)
        except OSError as exc:  # pragma: no cover - filesystem level failure
            raise RuntimeError(f"Unable to read input PDF '{source_path}': {exc}") from exc

        if not header_line.startswith(b"%PDF-"):
            raise ValueError(
                "Input document does not appear to be a valid PDF (missing '%PDF' header)."
            )

        header_text = header_line.decode("ascii", errors="ignore")
        version_match = re.match(r"%PDF-(\d+(?:\.\d+)?)", header_text)
        if version_match is None:
            raise ValueError("Unable to determine PDF version from document header.")
        pdf_version = version_match.group(1)

        target_dir = destination.parent
        if not target_dir.exists():
            raise FileNotFoundError(f"Output directory does not exist: {target_dir}")
        if not os.access(target_dir, os.W_OK):
            raise PermissionError(f"Output directory is not writable: {target_dir}")

        if destination.exists() and not os.access(destination, os.W_OK):
            raise PermissionError(f"Output file is not writable: {destination}")

        return pdf_version

    def _resolve_pdf_password(self, context: ConversionContext | None) -> str | None:
        if getattr(self.options, "password", None):
            return self.options.password
        if context is not None:
            config = getattr(context, "config", {})
            if isinstance(config, dict):
                for key in ("password", "pdf_password", "user_password"):
                    value = config.get(key)
                    if value:
                        return str(value)
        return None

    def _open_pdf_document(
        self,
        parser: PDFParser,
        logger: PipelineLogger,
        resources: dict[str, Any],
        context: ConversionContext | None,
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

        encrypted = bool(getattr(reader, "is_encrypted", False))
        resources["pdf_encrypted"] = encrypted
        password = None
        if encrypted:
            password = self._resolve_pdf_password(context)
            if not password:
                raise ValueError(
                    "Input PDF is encrypted and requires a password for conversion."
                )
            try:
                status = reader.decrypt(password)
            except Exception as exc:  # pragma: no cover - delegated to parser/lib
                message = f"Unable to decrypt encrypted PDF '{parser.source}': {exc}"
                raise RuntimeError(message) from exc
            if status == 0:
                raise ValueError(
                    "Provided password could not decrypt the encrypted PDF document."
                )
            resources["pdf_password_provided"] = True
        else:
            resources["pdf_password_provided"] = False

        page_hint = 0
        try:
            page_hint = len(getattr(reader, "pages", []) or [])
        except Exception:  # pragma: no cover - defensive for exotic readers
            page_hint = 0

        detail = "Opened input PDF in binary mode via parser backend."
        suffix_parts: list[str] = []
        if encrypted:
            suffix_parts.append("decrypted with supplied password")
        if page_hint:
            suffix_parts.append(f"page_hint={page_hint}")
        if suffix_parts:
            detail = (
                "Opened input PDF in binary mode via parser backend ("
                + ", ".join(suffix_parts)
                + ")."
            )
        self._advance_logger(logger, detail)

    def _locate_cross_reference(
        self,
        parser: PDFParser,
        logger: PipelineLogger,
        resources: dict[str, Any],
    ) -> tuple[int, Literal["table", "stream"]]:
        """Locate the PDF cross-reference and log the findings."""

        try:
            startxref, xref_kind = parser.locate_cross_reference()
        except Exception as exc:  # pragma: no cover - delegated to parser/lib
            message = f"Unable to locate cross-reference data in '{parser.source}': {exc}"
            raise RuntimeError(message) from exc

        resources["pdf_startxref"] = startxref
        resources["pdf_cross_reference_kind"] = xref_kind

        detail = (
            f"Located PDF cross-reference {xref_kind} at byte offset {startxref}."
        )
        self._advance_logger(logger, detail)
        return startxref, xref_kind

    def _read_trailer(
        self,
        parser: PDFParser,
        logger: PipelineLogger,
        resources: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse the PDF trailer dictionary and capture summary details."""

        try:
            trailer_info = parser.read_trailer()
        except Exception as exc:  # pragma: no cover - delegated to parser/lib
            message = f"Unable to parse PDF trailer dictionary for '{parser.source}': {exc}"
            raise RuntimeError(message) from exc

        entries = trailer_info.get("entries") or {}
        resources.setdefault("pdf_trailer", entries)
        resources.setdefault("pdf_trailer_info", trailer_info)

        entries_dereferenced = trailer_info.get("entries_dereferenced")
        if entries_dereferenced:
            resources.setdefault("pdf_trailer_dereferenced", entries_dereferenced)

        root_ref = trailer_info.get("root_ref")
        if root_ref is not None:
            resources.setdefault("pdf_catalog_ref", root_ref)

        size = trailer_info.get("size")
        if size is not None:
            resources.setdefault("pdf_object_count", size)

        hybrid = trailer_info.get("hybrid_xref_offset")
        sources = trailer_info.get("sources")

        detail_parts: list[str] = []
        if size is not None:
            detail_parts.append(f"size={size}")
        if root_ref is not None:
            detail_parts.append(f"root_ref={root_ref[0]} {root_ref[1]}")
        if hybrid is not None:
            detail_parts.append(f"hybrid_xref_offset={hybrid}")
        if sources:
            detail_parts.append("sources=" + ",".join(str(source) for source in sources))

        if detail_parts:
            detail = "Parsed PDF trailer dictionary (" + ", ".join(detail_parts) + ")."
        else:
            detail = "Parsed PDF trailer dictionary."

        self._advance_logger(logger, detail)
        return trailer_info

    def _load_document_catalog(
        self,
        parser: PDFParser,
        logger: PipelineLogger,
        resources: dict[str, Any],
        trailer_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retrieve the PDF document catalog and pages tree metadata."""

        try:
            catalog_info = parser.read_document_catalog()
        except Exception as exc:  # pragma: no cover - delegated to parser/lib
            message = f"Unable to load PDF document catalog for '{parser.source}': {exc}"
            raise RuntimeError(message) from exc

        catalog = catalog_info.get("catalog")
        if catalog is not None:
            resources.setdefault("pdf_catalog", catalog)

        catalog_ref = catalog_info.get("catalog_ref")
        if catalog_ref is not None:
            resources.setdefault("pdf_catalog_ref", catalog_ref)
        elif trailer_info is not None:
            root_ref = trailer_info.get("root_ref")
            if root_ref is not None:
                resources.setdefault("pdf_catalog_ref", root_ref)

        pages_ref = catalog_info.get("pages_ref")
        if pages_ref is not None:
            resources.setdefault("pdf_pages_ref", pages_ref)

        pages_summary: dict[str, Any] | None = None

        pages_tree = catalog_info.get("pages")
        if pages_tree is not None:
            resources.setdefault("pdf_pages_tree", pages_tree)

        summary_candidate = catalog_info.get("pages_tree_summary")
        if isinstance(summary_candidate, dict):
            pages_summary = summary_candidate
            resources.setdefault("pdf_pages_tree_summary", pages_summary)

        pages_count = catalog_info.get("pages_count")
        if pages_count is not None:
            resources.setdefault("pdf_pages_count", pages_count)

        leaf_count = catalog_info.get("pages_leaf_count")
        if leaf_count is not None:
            resources.setdefault("pdf_pages_leaf_count", leaf_count)

        leaves = catalog_info.get("pages_leaves")
        if isinstance(leaves, list) and leaves:
            resources.setdefault("pdf_pages_leaves", leaves)
            resources.setdefault(
                "pdf_page_refs",
                [entry.get("ref") for entry in leaves],
            )

        detail_parts: list[str] = []
        if pages_ref is not None:
            detail_parts.append(f"pages_ref={pages_ref[0]} {pages_ref[1]}")
        if isinstance(pages_count, int):
            detail_parts.append(f"pages_count={pages_count}")
        if catalog_ref is not None:
            detail_parts.append(f"catalog_ref={catalog_ref[0]} {catalog_ref[1]}")
        if isinstance(pages_summary, dict):
            kids_count = pages_summary.get("kids_count")
            if isinstance(kids_count, int):
                detail_parts.append(f"pages_kids={kids_count}")
        if isinstance(leaf_count, int):
            detail_parts.append(f"page_leaves={leaf_count}")

        if detail_parts:
            detail = "Loaded PDF document catalog (" + ", ".join(detail_parts) + ")."
        else:
            detail = "Loaded PDF document catalog."

        self._advance_logger(logger, detail)
        return catalog_info


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
