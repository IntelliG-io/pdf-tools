"""
Test cases for PDF splitter utility functions.
"""

import os
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from pdf_splitter.utils import get_pdf_info, validate_pdf, format_file_size
from pdf_splitter.splitter import PDFSplitter, parse_ranges, validate_ranges, parse_page_spec
from pdf_splitter.types import PDFInfo
from pdf_splitter.exceptions import (
    EncryptedPDFError,
    InvalidPDFError,
    InvalidRangeError,
    PageOutOfBoundsError,
)


class TestPdfUtils(unittest.TestCase):
    """Test cases for PDF utility functions."""
    
    @classmethod
    def setUpClass(cls):
        """Create a temporary test PDF file."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_pdf_path = os.path.join(cls.temp_dir, 'test.pdf')
        
        # Create a simple test PDF
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_blank_page(width=200, height=200)
        
        with open(cls.test_pdf_path, 'wb') as f:
            writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_validate_pdf_valid_file(self):
        """Test validation with a valid PDF file."""
        is_valid, error_msg = validate_pdf(self.test_pdf_path)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_pdf_nonexistent_file(self):
        """Test validation with non-existent file."""
        is_valid, error_msg = validate_pdf('/nonexistent/file.pdf')
        self.assertFalse(is_valid)
        self.assertIn('not found', error_msg.lower())
    
    def test_validate_pdf_wrong_extension(self):
        """Test validation with wrong file extension."""
        temp_file = os.path.join(self.temp_dir, 'test.txt')
        with open(temp_file, 'w') as f:
            f.write('test')
        
        is_valid, error_msg = validate_pdf(temp_file)
        self.assertFalse(is_valid)
        self.assertIn('extension', error_msg.lower())
    
    def test_get_pdf_info_valid_file(self):
        """Test getting info from a valid PDF."""
        info = get_pdf_info(self.test_pdf_path)

        self.assertIsInstance(info, PDFInfo)
        self.assertEqual(info.num_pages, 2)
        self.assertGreater(info.file_size, 0)
        self.assertFalse(info.is_encrypted)

    def test_get_pdf_info_nonexistent_file(self):
        """Test getting info from non-existent file."""
        with self.assertRaises(InvalidPDFError):
            get_pdf_info('/nonexistent/file.pdf')
    
    def test_format_file_size(self):
        """Test file size formatting."""
        self.assertEqual(format_file_size(500), '500.0 B')
        self.assertEqual(format_file_size(1024), '1.0 KB')
        self.assertEqual(format_file_size(1024 * 1024), '1.0 MB')
        self.assertEqual(format_file_size(1536), '1.5 KB')


class TestPDFSplitter(unittest.TestCase):
    """Test cases for PDFSplitter class."""
    
    @classmethod
    def setUpClass(cls):
        """Create a temporary test PDF file with 10 pages."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_pdf_path = os.path.join(cls.temp_dir, 'test_10pages.pdf')
        
        # Create a test PDF with 10 pages
        writer = PdfWriter()
        for i in range(10):
            writer.add_blank_page(width=200, height=200)
        
        with open(cls.test_pdf_path, 'wb') as f:
            writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_splitter_initialization(self):
        """Test PDFSplitter initialization."""
        splitter = PDFSplitter(self.test_pdf_path)
        self.assertEqual(splitter.num_pages, 10)
        self.assertEqual(splitter.input_path, self.test_pdf_path)
    
    def test_splitter_nonexistent_file(self):
        """Test PDFSplitter with non-existent file."""
        with self.assertRaises(InvalidPDFError):
            PDFSplitter('/nonexistent/file.pdf')
    
    def test_split_to_pages(self):
        """Test splitting PDF into individual pages."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output')
        
        created_files = splitter.split_to_pages(output_dir, prefix='page', padding=3)
        
        # Verify correct number of files created
        self.assertEqual(len(created_files), 10)
        
        # Verify all files exist
        for file_path in created_files:
            self.assertTrue(os.path.exists(file_path))
        
        # Verify filenames are correct
        self.assertTrue(created_files[0].endswith('page_001.pdf'))
        self.assertTrue(created_files[9].endswith('page_010.pdf'))
        
        # Verify each file has exactly 1 page
        for file_path in created_files:
            reader = PdfReader(file_path)
            self.assertEqual(len(reader.pages), 1)
    
    def test_split_to_pages_custom_prefix(self):
        """Test splitting with custom prefix."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_custom')
        
        created_files = splitter.split_to_pages(output_dir, prefix='chapter', padding=2)
        
        self.assertEqual(len(created_files), 10)
        self.assertTrue(created_files[0].endswith('chapter_01.pdf'))
        self.assertTrue(created_files[9].endswith('chapter_10.pdf'))
    
    def test_split_by_range(self):
        """Test extracting a range of pages."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_range')
        
        output_file = splitter.split_by_range(output_dir, start_page=3, end_page=7)
        
        # Verify file exists
        self.assertTrue(os.path.exists(output_file))
        
        # Verify file has correct number of pages (3-7 inclusive = 5 pages)
        reader = PdfReader(output_file)
        self.assertEqual(len(reader.pages), 5)
    
    def test_split_by_range_invalid(self):
        """Test split_by_range with invalid range."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_invalid')
        
        # Test start > end
        with self.assertRaises(InvalidRangeError):
            splitter.split_by_range(output_dir, start_page=7, end_page=3)
        
        # Test out of bounds
        with self.assertRaises(PageOutOfBoundsError):
            splitter.split_by_range(output_dir, start_page=1, end_page=20)
    
    def test_get_page_count(self):
        """Test getting page count."""
        splitter = PDFSplitter(self.test_pdf_path)
        self.assertEqual(splitter.get_page_count(), 10)


