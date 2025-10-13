"""CLI helpers for the split command."""

from __future__ import annotations

from argparse import ArgumentParser, _SubParsersAction

from ...tools.common.interfaces import ConversionContext


def configure_parser(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("split", help="Split a PDF into multiple files")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("output", help="Output directory for split pages")
    parser.add_argument("--mode", choices=["range", "pages"], default="range")
    parser.add_argument("--ranges", help="Comma separated page ranges", default=None)
    parser.add_argument(
        "--pages",
        nargs="+",
        help="Explicit page numbers when using --mode pages",
        default=None,
    )
    parser.set_defaults(tool_name="split", build_context=_build_context)


def _build_context(args) -> ConversionContext:
    return ConversionContext(
        input_path=args.input,
        output_path=args.output,
        config={"mode": args.mode, "ranges": args.ranges, "pages": args.pages},
    )
