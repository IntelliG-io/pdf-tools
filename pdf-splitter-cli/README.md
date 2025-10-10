# PDF Splitter CLI

A powerful command-line tool to split PDF files into individual pages or extract specific page ranges. Built with Python, pypdf, Click, and Rich for a beautiful terminal experience.

## Features

- ✅ **Split PDF into individual pages** - Extract each page as a separate PDF file
- ✅ **Extract single page range** - Create a new PDF from a specific range of pages
- ✅ **Split by multiple ranges** - Split PDF into multiple files based on custom page ranges
- ✅ **Split into equal chunks** - Split PDF into chunks of N pages each
- ✅ **Extract specific pages** - Extract selected pages into a single PDF
- ✅ **Batch processing** - Process multiple PDF files at once from a directory
- ✅ **Metadata preservation** - Maintains original PDF metadata (title, author, subject, etc.) in split files
- ✅ **PDF information display** - View detailed metadata about PDF files
- ✅ **Custom naming** - Configure output filenames with custom prefixes and padding
- ✅ **Beautiful CLI** - Rich terminal output with **real-time progress bars** and tables
- ✅ **Progress tracking** - Visual progress bars showing completion percentage and time remaining
- ✅ **Comprehensive error handling** - Validates PDFs and provides clear error messages
- ✅ **Well-tested** - 72 tests (61 unit + 11 integration) with 84% code coverage

## Installation

### Prerequisites

- Python 3.7 or higher
- pip

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd pdf-splitter-cli
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package:**
   ```bash
   pip install -e .
   ```

## Usage

### Command Overview

```bash
pdf-splitter --help
```

Available commands:
- `split-pages` - Split PDF into individual pages
- `split-range` - Extract a single range of pages
- `split-ranges` - Split PDF into multiple custom ranges
- `split-chunks` - Split PDF into equal-sized chunks
- `extract` - Extract specific pages into single PDF
- `batch` - Process multiple PDFs at once
- `info` - Display PDF information

### 1. Split PDF into Individual Pages

Split a PDF file into separate files, one per page:

```bash
pdf-splitter split-pages input.pdf
```

**Options:**
- `-o, --output-dir` - Output directory (default: `./output`)
- `-p, --prefix` - Filename prefix (default: `page`)
- `--padding` - Number of digits for page numbering (default: 3)

**Examples:**

```bash
# Basic usage - creates page_001.pdf, page_002.pdf, etc.
pdf-splitter split-pages document.pdf

# Custom output directory
pdf-splitter split-pages document.pdf -o my_pages

# Custom prefix and padding
pdf-splitter split-pages document.pdf -p chapter --padding 2
# Creates: chapter_01.pdf, chapter_02.pdf, etc.
```

**Output:**
```
Validating PDF...
      PDF Information       
┌───────┬──────────────────┐
│ File  │ document.pdf     │
│ Pages │ 10               │
│ Size  │ 1.5 KB           │
└───────┴──────────────────┘

✓ Successfully split into 10 files
Output directory: /path/to/output

Created files:
  • page_001.pdf
  • page_002.pdf
  • page_003.pdf
  ...
```

### 2. Extract Page Range

Extract a specific range of pages into a single PDF:

```bash
pdf-splitter split-range input.pdf --start 5 --end 10
```

**Options:**
- `-s, --start` - Starting page number (1-indexed, required)
- `-e, --end` - Ending page number (1-indexed, inclusive, required)
- `-o, --output-dir` - Output directory (default: `./output`)
- `-n, --output-name` - Custom output filename (optional)

**Examples:**

```bash
# Extract pages 5-10
pdf-splitter split-range document.pdf -s 5 -e 10

# Custom output name
pdf-splitter split-range document.pdf -s 1 -e 3 -n intro.pdf

# Custom output directory
pdf-splitter split-range document.pdf -s 5 -e 10 -o extracted
```