class TestRangeParsing(unittest.TestCase):
    """Test cases for range parsing and validation."""
    
    def test_parse_ranges_simple(self):
        """Test parsing simple range string."""
        result = parse_ranges('1-5')
        self.assertEqual(result, [(1, 5)])
    
    def test_parse_ranges_multiple(self):
        """Test parsing multiple ranges."""
        result = parse_ranges('1-5,6-10,11-15')
        self.assertEqual(result, [(1, 5), (6, 10), (11, 15)])
    
    def test_parse_ranges_with_spaces(self):
        """Test parsing ranges with spaces."""
        result = parse_ranges('1-3, 7-9, 12-20')
        self.assertEqual(result, [(1, 3), (7, 9), (12, 20)])
    
    def test_parse_ranges_invalid_format(self):
        """Test parsing invalid range format."""
        with self.assertRaises(InvalidRangeError) as cm:
            parse_ranges('1-5-10')
        self.assertIn('Invalid range format', str(cm.exception))
    
    def test_parse_ranges_start_greater_than_end(self):
        """Test parsing range where start > end."""
        with self.assertRaises(InvalidRangeError) as cm:
            parse_ranges('10-5')
        self.assertIn('must be <=', str(cm.exception))
    
    def test_parse_ranges_empty_string(self):
        """Test parsing empty string."""
        with self.assertRaises(InvalidRangeError) as cm:
            parse_ranges('')
        self.assertIn('cannot be empty', str(cm.exception))
    
    def test_parse_ranges_zero_page(self):
        """Test parsing range with page 0."""
        with self.assertRaises(PageOutOfBoundsError) as cm:
            parse_ranges('0-5')
        self.assertIn('must be >= 1', str(cm.exception))
    
    def test_validate_ranges_within_bounds(self):
        """Test validating ranges within PDF bounds."""
        ranges = [(1, 5), (6, 10)]
        # Should not raise
        validate_ranges(ranges, total_pages=10)
    
    def test_validate_ranges_exceeds_bounds(self):
        """Test validating ranges that exceed PDF bounds."""
        ranges = [(1, 5), (6, 15)]
        with self.assertRaises(PageOutOfBoundsError) as cm:
            validate_ranges(ranges, total_pages=10)
        self.assertIn('exceeds PDF page count', str(cm.exception))
    
    def test_validate_ranges_overlapping(self):
        """Test validating overlapping ranges."""
        ranges = [(1, 5), (4, 8)]
        with self.assertRaises(InvalidRangeError) as cm:
            validate_ranges(ranges, total_pages=10)
        self.assertIn('Overlapping ranges', str(cm.exception))
    
    def test_validate_ranges_no_overlap_check(self):
        """Test validating with overlap check disabled."""
        ranges = [(1, 5), (4, 8)]
        # Should not raise when check_overlaps=False
        validate_ranges(ranges, total_pages=10, check_overlaps=False)


