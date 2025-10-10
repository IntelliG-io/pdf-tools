# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-04

### Added
- **Core Functionality**
  - Split PDF into individual pages with custom naming
  - Extract single page range into new PDF
  - Split by multiple custom page ranges
  - Split into equal-sized chunks
  - Extract specific pages into single PDF
  - Batch processing for multiple PDFs
  - PDF information display with metadata

- **Enhanced Features**
  - Real-time progress bars with completion percentage
  - Time remaining estimates for all operations
  - Metadata preservation (title, author, subject, creator)
  - Automatic title updates with page/range information
  - Beautiful terminal UI with Rich library
  - Colored output and formatted tables

- **Error Handling**
  - Encrypted PDF detection with clear messages
  - Disk space checking before operations
  - Permission validation for read/write operations
  - Corrupted PDF detection and reporting
  - Invalid page range validation
  - Graceful error recovery in batch operations

- **Testing**
  - 61 comprehensive unit tests
  - 11 integration tests for end-to-end workflows
  - 84% code coverage for core functionality
  - Automated test fixtures and cleanup

- **Documentation**
  - Complete README with examples
  - Detailed usage guide (QUICKSTART.md)
  - Project summary documentation
  - Inline code documentation with Google-style docstrings
  - Error handling guide
  - Troubleshooting section

### Commands
- `pdf-splitter info` - Display PDF information
- `pdf-splitter split-pages` - Split into individual pages
- `pdf-splitter split-range` - Extract single page range
- `pdf-splitter split-ranges` - Split by multiple ranges
- `pdf-splitter split-chunks` - Split into equal chunks
- `pdf-splitter extract` - Extract specific pages
- `pdf-splitter batch` - Process multiple PDFs

### Technical Details
- **Language**: Python 3.7+
- **Dependencies**: pypdf (6.1.1), click (8.3.0), rich (14.1.0)
- **Architecture**: Modular design with separate CLI, splitter, and utils modules
- **Testing**: unittest + pytest with coverage reporting
- **Code Quality**: Type hints, comprehensive error handling, clean architecture

### Performance
- Fast processing with minimal memory footprint
- Progress tracking for long-running operations
- Efficient batch processing with error resilience
- Automatic cleanup of temporary files

## [Unreleased]

### Planned Features
- Password-protected PDF support with decryption
- PDF merging capabilities
- Watermark addition
- Page rotation and manipulation
- OCR text extraction
- Bookmark preservation
- Form field handling

---

## Version History

### Version 1.0.0 (2025-10-04)
- Initial production release
- Complete feature set implemented
- Comprehensive test coverage
- Full documentation
- Production-ready error handling

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

See [LICENSE](LICENSE) for license information.
