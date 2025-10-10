"""
Integration tests for PDF Splitter CLI.
Tests complete workflows end-to-end.
"""

import os
import tempfile
import unittest
import shutil
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from pdf_splitter.splitter import PDFSplitter, BatchProcessor
from pdf_splitter.exceptions import InvalidRangeError, PageOutOfBoundsError
from pdf_splitter.utils import get_pdf_info


class TestCompleteSplitWorkflow(unittest.TestCase):
    """Test complete split workflow end-to-end."""
    
    @classmethod
    def setUpClass(cls):
        """Create test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test PDF with 10 pages and metadata
        cls.test_pdf = os.path.join(cls.temp_dir, 'test_document.pdf')
        writer = PdfWriter()
        for i in range(10):
            writer.add_blank_page(width=612, height=792)
        
        # Add metadata
        writer.add_metadata({
            '/Title': 'Test Document 2024',
            '/Author': 'Test Author',
            '/Subject': 'Integration Test',
            '/Creator': 'PDF Splitter Test Suite'
        })
        
        with open(cls.test_pdf, 'wb') as f:
            writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_split_pages_workflow(self):
        """Test complete split-pages workflow."""
        # Step 1: Initialize splitter
        splitter = PDFSplitter(self.test_pdf)
        
        # Step 2: Run split-pages
        output_dir = os.path.join(self.temp_dir, 'split_output')
        created_files = splitter.split_to_pages(output_dir, prefix='page', padding=2)
        
        # Step 3: Verify 10 output files created
        self.assertEqual(len(created_files), 10)
        
        # Step 4: Verify each file exists and has 1 page
        for i, file_path in enumerate(created_files, 1):
            self.assertTrue(os.path.exists(file_path))
            
            reader = PdfReader(file_path)
            self.assertEqual(len(reader.pages), 1)
            
            # Step 5: Verify metadata preserved
            metadata = reader.metadata
            self.assertIsNotNone(metadata)
            if metadata and metadata.title:
                self.assertIn('Test Document 2024', metadata.title)
                self.assertIn(f'Page {i}', metadata.title)
            
            if metadata and metadata.author:
                self.assertEqual(metadata.author, 'Test Author')
    
    def test_split_by_range_workflow(self):
        """Test split-by-range workflow."""
        splitter = PDFSplitter(self.test_pdf)
        
        # Extract pages 3-7
        output_dir = os.path.join(self.temp_dir, 'range_output')
        output_file = splitter.split_by_range(
            output_dir,
            start_page=3,
            end_page=7,
            output_filename='pages_3-7.pdf'
        )
        
        # Verify file created
        self.assertTrue(os.path.exists(output_file))
        
        # Verify correct page count
        reader = PdfReader(output_file)
        self.assertEqual(len(reader.pages), 5)  # Pages 3-7 = 5 pages
        
        # Verify metadata
        if reader.metadata and reader.metadata.title:
            self.assertIn('Pages 3-7', reader.metadata.title)
    
    def test_split_by_chunks_workflow(self):
        """Test split-by-chunks workflow."""
        splitter = PDFSplitter(self.test_pdf)
        
        # Split into chunks of 3 pages
        output_dir = os.path.join(self.temp_dir, 'chunks_output')
        created_files = splitter.split_by_chunks(3, output_dir, prefix='chunk')
        
        # Verify correct number of chunks (10 pages / 3 = 4 chunks)
        self.assertEqual(len(created_files), 4)
        
        # Verify chunk sizes
        expected_sizes = [3, 3, 3, 1]  # Last chunk has 1 page
        for i, (file_path, expected_size) in enumerate(zip(created_files, expected_sizes)):
            reader = PdfReader(file_path)
            self.assertEqual(len(reader.pages), expected_size)
    
    def test_extract_pages_workflow(self):
        """Test extract-pages workflow."""
        splitter = PDFSplitter(self.test_pdf)
        
        # Extract specific pages
        output_file = os.path.join(self.temp_dir, 'extracted.pdf')
        result = splitter.extract_pages('1,3,5,7-9', output_file)
        
        # Verify file created
        self.assertTrue(os.path.exists(result))
        
        # Verify correct pages extracted (1,3,5,7,8,9 = 6 pages)
        reader = PdfReader(result)
        self.assertEqual(len(reader.pages), 6)


class TestBatchProcessingWorkflow(unittest.TestCase):
    """Test batch processing workflow end-to-end."""
    
    @classmethod
    def setUpClass(cls):
        """Create test environment with multiple PDFs."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.pdf_dir = os.path.join(cls.temp_dir, 'input_pdfs')
        os.makedirs(cls.pdf_dir)
        
        # Create 5 test PDFs with different page counts
        cls.pdf_configs = [
            ('doc1.pdf', 3),
            ('doc2.pdf', 5),
            ('doc3.pdf', 7),
            ('doc4.pdf', 4),
            ('doc5.pdf', 6),
        ]
        
        for filename, num_pages in cls.pdf_configs:
            pdf_path = os.path.join(cls.pdf_dir, filename)
            writer = PdfWriter()
            for _ in range(num_pages):
                writer.add_blank_page(width=612, height=792)
            
            writer.add_metadata({
                '/Title': f'{filename} Document',
                '/Author': 'Batch Test'
            })
            
            with open(pdf_path, 'wb') as f:
                writer.write(f)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_batch_split_pages_workflow(self):
        processor = BatchProcessor()
        
        # Step 1: Find all PDFs
        pdf_files = processor.find_pdf_files(self.pdf_dir)
        self.assertEqual(len(pdf_files), 5)
        output_dir = os.path.join(self.temp_dir, 'batch_output')
        manifest_path = os.path.join(output_dir, 'manifest.json')
        processor = BatchProcessor(manifest_path=manifest_path, resume=False)

        # Step 2: Run batch operation
        results = processor.process_directory(
            self.pdf_dir,
            'pages',
            output_dir,
            options={'prefix': 'page', 'padding': 2}
        )
        self.assertEqual(results.total, 5)
        self.assertEqual(results.success, 5)
        self.assertEqual(results.failure, 0)
        self.assertEqual(results.skipped, 0)
        self.assertEqual(results.total_attempts, 5)
        
        # Verify all PDFs processed
        self.assertEqual(results.success, 5)
        self.assertEqual(results.failure, 0)
        self.assertEqual(results.skipped, 0)
        self.assertEqual(results.total_attempts, 5)
        
        # Step 4: Verify correct directory structure
        for filename, num_pages in self.pdf_configs:
            doc_name = filename.replace('.pdf', '')
            doc_dir = os.path.join(output_dir, doc_name)
            
            # Check subdirectory exists
            self.assertTrue(os.path.exists(doc_dir))
            
            # Check correct number of files
            files = list(Path(doc_dir).glob('*.pdf'))
            self.assertEqual(len(files), num_pages)
        
        # Step 5: Check summary report
        self.assertEqual(len(results.results), 5)
        
        for result in results.results:
            self.assertEqual(result['status'], 'success')
            self.assertIn('files_created', result)
    
    def test_batch_chunks_workflow(self):
        """Test batch chunks workflow."""
        output_dir = os.path.join(self.temp_dir, 'batch_chunks')
        manifest_path = os.path.join(output_dir, 'manifest.json')
        processor = BatchProcessor(manifest_path=manifest_path)

        results = processor.process_directory(
            self.pdf_dir,
            'chunks',
            output_dir,
            options={'chunk_size': 2}
        )
        self.assertEqual(results.total, 5)
        self.assertEqual(results.success, 5)
        self.assertEqual(results.failure, 0)
        self.assertEqual(results.skipped, 0)
        self.assertEqual(results.total_attempts, 5)
        
        # Verify chunks created correctly
        for filename, num_pages in self.pdf_configs:
            doc_name = filename.replace('.pdf', '')
            doc_dir = os.path.join(output_dir, doc_name)
            
            # Calculate expected chunks
            import math
            expected_chunks = math.ceil(num_pages / 2)
            
            files = list(Path(doc_dir).glob('*.pdf'))
            self.assertEqual(len(files), expected_chunks)