class TestSplitByRanges(unittest.TestCase):
    """Test cases for split_by_ranges method."""
    
    @classmethod
    def setUpClass(cls):
        """Create a temporary test PDF file with 20 pages."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_pdf_path = os.path.join(cls.temp_dir, 'test_20pages.pdf')
        
        # Create a test PDF with 20 pages
        writer = PdfWriter()
        for i in range(20):
            writer.add_blank_page(width=200, height=200)
        
        with open(cls.test_pdf_path, 'wb') as f:
            writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_split_by_ranges_string(self):
        """Test splitting by ranges using string format."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_ranges_str')
        
        created_files = splitter.split_by_ranges('1-5,6-10,11-15', output_dir)
        
        # Verify correct number of files
        self.assertEqual(len(created_files), 3)
        
        # Verify all files exist
        for file_path in created_files:
            self.assertTrue(os.path.exists(file_path))
        
        # Verify filenames
        self.assertTrue(created_files[0].endswith('range_1-5.pdf'))
        self.assertTrue(created_files[1].endswith('range_6-10.pdf'))
        self.assertTrue(created_files[2].endswith('range_11-15.pdf'))
        
        # Verify page counts
        reader1 = PdfReader(created_files[0])
        reader2 = PdfReader(created_files[1])
        reader3 = PdfReader(created_files[2])
        self.assertEqual(len(reader1.pages), 5)
        self.assertEqual(len(reader2.pages), 5)
        self.assertEqual(len(reader3.pages), 5)
    
    def test_split_by_ranges_list(self):
        """Test splitting by ranges using list format."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_ranges_list')
        
        created_files = splitter.split_by_ranges([(1, 3), (7, 9)], output_dir, prefix='chapter')
        
        self.assertEqual(len(created_files), 2)
        self.assertTrue(created_files[0].endswith('chapter_1-3.pdf'))
        self.assertTrue(created_files[1].endswith('chapter_7-9.pdf'))
        
        # Verify page counts
        reader1 = PdfReader(created_files[0])
        reader2 = PdfReader(created_files[1])
        self.assertEqual(len(reader1.pages), 3)
        self.assertEqual(len(reader2.pages), 3)
    
    def test_split_by_ranges_custom_prefix(self):
        """Test splitting with custom prefix."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_custom_prefix')
        
        created_files = splitter.split_by_ranges('1-5,6-10', output_dir, prefix='section')
        
        self.assertTrue(created_files[0].endswith('section_1-5.pdf'))
        self.assertTrue(created_files[1].endswith('section_6-10.pdf'))
    
    def test_split_by_ranges_invalid(self):
        """Test splitting with invalid ranges."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_invalid_ranges')
        
        # Test out of bounds
        with self.assertRaises(PageOutOfBoundsError):
            splitter.split_by_ranges('1-25', output_dir)
        
        # Test overlapping
        with self.assertRaises(InvalidRangeError):
            splitter.split_by_ranges('1-10,5-15', output_dir)


class TestSplitByChunks(unittest.TestCase):
    """Test cases for split_by_chunks method."""
    
    @classmethod
    def setUpClass(cls):
        """Create a temporary test PDF file with 23 pages."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_pdf_path = os.path.join(cls.temp_dir, 'test_23pages.pdf')
        
        # Create a test PDF with 23 pages
        writer = PdfWriter()
        for i in range(23):
            writer.add_blank_page(width=200, height=200)
        
        with open(cls.test_pdf_path, 'wb') as f:
            writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_split_by_chunks_equal(self):
        """Test splitting into equal chunks."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_chunks_equal')
        
        # Split into chunks of 5 pages
        created_files = splitter.split_by_chunks(5, output_dir)
        
        # Should create 5 chunks (5+5+5+5+3)
        self.assertEqual(len(created_files), 5)
        
        # Verify all files exist
        for file_path in created_files:
            self.assertTrue(os.path.exists(file_path))
        
        # Verify filenames
        self.assertTrue(created_files[0].endswith('chunk_001.pdf'))
        self.assertTrue(created_files[4].endswith('chunk_005.pdf'))
        
        # Verify page counts
        reader1 = PdfReader(created_files[0])
        reader2 = PdfReader(created_files[1])
        reader3 = PdfReader(created_files[2])
        reader4 = PdfReader(created_files[3])
        reader5 = PdfReader(created_files[4])
        
        self.assertEqual(len(reader1.pages), 5)  # Pages 1-5
        self.assertEqual(len(reader2.pages), 5)  # Pages 6-10
        self.assertEqual(len(reader3.pages), 5)  # Pages 11-15
        self.assertEqual(len(reader4.pages), 5)  # Pages 16-20
        self.assertEqual(len(reader5.pages), 3)  # Pages 21-23 (last chunk)
    
    def test_split_by_chunks_custom_prefix(self):
        """Test splitting with custom prefix."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_chunks_prefix')
        
        created_files = splitter.split_by_chunks(10, output_dir, prefix='section')
        
        # Should create 3 chunks (10+10+3)
        self.assertEqual(len(created_files), 3)
        self.assertTrue(created_files[0].endswith('section_001.pdf'))
        self.assertTrue(created_files[1].endswith('section_002.pdf'))
        self.assertTrue(created_files[2].endswith('section_003.pdf'))
    
    def test_split_by_chunks_single_page(self):
        """Test splitting with chunk size of 1."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_chunks_single')
        
        created_files = splitter.split_by_chunks(1, output_dir)
        
        # Should create 23 chunks
        self.assertEqual(len(created_files), 23)
        
        # Each file should have 1 page
        for file_path in created_files:
            reader = PdfReader(file_path)
            self.assertEqual(len(reader.pages), 1)
    
    def test_split_by_chunks_full_pdf(self):
        """Test splitting with chunk size equal to total pages."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_chunks_full')
        
        created_files = splitter.split_by_chunks(23, output_dir)
        
        # Should create 1 chunk
        self.assertEqual(len(created_files), 1)
        
        # File should have all 23 pages
        reader = PdfReader(created_files[0])
        self.assertEqual(len(reader.pages), 23)
    
    def test_split_by_chunks_invalid_size(self):
        """Test splitting with invalid chunk sizes."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_chunks_invalid')
        
        # Test chunk size < 1
        with self.assertRaises(InvalidRangeError) as cm:
            splitter.split_by_chunks(0, output_dir)
        self.assertIn('must be >= 1', str(cm.exception))
        
        # Test chunk size > total pages
        with self.assertRaises(InvalidRangeError) as cm:
            splitter.split_by_chunks(50, output_dir)
        self.assertIn('cannot exceed total pages', str(cm.exception))
    
    def test_split_by_chunks_large_size(self):
        """Test splitting with large chunk size."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_dir = os.path.join(self.temp_dir, 'output_chunks_large')
        
        # Split into chunks of 15 pages
        created_files = splitter.split_by_chunks(15, output_dir)
        
        # Should create 2 chunks (15+8)
        self.assertEqual(len(created_files), 2)
        
        reader1 = PdfReader(created_files[0])
        reader2 = PdfReader(created_files[1])
        
        self.assertEqual(len(reader1.pages), 15)
        self.assertEqual(len(reader2.pages), 8)


