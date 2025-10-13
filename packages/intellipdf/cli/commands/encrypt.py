"""CLI helpers for PDF encryption and decryption."""

from __future__ import annotations

from argparse import ArgumentParser, _SubParsersAction

from ...tools.common.interfaces import ConversionContext


MODES = {
    "encrypt": "encrypt",
    "decrypt": "decrypt",
}


def configure_parser(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    parser = subparsers.add_parser("encrypt", help="Encrypt or decrypt a PDF")
    parser.add_argument("input", help="Input PDF path")
    parser.add_argument("output", help="Destination PDF path")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--owner-password", help="Owner password for encryption")
    parser.add_argument(
        "--mode",
        choices=sorted(MODES.keys()),
        default="encrypt",
        help="Operation to perform",
    )
    parser.set_defaults(build_context=_build_context, tool_name_resolver=_resolve_tool_name)


def _resolve_tool_name(mode: str) -> str:
    return MODES[mode]


def _build_context(args) -> ConversionContext:
    context = ConversionContext(
        input_path=args.input,
        output_path=args.output,
        config={
            "password": args.password,
            "owner_password": args.owner_password,
            "mode": args.mode,
        },
    )
    context.resources["tool_name"] = _resolve_tool_name(args.mode)
    return context
