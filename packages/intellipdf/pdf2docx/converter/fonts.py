"""Font translation helpers for the converter."""

from __future__ import annotations

from typing import Mapping

from pypdf import _cmap
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject

__all__ = [
    "apply_translation_map",
    "collect_font_dictionaries",
    "font_translation_maps",
]


def _glyph_name_to_unicode(name: str) -> str | None:
    if not name:
        return None
    if not name.startswith("/"):
        name = f"/{name}"
    return _cmap.adobe_glyphs.get(name)


def _build_font_translation(font_dict: DictionaryObject) -> tuple[dict[str, str], int]:
    translation: dict[str, str] = {}
    max_key_length = 1
    try:
        encoding, cmap = _cmap.get_encoding(font_dict)
    except Exception:
        encoding, cmap = None, {}
    if isinstance(cmap, dict) and cmap:
        for key, value in cmap.items():
            if key == -1 or not isinstance(key, str):
                continue
            mapped_value: str
            if isinstance(value, bytes):
                try:
                    mapped_value = value.decode("utf-16-be", "surrogatepass")
                except Exception:
                    mapped_value = value.decode("latin-1", "ignore")
            else:
                mapped_value = str(value)
            translation[key] = mapped_value
            if len(key) > max_key_length:
                max_key_length = len(key)
    if not translation and isinstance(encoding, dict):
        for raw_code, glyph_name in encoding.items():
            if isinstance(raw_code, int):
                try:
                    key = chr(raw_code)
                except ValueError:
                    continue
            elif isinstance(raw_code, str):
                key = raw_code
            else:
                continue
            mapped_value: str | None
            if isinstance(glyph_name, str):
                mapped_value = _glyph_name_to_unicode(glyph_name) or glyph_name.lstrip("/")
            else:
                mapped_value = None
            if mapped_value:
                translation[key] = mapped_value
    if translation:
        max_key_length = max(max_key_length, max(len(key) for key in translation))
    else:
        max_key_length = 1
    return translation, max_key_length


def collect_font_dictionaries(font_obj: DictionaryObject) -> list[DictionaryObject]:
    dictionaries = [font_obj]
    descendants = font_obj.get(NameObject("/DescendantFonts"))
    if isinstance(descendants, ArrayObject):
        for entry in descendants:
            try:
                resolved = entry.get_object() if isinstance(entry, IndirectObject) else entry
            except Exception:
                continue
            if isinstance(resolved, DictionaryObject):
                dictionaries.append(resolved)
    return dictionaries


def font_translation_maps(page: DictionaryObject) -> dict[int, tuple[dict[str, str], int]]:
    maps: dict[int, tuple[dict[str, str], int]] = {}
    resources = page.get(NameObject("/Resources"))
    if isinstance(resources, IndirectObject):
        try:
            resources = resources.get_object()
        except Exception:
            resources = None
    if not isinstance(resources, DictionaryObject):
        return maps
    fonts = resources.get(NameObject("/Font"))
    if isinstance(fonts, IndirectObject):
        try:
            fonts = fonts.get_object()
        except Exception:
            fonts = None
    if not isinstance(fonts, DictionaryObject):
        return maps
    for font in fonts.values():
        try:
            resolved_font = font.get_object() if isinstance(font, IndirectObject) else font
        except Exception:
            continue
        if not isinstance(resolved_font, DictionaryObject):
            continue
        for dictionary in collect_font_dictionaries(resolved_font):
            if not isinstance(dictionary, DictionaryObject):
                continue
            try:
                translation, max_key_length = _build_font_translation(dictionary)
            except Exception:
                continue
            if translation:
                maps[id(dictionary)] = (translation, max_key_length)
    return maps


def apply_translation_map(text: str, mapping: Mapping[str, str], max_key_length: int) -> str:
    if not mapping:
        return text
    if max_key_length <= 1:
        return "".join(mapping.get(char, char) for char in text)
    result: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        matched = False
        max_window = min(max_key_length, length - index)
        for window in range(max_window, 0, -1):
            segment = text[index : index + window]
            mapped = mapping.get(segment)
            if mapped is not None:
                result.append(mapped)
                index += window
                matched = True
                break
        if not matched:
            result.append(text[index])
            index += 1
    return "".join(result)