class TestPageSpecParsing(unittest.TestCase):
    """Test cases for page specification parsing."""
    
    def test_parse_page_spec_individual(self):
        """Test parsing individual pages."""
        result = parse_page_spec('1,3,5')
        self.assertEqual(result, [1, 3, 5])
    
    def test_parse_page_spec_range(self):
        """Test parsing page range."""
        result = parse_page_spec('7-10')
        self.assertEqual(result, [7, 8, 9, 10])
    
    def test_parse_page_spec_mixed(self):
        """Test parsing mixed pages and ranges."""
        result = parse_page_spec('1,3,5,7-10')
        self.assertEqual(result, [1, 3, 5, 7, 8, 9, 10])
    
    def test_parse_page_spec_complex(self):
        """Test parsing complex specification."""
        result = parse_page_spec('5-10,15,20-25')
        self.assertEqual(result, [5, 6, 7, 8, 9, 10, 15, 20, 21, 22, 23, 24, 25])
    
    def test_parse_page_spec_duplicates(self):
        """Test that duplicates are removed."""
        result = parse_page_spec('1,3,3,5,5,7-10,9')
        self.assertEqual(result, [1, 3, 5, 7, 8, 9, 10])
    
    def test_parse_page_spec_with_spaces(self):
        """Test parsing with spaces."""
        result = parse_page_spec('1, 3, 5, 7-10')
        self.assertEqual(result, [1, 3, 5, 7, 8, 9, 10])
    
    def test_parse_page_spec_empty(self):
        """Test parsing empty string."""
        with self.assertRaises(InvalidRangeError) as cm:
            parse_page_spec('')
        self.assertIn('cannot be empty', str(cm.exception))
    
    def test_parse_page_spec_invalid_format(self):
        """Test parsing invalid format."""
        with self.assertRaises(InvalidRangeError) as cm:
            parse_page_spec('1,abc,5')
        self.assertIn('Invalid page number', str(cm.exception))

    def test_parse_page_spec_invalid_range(self):
        """Test parsing invalid range."""
        with self.assertRaises(InvalidRangeError) as cm:
            parse_page_spec('10-5')
        self.assertIn('must be <=', str(cm.exception))

    def test_parse_page_spec_zero_page(self):
        """Test parsing page 0."""
        with self.assertRaises(PageOutOfBoundsError) as cm:
            parse_page_spec('0,1,2')
        self.assertIn('must be >= 1', str(cm.exception))