class TestErrorRecoveryWorkflow(unittest.TestCase):
    """Test error recovery and resilience."""
    
    @classmethod
    def setUpClass(cls):
        """Create test environment with mixed valid/invalid PDFs."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.pdf_dir = os.path.join(cls.temp_dir, 'mixed_pdfs')
        os.makedirs(cls.pdf_dir)
        
        # Create 3 valid PDFs
        for i in range(1, 4):
            pdf_path = os.path.join(cls.pdf_dir, f'valid{i}.pdf')
            writer = PdfWriter()
            for _ in range(3):
                writer.add_blank_page(width=612, height=792)
            with open(pdf_path, 'wb') as f:
                writer.write(f)
        
        # Create 1 corrupted PDF (just text file with .pdf extension)
        corrupted_path = os.path.join(cls.pdf_dir, 'corrupted.pdf')
        with open(corrupted_path, 'w') as f:
            f.write('This is not a valid PDF file')
        
        # Create 1 empty PDF
        empty_path = os.path.join(cls.pdf_dir, 'empty.pdf')
        with open(empty_path, 'wb') as f:
            f.write(b'%PDF-1.4\n%%EOF')
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_batch_continues_after_errors(self):
        """Test that batch processing continues after encountering errors."""
        processor = BatchProcessor()
        
        output_dir = os.path.join(self.temp_dir, 'error_recovery')
        results = processor.process_directory(
            self.pdf_dir,
            'pages',
            output_dir,
            options={'prefix': 'page'}
        )
        
        # Verify some succeeded and some failed
        self.assertEqual(results.total, 5)
        self.assertGreater(results.success, 0)  # At least some succeeded
        self.assertGreater(results.failure, 0)  # At least some failed
        
        # Verify valid files were processed
        self.assertGreaterEqual(results.success, 3)  # 3 valid PDFs
        
        # Check that error information is captured
        failed_results = [r for r in results.results if r['status'] == 'failure']
        self.assertGreater(len(failed_results), 0)
        
        for failed in failed_results:
            self.assertIn('error', failed)
            self.assertIsInstance(failed['error'], str)
    
    def test_invalid_range_error_handling(self):
        """Test error handling for invalid page ranges."""
        # Create a 5-page PDF
        pdf_path = os.path.join(self.temp_dir, 'test_5pages.pdf')
        writer = PdfWriter()
        for _ in range(5):
            writer.add_blank_page(width=612, height=792)
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        
        splitter = PDFSplitter(pdf_path)
        
        # Try to extract invalid range
        with self.assertRaises(PageOutOfBoundsError) as cm:
            splitter.split_by_range(
                self.temp_dir,
                start_page=1,
                end_page=10  # Beyond page count
            )
        
        self.assertIn('Invalid page range', str(cm.exception))
    
    def test_invalid_page_spec_error_handling(self):
        """Test error handling for invalid page specifications."""
        pdf_path = os.path.join(self.temp_dir, 'test_5pages.pdf')
        if not os.path.exists(pdf_path):
            writer = PdfWriter()
            for _ in range(5):
                writer.add_blank_page(width=612, height=792)
            with open(pdf_path, 'wb') as f:
                writer.write(f)
        
        splitter = PDFSplitter(pdf_path)
        
        # Try to extract pages out of bounds
        with self.assertRaises(PageOutOfBoundsError) as cm:
            output_file = os.path.join(self.temp_dir, 'invalid_extract.pdf')
            splitter.extract_pages('1,10,20', output_file)
        
        self.assertIn('out of bounds', str(cm.exception))


class TestEndToEndScenarios(unittest.TestCase):
    """Test realistic end-to-end scenarios."""
    
    @classmethod
    def setUpClass(cls):
        """Create test environment."""
        cls.temp_dir = tempfile.mkdtemp()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_complete_document_processing_pipeline(self):
        """Test a complete document processing pipeline."""
        # Step 1: Create a large document
        large_doc = os.path.join(self.temp_dir, 'large_document.pdf')
        writer = PdfWriter()
        for i in range(50):
            writer.add_blank_page(width=612, height=792)
        writer.add_metadata({
            '/Title': 'Large Document',
            '/Author': 'Pipeline Test'
        })
        with open(large_doc, 'wb') as f:
            writer.write(f)
        
        splitter = PDFSplitter(large_doc)
        
        # Step 2: Extract first 10 pages
        first_10 = os.path.join(self.temp_dir, 'first_10.pdf')
        splitter.extract_pages('1-10', first_10)
        self.assertTrue(os.path.exists(first_10))
        
        # Step 3: Split those 10 pages into chunks of 3
        chunk_splitter = PDFSplitter(first_10)
        chunks_dir = os.path.join(self.temp_dir, 'chunks')
        chunks = chunk_splitter.split_by_chunks(3, chunks_dir)
        
        # Verify pipeline results
        self.assertEqual(len(chunks), 4)  # 10 pages / 3 = 4 chunks
        
        # Step 4: Verify metadata preserved through pipeline
        for chunk_file in chunks:
            reader = PdfReader(chunk_file)
            if reader.metadata and reader.metadata.title:
                self.assertIn('Large Document', reader.metadata.title)
    
    def test_multiple_operations_on_same_pdf(self):
        """Test multiple operations on the same PDF."""
        # Create test PDF
        test_pdf = os.path.join(self.temp_dir, 'multi_op.pdf')
        writer = PdfWriter()
        for _ in range(20):
            writer.add_blank_page(width=612, height=792)
        with open(test_pdf, 'wb') as f:
            writer.write(f)
        
        splitter = PDFSplitter(test_pdf)
        
        # Operation 1: Split to pages
        pages_dir = os.path.join(self.temp_dir, 'all_pages')
        pages = splitter.split_to_pages(pages_dir)
        self.assertEqual(len(pages), 20)
        
        # Operation 2: Extract range
        range_file = os.path.join(self.temp_dir, 'range.pdf')
        range_result = splitter.split_by_range(self.temp_dir, 5, 15, 'range.pdf')
        self.assertTrue(os.path.exists(range_result))
        
        # Operation 3: Split by chunks
        chunks_dir = os.path.join(self.temp_dir, 'chunks_multi')
        chunks = splitter.split_by_chunks(5, chunks_dir)
        self.assertEqual(len(chunks), 4)
        
        # Operation 4: Extract specific pages
        extract_file = os.path.join(self.temp_dir, 'extracted_multi.pdf')
        extracted = splitter.extract_pages([1, 5, 10, 15, 20], extract_file)
        reader = PdfReader(extracted)
        self.assertEqual(len(reader.pages), 5)


if __name__ == '__main__':
    unittest.main()
