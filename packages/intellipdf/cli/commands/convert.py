"""CLI helpers for document conversion commands."""

from __future__ import annotations

from argparse import ArgumentParser, _SubParsersAction

from ...tools.common.interfaces import ConversionContext

SUPPORTED_FORMATS = {
    "docx": "convert_docx",
}


def configure_parser(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("convert", help="Convert a PDF into a different format")
    parser.add_argument("input", help="Input PDF path")
    parser.add_argument("output", nargs="?", help="Destination file path")
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS.keys()),
        default="docx",
        help="Output format",
    )
    parser.set_defaults(build_context=_build_context, tool_name_resolver=_select_tool)


def _select_tool(format_name: str) -> str:
    return SUPPORTED_FORMATS[format_name]


def _build_context(args) -> ConversionContext:
    tool_name = _select_tool(args.format)
    context = ConversionContext(
        input_path=args.input,
        output_path=args.output,
        config={"options": None, "metadata": None},
    )
    context.resources["tool_name"] = tool_name
    return context
