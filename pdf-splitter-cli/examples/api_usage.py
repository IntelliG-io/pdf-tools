"""
PDF Splitter - Library API Usage Examples

This script demonstrates how to use the PDF Splitter library programmatically.
"""

from pdf_splitter import (
    PDFSplitter,
    BatchProcessor,
    get_pdf_info,
    validate_pdf,
    format_file_size,
    __version__
)


def example_1_basic_splitting():
    """Example 1: Basic page splitting"""
    print("\n=== Example 1: Basic Page Splitting ===")
    
    # Note: You need a PDF file to run this example
    # Uncomment and modify the path below:
    
    # splitter = PDFSplitter('document.pdf')
    # files = splitter.split_to_pages('output/')
    # print(f"Created {len(files)} files")
    
    print("Code example:")
    print("""
    splitter = PDFSplitter('document.pdf')
    files = splitter.split_to_pages('output/')
    print(f"Created {len(files)} files")
    """)


def example_2_extract_pages():
    """Example 2: Extract specific pages"""
    print("\n=== Example 2: Extract Specific Pages ===")
    
    print("Code example:")
    print("""
    splitter = PDFSplitter('document.pdf')
    
    # Extract pages 1, 3, 5, and 7-10
    output = splitter.extract_pages('1,3,5,7-10', 'selected.pdf')
    print(f"Created: {output}")
    """)


def example_3_split_by_chunks():
    """Example 3: Split into chunks"""
    print("\n=== Example 3: Split into Chunks ===")
    
    print("Code example:")
    print("""
    splitter = PDFSplitter('large_document.pdf')
    
    # Split into chunks of 10 pages each
    chunks = splitter.split_by_chunks(10, 'chunks/', prefix='section')
    print(f"Created {len(chunks)} chunks")
    """)


def example_4_batch_processing():
    """Example 4: Batch processing"""
    print("\n=== Example 4: Batch Processing ===")
    
    print("Code example:")
    print("""
    processor = BatchProcessor()
    
    results = processor.process_directory(
        './pdfs',
        'pages',
        './output',
        options={'prefix': 'page', 'padding': 3}
    )
    
    print(f"Total: {results['total']}")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failure']}")
    """)


def example_5_pdf_info():
    """Example 5: Get PDF information"""
    print("\n=== Example 5: Get PDF Information ===")
    
    print("Code example:")
    print("""
    # Validate PDF first
    is_valid, error = validate_pdf('document.pdf')
    if not is_valid:
        print(f"Invalid PDF: {error}")
        exit(1)
    
    # Get PDF information
    info = get_pdf_info('document.pdf')
    
    print(f"Title: {info['title']}")
    print(f"Author: {info['author']}")
    print(f"Pages: {info['num_pages']}")
    print(f"Size: {format_file_size(info['file_size'])}")
    """)


def example_6_error_handling():
    """Example 6: Error handling"""
    print("\n=== Example 6: Error Handling ===")
    
    print("Code example:")
    print("""
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
        print(f"Success: {len(files)} files created")
    except ValueError as e:
        print(f"Validation error: {e}")
    except OSError as e:
        print(f"File system error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    """)


def example_7_progress_callback():
    """Example 7: Progress callback"""
    print("\n=== Example 7: Progress Callback ===")
    
    print("Code example:")
    print("""
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f"Progress: {current}/{total} ({percent:.1f}%)")
    
    splitter = PDFSplitter('document.pdf')
    files = splitter.split_to_pages(
        'output/',
        progress_callback=progress_callback
    )
    """)


def main():
    """Run all examples"""
    print("=" * 60)
    print(f"PDF Splitter Library API Examples (v{__version__})")
    print("=" * 60)
    
    example_1_basic_splitting()
    example_2_extract_pages()
    example_3_split_by_chunks()
    example_4_batch_processing()
    example_5_pdf_info()
    example_6_error_handling()
    example_7_progress_callback()
    
    print("\n" + "=" * 60)
    print("For more examples, see API.md documentation")
    print("=" * 60)


if __name__ == '__main__':
    main()
