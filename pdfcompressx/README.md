# pdfcompressx

`pdfcompressx` is a production-ready Python library for compressing and optimising PDF
files. It combines a rich Python API powered by [`pypdf`](https://pypdf.readthedocs.io)
with best-effort integration of external optimisers such as `qpdf` and Ghostscript. The
library focuses on safe, metadata-preserving compression that fits neatly into any
automation workflow.

## Features

- 🔧 **Configurable compression levels** (`low`, `medium`, `high`) that control
  stream recompression and image downsampling.
- 🧠 **Smart backend selection** that uses `qpdf` or Ghostscript when available and
  gracefully falls back to pure Python processing.
- 🧾 **Metadata preservation** and optional post-compression validation.
- 📊 **Compression insights** exposing file metrics and heuristic savings estimates.
- 🧪 **Full test coverage** with pytest and structured logging for observability.

## Installation

```bash
pip install pdfcompressx
```

To enable high quality image downsampling install the optional Pillow dependency:

```bash
pip install pdfcompressx[images]
```

## Usage

```python
from pdfcompressx import compress_pdf, get_compression_info, validate_pdf

result = compress_pdf("input.pdf", "output.pdf", level="medium", post_validate=True)
print(f"Compressed to {result.compressed_size} bytes using {result.backend}")

info = get_compression_info("output.pdf")
print(f"Images: {info.image_count} | Estimated savings: {info.potential_savings_bytes} bytes")

validate_pdf("output.pdf")
```

### Public API

- `compress_pdf(input_path, output_path, level="medium", post_validate=False)`
- `get_compression_info(path)`
- `validate_pdf(path, use_external=True)`

Each function is fully type annotated and documented for use in static analysis
workflows. `CompressionResult` and `CompressionInfo` dataclasses expose detailed state
about the operation.

## Compression benchmarks

The table below provides indicative results from compressing sample 20-page PDF
brochures containing mixed text and imagery (initial size: 12.4 MiB) on a standard
workstation. Exact numbers vary depending on content and available backends.

| Level  | Backend     | Output Size | Size Reduction |
| ------ | ----------- | ----------- | -------------- |
| low    | pypdf       | 10.9 MiB    | 12%            |
| medium | qpdf        | 7.4 MiB     | 40%            |
| high   | Ghostscript | 4.1 MiB     | 67%            |

## Development

Clone the repository and install development dependencies:

```bash
pip install -e .[dev]
```

Run the test-suite with coverage:

```bash
pytest --cov=pdfcompressx
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