### 3. Split PDF by Multiple Ranges

Split a PDF into multiple files based on custom page ranges:

```bash
pdf-splitter split-ranges input.pdf --ranges '1-5,6-10,11-15'
```

**Options:**
- `-r, --ranges` - Page ranges as comma-separated values (required)
- `-o, --output-dir` - Output directory (default: `./output`)
- `-p, --prefix` - Filename prefix (default: `range`)

**Examples:**

```bash
# Split into 3 sections
pdf-splitter split-ranges document.pdf -r '1-10,11-20,21-30'
# Creates: range_1-10.pdf, range_11-20.pdf, range_21-30.pdf

# Custom prefix
pdf-splitter split-ranges document.pdf -r '1-5,6-10' -p chapter
# Creates: chapter_1-5.pdf, chapter_6-10.pdf

# Custom output directory
pdf-splitter split-ranges document.pdf -r '1-3,7-9,12-20' -o chapters
```

**Output:**
```
Validating PDF...
   PDF Information    
┌───────┬────────────┐
│ File  │ document.pdf│
│ Pages │ 34         │
│ Size  │ 1.1 MB     │
└───────┴────────────┘

Parsing ranges...
Ranges to extract: 1-10, 11-20, 21-34

✓ Successfully created 3 file(s)

Created files:
  • range_1-10.pdf
  • range_11-20.pdf
  • range_21-34.pdf
```

**Range Validation:**
- Ranges must be within PDF bounds
- No overlapping ranges allowed
- Format: `start-end` (e.g., `1-5`)
- Page numbers are 1-indexed

### 4. Split PDF into Equal Chunks

Split a PDF into chunks of N pages each:

```bash
pdf-splitter split-chunks input.pdf --size 5
```

**Options:**
- `-s, --size` - Number of pages per chunk (required)
- `-o, --output-dir` - Output directory (default: `./output`)
- `-p, --prefix` - Filename prefix (default: `chunk`)

**Examples:**

```bash
# Split into chunks of 5 pages
pdf-splitter split-chunks document.pdf -s 5
# 23-page PDF → 5 chunks: chunk_001.pdf (5), chunk_002.pdf (5), ..., chunk_005.pdf (3)

# Custom output directory
pdf-splitter split-chunks document.pdf --size 10 -o chunks

# Custom prefix
pdf-splitter split-chunks document.pdf -s 5 -p section
# Creates: section_001.pdf, section_002.pdf, etc.
```

**Output:**
```
Validating PDF...
         PDF Information         
┌────────────┬──────────────────┐
│ File       │ document.pdf     │
│ Pages      │ 23               │
│ Size       │ 3.0 KB           │
│ Chunk Size │ 5 pages          │
│ Chunks     │ 5                │
└────────────┴──────────────────┘

✓ Successfully created 5 chunk(s)

Created files:
  • chunk_001.pdf (pages 1-5, 5 pages)
  • chunk_002.pdf (pages 6-10, 5 pages)
  • chunk_003.pdf (pages 11-15, 5 pages)
  • chunk_004.pdf (pages 16-20, 5 pages)
  • chunk_005.pdf (pages 21-23, 3 pages)
```

**Use Cases:**
- Split large PDFs for easier handling
- Create equal-sized batches for processing
- Distribute PDF content evenly

### 5. Extract Specific Pages

Extract selected pages into a single new PDF:

```bash
pdf-splitter extract input.pdf --pages '1,3,5,7-10' --output selected.pdf
```

**Options:**
- `-p, --pages` - Pages to extract (required, e.g., `'1,3,5,7-10'`)
- `-o, --output` - Output PDF path (required)

**Page Specification Format:**
- Individual pages: `'1,3,5'`
- Ranges: `'7-10'`
- Mixed: `'1,3,5,7-10'`
- Duplicates are automatically removed
- Pages are sorted in ascending order

**Examples:**

