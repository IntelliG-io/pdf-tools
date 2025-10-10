# pdf2docxplus

`pdf2docxplus` is a production-ready Python library that delivers high-fidelity
conversion of PDF documents into editable DOCX files. It builds on the powerful
[`pdf2docx`](https://github.com/dothinking/pdf2docx) conversion engine while
adding first-class metadata preservation, formatting normalization, and robust
validation so that resulting Word documents are immediately usable in business
workflows.

## Features

- **Layout fidelity** – preserves paragraphs, tables, multi-column layouts,
  vector graphics, and inline images with pixel-perfect placement.
- **Metadata round-trip** – extracts title, author, subject, keywords, creator,
  producer, creation date, modification date, and custom properties from the
  source PDF and embeds them into the DOCX output.
- **Font and style preservation** – recreates paragraph styles, font families,
  emphasis, alignment, and indentation using the Python `python-docx` API.
- **Image & chart pipeline** – leverages `pdf2docx` to extract raster images at
  original DPI, re-encodes vector diagrams using EMF when available, and falls
  back to high-resolution bitmap rendering.
- **Resilient processing** – detailed logging, validation hooks, and graceful
  fallbacks for non-standard PDFs ensure consistent outcomes.
- **Typed API** – minimal top-level function
  `convert_pdf_to_docx(input_path, output_path, preserve_formatting=True,
  include_metadata=True)` for easy adoption.

## Installation

```bash
pip install pdf2docxplus
```

For development work install the optional dependencies:

```bash
pip install pdf2docxplus[dev]
```

## Usage

```python
from pdf2docxplus import convert_pdf_to_docx

convert_pdf_to_docx("sample.pdf", "sample.docx")
```

Advanced usage with logging and metadata handling:

```python
import logging
from pdf2docxplus import convert_pdf_to_docx
from pdf2docxplus.utils import configure_logging

configure_logging()
convert_pdf_to_docx(
    "brochure.pdf",
    "brochure.docx",
    preserve_formatting=True,
    include_metadata=True,
)
```

## Quality Assurance

- Unit tests with Pytest validate metadata fidelity, conversion pipeline
  orchestration, and utility helpers.
- Conversion validation ensures generated DOCX files are readable and contain
  expected metadata.
- CI workflow (GitHub Actions) runs linting and test suites against supported
  Python versions.

## Limitations

- Extremely complex vector graphics may require manual post-processing.
- Password-protected PDFs are not currently supported.

## License

MIT License
