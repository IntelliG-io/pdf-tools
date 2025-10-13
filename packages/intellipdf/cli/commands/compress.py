"""CLI helpers for compressing PDF files."""

from __future__ import annotations

from argparse import ArgumentParser, _SubParsersAction

from ...tools.common.interfaces import ConversionContext


def configure_parser(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("compress", help="Compress a PDF file")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("output", help="Destination for compressed PDF")
    parser.add_argument(
        "--level",
        choices=["low", "medium", "high"],
        default="medium",
        help="Compression level",
    )
    parser.set_defaults(tool_name="compress", build_context=_build_context)


def _build_context(args) -> ConversionContext:
    return ConversionContext(
        input_path=args.input,
        output_path=args.output,
        config={"level": args.level},
    )
