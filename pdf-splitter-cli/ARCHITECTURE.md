# PDF Splitter - Architecture & Design

## Overview

PDF Splitter is designed as a **dual-purpose package** that works excellently both as a **library** (programmatic API) and as a **CLI tool** (command-line interface).

## Design Principles

1. **Separation of Concerns**: Clear separation between library code and CLI code
2. **Clean API**: Simple, intuitive imports for library users
3. **Type Safety**: Comprehensive type hints and dataclasses
4. **Error Handling**: Custom exceptions for different error scenarios
5. **Testability**: Pure functions and classes that are easy to test
6. **Documentation**: Well-documented code with examples

## Project Structure

```
pdf-splitter-cli/
├── pdf_splitter/              # Main package (library)
│   ├── __init__.py           # Public API exports
│   ├── splitter.py           # Core splitting logic (library)
│   ├── cli.py                # CLI interface (uses splitter.py)
│   ├── utils.py              # Utility functions (library)
│   ├── types.py              # Data types and dataclasses
│   └── exceptions.py         # Custom exceptions
│
├── tests/                     # Test suite
│   ├── test_splitter.py      # Unit tests
│   └── test_integration.py   # Integration tests
│
├── examples/                  # Usage examples
│   └── api_usage.py          # Library API examples
│
├── setup.py                   # Package configuration
├── pyproject.toml            # Modern packaging
├── requirements.txt          # Dependencies
└── README.md                 # Documentation
```

## Module Breakdown

### Core Library (No CLI Dependencies)

#### `splitter.py` - Core Splitting Logic
**Purpose**: Main library functionality for PDF splitting operations.

**Contains**:
- `PDFSplitter` class - Main class for all splitting operations
- `BatchProcessor` class - Batch processing multiple PDFs
- Helper functions: `parse_ranges()`, `validate_ranges()`, `parse_page_spec()`

**No Dependencies On**: CLI libraries (click, rich)

**Example Usage**:
```python
from pdf_splitter import PDFSplitter

splitter = PDFSplitter('document.pdf')
files = splitter.split_to_pages('output/')
```

---

#### `utils.py` - Utility Functions
**Purpose**: Standalone utility functions for PDF operations.

**Contains**:
- `get_pdf_info()` - Extract PDF metadata
- `validate_pdf()` - Validate PDF file
- `format_file_size()` - Format file sizes

**No Dependencies On**: CLI libraries

**Example Usage**:
```python
from pdf_splitter import get_pdf_info, validate_pdf

info = get_pdf_info('document.pdf')
is_valid, error = validate_pdf('document.pdf')
```

---

#### `types.py` - Data Types
**Purpose**: Define data structures used throughout the library.

**Contains**:
- `PDFInfo` - PDF metadata dataclass
- `SplitResult` - Result of split operation
- `BatchResult` - Result of batch operation

**Example Usage**:
```python
from pdf_splitter import PDFInfo, SplitResult

# These are returned by library functions
info: PDFInfo = get_pdf_info('document.pdf')
result: SplitResult = splitter.split_to_pages('output/')
```

---

#### `exceptions.py` - Custom Exceptions
**Purpose**: Define custom exceptions for error handling.

**Contains**:
- `PDFSplitterException` - Base exception
- `InvalidPDFError` - Invalid or corrupted PDF
- `EncryptedPDFError` - Encrypted PDF
- `InvalidRangeError` - Invalid page range
- `PageOutOfBoundsError` - Page out of bounds
- `InsufficientDiskSpaceError` - Disk space error

**Example Usage**:
```python
from pdf_splitter import PDFSplitter, EncryptedPDFError

try:
    splitter = PDFSplitter('encrypted.pdf')
except EncryptedPDFError as e:
    print(f"Cannot process encrypted PDF: {e}")
```

---

### CLI Layer (Uses Core Library)

#### `cli.py` - Command-Line Interface
**Purpose**: CLI wrapper around core library functionality.

**Contains**:
- Click commands for each operation
- Rich formatting for terminal output
- Progress bars and user interaction
- CLI-specific error handling

**Dependencies**: click, rich, core library (splitter.py, utils.py)

**Example Usage**:
```bash
pdf-splitter split-pages document.pdf
pdf-splitter extract document.pdf -p '1,3,5' -o selected.pdf
```

---

### Public API (`__init__.py`)

The `__init__.py` file defines the public API that library users interact with:

```python
# Main classes
from pdf_splitter import PDFSplitter, BatchProcessor

# Data types
from pdf_splitter import PDFInfo, SplitResult, BatchResult

# Exceptions
from pdf_splitter import (
    PDFSplitterException,
    InvalidPDFError,
    EncryptedPDFError,
    InvalidRangeError,
    PageOutOfBoundsError,
)

# Utility functions
from pdf_splitter import get_pdf_info, validate_pdf, format_file_size

# Version
from pdf_splitter import __version__
```

---

## Separation of Concerns

### Library Code (Pure Python API)
**Files**: `splitter.py`, `utils.py`, `types.py`, `exceptions.py`