class TestExtractPages(unittest.TestCase):
    """Test cases for extract_pages method."""
    
    @classmethod
    def setUpClass(cls):
        """Create a temporary test PDF file with 20 pages."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_pdf_path = os.path.join(cls.temp_dir, 'test_20pages.pdf')
        
        # Create a test PDF with 20 pages
        writer = PdfWriter()
        for i in range(20):
            writer.add_blank_page(width=200, height=200)
        
        with open(cls.test_pdf_path, 'wb') as f:
            writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_extract_pages_string(self):
        """Test extracting pages using string specification."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_str.pdf')
        
        result = splitter.extract_pages('1,3,5,7-10', output_path)
        
        # Verify file created
        self.assertTrue(os.path.exists(result))
        self.assertEqual(result, output_path)
        
        # Verify page count
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 7)  # 1,3,5,7,8,9,10
    
    def test_extract_pages_list(self):
        """Test extracting pages using list."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_list.pdf')
        
        result = splitter.extract_pages([1, 3, 5, 7, 8, 9, 10], output_path)
        
        # Verify file created
        self.assertTrue(os.path.exists(result))
        
        # Verify page count
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 7)
    
    def test_extract_pages_single(self):
        """Test extracting single page."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_single.pdf')
        
        result = splitter.extract_pages('5', output_path)
        
        # Verify page count
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 1)
    
    def test_extract_pages_all(self):
        """Test extracting all pages."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_all.pdf')
        
        result = splitter.extract_pages('1-20', output_path)
        
        # Verify page count
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 20)
    
    def test_extract_pages_out_of_bounds(self):
        """Test extracting pages out of bounds."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_oob.pdf')
        
        # Test page > total
        with self.assertRaises(PageOutOfBoundsError) as cm:
            splitter.extract_pages('1,25', output_path)
        self.assertIn('out of bounds', str(cm.exception))
    
    def test_extract_pages_duplicates(self):
        """Test that duplicates are handled."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_dup.pdf')
        
        result = splitter.extract_pages([1, 1, 3, 3, 5], output_path)
        
        # Verify duplicates removed
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 3)  # 1,3,5
    
    def test_extract_pages_sorted(self):
        """Test that pages are sorted."""
        splitter = PDFSplitter(self.test_pdf_path)
        output_path = os.path.join(self.temp_dir, 'extracted_sorted.pdf')
        
        # Provide pages out of order
        result = splitter.extract_pages([10, 5, 1, 15, 3], output_path)
        
        # Pages should be in order: 1,3,5,10,15
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 5)


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()

        cls.test_pdf_path = os.path.join(cls.temp_dir, 'test.pdf')
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with open(cls.test_pdf_path, 'wb') as f:
            writer.write(f)

        cls.encrypted_pdf_path = os.path.join(cls.temp_dir, 'encrypted.pdf')
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.encrypt(user_password="test123")
        with open(cls.encrypted_pdf_path, 'wb') as f:
            writer.write(f)

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_validate_encrypted_pdf(self):
        is_valid, error_msg = validate_pdf(self.encrypted_pdf_path)
        self.assertFalse(is_valid)
        self.assertIn('encrypted', error_msg.lower())

    def test_splitter_encrypted_pdf(self):
        with self.assertRaises(EncryptedPDFError) as cm:
            PDFSplitter(self.encrypted_pdf_path)
        self.assertIn('encrypted', str(cm.exception).lower())

    def test_get_pdf_info_encrypted(self):
        with self.assertRaises(EncryptedPDFError):
            get_pdf_info(self.encrypted_pdf_path)

    def test_parse_ranges_edge_cases(self):
        result = parse_ranges('1-5, 6-10')
        self.assertEqual(result, [(1, 5), (6, 10)])

        with self.assertRaises(InvalidRangeError):
            parse_ranges('1-5-10')

        with self.assertRaises(InvalidRangeError):
            parse_ranges('10-5')

    def test_parse_page_spec_edge_cases(self):
        with self.assertRaises(InvalidRangeError):
            parse_page_spec('-1,2,3')

        with self.assertRaises(InvalidRangeError):
            parse_page_spec('1,2,abc')

    def test_validate_ranges_edge_cases(self):
        with self.assertRaises(PageOutOfBoundsError):
            validate_ranges([(1, 100)], total_pages=10)

        with self.assertRaises(InvalidRangeError):
            validate_ranges([(1, 10), (5, 15)], total_pages=20)

        try:
            validate_ranges([(1, 10), (5, 15)], total_pages=20, check_overlaps=False)
        except InvalidRangeError:
            self.fail("Should not raise error when overlap check is disabled")


class TestBatchProcessor(unittest.TestCase):
    """Test cases for BatchProcessor."""
    
    @classmethod
    def setUpClass(cls):
        """Create test directory with PDFs."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.pdf_dir = os.path.join(cls.temp_dir, 'pdfs')
        os.makedirs(cls.pdf_dir)
        
        # Create 3 test PDFs
        for i in range(1, 4):
            pdf_path = os.path.join(cls.pdf_dir, f'doc{i}.pdf')
            writer = PdfWriter()
            for _ in range(5):
                writer.add_blank_page(width=200, height=200)
            with open(pdf_path, 'wb') as f:
                writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_find_pdf_files(self):
        """Test finding PDF files in directory."""
        from pdf_splitter.splitter import BatchProcessor
        processor = BatchProcessor()
        
        pdf_files = processor.find_pdf_files(self.pdf_dir)
        self.assertEqual(len(pdf_files), 3)
    
    def test_find_pdf_files_nonexistent_dir(self):
        """Test finding PDFs in non-existent directory."""
        from pdf_splitter.splitter import BatchProcessor
        processor = BatchProcessor()
        
        with self.assertRaises(FileNotFoundError):
            processor.find_pdf_files('/nonexistent/directory')
    
    def test_process_directory_pages(self):
        """Test batch processing with pages operation."""
        from pdf_splitter.splitter import BatchProcessor
        output_dir = os.path.join(self.temp_dir, 'batch_output')
        manifest_path = os.path.join(output_dir, 'manifest.json')

        processor = BatchProcessor(manifest_path=manifest_path, resume=False)
        results = processor.process_directory(
            self.pdf_dir,
            'pages',
            output_dir,
            options={'prefix': 'page', 'padding': 3}
        )

        self.assertEqual(results.total, 3)
        self.assertEqual(results.success, 3)
        self.assertEqual(results.failure, 0)
        self.assertEqual(results.skipped, 0)
        self.assertEqual(results.total_attempts, 3)
        self.assertTrue(results.manifest_path)
        self.assertTrue(os.path.exists(results.manifest_path))
        self.assertTrue(all(entry['status'] == 'success' for entry in results.results))
    
    def test_process_directory_chunks_resume_skips(self):
        """Test resume logic skipping already-processed PDFs."""
        from pdf_splitter.splitter import BatchProcessor
        output_dir = os.path.join(self.temp_dir, 'batch_chunks')
        manifest_path = os.path.join(output_dir, 'manifest.json')

        initial = BatchProcessor(manifest_path=manifest_path, resume=True)
        first_run = initial.process_directory(
            self.pdf_dir,
            'chunks',
            output_dir,
            options={'chunk_size': 2}
        )
        self.assertEqual(first_run.success, 3)
        self.assertEqual(first_run.total_attempts, 3)

        second = BatchProcessor(manifest_path=manifest_path, resume=True)
        second_run = second.process_directory(
            self.pdf_dir,
            'chunks',
            output_dir,
        )
        self.assertEqual(second_run.total, 3)
        self.assertEqual(second_run.skipped, 3)
        self.assertEqual(second_run.success, 0)
        self.assertEqual(second_run.failure, 0)
        self.assertEqual(second_run.total_attempts, first_run.total_attempts)
        self.assertTrue(all(entry['status'] == 'skipped' for entry in second_run.results))

    def test_process_directory_failure_records_manifest(self):
        """Test that failures are recorded with attempts in manifest."""
        from pdf_splitter.splitter import BatchProcessor
        corrupt_dir = os.path.join(self.temp_dir, 'mixed')
        os.makedirs(corrupt_dir)

        # valid pdf
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        valid_path = os.path.join(corrupt_dir, 'valid.pdf')
        with open(valid_path, 'wb') as f:
            writer.write(f)

        # corrupted file with .pdf extension
        with open(os.path.join(corrupt_dir, 'corrupt.pdf'), 'w') as f:
            f.write('not a pdf')

        output_dir = os.path.join(self.temp_dir, 'batch_failure')
        manifest_path = os.path.join(output_dir, 'manifest.json')
        processor = BatchProcessor(manifest_path=manifest_path, max_retries=0, resume=False)

        results = processor.process_directory(corrupt_dir, 'pages', output_dir)

        self.assertEqual(results.total, 2)
        self.assertEqual(results.success, 1)
        self.assertEqual(results.failure, 1)
        self.assertEqual(results.skipped, 0)
        self.assertGreaterEqual(results.total_attempts, 2)
        failure_entries = [entry for entry in results.results if entry['status'] == 'failure']
        self.assertEqual(len(failure_entries), 1)
        self.assertIn('error', failure_entries[0])


if __name__ == '__main__':
    unittest.main()
