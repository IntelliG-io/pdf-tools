"""CLI helpers for merging PDFs."""

from __future__ import annotations

from argparse import ArgumentParser, _SubParsersAction

from ...tools.common.interfaces import ConversionContext


def configure_parser(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("merge", help="Merge multiple PDFs into one")
    parser.add_argument("inputs", nargs="+", help="Input PDF files")
    parser.add_argument("output", help="Output PDF path")
    parser.add_argument(
        "--bookmark",
        dest="bookmarks",
        action="append",
        help="Add bookmark titles matching each input",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Do not copy metadata from the first document",
    )
    parser.set_defaults(tool_name="merge", build_context=_build_context)


def _build_context(args) -> ConversionContext:
    return ConversionContext(
        output_path=args.output,
        config={
            "inputs": args.inputs,
            "bookmarks": args.bookmarks,
            "metadata": not args.no_metadata,
        },
    )
