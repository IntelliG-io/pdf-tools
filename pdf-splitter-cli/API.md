# PDF Splitter - Library API Documentation

## Overview

PDF Splitter provides a clean, intuitive Python API for programmatic PDF manipulation. This document covers the library usage (not CLI).

## Installation

```bash
pip install pdf-splitter-cli
```

## Quick Start

```python
from pdf_splitter import PDFSplitter

# Initialize with PDF file
splitter = PDFSplitter('document.pdf')

# Split into individual pages
files = splitter.split_to_pages('output/')

# Extract specific pages
output = splitter.extract_pages('1,3,5,7-10', 'selected.pdf')

# Split into chunks
chunks = splitter.split_by_chunks(5, 'chunks/')
```

## API Reference

### Main Classes

#### PDFSplitter

Main class for all PDF splitting operations.

**Import:**
```python
from pdf_splitter import PDFSplitter
```

**Constructor:**
```python
PDFSplitter(input_path: str)
```

**Parameters:**
- `input_path` (str): Path to input PDF file

**Raises:**
- `FileNotFoundError`: If PDF file doesn't exist
- `ValueError`: If PDF is encrypted or invalid
- `PdfReadError`: If PDF is corrupted

**Example:**
```python
splitter = PDFSplitter('document.pdf')
print(f"PDF has {splitter.num_pages} pages")
```

---

#### Methods

##### split_to_pages()

Split PDF into individual pages.

```python
split_to_pages(
    output_dir: str,
    prefix: str = "page",
    padding: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[str]
```

**Parameters:**
- `output_dir` (str): Directory for output files
- `prefix` (str): Prefix for output filenames (default: "page")
- `padding` (int): Number of digits for page numbering (default: 3)
- `progress_callback` (callable, optional): Callback function(current, total)

**Returns:**
- `List[str]`: List of created file paths

**Example:**
```python
splitter = PDFSplitter('document.pdf')
files = splitter.split_to_pages('output/', prefix='page', padding=3)
print(f"Created {len(files)} files")
```

---

##### split_by_range()

Extract a range of pages into a single PDF.

```python
split_by_range(
    output_dir: str,
    start_page: int,
    end_page: int,
    output_filename: str = None
) -> str
```

**Parameters:**
- `output_dir` (str): Directory for output file
- `start_page` (int): Starting page number (1-indexed)
- `end_page` (int): Ending page number (1-indexed, inclusive)
- `output_filename` (str, optional): Custom output filename

**Returns:**
- `str`: Path to created file

**Example:**
```python
splitter = PDFSplitter('document.pdf')
output = splitter.split_by_range('output/', 1, 10, 'first_10_pages.pdf')
```

---

##### split_by_ranges()

Split PDF into specified page ranges.

```python
split_by_ranges(
    ranges: Union[str, List[Tuple[int, int]]],
    output_dir: str,
    prefix: str = "range",
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[str]
```

**Parameters:**
- `ranges` (str or list): Page ranges as string '1-5,6-10' or list [(1,5), (6,10)]
- `output_dir` (str): Output directory for files
- `prefix` (str): Prefix for output filenames (default: "range")
- `progress_callback` (callable, optional): Callback function(current, total)

**Returns:**
- `List[str]`: List of created file paths

**Example:**
```python
splitter = PDFSplitter('document.pdf')
files = splitter.split_by_ranges('1-10,11-20,21-30', 'output/')
```

---

##### split_by_chunks()

Split PDF into equal-sized chunks.

```python
split_by_chunks(
    chunk_size: int,
    output_dir: str,
    prefix: str = "chunk",
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[str]
```

**Parameters:**
- `chunk_size` (int): Number of pages per chunk
- `output_dir` (str): Output directory for files
- `prefix` (str): Prefix for output filenames (default: "chunk")
- `progress_callback` (callable, optional): Callback function(current, total)

**Returns:**
- `List[str]`: List of created file paths

**Raises:**
- `ValueError`: If chunk_size is invalid

**Example:**
```python
splitter = PDFSplitter('document.pdf')
chunks = splitter.split_by_chunks(5, 'chunks/')
print(f"Created {len(chunks)} chunks")
```

---

##### extract_pages()

Extract specific pages into a single new PDF.

