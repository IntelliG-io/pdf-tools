"""Plugin exposing PDF encryption utilities."""

from __future__ import annotations

from ...core.utils import get_logger
from ...security import PdfSecurityError, protect_pdf, unprotect_pdf
from ..common.interfaces import BaseTool
from ..common.pipeline import register_tool

LOGGER = get_logger("intellipdf.tools.encrypt")


@register_tool("encrypt")
class EncryptTool(BaseTool):
    name = "encrypt"

    def run(self) -> Path:
        context = self.context
        if context.input_path is None or context.output_path is None:
            raise PdfSecurityError("Encryption requires input and output paths")

        password = context.config.get("password")
        owner_password = context.config.get("owner_password")
        if not password:
            raise PdfSecurityError("A password is required for encryption")

        LOGGER.debug(
            "Encrypting %s to %s with owner password %s",
            context.input_path,
            context.output_path,
            "<provided>" if owner_password else "<default>",
        )
        result = protect_pdf(
            context.input_path,
            context.output_path,
            password,
            owner_password=owner_password,
        )
        context.resources["result"] = result
        return result


@register_tool("decrypt")
class DecryptTool(BaseTool):
    name = "decrypt"

    def run(self) -> Path:
        context = self.context
        if context.input_path is None or context.output_path is None:
            raise PdfSecurityError("Decryption requires input and output paths")

        password = context.config.get("password")
        if not password:
            raise PdfSecurityError("A password is required for decryption")

        LOGGER.debug(
            "Decrypting %s to %s",
            context.input_path,
            context.output_path,
        )
        result = unprotect_pdf(context.input_path, context.output_path, password)
        context.resources["result"] = result
        return result
