"""Shared PDF parsing helpers for IntelliPDF tools.

This module provides a thin abstraction around :class:`pypdf.PdfReader`
that exposes a normalized view of the PDF structure suited for the
converter pipeline.  The parser focuses on structural insights such as
page hierarchy, resource inheritance, and decoded content streams while
retaining access to the underlying reader for advanced consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
import xml.etree.ElementTree as ET

from pypdf import PdfReader
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    StreamObject,
    TextStringObject,
)

from .utils import resolve_path

__all__ = ["ParsedDocument", "ParsedPage", "PageGeometry", "ObjectResolver", "PDFParser"]


# -- Parsed object models ----------------------------------------------------


@dataclass(slots=True)
class PageGeometry:
    """Normalized geometry information for a page."""

    media_box: tuple[float, float, float, float]
    crop_box: tuple[float, float, float, float] | None
    rotate: int | None
    user_unit: float


@dataclass(slots=True)
class ParsedPage:
    """Concrete page extracted from the PDF page tree."""

    number: int
    object_ref: tuple[int, int] | None
    geometry: PageGeometry
    resources: dict[str, Any]
    contents: bytes
    content_streams: list[bytes] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ObjectResolver:
    """Lookup helper to resolve PDF indirect references on demand."""

    reader: PdfReader
    offsets: Mapping[tuple[int, int], int]

    def resolve(self, obj_ref: tuple[int, int]) -> Any | None:
        """Resolve an indirect reference using the underlying reader."""

        idnum, generation = obj_ref
        try:
            indirect = IndirectObject(idnum, generation, self.reader)
            return indirect.get_object()
        except Exception:
            return None

    def byte_offset(self, obj_ref: tuple[int, int]) -> int | None:
        """Return the byte offset for a given reference, if known."""

        return self.offsets.get(obj_ref)


@dataclass(slots=True)
class ParsedDocument:
    """Full PDF representation produced by :class:`PDFParser`."""

    path: Path
    version: str
    pages: Sequence[ParsedPage]
    metadata: dict[str, str]
    info: dict[str, str]
    trailer: dict[str, Any]
    root: dict[str, Any]
    startxref: int
    object_offsets: dict[tuple[int, int], int]
    resolver: ObjectResolver

    @property
    def page_count(self) -> int:
        return len(self.pages)


# -- Utility helpers ---------------------------------------------------------


_WHITESPACE = b"\x00\t\n\r\f "


def _as_bytes(obj: object) -> bytes:
    if isinstance(obj, bytes):
        return obj
    if isinstance(obj, bytearray):
        return bytes(obj)
    return str(obj).encode("latin-1", "ignore")


def _skip_ws(buffer: bytes, index: int) -> int:
    while index < len(buffer) and buffer[index] in _WHITESPACE:
        index += 1
    return index


def _read_int(buffer: bytes, index: int) -> tuple[int, int]:
    index = _skip_ws(buffer, index)
    start = index
    while index < len(buffer) and buffer[index] in b"+-0123456789":
        index += 1
    if start == index:
        raise ValueError("Expected integer in xref table")
    return int(buffer[start:index]), index


def _search_object_offset(data: bytes, obj_ref: tuple[int, int]) -> int | None:
    """Best-effort search to locate an object declaration in the raw file."""

    idnum, generation = obj_ref
    # Ensure matches align with line boundaries to reduce false positives.
    # Formats can be ``<obj> <gen> obj`` or preceded by whitespace/newlines.
    pattern = f"{idnum} {generation} obj".encode("ascii")
    match = re.search(rb"(?m)(?:^|\s)" + re.escape(pattern), data)
    if not match:
        return None
    # Remove leading whitespace from the match to pinpoint the header start.
    matched = match.group(0)
    offset = match.start(0)
    if matched.startswith(pattern):
        return offset
    # If the first byte is whitespace, advance until the digit.
    while offset < len(data) and data[offset] in _WHITESPACE:
        offset += 1
    return offset


def _merge_dicts(*candidates: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for candidate in candidates:
        for key, value in candidate.items():
            if value is None:
                continue
            merged[key] = value
    return merged


# -- Core parser implementation ----------------------------------------------


class PDFParser:
    """Structured PDF parsing facade tailored for IntelliPDF tools."""

    def __init__(self, source: str | Path, *, preload: bool = False) -> None:
        self.source = resolve_path(source)
        self._reader: PdfReader | None = None
        self._raw_bytes: bytes | None = None
        self._parsed: ParsedDocument | None = None
        if preload:
            self.load()

    # -- Cached accessors ----------------------------------------------------

    @property
    def reader(self) -> PdfReader:
        """Return a cached :class:`PdfReader` instance for ``source``."""

        return self.load()

    def load(self) -> PdfReader:
        if self._reader is None:
            self._reader = PdfReader(str(self.source))
        return self._reader

    def metadata(self) -> dict[str, str]:
        """Return merged document metadata (Info + XMP, if available)."""

        parsed = self.parse()
        return {key: str(value) for key, value in parsed.metadata.items()}

    def page_count(self) -> int:
        """Return the number of pages in the PDF."""

        return self.parse().page_count

    def iter_pages(self, *, indices: Iterable[int] | None = None):
        reader = self.reader
        if indices is None:
            yield from reader.pages
            return
        for index in indices:
            yield reader.pages[index]

    # -- Parsing entrypoints -------------------------------------------------

    def parse(self) -> ParsedDocument:
        """Parse the PDF file and return a :class:`ParsedDocument` model."""

        if self._parsed is not None:
            return self._parsed

        raw_bytes = self._load_bytes()
        version = self._detect_version(raw_bytes)
        startxref = self._locate_startxref(raw_bytes)

        reader = self.reader

        object_offsets = self._build_object_offsets(reader, raw_bytes, startxref)
        resolver = ObjectResolver(reader=reader, offsets=object_offsets)

        info_dict = self._extract_info(reader)
        xmp_dict = self._extract_xmp_metadata(reader)
        metadata_raw = _merge_dicts(info_dict, xmp_dict)
        metadata = {key: str(value) for key, value in metadata_raw.items()}

        trailer = self._to_python(reader.trailer, dereference=True)
        root_obj = reader.trailer.get(NameObject("/Root"))
        root = self._to_python(root_obj, dereference=True)

        pages = self._build_pages(reader, raw_bytes, object_offsets)

        document = ParsedDocument(
            path=self.source,
            version=version,
            pages=pages,
            metadata=metadata,
            info=info_dict,
            trailer=trailer,
            root=root,
            startxref=startxref,
            object_offsets=object_offsets,
            resolver=resolver,
        )
        self._parsed = document
        return document

    # -- Internal helpers ----------------------------------------------------

    def _load_bytes(self) -> bytes:
        if self._raw_bytes is None:
            self._raw_bytes = self.source.read_bytes()
        return self._raw_bytes

    @staticmethod
    def _detect_version(data: bytes) -> str:
        if not data.startswith(b"%PDF-"):
            raise ValueError("Missing %PDF- header")
        header_line = data.splitlines()[0].decode("latin-1", "ignore")
        return header_line[5:].strip() or "1.0"

    @staticmethod
    def _locate_startxref(data: bytes) -> int:
        marker = b"startxref"
        index = data.rfind(marker)
        if index == -1:
            raise ValueError("Unable to locate startxref marker")
        remainder = data[index + len(marker) :]
        for line in remainder.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.isdigit():
                return int(stripped)
            # Some generators prefix with comments; ignore them.
            digit_match = re.match(rb"([0-9]+)", stripped)
            if digit_match:
                return int(digit_match.group(1))
        raise ValueError("startxref offset not found")

    def _build_object_offsets(
        self,
        reader: PdfReader,
        data: bytes,
        startxref: int,
    ) -> dict[tuple[int, int], int]:
        offsets = self._parse_xref_tables(data, startxref)
        if offsets:
            return offsets

        reader_offsets = self._offsets_from_reader(reader)
        if reader_offsets:
            return reader_offsets

        # Fallback: infer offsets from indirect references we encounter.
        inferred: dict[tuple[int, int], int] = {}
        trailer = reader.trailer
        size_obj = trailer.get(NameObject("/Size"))
        max_obj = 0
        if isinstance(size_obj, (int, float)):
            max_obj = int(size_obj)

        if max_obj:
            for obj_num in range(max_obj):
                candidate = (obj_num, 0)
                position = _search_object_offset(data, candidate)
                if position is not None:
                    inferred[candidate] = position

        # Capture offsets for objects referenced from the catalog/pages.
        def _record_from(obj: Any) -> None:
            if isinstance(obj, IndirectObject):
                ref = (obj.idnum, obj.generation)
                if ref not in inferred:
                    position = _search_object_offset(data, ref)
                    if position is not None:
                        inferred[ref] = position
                try:
                    deref = obj.get_object()
                except Exception:
                    return
                _record_from(deref)
                return
            if isinstance(obj, DictionaryObject):
                for value in obj.values():
                    _record_from(value)
                return
            if isinstance(obj, ArrayObject):
                for value in obj:
                    _record_from(value)

        try:
            root = reader.trailer.get(NameObject("/Root"))
            if root is not None:
                _record_from(root)
        except Exception:
            pass
        return inferred

    def _parse_xref_tables(self, data: bytes, startxref: int) -> dict[tuple[int, int], int]:
        if startxref < 0 or startxref >= len(data):
            return {}
        view = data[startxref:]
        if not view.startswith(b"xref"):
            # XRef stream or unsupported format; bail out.
            return {}

        offsets: dict[tuple[int, int], int] = {}
        index = startxref + len(b"xref")
        index = _skip_ws(data, index)
        length = len(data)
        while index < length:
            if data[index : index + 7] == b"trailer":
                break
            try:
                start_obj, index = _read_int(data, index)
                count, index = _read_int(data, index)
            except ValueError:
                break
            index = _skip_ws(data, index)
            for i in range(count):
                if index + 20 > length:
                    break
                record = data[index : index + 20]
                try:
                    offset = int(record[0:10])
                    generation = int(record[11:16])
                    in_use = record[17:18]
                except ValueError:
                    break
                if in_use == b"n":
                    offsets[(start_obj + i, generation)] = offset
                index += 20
                while index < length and data[index] in b"\r\n":
                    index += 1
            index = _skip_ws(data, index)
        return offsets

    def _offsets_from_reader(self, reader: PdfReader) -> dict[tuple[int, int], int]:
        """Reuse the internal pypdf cross reference tables when available."""

        offsets: dict[tuple[int, int], int] = {}

        xref = getattr(reader, "xref", None)
        if xref is None:
            return offsets

        candidate_tables: list[Mapping[Any, Any]] = []
        for attr_name in ("_xref_table", "xref_table"):
            table = getattr(xref, attr_name, None)
            if isinstance(table, Mapping):
                candidate_tables.append(table)

        def _record(obj_num: Any, generation: Any, entry: Any) -> None:
            try:
                obj_id = int(obj_num)
            except Exception:
                return
            try:
                gen_id = int(generation)
            except Exception:
                gen_id = 0

            target_offset: int | None = None
            # Entry can be a bare int, tuple, or a lightweight object.
            if isinstance(entry, (int, float)):
                target_offset = int(entry)
            elif isinstance(entry, (list, tuple)):
                for item in entry:
                    if isinstance(item, (int, float)):
                        target_offset = int(item)
                        break
                    candidate = getattr(item, "offset", None)
                    if isinstance(candidate, (int, float)):
                        target_offset = int(candidate)
                        break
            else:
                candidate = getattr(entry, "offset", None)
                if isinstance(candidate, (int, float)):
                    target_offset = int(candidate)
                else:
                    # Some versions expose ``byte_offset`` or ``get_offset`` accessors.
                    candidate = getattr(entry, "byte_offset", None)
                    if isinstance(candidate, (int, float)):
                        target_offset = int(candidate)
                    else:
                        getter = getattr(entry, "get_offset", None)
                        if callable(getter):
                            try:
                                value = getter()
                            except Exception:
                                value = None
                            if isinstance(value, (int, float)):
                                target_offset = int(value)

            if target_offset is None or target_offset < 0:
                return

            entry_type = getattr(entry, "type", None)
            if entry_type in {"f", 0, False}:
                # Skip free entries.
                return
            if getattr(entry, "is_free", False):
                return

            offsets[(obj_id, gen_id)] = target_offset

        for table in candidate_tables:
            for obj_num, generation_map in table.items():
                if isinstance(generation_map, Mapping):
                    for generation, entry in generation_map.items():
                        _record(obj_num, generation, entry)
                else:
                    _record(obj_num, 0, generation_map)
        return offsets

    def _extract_info(self, reader: PdfReader) -> dict[str, str]:
        info: dict[str, str] = {}
        try:
            raw_info = reader.trailer.get(NameObject("/Info"))
        except Exception:
            raw_info = None
        resolved = self._resolve(raw_info)
        if isinstance(resolved, DictionaryObject):
            for key, value in resolved.items():
                name = str(key)
                info[name] = str(self._coerce_simple(value))
        # Fallback to reader.metadata which normalizes keys (may overlap).
        try:
            metadata = reader.metadata or {}
            for key, value in metadata.items():
                if value is None:
                    continue
                info_key = str(key)
                info.setdefault(info_key, str(value))
        except Exception:
            pass
        return info

    def _extract_xmp_metadata(self, reader: PdfReader) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        try:
            root = reader.trailer.get(NameObject("/Root"))
            root_dict = self._resolve(root)
            if not isinstance(root_dict, DictionaryObject):
                return metadata
            metadata_obj = root_dict.get(NameObject("/Metadata"))
            metadata_stream = self._resolve(metadata_obj)
            if not isinstance(metadata_stream, StreamObject):
                return metadata
            xmp_bytes = metadata_stream.get_data()  # type: ignore[call-arg]
        except Exception:
            return metadata

        text = xmp_bytes.decode("utf-8", "ignore")
        metadata["xmp_raw"] = text
        try:
            xml_root = ET.fromstring(text)
        except Exception:
            return metadata

        def _iter_text(tag: str) -> list[str]:
            values: list[str] = []
            for element in xml_root.findall(f".//{{*}}{tag}"):
                content = "".join(element.itertext()).strip()
                if content:
                    values.append(content)
            return values

        title_values = _iter_text("title")
        if title_values:
            metadata.setdefault("/Title", title_values[0])
        creator_values = _iter_text("creator")
        if creator_values:
            metadata.setdefault("/Author", creator_values[0])
        producer_values = _iter_text("producer")
        if producer_values:
            metadata.setdefault("/Producer", producer_values[0])
        create_values = _iter_text("CreateDate")
        if create_values:
            metadata.setdefault("/CreationDate", create_values[0])
        modify_values = _iter_text("ModifyDate")
        if modify_values:
            metadata.setdefault("/ModDate", modify_values[0])
        return metadata

    # -- Page construction ---------------------------------------------------

    def _build_pages(
        self,
        reader: PdfReader,
        data: bytes,
        offsets: dict[tuple[int, int], int],
    ) -> list[ParsedPage]:
        pages: list[ParsedPage] = []
        for index, page in enumerate(reader.pages):
            page_dict = self._resolve(page)
            if not isinstance(page_dict, DictionaryObject):
                continue

            ref = getattr(page, "indirect_reference", None)
            object_ref: tuple[int, int] | None = None
            if isinstance(ref, IndirectObject):
                object_ref = (ref.idnum, ref.generation)
                if object_ref not in offsets:
                    position = _search_object_offset(data, object_ref)
                    if position is not None:
                        offsets[object_ref] = position

            geometry = self._build_geometry(page_dict)
            resources = self._resolve_resources(page_dict)
            content_streams, concatenated = self._decode_contents(page_dict)
            attributes = self._collect_page_attributes(page_dict)

            pages.append(
                ParsedPage(
                    number=index,
                    object_ref=object_ref,
                    geometry=geometry,
                    resources=resources,
                    contents=concatenated,
                    content_streams=content_streams,
                    attributes=attributes,
                )
            )
        return pages

    def _collect_page_attributes(self, page: DictionaryObject) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        keys = [
            "/Group",
            "/LastModified",
            "/Thumb",
            "/Dur",
            "/Trans",
            "/StructParents",
            "/Tabs",
        ]
        for key in keys:
            value = page.get(NameObject(key))
            if value is None:
                continue
            attrs[key] = self._to_python(value, dereference=False)
        return attrs

    def _build_geometry(self, page: DictionaryObject) -> PageGeometry:
        media_box = self._inherit_array(page, "/MediaBox")
        crop_box = self._inherit_array(page, "/CropBox")
        rotate = self._inherit_scalar(page, "/Rotate")
        user_unit = self._inherit_scalar(page, "/UserUnit") or 1.0

        def _normalize_box(values: Sequence[float] | None) -> tuple[float, float, float, float]:
            if not values or len(values) < 4:
                return (0.0, 0.0, 0.0, 0.0)
            left, bottom, right, top = (float(values[i]) for i in range(4))
            return (
                min(left, right),
                min(bottom, top),
                max(left, right),
                max(bottom, top),
            )

        media_tuple = _normalize_box(media_box)
        crop_tuple = _normalize_box(crop_box) if crop_box else None
        rotation = int(rotate) if rotate is not None else None
        return PageGeometry(
            media_box=media_tuple,
            crop_box=crop_tuple,
            rotate=rotation,
            user_unit=float(user_unit),
        )

    def _inherit_scalar(self, page: DictionaryObject, key: str) -> float | int | None:
        visited: set[int] = set()
        current: DictionaryObject | None = page
        while current is not None:
            obj_id = id(current)
            if obj_id in visited:
                break
            visited.add(obj_id)
            candidate = current.get(NameObject(key))
            if candidate is not None:
                resolved = self._resolve(candidate)
                try:
                    return float(resolved) if resolved is not None else None
                except Exception:
                    return None
            parent = current.get(NameObject("/Parent"))
            parent_resolved = self._resolve(parent)
            current = parent_resolved if isinstance(parent_resolved, DictionaryObject) else None
        return None

    def _inherit_array(self, page: DictionaryObject, key: str) -> list[float] | None:
        visited: set[int] = set()
        current: DictionaryObject | None = page
        while current is not None:
            obj_id = id(current)
            if obj_id in visited:
                break
            visited.add(obj_id)
            candidate = current.get(NameObject(key))
            if candidate is not None:
                resolved = self._resolve(candidate)
                if isinstance(resolved, ArrayObject):
                    try:
                        return [float(item) for item in resolved]
                    except Exception:
                        return None
            parent = current.get(NameObject("/Parent"))
            parent_resolved = self._resolve(parent)
            current = parent_resolved if isinstance(parent_resolved, DictionaryObject) else None
        return None

    def _resolve_resources(self, page: DictionaryObject) -> dict[str, Any]:
        resources_obj = self._inherit_dictionary(page, "/Resources")
        if resources_obj is None:
            return {}
        return self._to_python(resources_obj, dereference=True)

    def _inherit_dictionary(self, page: DictionaryObject, key: str) -> DictionaryObject | None:
        visited: set[int] = set()
        current: DictionaryObject | None = page
        while current is not None:
            obj_id = id(current)
            if obj_id in visited:
                break
            visited.add(obj_id)
            candidate = current.get(NameObject(key))
            resolved = self._resolve(candidate)
            if isinstance(resolved, DictionaryObject):
                return resolved
            parent = current.get(NameObject("/Parent"))
            parent_resolved = self._resolve(parent)
            current = parent_resolved if isinstance(parent_resolved, DictionaryObject) else None
        return None

    def _decode_contents(self, page: DictionaryObject) -> tuple[list[bytes], bytes]:
        content_obj = page.get(NameObject("/Contents"))
        if content_obj is None:
            return [], b""
        resolved = self._resolve(content_obj)
        streams: list[StreamObject] = []
        if isinstance(resolved, StreamObject):
            streams.append(resolved)
        elif isinstance(resolved, ArrayObject):
            for item in resolved:
                candidate = self._resolve(item)
                if isinstance(candidate, StreamObject):
                    streams.append(candidate)
        content_streams: list[bytes] = []
        for stream in streams:
            try:
                data = stream.get_data()  # type: ignore[call-arg]
            except Exception:
                data = stream.get_rawdata() if hasattr(stream, "get_rawdata") else b""
            content_streams.append(data)
        concatenated = b"\n".join(content_streams)
        return content_streams, concatenated

    # -- Generic PDF object helpers -----------------------------------------

    def _resolve(self, obj: Any) -> Any:
        if isinstance(obj, IndirectObject):
            try:
                return obj.get_object()
            except Exception:
                return obj
        return obj

    def _coerce_simple(self, obj: Any) -> Any:
        obj = self._resolve(obj)
        if isinstance(obj, TextStringObject):
            return str(obj)
        if isinstance(obj, NameObject):
            return str(obj)
        if isinstance(obj, ArrayObject):
            return [self._coerce_simple(item) for item in obj]
        if isinstance(obj, DictionaryObject):
            return {str(key): self._coerce_simple(value) for key, value in obj.items()}
        if isinstance(obj, (bytes, bytearray)):
            return bytes(obj)
        return obj

    def _to_python(self, obj: Any, *, dereference: bool, _visited: set[int] | None = None) -> Any:
        if _visited is None:
            _visited = set()
        if isinstance(obj, IndirectObject):
            ref_id = (obj.idnum << 16) + obj.generation
            if ref_id in _visited:
                return {"$ref": (obj.idnum, obj.generation)}
            if not dereference:
                return {"$ref": (obj.idnum, obj.generation)}
            _visited.add(ref_id)
            try:
                resolved = obj.get_object()
            except Exception:
                return {"$ref": (obj.idnum, obj.generation)}
            return self._to_python(resolved, dereference=dereference, _visited=_visited)

        if isinstance(obj, DictionaryObject):
            python_dict: dict[str, Any] = {}
            for key, value in obj.items():
                name = str(key)
                python_dict[name] = self._to_python(value, dereference=dereference, _visited=_visited)
            return python_dict

        if isinstance(obj, ArrayObject):
            return [self._to_python(item, dereference=dereference, _visited=_visited) for item in obj]

        if isinstance(obj, StreamObject):
            entries = {
                str(key): self._to_python(value, dereference=dereference, _visited=_visited)
                for key, value in obj.items()
            }
            try:
                data = obj.get_data() if dereference else b""
            except Exception:
                data = b""
            entries["__stream_length__"] = len(data)
            if dereference and data:
                entries["__stream_data__"] = data
            return entries

        if isinstance(obj, TextStringObject):
            return str(obj)

        if isinstance(obj, NameObject):
            return str(obj)

        if isinstance(obj, (int, float, bool)):
            return obj

        if obj is None:
            return None

        return _as_bytes(obj)