```python
extract_pages(
    pages: Union[str, List[int]],
    output_path: str
) -> str
```

**Parameters:**
- `pages` (str or list): Pages to extract as string '1,3,5,7-10' or list [1,3,5,7,8,9,10]
- `output_path` (str): Output PDF file path

**Returns:**
- `str`: Path to created PDF file

**Raises:**
- `ValueError`: If page specification is invalid or pages out of bounds

**Example:**
```python
splitter = PDFSplitter('document.pdf')
output = splitter.extract_pages('1,3,5,7-10', 'selected.pdf')
```

---

##### get_page_count()

Get the total number of pages in the PDF.

```python
get_page_count() -> int
```

**Returns:**
- `int`: Number of pages

**Example:**
```python
splitter = PDFSplitter('document.pdf')
count = splitter.get_page_count()
print(f"PDF has {count} pages")
```

---

### BatchProcessor

Process multiple PDF files at once.

**Import:**
```python
from pdf_splitter import BatchProcessor
```

**Constructor:**
```python
BatchProcessor()
```

**Example:**
```python
processor = BatchProcessor()
results = processor.process_directory(
    './pdfs',
    'pages',
    './output',
    options={'prefix': 'page'}
)
print(f"Processed {results['success']} files successfully")
```

---

#### Methods

##### find_pdf_files()

Find all PDF files in a directory.

```python
find_pdf_files(input_dir: str) -> List[str]
```

**Parameters:**
- `input_dir` (str): Directory to search for PDFs

**Returns:**
- `List[str]`: List of PDF file paths

**Raises:**
- `FileNotFoundError`: If directory doesn't exist
- `ValueError`: If path is not a directory

---

##### process_directory()

Process all PDF files in a directory.

```python
process_directory(
    input_dir: str,
    operation: str,
    output_dir: str,
    options: dict = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> dict
```

**Parameters:**
- `input_dir` (str): Directory containing PDF files
- `operation` (str): Operation to perform ('pages', 'chunks', 'ranges', 'extract')
- `output_dir` (str): Base output directory
- `options` (dict, optional): Operation-specific options
- `progress_callback` (callable, optional): Callback function(filename, current, total)

**Returns:**
- `dict`: Results dictionary with keys:
  - `total` (int): Total files processed
  - `success` (int): Successfully processed files
  - `failure` (int): Failed files
  - `results` (list): Detailed results for each file

**Example:**
```python
processor = BatchProcessor()
results = processor.process_directory(
    './pdfs',
    'chunks',
    './output',
    options={'chunk_size': 5}
)

print(f"Total: {results['total']}")
print(f"Success: {results['success']}")
print(f"Failed: {results['failure']}")
```

---

### Utility Functions

#### get_pdf_info()

Extract basic PDF information.

**Import:**
```python
from pdf_splitter import get_pdf_info
```

**Signature:**
```python
get_pdf_info(pdf_path: str) -> Dict
```

**Parameters:**
- `pdf_path` (str): Path to PDF file

**Returns:**
- `dict`: Dictionary containing:
  - `num_pages` (int): Number of pages
  - `file_size` (int): File size in bytes
  - `title` (str or None): PDF title
  - `author` (str or None): PDF author
  - `subject` (str or None): PDF subject
  - `creator` (str or None): PDF creator
  - `producer` (str or None): PDF producer
  - `is_encrypted` (bool): Whether PDF is encrypted

**Example:**
```python
from pdf_splitter import get_pdf_info

info = get_pdf_info('document.pdf')
print(f"Pages: {info['num_pages']}")
print(f"Title: {info['title']}")
print(f"Author: {info['author']}")
```

---

#### validate_pdf()

Check if file is a valid PDF.

**Import:**
```python
from pdf_splitter import validate_pdf
```

**Signature:**
```python
validate_pdf(pdf_path: str) -> Tuple[bool, str]
```

**Parameters:**
- `pdf_path` (str): Path to PDF file

**Returns:**
- `tuple`: (is_valid, error_message)
  - `is_valid` (bool): True if PDF is valid
  - `error_message` (str): Empty if valid, error description if invalid

**Example:**
```python
from pdf_splitter import validate_pdf

is_valid, error = validate_pdf('document.pdf')
if is_valid:
    print("PDF is valid")
else:
    print(f"Invalid PDF: {error}")
```