```bash
# Extract specific pages
pdf-splitter extract document.pdf -p '1,3,5' -o selected.pdf

# Extract ranges and individual pages
pdf-splitter extract document.pdf --pages '1-5,10,15-20' --output extracted.pdf

# Extract even pages
pdf-splitter extract document.pdf -p '2,4,6,8-12' -o even_pages.pdf
```

**Output:**
```
Validating PDF...
      PDF Information       
┌─────────────┬────────────┐
│ File        │ document.pdf│
│ Total Pages │ 34         │
│ Size        │ 1.1 MB     │
└─────────────┴────────────┘

Parsing page specification...
Pages to extract: 1, 3, 5, 7, 8, 9, 10
Total pages to extract: 7

✓ Successfully created: selected.pdf
Output size: 933.2 KB
Pages extracted: 7 of 34
```

**Use Cases:**
- Extract specific chapters or sections
- Create custom document subsets
- Remove unwanted pages
- Combine non-contiguous pages

### 6. Batch Processing

Process multiple PDF files at once from a directory:

```bash
pdf-splitter batch INPUT_DIR --operation OPERATION [OPTIONS]
```

**Options:**
- `-op, --operation` - Operation to perform: `pages`, `chunks`, or `ranges` (required)
- `-o, --output-dir` - Base output directory (default: `./batch_output`)
- `-s, --size` - Chunk size (required for `chunks` operation)
- `-r, --ranges` - Page ranges (required for `ranges` operation)
- `-p, --prefix` - Prefix for output filenames
- `--padding` - Number of digits for page numbering (for `pages` operation)

**Examples:**

```bash
# Split all PDFs in a directory into individual pages
pdf-splitter batch ./pdfs --operation pages

# Split all PDFs into chunks of 5 pages
pdf-splitter batch ./docs --operation chunks --size 5

# Apply custom ranges to all PDFs
pdf-splitter batch ./files --operation ranges -r '1-5,6-10'
```

**Output:**
```
Initializing batch processor...
Scanning directory: batch_test_pdfs
✓ Found 5 PDF file(s)

 Files to Process  
┏━━━━━━┳━━━━━━━━━━┓
┃ #    ┃ Filename ┃
┡━━━━━━╇━━━━━━━━━━┩
│ 1    │ doc1.pdf │
│ 2    │ doc2.pdf │
│ 3    │ doc3.pdf │
│ 4    │ doc4.pdf │
│ 5    │ doc5.pdf │
└──────┴──────────┘

Processing 5 PDF(s) with operation: pages
Processing: doc5 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00

Batch Processing Summary
==================================================
┌──────────────────┬────────────────────────────┐
│ Total Files      │ 5                          │
│ ✓ Successful     │ 5                          │
│ ✗ Failed         │ 0                          │
│ Output Directory │ ./batch_output             │
└──────────────────┴────────────────────────────┘

Successfully Processed:
  ✓ doc1.pdf → 5 file(s)
  ✓ doc2.pdf → 8 file(s)
  ✓ doc3.pdf → 10 file(s)
  ✓ doc4.pdf → 3 file(s)
  ✓ doc5.pdf → 12 file(s)
```

**Use Cases:**
- Process entire directories of PDFs
- Apply same operation to multiple files
- Automated document processing workflows
- Bulk PDF manipulation

### 7. Display PDF Information

View detailed information about a PDF file:

```bash
pdf-splitter info document.pdf
```

**Output:**
```
              PDF Information: document.pdf              
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property        ┃ Value                                   ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ File Path       │ /path/to/document.pdf                   │
│ File Size       │ 1.5 KB                                  │
│ Number of Pages │ 10                                      │
│ Encrypted       │ No                                      │
│ Title           │ My Document                             │
│ Author          │ John Doe                                │
│ Producer        │ pypdf                                   │
└─────────────────┴─────────────────────────────────────────┘
```

## Python API

