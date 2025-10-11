# IntelliPDF

IntelliPDF is now organised as a small monorepo that bundles everything
required to build PDF-centric workflows:

- **`packages/intellipdf`** – the core Python toolkit that provides PDF
  splitting, merging, compression, and PDF→DOCX conversion utilities on top
  of [`pypdf`](https://pypi.org/project/pypdf/).
- **`apps/backend`** – a FastAPI service that exposes the library’s
  functionality over HTTP for automation or browser clients.
- **`apps/frontend`** – a Next.js dashboard that talks to the backend for a
  user-friendly experience.

The shared library remains a production-ready, well-typed, and well-tested
foundation for the services that sit on top of it.

## Features

- Split PDFs into page ranges or explicit page selections while preserving
  metadata.
- Extract specific pages into a standalone PDF document.
- Merge multiple PDFs, optionally optimising the result with `qpdf` when
  available.
- Compress PDFs using configurable optimisation backends and surface detailed
  compression metrics.
- Convert PDFs into lightweight DOCX documents that retain page ordering,
  paragraph structure, and semantic roles when working with tagged PDFs, while
  rebuilding PDF outlines as Word bookmarks and linked tables of contents.
- Flatten interactive form fields into readable DOCX tables with checkbox,
  dropdown, and signature placeholders.
- Validate documents and query document information before operating on them.

## Installation

```bash
pip install intellipdf
```

## Usage

```python
from pathlib import Path

from intellipdf import (
    compress_document,
    extract_document_pages,
    merge_documents,
    split_document,
    convert_document,
)

source = Path("document.pdf")
output_dir = Path("output")

# Split into ranges: pages 1-3 and 4-6.
parts = split_document(source, output_dir, mode="range", ranges="1-3,4-6")

# Extract individual pages to a single file.
extract_document_pages(source, [1, 4, 8], Path("highlights.pdf"))

# Merge multiple PDFs into one.
merge_documents([Path("a.pdf"), Path("b.pdf")], Path("combined.pdf"))

# Compress a document and inspect the resulting metrics.
result = compress_document(source, Path("compressed.pdf"))
print(result.compressed_size, result.backend)

# Convert the PDF into a DOCX file. The converter can accept either a path or
# the primitives returned by IntelliPDF's core parser.
conversion = convert_document(source, Path("document.docx"))
print(conversion.output_path, conversion.tagged_pdf)

# Using primitives that might come from a custom parser.
from intellipdf.pdf2docx import BoundingBox, Page, PdfDocument, TextBlock

page = Page(
    number=0,
    width=200,
    height=200,
    text_blocks=[
        TextBlock(text="Hello", bbox=BoundingBox(0, 0, 200, 20), role="P"),
    ],
    images=[],
    lines=[],
)
doc = PdfDocument(pages=[page], tagged=True)
convert_document(doc, Path("primitives.docx"))

# Streaming mode keeps memory usage predictable by processing PDF pages one at a
# time. Disable it via `ConversionOptions(stream_pages=False)` if you need to
# re-use intermediate page structures.
```

Set the environment variable `INTELLIPDF_SPLIT_OPTIMIZE=1` (or the more general
`INTELLIPDF_OPTIMIZE=1`) to enable optional `qpdf`-based optimisation after
splitting.

## Development

| Area      | How to get started |
|-----------|--------------------|
| Library   | `pip install -e packages/intellipdf[dev]` then `pytest` |
| Backend   | Follow the setup steps in `apps/backend/README.md` and run `uvicorn app.main:app --reload` |
| Frontend  | Follow `apps/frontend/README.md` and run `npm run dev` |

The repository root still includes a `pyproject.toml` so the library can be
installed with `pip install .` if required.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