---

#### format_file_size()

Format file size in human-readable format.

**Import:**
```python
from pdf_splitter import format_file_size
```

**Signature:**
```python
format_file_size(size_bytes: int) -> str
```

**Parameters:**
- `size_bytes` (int): File size in bytes

**Returns:**
- `str`: Formatted string (e.g., "1.5 MB", "500 KB")

**Example:**
```python
from pdf_splitter import format_file_size

size = format_file_size(1536000)
print(size)  # "1.5 MB"
```

---

## Complete Examples

### Example 1: Split Large PDF into Chunks

```python
from pdf_splitter import PDFSplitter

# Initialize splitter
splitter = PDFSplitter('large_document.pdf')

# Split into chunks of 10 pages
chunks = splitter.split_by_chunks(10, 'chunks/', prefix='section')

print(f"Created {len(chunks)} chunks:")
for chunk in chunks:
    print(f"  - {chunk}")
```

### Example 2: Extract Specific Sections

```python
from pdf_splitter import PDFSplitter

splitter = PDFSplitter('book.pdf')

# Extract table of contents (pages 1-5)
toc = splitter.split_by_range('output/', 1, 5, 'toc.pdf')

# Extract chapters
chapters = splitter.split_by_ranges('6-25,26-50,51-75', 'chapters/', prefix='chapter')

print(f"Extracted TOC: {toc}")
print(f"Extracted {len(chapters)} chapters")
```

### Example 3: Batch Processing with Progress

```python
from pdf_splitter import BatchProcessor

def progress_callback(filename, current, total):
    print(f"Processing {filename} ({current}/{total})")

processor = BatchProcessor()
results = processor.process_directory(
    './documents',
    'pages',
    './output',
    options={'prefix': 'page', 'padding': 3},
    progress_callback=progress_callback
)

print(f"\nProcessing complete!")
print(f"Success: {results['success']}/{results['total']}")
```

### Example 4: Error Handling

```python
from pdf_splitter import PDFSplitter, validate_pdf

# Validate before processing
is_valid, error = validate_pdf('document.pdf')
if not is_valid:
    print(f"Invalid PDF: {error}")
    exit(1)

try:
    splitter = PDFSplitter('document.pdf')
    files = splitter.split_to_pages('output/')
    print(f"Successfully created {len(files)} files")
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Example 5: Get PDF Information

```python
from pdf_splitter import get_pdf_info, format_file_size

info = get_pdf_info('document.pdf')

print(f"PDF Information:")
print(f"  Title: {info['title'] or 'N/A'}")
print(f"  Author: {info['author'] or 'N/A'}")
print(f"  Pages: {info['num_pages']}")
print(f"  Size: {format_file_size(info['file_size'])}")
print(f"  Encrypted: {info['is_encrypted']}")
```

---

## Type Hints

All public APIs include type hints for IDE support:

```python
from typing import List, Tuple, Union, Optional, Callable, Dict

def split_to_pages(
    self,
    output_dir: str,
    prefix: str = "page",
    padding: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[str]:
    ...
```

---

## Error Handling

### Common Exceptions

- **FileNotFoundError**: PDF file doesn't exist
- **ValueError**: Invalid parameters or encrypted PDF
- **PdfReadError**: Corrupted or invalid PDF
- **OSError**: Disk full or permission denied
- **RuntimeError**: Unexpected errors

### Best Practices

```python
from pdf_splitter import PDFSplitter, validate_pdf

# Always validate first
is_valid, error = validate_pdf('document.pdf')
if not is_valid:
    print(f"Invalid PDF: {error}")
    exit(1)

# Use try-except for operations
try:
    splitter = PDFSplitter('document.pdf')
    files = splitter.split_to_pages('output/')
except ValueError as e:
    print(f"Validation error: {e}")
except OSError as e:
    print(f"File system error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Version Information

```python
import pdf_splitter

print(pdf_splitter.__version__)  # "1.0.0"
print(pdf_splitter.__author__)   # "PDF Splitter CLI Contributors"
print(pdf_splitter.__license__)  # "MIT"
```

---

## See Also

- [README.md](README.md) - Project overview and CLI usage
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines

---

**Version**: 1.0.0  
**License**: MIT  
**Python**: 3.7+
