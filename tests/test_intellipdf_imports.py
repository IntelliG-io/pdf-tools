from importlib import reload


def test_pdf2docx_reexport_available():
    import intellipdf

    reload(intellipdf)

    assert hasattr(intellipdf, "pdf2docx"), "pdf2docx submodule should be accessible via intellipdf"

    from intellipdf import pdf2docx  # noqa: WPS433 - re-export check

    assert hasattr(pdf2docx, "convert_pdf_to_docx"), "pdf2docx module must expose convert_pdf_to_docx"


def test_converter_shim_imports():
    from intellipdf import convert_document, PdfToDocxConverter

    converter = PdfToDocxConverter()
    assert callable(convert_document)
    assert hasattr(converter, "convert")
