"""Image extraction and rasterisation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

from pypdf import PdfReader
from pypdf._page import ContentStream
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    EncodedStreamObject,
    IndirectObject,
    NameObject,
    NumberObject,
    StreamObject,
)

from ..ir import Picture
from ..primitives import BoundingBox, Image, Line, Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

__all__ = [
    "extract_page_images",
    "image_to_picture",
    "line_to_picture",
    "lines_to_picture",
    "path_to_picture",
]


@dataclass(slots=True)
class _ResolvedImage:
    name: str
    data: bytes
    mime_type: str
    width: float
    height: float
    bbox: BoundingBox
    description: str | None = None


def extract_page_images(page: DictionaryObject, reader: PdfReader) -> list[Image]:
    """Return decoded :class:`Image` primitives for *page*."""

    resource_map = _collect_image_resources(page, reader)
    if not resource_map:
        return []

    placements = _collect_image_placements(page, reader, resource_map)
    images: list[Image] = []
    for placement in placements:
        images.append(
            Image(
                data=placement.data,
                bbox=placement.bbox,
                mime_type=placement.mime_type,
                name=placement.name,
            )
        )
    return images


def image_to_picture(image: Image) -> Picture:
    """Convert an :class:`Image` primitive to a :class:`Picture`."""

    width = max(image.bbox.width(), 1.0)
    height = max(image.bbox.height(), 1.0)
    data = image.data
    mime_type = image.mime_type or _sniff_mime(data)
    if mime_type not in {"image/png", "image/jpeg", "image/gif", "image/bmp"}:
        data = _placeholder_png(max(1, int(round(width))), max(1, int(round(height))))
        mime_type = "image/png"
    return Picture(
        data=data,
        width=width,
        height=height,
        mime_type=mime_type,
        name=image.name,
    )


def line_to_picture(line: Line) -> Picture:
    """Rasterise *line* into a transparent PNG-backed picture."""

    bbox = BoundingBox(
        left=min(line.start[0], line.end[0]),
        bottom=min(line.start[1], line.end[1]),
        right=max(line.start[0], line.end[0]),
        top=max(line.start[1], line.end[1]),
    )
    width = max(bbox.width(), 1.0)
    height = max(bbox.height(), 1.0)
    scale = 2.0
    px_w = max(1, int(round(width * scale)))
    px_h = max(1, int(round(height * scale)))
    px_w = max(px_w, 2 if width > 0 else 1)
    px_h = max(px_h, 2 if height > 0 else 1)

    pixels = bytearray(px_w * px_h * 4)

    def _to_pixel(coord: tuple[float, float]) -> tuple[int, int]:
        x = 0 if width == 0 else (coord[0] - bbox.left) / width
        y = 0 if height == 0 else (coord[1] - bbox.bottom) / height
        px = min(px_w - 1, max(0, int(round(x * (px_w - 1)))))
        py = min(px_h - 1, max(0, int(round((1 - y) * (px_h - 1)))))
        return px, py

    x0, y0 = _to_pixel(line.start)
    x1, y1 = _to_pixel(line.end)
    stroke_width = line.stroke_width if line.stroke_width is not None else 1.0
    thickness = max(1, int(round(max(stroke_width * scale, 1.0))))
    _draw_line_rgba(pixels, px_w, px_h, x0, y0, x1, y1, (0, 0, 0, 255), thickness)

    png_data = _encode_png(px_w, px_h, bytes(pixels), components=4)
    description = f"Line from {line.start} to {line.end}"
    return Picture(
        data=png_data,
        width=width,
        height=height,
        mime_type="image/png",
        name="line",
        description=description,
    )


def lines_to_picture(lines: Sequence[Line], bbox: BoundingBox | None = None) -> Picture:
    """Rasterise multiple lines into a transparent PNG-backed picture."""

    if not lines:
        raise ValueError("lines must contain at least one element")
    if bbox is None:
        left = min(min(line.start[0], line.end[0]) for line in lines)
        right = max(max(line.start[0], line.end[0]) for line in lines)
        bottom = min(min(line.start[1], line.end[1]) for line in lines)
        top = max(max(line.start[1], line.end[1]) for line in lines)
        bbox = BoundingBox(left=left, bottom=bottom, right=right, top=top)
    width = max(bbox.width(), 1.0)
    height = max(bbox.height(), 1.0)
    scale = 2.0
    px_w = max(1, int(round(width * scale)))
    px_h = max(1, int(round(height * scale)))
    px_w = max(px_w, 2 if width > 0 else 1)
    px_h = max(px_h, 2 if height > 0 else 1)

    pixels = bytearray(px_w * px_h * 4)

    def _to_pixel(coord: tuple[float, float]) -> tuple[int, int]:
        x = 0.0 if width == 0 else (coord[0] - bbox.left) / width
        y = 0.0 if height == 0 else (coord[1] - bbox.bottom) / height
        px = min(px_w - 1, max(0, int(round(x * (px_w - 1)))))
        py = min(px_h - 1, max(0, int(round((1 - y) * (px_h - 1)))))
        return px, py

    for line in lines:
        x0, y0 = _to_pixel(line.start)
        x1, y1 = _to_pixel(line.end)
        stroke_width = line.stroke_width if line.stroke_width is not None else 1.0
        thickness = max(1, int(round(max(stroke_width * scale, 1.0))))
        _draw_line_rgba(pixels, px_w, px_h, x0, y0, x1, y1, (0, 0, 0, 255), thickness)

    png_data = _encode_png(px_w, px_h, bytes(pixels), components=4)
    description = "Vector equation"
    return Picture(
        data=png_data,
        width=width,
        height=height,
        mime_type="image/png",
        name="equation",
        description=description,
    )


def path_to_picture(path: Path) -> Picture:
    """Rasterise a vector :class:`Path` into a :class:`Picture`."""

    bbox = path.bbox
    width = max(bbox.width(), 1.0)
    height = max(bbox.height(), 1.0)
    scale = 2.0
    px_w = max(1, int(round(max(width, 1.0) * scale)))
    px_h = max(1, int(round(max(height, 1.0) * scale)))
    px_w = max(px_w, 2 if width > 0 else 1)
    px_h = max(px_h, 2 if height > 0 else 1)

    pixels = bytearray(px_w * px_h * 4)

    def _to_pixel_float(point: tuple[float, float]) -> tuple[float, float]:
        if width == 0:
            x_ratio = 0.0
        else:
            x_ratio = (point[0] - bbox.left) / max(width, 1e-6)
        if height == 0:
            y_ratio = 0.0
        else:
            y_ratio = (bbox.top - point[1]) / max(height, 1e-6)
        return x_ratio * (px_w - 1), y_ratio * (px_h - 1)

    fill_rgba: tuple[int, int, int, int] | None = None
    if path.fill_color is not None and path.fill_alpha > 0:
        r = int(round(max(0.0, min(path.fill_color[0], 1.0)) * 255))
        g = int(round(max(0.0, min(path.fill_color[1], 1.0)) * 255))
        b = int(round(max(0.0, min(path.fill_color[2], 1.0)) * 255))
        a = int(round(max(0.0, min(path.fill_alpha, 1.0)) * 255))
        fill_rgba = (r, g, b, a)

    stroke_rgba: tuple[int, int, int, int] | None = None
    if path.stroke_color is not None and path.stroke_alpha > 0:
        r = int(round(max(0.0, min(path.stroke_color[0], 1.0)) * 255))
        g = int(round(max(0.0, min(path.stroke_color[1], 1.0)) * 255))
        b = int(round(max(0.0, min(path.stroke_color[2], 1.0)) * 255))
        a = int(round(max(0.0, min(path.stroke_alpha, 1.0)) * 255))
        stroke_rgba = (r, g, b, a)

    polygon_sets: list[list[tuple[float, float]]] = []
    for subpath in path.subpaths:
        if len(subpath) < 3:
            continue
        polygon_sets.append([_to_pixel_float(point) for point in subpath])

    if fill_rgba and fill_rgba[3] > 0:
        for polygon in polygon_sets:
            _fill_polygon(pixels, px_w, px_h, polygon, fill_rgba)

    if stroke_rgba and stroke_rgba[3] > 0:
        thickness = max(1, int(round(max((path.stroke_width or 1.0) * scale, 1.0))))
        for subpath in path.subpaths:
            if len(subpath) < 2:
                continue
            previous = _to_pixel_float(subpath[0])
            for point in subpath[1:]:
                current = _to_pixel_float(point)
                x0, y0 = int(round(previous[0])), int(round(previous[1]))
                x1, y1 = int(round(current[0])), int(round(current[1]))
                _draw_line_rgba(pixels, px_w, px_h, x0, y0, x1, y1, stroke_rgba, thickness)
                previous = current

    png_data = _encode_png(px_w, px_h, bytes(pixels), components=4)
    description = "Rectangle" if path.is_rectangle else "Vector graphic"
    return Picture(
        data=png_data,
        width=width,
        height=height,
        mime_type="image/png",
        name="vector",
        description=description,
    )


def _collect_image_resources(
    page: DictionaryObject, reader: PdfReader
) -> dict[str, EncodedStreamObject]:
    resources = _resolve(page.get(NameObject("/Resources")), reader)
    if not isinstance(resources, DictionaryObject):
        return {}
    xobjects = _resolve(resources.get(NameObject("/XObject")), reader)
    if not isinstance(xobjects, DictionaryObject):
        return {}
    images: dict[str, EncodedStreamObject] = {}
    for name_obj, raw in xobjects.items():
        name = _clean_name(name_obj)
        stream = _resolve(raw, reader)
        if isinstance(stream, EncodedStreamObject) and _is_image_xobject(stream):
            images[name] = stream
    return images


def _collect_image_placements(
    page: DictionaryObject,
    reader: PdfReader,
    resources: dict[str, EncodedStreamObject],
) -> list[_ResolvedImage]:
    content = ContentStream(page.get_contents(), reader)
    resolved: list[_ResolvedImage] = []

    matrix_stack: list[tuple[float, float, float, float, float, float]] = [
        (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    ]

    for operands, operator in content.operations:
        if operator == b"q":
            matrix_stack.append(matrix_stack[-1])
            continue
        if operator == b"Q":
            if len(matrix_stack) > 1:
                matrix_stack.pop()
            continue
        if operator == b"cm":
            if len(operands) == 6:
                matrix_stack[-1] = _matrix_multiply(
                    matrix_stack[-1],
                    tuple(float(o) for o in operands),
                )
            continue
        if operator == b"Do" and operands:
            name = _clean_name(operands[0])
            stream = resources.get(name)
            if stream is None:
                continue
            placement = _resolve_stream(name, stream, matrix_stack[-1], reader)
            if placement:
                resolved.append(placement)
    return resolved


def _is_image_xobject(stream: EncodedStreamObject) -> bool:
    subtype = stream.get(NameObject("/Subtype"))
    return isinstance(subtype, NameObject) and subtype == NameObject("/Image")


def _clean_name(name: object) -> str:
    raw = str(name)
    return raw[1:] if raw.startswith("/") else raw


def _resolve(obj: object | None, reader: PdfReader) -> object | None:
    if isinstance(obj, IndirectObject):
        try:
            return obj.get_object()
        except Exception:
            return None
    return obj


def _matrix_multiply(
    lhs: tuple[float, float, float, float, float, float],
    rhs: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    a1, b1, c1, d1, e1, f1 = lhs
    a2, b2, c2, d2, e2, f2 = rhs
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _matrix_apply(
    matrix: tuple[float, float, float, float, float, float],
    x: float,
    y: float,
) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def _resolve_stream(
    name: str,
    stream: EncodedStreamObject,
    matrix: tuple[float, float, float, float, float, float],
    reader: PdfReader,
) -> _ResolvedImage | None:
    width = float(stream.get(NameObject("/Width"), 0))
    height = float(stream.get(NameObject("/Height"), 0))
    if not width or not height:
        return None

    data, mime_type, description = _stream_data(stream, reader)
    if data is None:
        data = _placeholder_png(int(max(width, 1)), int(max(height, 1)))
        mime_type = "image/png"
        description = description or "Unsupported image format"

    x0, y0 = _matrix_apply(matrix, 0, 0)
    x1, y1 = _matrix_apply(matrix, 1, 0)
    x2, y2 = _matrix_apply(matrix, 0, 1)
    x3, y3 = _matrix_apply(matrix, 1, 1)

    xs = [x0, x1, x2, x3]
    ys = [y0, y1, y2, y3]
    left = min(xs)
    right = max(xs)
    bottom = min(ys)
    top = max(ys)
    bbox = BoundingBox(left=left, bottom=bottom, right=right, top=top)

    return _ResolvedImage(
        name=name,
        data=data,
        mime_type=mime_type,
        width=bbox.width(),
        height=bbox.height(),
        bbox=bbox,
        description=description,
    )


def _stream_data(
    stream: EncodedStreamObject,
    reader: PdfReader,
) -> tuple[bytes | None, str, str | None]:
    filters = _normalise_filters(stream.get(NameObject("/Filter")))
    if "DCTDecode" in filters and stream.get(NameObject("/SMask")) is None:
        raw = getattr(stream, "_data", None)
        data = bytes(raw) if raw is not None else stream.get_data()
        return data, "image/jpeg", None

    raw = stream.get_data()
    color_space = _resolve(stream.get(NameObject("/ColorSpace")), reader)
    bits = int(stream.get(NameObject("/BitsPerComponent"), 8) or 8)

    alpha = _extract_alpha(stream, reader)
    try:
        rgb_data = _normalise_image_bytes(raw, color_space, bits, reader)
        if rgb_data is None:
            raise ValueError("Unsupported colorspace")
    except Exception:
        return None, "image/png", "Unsupported image colorspace"

    if alpha is not None and len(alpha) == len(rgb_data) // 3:
        rgba = bytearray()
        for index, value in enumerate(rgb_data):
            rgba.append(value)
            if (index + 1) % 3 == 0:
                rgba.append(alpha[(index + 1) // 3 - 1])
        data = _encode_png(
            int(stream.get(NameObject("/Width"), 1)),
            int(stream.get(NameObject("/Height"), 1)),
            bytes(rgba),
            components=4,
        )
        return data, "image/png", None

    pixel_data = rgb_data
    components = 3 if rgb_data is not None else 0
    if components == 0:
        return None, "image/png", "Unsupported image data"
    data = _encode_png(
        int(stream.get(NameObject("/Width"), 1)),
        int(stream.get(NameObject("/Height"), 1)),
        pixel_data,
        components=3,
    )
    return data, "image/png", None


def _normalise_filters(filter_obj: object | None) -> set[str]:
    if filter_obj is None:
        return set()
    if isinstance(filter_obj, NameObject):
        return {_clean_name(filter_obj)}
    if isinstance(filter_obj, ArrayObject):
        return {_clean_name(item) for item in filter_obj}
    return {str(filter_obj)}


def _extract_alpha(stream: EncodedStreamObject, reader: PdfReader) -> bytes | None:
    smask = _resolve(stream.get(NameObject("/SMask")), reader)
    if isinstance(smask, (EncodedStreamObject, StreamObject)):
        alpha = smask.get_data()
        return _normalise_alpha(alpha, smask, reader)
    mask = _resolve(stream.get(NameObject("/Mask")), reader)
    if isinstance(mask, (EncodedStreamObject, StreamObject)):
        alpha = mask.get_data()
        return _normalise_alpha(alpha, mask, reader)
    return None


def _normalise_alpha(
    alpha: bytes,
    stream: EncodedStreamObject | StreamObject,
    reader: PdfReader,
) -> bytes | None:
    bits = int(stream.get(NameObject("/BitsPerComponent"), 8) or 8)
    if bits == 8:
        return alpha
    if bits == 1:
        expanded = bytearray()
        for byte in alpha:
            for bit in range(7, -1, -1):
                expanded.append(255 if (byte >> bit) & 1 else 0)
        width = int(stream.get(NameObject("/Width"), 1))
        height = int(stream.get(NameObject("/Height"), 1))
        expected = width * height
        return bytes(expanded[:expected])
    return None


def _normalise_image_bytes(
    raw: bytes,
    color_space: object | None,
    bits: int,
    reader: PdfReader,
) -> bytes | None:
    if bits != 8:
        return None
    if isinstance(color_space, NameObject):
        if color_space == NameObject("/DeviceRGB"):
            return raw
        if color_space == NameObject("/DeviceGray"):
            return bytes(_expand_gray(raw))
        if color_space == NameObject("/DeviceCMYK"):
            return bytes(_convert_cmyk_to_rgb(raw))
    if isinstance(color_space, ArrayObject) and color_space:
        kind = color_space[0]
        if kind == NameObject("/CalRGB"):
            return raw
        if kind == NameObject("/ICCBased") and len(color_space) > 1:
            alternate = _resolve(color_space[1], reader)
            if isinstance(alternate, StreamObject):
                n = int(alternate.get(NameObject("/N"), 3) or 3)
                if n == 3:
                    return raw
        if kind == NameObject("/Indexed") and len(color_space) >= 4:
            base = color_space[1]
            hival = int(color_space[2])
            lookup = _resolve(color_space[3], reader)
            palette = _extract_palette(lookup, base, hival, reader)
            if palette is None:
                return None
            return bytes(_apply_palette(raw, palette))
    return None


def _expand_gray(raw: bytes) -> Iterator[int]:
    for value in raw:
        yield value
        yield value
        yield value


def _convert_cmyk_to_rgb(raw: bytes) -> Iterator[int]:
    for index in range(0, len(raw), 4):
        c, m, y, k = raw[index : index + 4]
        r = 255 - min(255, c + k)
        g = 255 - min(255, m + k)
        b = 255 - min(255, y + k)
        yield r
        yield g
        yield b


def _extract_palette(
    lookup: object | None,
    base: object,
    hival: int,
    reader: PdfReader,
) -> list[tuple[int, int, int]] | None:
    if isinstance(base, ArrayObject):
        base = base[0]
    if isinstance(base, NameObject) and base == NameObject("/DeviceRGB"):
        pass
    elif isinstance(base, NameObject) and base == NameObject("/DeviceGray"):
        pass
    else:
        return None
    if isinstance(lookup, StreamObject):
        data = lookup.get_data()
    elif isinstance(lookup, (bytes, bytearray)):
        data = bytes(lookup)
    else:
        data = bytes(str(lookup), "latin1") if lookup is not None else b""
    step = 3 if base == NameObject("/DeviceRGB") else 1
    palette: list[tuple[int, int, int]] = []
    for index in range(0, min(len(data), (hival + 1) * step), step):
        if step == 3:
            palette.append((data[index], data[index + 1], data[index + 2]))
        else:
            value = data[index]
            palette.append((value, value, value))
    if not palette:
        return None
    return palette


def _apply_palette(raw: bytes, palette: Sequence[tuple[int, int, int]]) -> Iterator[int]:
    limit = len(palette)
    for index in raw:
        entry = palette[index if index < limit else -1]
        yield from entry


def _encode_png(
    width: int,
    height: int,
    raw: bytes,
    *,
    components: int,
) -> bytes:
    import struct
    import zlib

    if width <= 0 or height <= 0:
        raise ValueError("Invalid PNG dimensions")

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    color_type = {1: 0, 3: 2, 4: 6}.get(components)
    if color_type is None:
        raise ValueError("Unsupported component count")

    rows = bytearray()
    row_stride = width * components
    for row in range(height):
        start = row * row_stride
        end = start + row_stride
        rows.append(0)
        rows.extend(raw[start:end])

    compressed = zlib.compress(bytes(rows))
    header = chunk(
        b"IHDR",
        struct.pack(
            ">IIBBBBB",
            width,
            height,
            8,
            color_type,
            0,
            0,
            0,
        ),
    )
    data = chunk(b"IDAT", compressed)
    end = chunk(b"IEND", b"")
    return PNG_SIGNATURE + header + data + end


def _placeholder_png(width: int, height: int) -> bytes:
    width = max(1, width)
    height = max(1, height)
    pixels = bytes([200, 200, 200, 255] * width * height)
    return _encode_png(width, height, pixels, components=4)


def _draw_line_rgba(
    buffer: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int, int],
    thickness: int,
) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    half = max(0, thickness // 2)
    while True:
        for offset_x in range(-half, half + 1):
            for offset_y in range(-half, half + 1):
                _blend_pixel(buffer, width, height, x0 + offset_x, y0 + offset_y, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _fill_polygon(
    buffer: bytearray,
    width: int,
    height: int,
    polygon: list[tuple[float, float]],
    color: tuple[int, int, int, int],
) -> None:
    if len(polygon) < 3 or color[3] == 0:
        return
    edge_count = len(polygon)
    for y in range(height):
        scan_y = y + 0.5
        intersections: list[float] = []
        for index in range(edge_count):
            x1, y1 = polygon[index]
            x2, y2 = polygon[(index + 1) % edge_count]
            if (y1 <= scan_y < y2) or (y2 <= scan_y < y1):
                if y2 == y1:
                    continue
                x = x1 + (scan_y - y1) * (x2 - x1) / (y2 - y1)
                intersections.append(x)
        intersections.sort()
        for index in range(0, len(intersections), 2):
            if index + 1 >= len(intersections):
                break
            start = intersections[index]
            end = intersections[index + 1]
            if end < start:
                start, end = end, start
            x_start = max(0, min(width - 1, int(round(start))))
            x_end = max(0, min(width - 1, int(round(end))))
            for x in range(x_start, x_end + 1):
                _blend_pixel(buffer, width, height, x, y, color)


def _blend_pixel(
    buffer: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    if not (0 <= x < width and 0 <= y < height):
        return
    index = (y * width + x) * 4
    existing = buffer[index : index + 4]
    if not existing:
        existing = b"\x00\x00\x00\x00"
    er, eg, eb, ea = existing
    new_alpha = color[3] / 255.0
    old_alpha = ea / 255.0
    out_alpha = new_alpha + old_alpha * (1 - new_alpha)
    if out_alpha <= 0:
        buffer[index : index + 4] = bytes((0, 0, 0, 0))
        return
    def _blend_component(new_value: int, old_value: int) -> int:
        return int(
            round(
                (
                    new_value * new_alpha
                    + old_value * old_alpha * (1 - new_alpha)
                )
                / out_alpha
            )
        )

    r = _blend_component(color[0], er)
    g = _blend_component(color[1], eg)
    b = _blend_component(color[2], eb)
    a = int(round(out_alpha * 255))
    buffer[index : index + 4] = bytes((r, g, b, a))


def _sniff_mime(data: bytes) -> str:
    if data.startswith(PNG_SIGNATURE):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if data[0:2] == b"BM":
        return "image/bmp"
    return "image/png"

