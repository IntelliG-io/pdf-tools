"""Construct individual DOCX XML parts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from xml.etree.ElementTree import Element, SubElement

from .elements import build_document_xml
from .namespaces import XML_NS
from .numbering import NUMBERING_SCHEMES, PUNCTUATION_MARKERS, ordered_level_formats
from .relationships import RelationshipManager
from .types import CoreProperties, DocumentStatistics
from .utils import serialize

__all__ = [
    "build_app_properties_xml",
    "build_content_types_xml",
    "build_core_properties_xml",
    "build_document_relationships_xml",
    "build_document_xml",
    "build_numbering_xml",
    "build_root_relationships_xml",
    "build_styles_xml",
]


def build_styles_xml() -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    root = Element(f"{w_ns}styles")

    doc_defaults = SubElement(root, f"{w_ns}docDefaults")
    r_pr_default = SubElement(doc_defaults, f"{w_ns}rPrDefault")
    r_pr_default_pr = SubElement(r_pr_default, f"{w_ns}rPr")
    SubElement(r_pr_default_pr, f"{w_ns}lang", {f"{w_ns}val": "en-US"})
    p_pr_default = SubElement(doc_defaults, f"{w_ns}pPrDefault")
    p_pr_default_pr = SubElement(p_pr_default, f"{w_ns}pPr")
    SubElement(
        p_pr_default_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "160",
            f"{w_ns}line": "240",
            f"{w_ns}lineRule": "auto",
        },
    )

    def _style(
        style_id: str,
        style_type: str,
        *,
        default: bool = False,
        based_on: str | None = None,
        name: str | None = None,
        quick_style: bool = False,
    ) -> Element:
        attrs = {f"{w_ns}type": style_type, f"{w_ns}styleId": style_id}
        if default:
            attrs[f"{w_ns}default"] = "1"
        style = SubElement(root, f"{w_ns}style", attrs)
        if name:
            SubElement(style, f"{w_ns}name", {f"{w_ns}val": name})
        if based_on:
            SubElement(style, f"{w_ns}basedOn", {f"{w_ns}val": based_on})
        if quick_style:
            SubElement(style, f"{w_ns}qFormat")
        return style

    normal = _style("Normal", "paragraph", default=True, name="Normal", quick_style=True)
    normal_p_pr = SubElement(normal, f"{w_ns}pPr")
    SubElement(
        normal_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "160",
            f"{w_ns}line": "240",
            f"{w_ns}lineRule": "auto",
        },
    )

    default_font = _style(
        "DefaultParagraphFont",
        "character",
        default=True,
        name="Default Paragraph Font",
    )
    SubElement(default_font, f"{w_ns}semiHidden")

    title = _style("Title", "paragraph", based_on="Normal", name="Title", quick_style=True)
    title_p_pr = SubElement(title, f"{w_ns}pPr")
    SubElement(title_p_pr, f"{w_ns}jc", {f"{w_ns}val": "center"})
    SubElement(
        title_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "160",
        },
    )
    title_r_pr = SubElement(title, f"{w_ns}rPr")
    SubElement(title_r_pr, f"{w_ns}b")
    SubElement(title_r_pr, f"{w_ns}sz", {f"{w_ns}val": "48"})

    subtitle = _style(
        "Subtitle",
        "paragraph",
        based_on="Normal",
        name="Subtitle",
        quick_style=True,
    )
    subtitle_p_pr = SubElement(subtitle, f"{w_ns}pPr")
    SubElement(subtitle_p_pr, f"{w_ns}jc", {f"{w_ns}val": "center"})
    SubElement(
        subtitle_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "160",
        },
    )
    subtitle_r_pr = SubElement(subtitle, f"{w_ns}rPr")
    SubElement(subtitle_r_pr, f"{w_ns}i")
    SubElement(subtitle_r_pr, f"{w_ns}sz", {f"{w_ns}val": "28"})

    for heading, size in (("Heading1", 32), ("Heading2", 26), ("Heading3", 22)):
        style = _style(heading, "paragraph", based_on="Normal", name=heading, quick_style=True)
        p_pr = SubElement(style, f"{w_ns}pPr")
        SubElement(p_pr, f"{w_ns}keepNext")
        SubElement(p_pr, f"{w_ns}keepLines")
        SubElement(
            p_pr,
            f"{w_ns}spacing",
            {
                f"{w_ns}before": "240",
                f"{w_ns}after": "120",
            },
        )
        r_pr = SubElement(style, f"{w_ns}rPr")
        SubElement(r_pr, f"{w_ns}b")
        SubElement(r_pr, f"{w_ns}sz", {f"{w_ns}val": str(size)})

    list_paragraph = _style(
        "ListParagraph",
        "paragraph",
        based_on="Normal",
        name="List Paragraph",
        quick_style=True,
    )
    list_p_pr = SubElement(list_paragraph, f"{w_ns}pPr")
    SubElement(
        list_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "120",
        },
    )
    SubElement(
        list_p_pr,
        f"{w_ns}ind",
        {
            f"{w_ns}left": "720",
            f"{w_ns}hanging": "360",
        },
    )

    quote = _style("Quote", "paragraph", based_on="Normal", name="Quote", quick_style=True)
    quote_p_pr = SubElement(quote, f"{w_ns}pPr")
    SubElement(
        quote_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "160",
        },
    )
    SubElement(
        quote_p_pr,
        f"{w_ns}ind",
        {
            f"{w_ns}left": "720",
            f"{w_ns}right": "720",
        },
    )

    caption = _style("Caption", "paragraph", based_on="Normal", name="Caption", quick_style=True)
    caption_p_pr = SubElement(caption, f"{w_ns}pPr")
    SubElement(caption_p_pr, f"{w_ns}jc", {f"{w_ns}val": "center"})
    SubElement(
        caption_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "120",
            f"{w_ns}after": "120",
        },
    )
    caption_r_pr = SubElement(caption, f"{w_ns}rPr")
    SubElement(caption_r_pr, f"{w_ns}i")

    code = _style("Code", "paragraph", based_on="Normal", name="Code", quick_style=True)
    code_p_pr = SubElement(code, f"{w_ns}pPr")
    SubElement(
        code_p_pr,
        f"{w_ns}spacing",
        {
            f"{w_ns}before": "0",
            f"{w_ns}after": "160",
            f"{w_ns}line": "240",
            f"{w_ns}lineRule": "auto",
        },
    )
    r_pr_code = SubElement(code, f"{w_ns}rPr")
    SubElement(
        r_pr_code,
        f"{w_ns}rFonts",
        {
            f"{w_ns}ascii": "Courier New",
            f"{w_ns}hAnsi": "Courier New",
            f"{w_ns}cs": "Courier New",
        },
    )
    SubElement(r_pr_code, f"{w_ns}sz", {f"{w_ns}val": "20"})

    hyperlink = _style(
        "Hyperlink",
        "character",
        based_on="DefaultParagraphFont",
        name="Hyperlink",
        quick_style=True,
    )
    r_pr = SubElement(hyperlink, f"{w_ns}rPr")
    SubElement(r_pr, f"{w_ns}color", {f"{w_ns}val": "0000FF"})
    SubElement(r_pr, f"{w_ns}u", {f"{w_ns}val": "single"})

    return serialize(root)


def build_numbering_xml() -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    root = Element(f"{w_ns}numbering")
    bullet_cycle = ["•", "◦", "▪", "–", "•", "◦", "▪", "–", "•"]
    for abstract_id, kind, format_name, punctuation in NUMBERING_SCHEMES:
        abstract = SubElement(
            root,
            f"{w_ns}abstractNum",
            {f"{w_ns}abstractNumId": str(abstract_id)},
        )
        if kind == "bullet":
            for level in range(9):
                glyph = bullet_cycle[level % len(bullet_cycle)]
                lvl = SubElement(abstract, f"{w_ns}lvl", {f"{w_ns}ilvl": str(level)})
                SubElement(lvl, f"{w_ns}start", {f"{w_ns}val": "1"})
                SubElement(lvl, f"{w_ns}numFmt", {f"{w_ns}val": "bullet"})
                SubElement(lvl, f"{w_ns}lvlText", {f"{w_ns}val": glyph})
                SubElement(lvl, f"{w_ns}lvlJc", {f"{w_ns}val": "left"})
                p_pr = SubElement(lvl, f"{w_ns}pPr")
                indent = 360 + level * 360
                SubElement(
                    p_pr,
                    f"{w_ns}ind",
                    {
                        f"{w_ns}left": str(indent),
                        f"{w_ns}hanging": "360",
                    },
                )
        else:
            formats = ordered_level_formats(format_name or "decimal")
            prefix, suffix = PUNCTUATION_MARKERS.get(punctuation or "dot", ("", "."))
            for level in range(9):
                lvl = SubElement(abstract, f"{w_ns}lvl", {f"{w_ns}ilvl": str(level)})
                SubElement(lvl, f"{w_ns}start", {f"{w_ns}val": "1"})
                fmt = formats[level]
                SubElement(lvl, f"{w_ns}numFmt", {f"{w_ns}val": fmt})
                lvl_text = f"{prefix}%{level + 1}{suffix}"
                SubElement(lvl, f"{w_ns}lvlText", {f"{w_ns}val": lvl_text})
                SubElement(lvl, f"{w_ns}lvlJc", {f"{w_ns}val": "left"})
                p_pr = SubElement(lvl, f"{w_ns}pPr")
                indent = 360 + level * 360
                SubElement(
                    p_pr,
                    f"{w_ns}ind",
                    {
                        f"{w_ns}left": str(indent),
                        f"{w_ns}hanging": "360",
                    },
                )

    for abstract_id, _, _, _ in NUMBERING_SCHEMES:
        num = SubElement(root, f"{w_ns}num", {f"{w_ns}numId": str(abstract_id)})
        SubElement(num, f"{w_ns}abstractNumId", {f"{w_ns}val": str(abstract_id)})

    return serialize(root)


def _format_w3cdtf(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_core_properties_xml(metadata: CoreProperties) -> bytes:
    metadata = metadata.normalise()
    root = Element(
        "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}coreProperties"
    )
    if metadata.title:
        SubElement(root, "{http://purl.org/dc/elements/1.1/}title").text = metadata.title
    if metadata.creator:
        SubElement(root, "{http://purl.org/dc/elements/1.1/}creator").text = metadata.creator
    if metadata.subject:
        SubElement(root, "{http://purl.org/dc/elements/1.1/}subject").text = metadata.subject
    if metadata.description:
        SubElement(root, "{http://purl.org/dc/elements/1.1/}description").text = metadata.description
    if metadata.keywords:
        SubElement(
            root,
            "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}keywords",
        ).text = metadata.keywords
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}revision",
    ).text = metadata.revision
    created = SubElement(
        root,
        "{http://purl.org/dc/terms/}created",
        {"{http://www.w3.org/2001/XMLSchema-instance}type": "dcterms:W3CDTF"},
    )
    created.text = _format_w3cdtf(metadata.created)
    modified = SubElement(
        root,
        "{http://purl.org/dc/terms/}modified",
        {"{http://www.w3.org/2001/XMLSchema-instance}type": "dcterms:W3CDTF"},
    )
    modified.text = _format_w3cdtf(metadata.modified)
    if metadata.last_modified_by:
        SubElement(
            root,
            "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy",
        ).text = metadata.last_modified_by
    if metadata.language:
        SubElement(root, "{http://purl.org/dc/elements/1.1/}language").text = metadata.language
    return serialize(root)


def build_app_properties_xml(stats: DocumentStatistics) -> bytes:
    root = Element(
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Properties",
        {"xmlns:vt": XML_NS["vt"]},
    )
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Application",
    ).text = "pdf2docx"
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}DocSecurity",
    ).text = "0"
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Pages",
    ).text = str(stats.pages)
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Words",
    ).text = str(stats.words)
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Paragraphs",
    ).text = str(stats.paragraphs)
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Lines",
    ).text = str(stats.lines)
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Characters",
    ).text = str(stats.characters)
    SubElement(
        root,
        "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}CharactersWithSpaces",
    ).text = str(stats.characters_with_spaces)
    return serialize(root)


def build_content_types_xml(
    media_defaults: Iterable[tuple[str, str]] | None = None,
    overrides: list[tuple[str, str]] | None = None,
) -> bytes:
    root = Element("Types", {"xmlns": "http://schemas.openxmlformats.org/package/2006/content-types"})
    SubElement(
        root,
        "Default",
        {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"},
    )
    SubElement(root, "Default", {"Extension": "xml", "ContentType": "application/xml"})
    SubElement(
        root,
        "Override",
        {
            "PartName": "/word/document.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        },
    )
    SubElement(
        root,
        "Override",
        {
            "PartName": "/word/styles.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml",
        },
    )
    SubElement(
        root,
        "Override",
        {
            "PartName": "/word/numbering.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml",
        },
    )
    SubElement(
        root,
        "Override",
        {
            "PartName": "/docProps/core.xml",
            "ContentType": "application/vnd.openxmlformats-package.core-properties+xml",
        },
    )
    SubElement(
        root,
        "Override",
        {
            "PartName": "/docProps/app.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.extended-properties+xml",
        },
    )

    extra = overrides or []
    for part_name, content_type in extra:
        SubElement(
            root,
            "Override",
            {"PartName": f"/word/{part_name}", "ContentType": content_type},
        )

    seen_defaults = {"rels", "xml"}
    unique_media: dict[str, str] = {}
    for extension, content_type in media_defaults or []:
        ext = extension.lower()
        if not ext or ext in seen_defaults:
            continue
        if ext in unique_media and unique_media[ext] != content_type:
            raise ValueError(
                f"Conflicting content type for extension '{ext}': "
                f"{unique_media[ext]} vs {content_type}"
            )
        unique_media.setdefault(ext, content_type)

    for ext, content_type in sorted(unique_media.items()):
        SubElement(root, "Default", {"Extension": ext, "ContentType": content_type})
    return serialize(root)


def build_root_relationships_xml() -> bytes:
    root = Element("Relationships", {"xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"})
    SubElement(
        root,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "word/document.xml",
        },
    )
    SubElement(
        root,
        "Relationship",
        {
            "Id": "rId2",
            "Type": "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
            "Target": "docProps/core.xml",
        },
    )
    SubElement(
        root,
        "Relationship",
        {
            "Id": "rId3",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
            "Target": "docProps/app.xml",
        },
    )
    return serialize(root)


def build_document_relationships_xml(relationships: RelationshipManager) -> bytes:
    root = Element("Relationships", {"xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"})
    SubElement(
        root,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "Target": "styles.xml",
        },
    )
    SubElement(
        root,
        "Relationship",
        {
            "Id": "rId2",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering",
            "Target": "numbering.xml",
        },
    )
    for rid, rel_type, target, mode in relationships.iter_relationships():
        attrs = {"Id": rid, "Type": rel_type, "Target": target}
        if mode:
            attrs["TargetMode"] = mode
        SubElement(root, "Relationship", attrs)
    return serialize(root)