You can also use the PDF splitter programmatically:

```python
from pdf_splitter import PDFSplitter, get_pdf_info, validate_pdf

# Validate a PDF
is_valid, error_msg = validate_pdf("input.pdf")
if not is_valid:
    print(f"Invalid PDF: {error_msg}")

# Get PDF information
info = get_pdf_info("input.pdf")
print(f"Pages: {info['num_pages']}")
print(f"Size: {info['file_size']} bytes")

# Split PDF into pages
splitter = PDFSplitter("input.pdf")
created_files = splitter.split_to_pages(
    output_dir="output",
    prefix="page",
    padding=3
)
print(f"Created {len(created_files)} files")

# Extract single page range
output_file = splitter.split_by_range(
    output_dir="output",
    start_page=5,
    end_page=10,
    output_filename="pages_5-10.pdf"
)
print(f"Created: {output_file}")

# Split by multiple ranges
created_files = splitter.split_by_ranges(
    ranges="1-5,6-10,11-15",  # or [(1,5), (6,10), (11,15)]
    output_dir="output",
    prefix="section"
)
print(f"Created {len(created_files)} range files")

# Split into equal chunks
created_files = splitter.split_by_chunks(
    chunk_size=5,
    output_dir="output",
    prefix="chunk"
)
print(f"Created {len(created_files)} chunks")

# Extract specific pages
output_file = splitter.extract_pages(
    pages="1,3,5,7-10",  # or [1, 3, 5, 7, 8, 9, 10]
    output_path="selected.pdf"
)
print(f"Extracted pages to: {output_file}")
```

## Project Structure

```
pdf-splitter-cli/
├── pdf_splitter/
│   ├── __init__.py       # Package initialization
│   ├── cli.py            # Command-line interface
│   ├── splitter.py       # Core PDF splitting logic
│   └── utils.py          # Utility functions
├── tests/
│   ├── __init__.py
│   └── test_splitter.py  # Unit tests
├── requirements.txt      # Dependencies
├── setup.py             # Package setup
└── README.md            # This file
```

## Dependencies

- **pypdf** (>=3.0.0) - PDF manipulation
- **click** (>=8.0.0) - CLI framework
- **rich** (>=13.0.0) - Beautiful terminal output

## Testing

Run the test suite:

```bash
python -m unittest tests.test_splitter -v
```

**Test Coverage:**
- ✅ PDF validation (valid files, missing files, wrong extensions)
- ✅ PDF info extraction
- ✅ File size formatting
- ✅ PDFSplitter initialization
- ✅ Split to individual pages
- ✅ Custom prefixes and padding
- ✅ Single page range extraction
- ✅ Multiple ranges splitting
- ✅ Range parsing and validation
- ✅ Overlap detection
- ✅ Bounds checking
- ✅ Invalid range handling
- ✅ Chunk splitting (equal chunks)
- ✅ Chunk size validation
- ✅ Last chunk handling
- ✅ Page specification parsing
- ✅ Extract specific pages
- ✅ Duplicate removal
- ✅ Page sorting
- ✅ Page count retrieval

All 72 tests pass successfully.

**Test Suite:**
- **Unit Tests**: 61 tests covering individual functions and methods
- **Integration Tests**: 11 tests covering complete workflows end-to-end
- **Total**: 72 tests with 100% pass rate

**Code Coverage:**
- `pdf_splitter/splitter.py`: 84% coverage
- `pdf_splitter/utils.py`: 73% coverage
- Overall core functionality: 80%+ coverage

**Integration Test Scenarios:**
- Complete split workflows (split-pages, split-range, split-chunks, extract)
- Batch processing workflows (multiple PDFs, directory structure)
- Error recovery workflows (corrupted PDFs, invalid ranges)
- End-to-end pipelines (multi-step processing)

## Error Handling

The tool provides clear, actionable error messages for all scenarios:

### File Errors
- **File not found**: `✗ Error: File not found: /path/to/file.pdf`
- **Invalid PDF**: `✗ Error: Corrupted or invalid PDF: ...`
- **Encrypted PDF**: `✗ Error: PDF is encrypted and requires a password. Please decrypt the PDF before processing.`
- **Permission denied**: `✗ Error: Cannot read file (permission denied): ...`

### Page Range Errors
- **Invalid page range**: `✗ Error: Invalid page range: 5-20. PDF has 10 pages.`
- **Overlapping ranges**: `✗ Error: Overlapping ranges detected: 1-10 and 5-15`
- **Out of bounds**: `✗ Error: Range 1-50 exceeds PDF page count (34 pages)`
- **Page out of bounds**: `✗ Error: Page 50 is out of bounds. PDF has 34 pages (1-34)`

### Operation Errors
- **Invalid chunk size**: `✗ Error: Chunk size must be >= 1, got 0`
- **Chunk size too large**: `✗ Error: Chunk size (50) cannot exceed total pages (23)`
- **Invalid page specification**: `✗ Error: Invalid page number: 'abc'. Expected a positive integer`

### System Errors
- **Disk full**: `✗ Error: Failed to write file. Successfully created N files before error.`
- **Permission denied (output)**: `✗ Error: Permission denied: Cannot create directory. Please check directory permissions.`
- **Insufficient disk space**: `✗ Error: Insufficient disk space. Available: X MB, Required: Y MB`

## Examples

### Example 1: Split a 100-page document

```bash
pdf-splitter split-pages large_document.pdf -o pages --padding 3
# Creates: pages/page_001.pdf through pages/page_100.pdf
```

### Example 2: Extract chapters

```bash
# Chapter 1 (pages 1-25)
pdf-splitter split-range book.pdf -s 1 -e 25 -n chapter1.pdf

# Chapter 2 (pages 26-50)
pdf-splitter split-range book.pdf -s 26 -e 50 -n chapter2.pdf
```

### Example 3: Split into custom ranges

```bash
# Split a 34-page document into 3 sections
pdf-splitter split-ranges document.pdf -r '1-10,11-20,21-34' -o sections
# Creates: sections/range_1-10.pdf, sections/range_11-20.pdf, sections/range_21-34.pdf
```

### Example 4: Extract specific chapters

```bash
# Extract chapters from a book
pdf-splitter split-ranges book.pdf -r '1-15,16-30,31-45' -p chapter -o chapters
# Creates: chapters/chapter_1-15.pdf, chapters/chapter_16-30.pdf, chapters/chapter_31-45.pdf
```

### Example 5: Split into equal chunks

```bash
# Split a 23-page document into chunks of 5 pages
pdf-splitter split-chunks document.pdf -s 5
# Creates 5 chunks: chunk_001.pdf (5), chunk_002.pdf (5), ..., chunk_005.pdf (3)

# Split into chunks of 10 pages
pdf-splitter split-chunks large_document.pdf --size 10 -o chunks
```

### Example 6: Extract specific pages

```bash
# Extract selected pages
pdf-splitter extract document.pdf -p '1,3,5,7-10' -o selected.pdf
# Extracts pages 1, 3, 5, 7, 8, 9, 10 into selected.pdf

# Extract first 5 pages and last 5 pages
pdf-splitter extract document.pdf -p '1-5,30-34' -o bookends.pdf
```

## Troubleshooting

### Command not found: pdf-splitter

Make sure you've installed the package and activated the virtual environment:
```bash
source venv/bin/activate
pip install -e .
```

### Import errors

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Permission errors

Check that you have read permissions for the input PDF and write permissions for the output directory.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up development environment
- Code style and conventions
- Testing requirements
- Pull request process

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and version information.

## Author

PDF Splitter CLI Contributors

## Version

1.0.0 - Production Release

---

**Happy PDF Splitting! 📄✂️**
