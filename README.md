# pdfsplitx

`pdfsplitx` is a lightweight, production-ready Python library for splitting and
extracting PDF pages. It is designed for embedding into other projects that
need straightforward, well-typed utilities on top of
[`pypdf`](https://pypi.org/project/pypdf/).

## Features

- Split PDFs using inclusive page ranges (`1-3,5,7-9`) or explicit page lists.
- Extract selected pages into a new PDF while preserving document metadata.
- Validate PDFs before processing and inspect document information.
- Optional post-processing using [`qpdf`](https://qpdf.sourceforge.io/) when
  available by setting `PDFSPLITX_OPTIMIZE=1`.
- Fully typed, well-tested codebase ready for redistribution.

## Installation

```bash
pip install pdfsplitx
```

## Usage

```python
from pathlib import Path

from pdfsplitx import extract_pages, get_pdf_info, split_pdf, validate_pdf

source = Path("document.pdf")
validate_pdf(source)

# Split into two ranges: pages 1-3 and 4-6.
parts = split_pdf(source, Path("output"), mode="range", ranges="1-3,4-6")

# Extract specific pages to a single file.
extract_pages(source, [1, 4, 8], Path("highlights.pdf"))

# Inspect metadata and page count.
info = get_pdf_info(source)
print(info["pages"], info["metadata"].get("/Title"))
```

## Development

```bash
pip install -e .[dev]
pytest
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
