from __future__ import annotations

from pathlib import Path

from intellipdf.tools import load_builtin_plugins
from intellipdf.tools.common.interfaces import ConversionContext
from intellipdf.tools.common.pipeline import registry


def setup_module(module):
    load_builtin_plugins()


def test_encrypt_and_decrypt(sample_pdf: Path, tmp_path: Path) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    decrypted = tmp_path / "decrypted.pdf"

    encrypt_context = ConversionContext(
        input_path=sample_pdf,
        output_path=encrypted,
        config={"password": "secret"},
    )
    encrypt_tool = registry.create("encrypt", encrypt_context)
    encrypt_tool.run()
    assert encrypted.exists()

    decrypt_context = ConversionContext(
        input_path=encrypted,
        output_path=decrypted,
        config={"password": "secret"},
    )
    decrypt_tool = registry.create("decrypt", decrypt_context)
    decrypt_tool.run()
    assert decrypted.exists()
