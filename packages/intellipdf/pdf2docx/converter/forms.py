"""Helpers for rendering PDF form fields into the document IR."""

from __future__ import annotations

from typing import Iterable

from ..ir import Paragraph, Run, Table, TableCell, TableRow
from ..primitives import FormField
from .text import normalise_text_content

__all__ = ["form_field_to_table"]

_CHECKED_SYMBOL = "\u2611"  # ☑
_UNCHECKED_SYMBOL = "\u2610"  # ☐
_SIGNATURE_PLACEHOLDER = "_" * 24
_NBSP = "\u00A0"


def _make_paragraph(text: str, *, strip: bool, bold: bool = False, italic: bool = False) -> Paragraph:
    cleaned = normalise_text_content(text, strip=strip) if text else ""
    if not cleaned:
        cleaned = _NBSP
    run = Run(text=cleaned, bold=bold, italic=italic)
    return Paragraph(runs=[run])


def _value_paragraphs(field: FormField, *, strip_whitespace: bool) -> Iterable[Paragraph]:
    kind = field.field_type.lower()
    if kind == "checkbox":
        symbol = _CHECKED_SYMBOL if field.checked else _UNCHECKED_SYMBOL
        label = field.value if field.value and field.value.lower() not in {"yes", "on"} else ""
        text = f"{symbol} {label}".strip()
        yield _make_paragraph(text or symbol, strip=False)
        if field.tooltip and field.tooltip != field.label:
            yield _make_paragraph(f"({field.tooltip})", strip=False, italic=True)
        return
    if kind == "dropdown":
        selected = field.value or ""
        if selected:
            yield _make_paragraph(f"Selected: {selected}", strip=False)
        else:
            yield _make_paragraph("Selected: (none)", strip=False)
        if field.options:
            yield _make_paragraph(
                "Options: " + ", ".join(field.options),
                strip=False,
            )
        if field.tooltip and field.tooltip not in {field.label, selected}:
            yield _make_paragraph(f"({field.tooltip})", strip=False, italic=True)
        return
    if kind == "signature":
        yield _make_paragraph(_SIGNATURE_PLACEHOLDER, strip=False)
        if field.value:
            yield _make_paragraph(f"Signed: {field.value}", strip=False)
        elif field.tooltip and field.tooltip != field.label:
            yield _make_paragraph(f"({field.tooltip})", strip=False, italic=True)
        return
    # Default to text field behaviour
    value = field.value or ""
    lines = value.splitlines() if value else [""]
    for line in lines:
        yield _make_paragraph(line, strip=strip_whitespace)
    if field.tooltip and field.tooltip not in {field.label, value}:
        yield _make_paragraph(f"({field.tooltip})", strip=False, italic=True)


def form_field_to_table(field: FormField, *, strip_whitespace: bool) -> Table:
    label_source = field.label or field.name or field.field_type.title()
    label = normalise_text_content(label_source, strip=False) if label_source else field.field_type.title()
    label_paragraph = _make_paragraph(label, strip=False, bold=True)
    value_paragraphs = list(_value_paragraphs(field, strip_whitespace=strip_whitespace))
    if not value_paragraphs:
        value_paragraphs = [_make_paragraph("", strip=False)]

    label_cell = TableCell(content=[label_paragraph])
    value_cell = TableCell(content=value_paragraphs)

    width = max(field.bbox.width(), 1.0)
    label_width = width * 0.35
    value_width = width - label_width

    table = Table(
        rows=[TableRow(cells=[label_cell, value_cell])],
        width=width,
        column_widths=[label_width, value_width],
        borders={
            "top": "single",
            "bottom": "single",
            "left": "single",
            "right": "single",
            "insideH": "single",
            "insideV": "single",
        },
        cell_padding=4.0,
    )
    table.alignment = "left"
    return table
