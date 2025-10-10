# pdfmergex

`pdfmergex` is a lightweight Python library that provides reusable tools for
merging, validating, and optimising PDF documents. It is designed for embedding
in larger projects and focuses on a small, well-typed API.

## Features

- Merge multiple PDFs while preserving metadata using `pypdf`
- Validate PDFs and collect document information
- Optimise PDFs using `qpdf` when available (falls back to copying)
- Fully typed and extensively tested with `pytest`

## Installation

```bash
pip install pdfmergex
```

## Usage

```python
from pdfmergex import merge_pdfs, optimize_pdf, validate_pdf, get_pdf_info

merge_pdfs(["input1.pdf", "input2.pdf"], "merged.pdf")
info = get_pdf_info("merged.pdf")
print(info.num_pages)

if validate_pdf("merged.pdf"):
    optimize_pdf("merged.pdf", "merged.optimized.pdf")
```

## Development

Install development dependencies and run tests:

```bash
pip install -e .[dev]
pytest --cov=pdfmergex
flake8 pdfmergex
```

## License

MIT License. See [LICENSE](LICENSE) for details.
