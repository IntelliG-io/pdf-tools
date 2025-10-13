"""Command line interface for the IntelliPDF toolkit."""

from __future__ import annotations

import argparse
from typing import Sequence

from ..tools import load_builtin_plugins
from ..tools.common.interfaces import ConversionContext
from ..tools.common.pipeline import registry
from .commands import compress, convert, encrypt, merge, split

COMMAND_MODULES = [split, merge, compress, convert, encrypt]


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intellipdf", description="IntelliPDF CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    for module in COMMAND_MODULES:
        module.configure_parser(subparsers)
    return parser


def _resolve_tool_name(args, context: ConversionContext) -> str:
    tool_name = getattr(args, "tool_name", None)
    if tool_name:
        return tool_name
    if "tool_name" in context.resources:
        return context.resources["tool_name"]
    resolver = getattr(args, "tool_name_resolver", None)
    if resolver is not None:
        key = getattr(args, "format", None)
        if key is None:
            key = getattr(args, "mode", None)
        if key is not None:
            return resolver(key)
    raise SystemExit("Unable to determine tool name from arguments")


def main(argv: Sequence[str] | None = None) -> object:
    load_builtin_plugins()
    parser = _create_parser()
    args = parser.parse_args(argv)
    context: ConversionContext = args.build_context(args)
    tool_name = _resolve_tool_name(args, context)
    tool = registry.create(tool_name, context)
    result = tool.run()
    return result


if __name__ == "__main__":  # pragma: no cover
    main()
