"""Manages relationships and media for DOCX packaging."""

from __future__ import annotations

from hashlib import sha256
from typing import Iterator

from ..ir import Picture

__all__ = ["RelationshipManager", "resolve_image_type"]


class RelationshipManager:
    def __init__(self) -> None:
        self._next_id = 3  # rId1 reserved for styles, rId2 for numbering
        self._used_names: set[str] = set()
        self._media_by_hash: dict[str, tuple[str, str, bytes, str]] = {}
        self._parts: list[tuple[str, bytes, str | None]] = []
        self._relationships: list[tuple[str, str, str, str | None]] = []
        self._hyperlinks: dict[str, str] = {}

    def _allocate_id(self) -> str:
        rid = f"rId{self._next_id}"
        self._next_id += 1
        return rid

    def register_image(self, picture: Picture) -> tuple[str, str]:
        ext, mime = resolve_image_type(picture.mime_type)
        digest = sha256(picture.data).hexdigest()
        if digest in self._media_by_hash:
            rid, part_name, _, _ = self._media_by_hash[digest]
            return rid, part_name
        base_name = picture.name or "image"
        index = 1
        while True:
            candidate = f"{base_name}{index}{ext}"
            if candidate not in self._used_names:
                break
            index += 1
        self._used_names.add(candidate)
        part_name = f"media/{candidate}"
        rid = self._allocate_id()
        self._media_by_hash[digest] = (rid, part_name, picture.data, mime)
        rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
        self._relationships.append((rid, rel_type, part_name, None))
        return rid, part_name

    def register_part(
        self,
        *,
        part_name: str,
        data: bytes,
        relationship_type: str,
        content_type: str | None = None,
    ) -> str:
        rid = self._allocate_id()
        if part_name in self._used_names:
            raise ValueError(f"Duplicate part name: {part_name}")
        self._used_names.add(part_name)
        self._parts.append((part_name, data, content_type))
        self._relationships.append((rid, relationship_type, part_name, None))
        return rid

    def register_hyperlink(self, target: str) -> str:
        if target in self._hyperlinks:
            return self._hyperlinks[target]
        rid = self._allocate_id()
        rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
        self._relationships.append((rid, rel_type, target, "External"))
        self._hyperlinks[target] = rid
        return rid

    def iter_media(self) -> Iterator[tuple[str, bytes, str]]:
        for _, part_name, data, mime in sorted(self._media_by_hash.values(), key=lambda item: item[1]):
            yield part_name, data, mime

    def iter_parts(self) -> Iterator[tuple[str, bytes, str | None]]:
        yield from sorted(self._parts, key=lambda item: item[0])

    def iter_relationships(self) -> Iterator[tuple[str, str, str, str | None]]:
        yield from self._relationships


def resolve_image_type(mime_type: str | None) -> tuple[str, str]:
    if mime_type in {"image/png", "image/jpeg", "image/gif", "image/bmp"}:
        return {
            "image/png": (".png", "image/png"),
            "image/jpeg": (".jpeg", "image/jpeg"),
            "image/gif": (".gif", "image/gif"),
            "image/bmp": (".bmp", "image/bmp"),
        }[mime_type]
    return ".png", "image/png"