**Characteristics**:
- No CLI dependencies (no click, no rich)
- Pure Python logic
- Type-hinted
- Well-documented
- Testable

**Usage**:
```python
# Import and use directly in Python code
from pdf_splitter import PDFSplitter

splitter = PDFSplitter('document.pdf')
files = splitter.split_to_pages('output/')
```

---

### CLI Code (Wrapper Layer)
**Files**: `cli.py`

**Characteristics**:
- Uses core library (imports from splitter.py, utils.py)
- Adds CLI-specific features (progress bars, formatting)
- Handles user interaction
- Provides command-line interface

**Usage**:
```bash
# Use from command line
pdf-splitter split-pages document.pdf
```

---

## Data Flow

### Library Usage Flow
```
User Code
    ↓
Import from pdf_splitter
    ↓
PDFSplitter class (splitter.py)
    ↓
pypdf library
    ↓
PDF files
```

### CLI Usage Flow
```
Command Line
    ↓
cli.py (Click commands)
    ↓
PDFSplitter class (splitter.py)
    ↓
pypdf library
    ↓
PDF files
```

---

## Type System

### Dataclasses

#### PDFInfo
```python
@dataclass
class PDFInfo:
    num_pages: int
    file_size: int
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    is_encrypted: bool = False
```

#### SplitResult
```python
@dataclass
class SplitResult:
    success: bool
    files_created: List[str]
    total_files: int
    source_file: str
    operation: str
    error: Optional[str] = None
```

#### BatchResult
```python
@dataclass
class BatchResult:
    total: int
    success: int
    failure: int
    results: List[dict]
```

---

## Exception Hierarchy

```
Exception
    └── PDFSplitterException (base)
        ├── InvalidPDFError
        ├── EncryptedPDFError
        ├── InvalidRangeError
        ├── PageOutOfBoundsError
        └── InsufficientDiskSpaceError
```

---

## Usage Patterns

### Pattern 1: Library Usage (Programmatic)
```python
from pdf_splitter import PDFSplitter, get_pdf_info

# Get info
info = get_pdf_info('document.pdf')
print(f"Pages: {info.num_pages}")

# Split
splitter = PDFSplitter('document.pdf')
files = splitter.split_to_pages('output/')
print(f"Created {len(files)} files")
```

### Pattern 2: CLI Usage (Command Line)
```bash
# Get info
pdf-splitter info document.pdf

# Split
pdf-splitter split-pages document.pdf -o output/
```

### Pattern 3: Error Handling
```python
from pdf_splitter import PDFSplitter, EncryptedPDFError, InvalidPDFError

try:
    splitter = PDFSplitter('document.pdf')
    files = splitter.split_to_pages('output/')
except EncryptedPDFError:
    print("PDF is encrypted")
except InvalidPDFError:
    print("PDF is invalid")
```

### Pattern 4: Batch Processing
```python
from pdf_splitter import BatchProcessor

processor = BatchProcessor()
results = processor.process_directory(
    './pdfs',
    'pages',
    './output'
)
print(f"Success: {results.success}/{results.total}")
```

---

## Testing Strategy

### Unit Tests (`test_splitter.py`)
- Test individual functions and methods
- Mock file I/O where appropriate
- Test edge cases and error conditions

### Integration Tests (`test_integration.py`)
- Test complete workflows end-to-end
- Test both library and CLI usage
- Test error recovery

### Test Coverage
- **Core library**: 84% coverage
- **Total tests**: 72 (61 unit + 11 integration)
- **Pass rate**: 100%

---

## Dependencies

### Core Library Dependencies
- `pypdf` >= 3.0.0 (PDF manipulation)

### CLI Dependencies
- `click` >= 8.0.0 (CLI framework)
- `rich` >= 13.0.0 (Terminal UI)

### Development Dependencies
- `pytest` >= 7.0.0 (Testing)
- `pytest-cov` >= 4.0.0 (Coverage)

---

## Extension Points

### Adding New Operations
1. Add method to `PDFSplitter` class in `splitter.py`
2. Add CLI command in `cli.py` (optional)
3. Add tests in `test_splitter.py`
4. Update documentation

### Adding New Data Types
1. Add dataclass to `types.py`
2. Export in `__init__.py`
3. Update API documentation

### Adding New Exceptions
1. Add exception to `exceptions.py`
2. Export in `__init__.py`
3. Use in appropriate places

---

## Best Practices

### For Library Users
1. Always validate PDFs before processing
2. Use try-except for error handling
3. Check return values and results
4. Use type hints for IDE support

### For Contributors
1. Keep library code separate from CLI code
2. Add type hints to all functions
3. Write tests for new features
4. Update documentation
5. Follow existing code style

---

## Version Information

- **Version**: 1.0.0
- **Status**: Production/Stable
- **Python**: 3.7+
- **License**: MIT

---

## See Also

- [README.md](README.md) - User documentation
- [API.md](API.md) - API reference
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines
- [CHANGELOG.md](CHANGELOG.md) - Version history
