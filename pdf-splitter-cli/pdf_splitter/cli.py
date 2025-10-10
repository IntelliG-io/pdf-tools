"""
Command-line interface for PDF splitter.
"""

import os
import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TaskProgressColumn
from rich.table import Table

from pdf_splitter.splitter import PDFSplitter, BatchProcessor
from pdf_splitter.backends.pypdf_backend import PypdfBackend
from pdf_splitter.utils import get_pdf_info, validate_pdf, format_file_size

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    PDF Splitter CLI - Split PDF files into individual pages or ranges.
    """
    pass


@cli.command(name="split-pages")
@click.argument('input_pdf', type=click.Path(exists=True))
@click.option(
    '--output-dir', '-o',
    default='./output',
    help='Output directory for split pages',
    type=click.Path()
)
@click.option(
    '--prefix', '-p',
    default='page',
    help='Prefix for output filenames',
    type=str
)
@click.option(
    '--padding',
    default=3,
    help='Number of digits for page numbering',
    type=int
)
def split_pages(input_pdf, output_dir, prefix, padding):
    """
    Split PDF into individual pages.
    
    Examples:
    
        pdf-splitter split-pages input.pdf
        
        pdf-splitter split-pages input.pdf -o my_pages
        
        pdf-splitter split-pages input.pdf -p chapter --padding 4
    """
    try:
        # Validate PDF
        console.print("\n[bold cyan]Validating PDF...[/bold cyan]")
        is_valid, error_msg = validate_pdf(input_pdf)
        
        if not is_valid:
            console.print(f"[bold red]✗ Error:[/bold red] {error_msg}")
            sys.exit(1)
        
        # Get PDF info
        info = get_pdf_info(input_pdf)
        
        # Display PDF information
        info_table = Table(title="PDF Information", show_header=False)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")
        
        info_table.add_row("File", os.path.basename(input_pdf))
        info_table.add_row("Pages", str(info['num_pages']))
        info_table.add_row("Size", format_file_size(info['file_size']))
        if info['title']:
            info_table.add_row("Title", info['title'])
        
        console.print(info_table)
        
        # Initialize splitter
        console.print("\n[bold cyan]Initializing splitter...[/bold cyan]")
        splitter = PDFSplitter(input_pdf)
        
        # Split pages with progress bar
        console.print(f"\n[bold cyan]Splitting {info['num_pages']} pages...[/bold cyan]")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Splitting pages", total=info['num_pages'])
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            created_files = splitter.split_to_pages(output_dir, prefix, padding, progress_callback=update_progress)
        
        # Display results
        console.print(f"\n[bold green]✓ Successfully split into {len(created_files)} files[/bold green]")
        console.print(f"[dim]Output directory: {os.path.abspath(output_dir)}[/dim]")
        
        # Show sample of created files
        console.print("\n[bold]Created files:[/bold]")
        sample_size = min(5, len(created_files))
        for file_path in created_files[:sample_size]:
            console.print(f"  • {os.path.basename(file_path)}")
        
        if len(created_files) > sample_size:
            console.print(f"  ... and {len(created_files) - sample_size} more")
        
        console.print()
        
    except FileNotFoundError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="info")
@click.argument('input_pdf', type=click.Path(exists=True))
def show_info(input_pdf):
    """
    Display information about a PDF file.
    
    Example:
    
        pdf-splitter info input.pdf
    """
    try:
        # Validate PDF
        is_valid, error_msg = validate_pdf(input_pdf)
        
        if not is_valid:
            console.print(f"[bold red]✗ Error:[/bold red] {error_msg}")
            sys.exit(1)
        
        # Get PDF info
        info = get_pdf_info(input_pdf)
        
        # Create detailed info table
        table = Table(title=f"PDF Information: {os.path.basename(input_pdf)}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("File Path", os.path.abspath(input_pdf))
        table.add_row("File Size", format_file_size(info['file_size']))
        table.add_row("Number of Pages", str(info['num_pages']))
        table.add_row("Encrypted", "Yes" if info['is_encrypted'] else "No")
        
        if info['title']:
            table.add_row("Title", info['title'])
        if info['author']:
            table.add_row("Author", info['author'])
        if info['subject']:
            table.add_row("Subject", info['subject'])
        if info['creator']:
            table.add_row("Creator", info['creator'])
        if info['producer']:
            table.add_row("Producer", info['producer'])
        
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="split-range")
@click.argument('input_pdf', type=click.Path(exists=True))
@click.option(
    '--start', '-s',
    required=True,
    help='Starting page number (1-indexed)',
    type=int
)
@click.option(
    '--end', '-e',
    required=True,
    help='Ending page number (1-indexed, inclusive)',
    type=int
)
@click.option(
    '--output-dir', '-o',
    default='./output',
    help='Output directory',
    type=click.Path()
)
@click.option(
    '--output-name', '-n',
    help='Custom output filename',
    type=str
)
def split_range(input_pdf, start, end, output_dir, output_name):
    """
    Extract a range of pages into a single PDF.
    
    Example:
    
        pdf-splitter split-range input.pdf --start 5 --end 10
        
        pdf-splitter split-range input.pdf -s 1 -e 3 -n chapter1.pdf
    """
    try:
        # Validate PDF
        is_valid, error_msg = validate_pdf(input_pdf)
        
        if not is_valid:
            console.print(f"[bold red]✗ Error:[/bold red] {error_msg}")
            sys.exit(1)
        
        # Initialize splitter
        splitter = PDFSplitter(input_pdf)
        
        console.print(f"\n[bold cyan]Extracting pages {start}-{end}...[/bold cyan]")
        
        # Split by range
        output_file = splitter.split_by_range(output_dir, start, end, output_name)
        
        console.print(f"\n[bold green]✓ Successfully created:[/bold green] {output_file}")
        console.print()
        
    except ValueError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="split-ranges")
@click.argument('input_pdf', type=click.Path(exists=True))
@click.option(
    '--ranges', '-r',
    required=True,
    help="Page ranges (e.g., '1-5,6-10,11-15')",
    type=str
)
@click.option(
    '--output-dir', '-o',
    default='./output',
    help='Output directory',
    type=click.Path()
)
@click.option(
    '--prefix', '-p',
    default='range',
    help='Prefix for output filenames',
    type=str
)
def split_ranges(input_pdf, ranges, output_dir, prefix):
    """
    Split PDF into specified page ranges.
    
    Examples:
    
        pdf-splitter split-ranges input.pdf -r '1-5,6-10'
        
        pdf-splitter split-ranges input.pdf --ranges '1-3,7-9,12-20' -o chapters
        
        pdf-splitter split-ranges input.pdf -r '1-10,11-20,21-30' -p section
    """
    try:
        # Validate PDF
        console.print("\n[bold cyan]Validating PDF...[/bold cyan]")
        is_valid, error_msg = validate_pdf(input_pdf)
        
        if not is_valid:
            console.print(f"[bold red]✗ Error:[/bold red] {error_msg}")
            sys.exit(1)
        
        # Get PDF info
        info = get_pdf_info(input_pdf)
        
        # Display PDF information
        info_table = Table(title="PDF Information", show_header=False)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")
        
        info_table.add_row("File", os.path.basename(input_pdf))
        info_table.add_row("Pages", str(info['num_pages']))
        info_table.add_row("Size", format_file_size(info['file_size']))
        
        console.print(info_table)
        
        # Initialize splitter
        console.print("\n[bold cyan]Parsing ranges...[/bold cyan]")
        splitter = PDFSplitter(input_pdf)
        
        # Parse and display ranges
        from pdf_splitter.splitter import parse_ranges
        parsed_ranges = parse_ranges(ranges)
        
        console.print(f"[dim]Ranges to extract: {', '.join([f'{s}-{e}' for s, e in parsed_ranges])}[/dim]")
        
        # Split by ranges with progress
        console.print(f"\n[bold cyan]Splitting into {len(parsed_ranges)} range(s)...[/bold cyan]")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing ranges", total=len(parsed_ranges))
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            created_files = splitter.split_by_ranges(ranges, output_dir, prefix, progress_callback=update_progress)
        
        # Display results
        console.print(f"\n[bold green]✓ Successfully created {len(created_files)} file(s)[/bold green]")
        console.print(f"[dim]Output directory: {os.path.abspath(output_dir)}[/dim]")
        
        # Show created files
        console.print("\n[bold]Created files:[/bold]")
        for file_path in created_files:
            console.print(f"  • {os.path.basename(file_path)}")
        
        console.print()
        
    except ValueError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="split-chunks")
@click.argument('input_pdf', type=click.Path(exists=True))
@click.option(
    '--size', '-s',
    required=True,
    help='Number of pages per chunk',
    type=int
)
@click.option(
    '--output-dir', '-o',
    default='./output',
    help='Output directory',
    type=click.Path()
)
@click.option(
    '--prefix', '-p',
    default='chunk',
    help='Prefix for output filenames',
    type=str
)
def split_chunks(input_pdf, size, output_dir, prefix):
    """
    Split PDF into chunks of N pages.
    
    Examples:
    
        pdf-splitter split-chunks input.pdf -s 5
        
        pdf-splitter split-chunks input.pdf --size 10 -o chunks
        
        pdf-splitter split-chunks input.pdf -s 5 -p section
    """
    try:
        # Validate PDF
        console.print("\n[bold cyan]Validating PDF...[/bold cyan]")
        is_valid, error_msg = validate_pdf(input_pdf)
        
        if not is_valid:
            console.print(f"[bold red]✗ Error:[/bold red] {error_msg}")
            sys.exit(1)
        
        # Get PDF info
        info = get_pdf_info(input_pdf)
        
        # Display PDF information
        info_table = Table(title="PDF Information", show_header=False)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")
        
        info_table.add_row("File", os.path.basename(input_pdf))
        info_table.add_row("Pages", str(info['num_pages']))
        info_table.add_row("Size", format_file_size(info['file_size']))
        info_table.add_row("Chunk Size", f"{size} pages")
        
        # Calculate number of chunks
        import math
        num_chunks = math.ceil(info['num_pages'] / size)
        info_table.add_row("Chunks", str(num_chunks))
        
        console.print(info_table)
        
        # Initialize splitter
        console.print("\n[bold cyan]Initializing splitter...[/bold cyan]")
        splitter = PDFSplitter(input_pdf)
        
        # Split by chunks with progress
        console.print(f"\n[bold cyan]Splitting into {num_chunks} chunk(s)...[/bold cyan]")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing chunks", total=num_chunks)
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            created_files = splitter.split_by_chunks(size, output_dir, prefix, progress_callback=update_progress)
        
        # Display results
        console.print(f"\n[bold green]✓ Successfully created {len(created_files)} chunk(s)[/bold green]")
        console.print(f"[dim]Output directory: {os.path.abspath(output_dir)}[/dim]")
        
        # Show created files with page info
        console.print("\n[bold]Created files:[/bold]")
        for i, file_path in enumerate(created_files):
            # Calculate pages in this chunk
            start_page = i * size + 1
            end_page = min((i + 1) * size, info['num_pages'])
            page_count = end_page - start_page + 1
            
            console.print(f"  • {os.path.basename(file_path)} [dim](pages {start_page}-{end_page}, {page_count} pages)[/dim]")
        
        console.print()
        
    except ValueError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="extract")
@click.argument('input_pdf', type=click.Path(exists=True))
@click.option(
    '--pages', '-p',
    required=True,
    help="Pages to extract (e.g., '1,3,5,7-10')",
    type=str
)
@click.option(
    '--output', '-o',
    required=True,
    help='Output PDF path',
    type=click.Path()
)
def extract(input_pdf, pages, output):
    """
    Extract specific pages into a single new PDF.
    
    Examples:
    
        pdf-splitter extract input.pdf -p '1,3,5' -o selected.pdf
        
        pdf-splitter extract input.pdf --pages '1-5,10,15-20' --output extracted.pdf
        
        pdf-splitter extract input.pdf -p '2,4,6,8-12' -o even_pages.pdf
    """
    try:
        # Validate PDF
        console.print("\n[bold cyan]Validating PDF...[/bold cyan]")
        is_valid, error_msg = validate_pdf(input_pdf)
        
        if not is_valid:
            console.print(f"[bold red]✗ Error:[/bold red] {error_msg}")
            sys.exit(1)
        
        # Get PDF info
        info = get_pdf_info(input_pdf)
        
        # Display PDF information
        info_table = Table(title="PDF Information", show_header=False)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")
        
        info_table.add_row("File", os.path.basename(input_pdf))
        info_table.add_row("Total Pages", str(info['num_pages']))
        info_table.add_row("Size", format_file_size(info['file_size']))
        
        console.print(info_table)
        
        # Initialize splitter
        console.print("\n[bold cyan]Parsing page specification...[/bold cyan]")
        splitter = PDFSplitter(input_pdf)
        
        # Parse pages
        from pdf_splitter.splitter import parse_page_spec
        page_list = parse_page_spec(pages)
        
        console.print(f"[dim]Pages to extract: {', '.join(map(str, page_list))}[/dim]")
        console.print(f"[dim]Total pages to extract: {len(page_list)}[/dim]")
        
        # Extract pages with progress
        console.print(f"\n[bold cyan]Extracting {len(page_list)} page(s)...[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting pages...", total=None)
            output_file = splitter.extract_pages(pages, output)
            progress.update(task, completed=True)
        
        # Display results
        console.print(f"\n[bold green]✓ Successfully created:[/bold green] {output_file}")
        
        # Show file info
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            console.print(f"[dim]Output size: {format_file_size(file_size)}[/dim]")
            console.print(f"[dim]Pages extracted: {len(page_list)} of {info['num_pages']}[/dim]")
        
        console.print()
        
    except ValueError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="batch")
@click.argument('input_dir', type=click.Path(exists=True))
@click.option(
    '--operation', '-op',
    required=True,
    type=click.Choice(['pages', 'chunks', 'ranges'], case_sensitive=False),
    help="Operation to perform on all PDFs"
)
@click.option(
    '--output-dir', '-o',
    default='./batch_output',
    help='Base output directory',
    type=click.Path()
)
@click.option(
    '--size', '-s',
    type=int,
    help='Chunk size (for chunks operation)'
)
@click.option(
    '--ranges', '-r',
    type=str,
    help="Page ranges (for ranges operation, e.g., '1-5,6-10')"
)
@click.option(
    '--prefix', '-p',
    default=None,
    help='Prefix for output filenames',
    type=str
)
@click.option(
    '--padding',
    default=3,
    type=int,
    help='Number of digits for page numbering (for pages operation)'
)
def batch(input_dir, operation, output_dir, size, ranges, prefix, padding):
    """
    Process multiple PDF files at once.
    
    Examples:
    
        pdf-splitter batch ./pdfs --operation pages
        
        pdf-splitter batch ./docs --operation chunks --size 5
        
        pdf-splitter batch ./files --operation ranges -r '1-5,6-10'
    """
    try:
        # Initialize batch processor
        console.print("\n[bold cyan]Initializing batch processor...[/bold cyan]")
        processor = BatchProcessor(backend=PypdfBackend())
        
        # Find PDF files
        console.print(f"[bold cyan]Scanning directory:[/bold cyan] {input_dir}")
        pdf_files = processor.find_pdf_files(input_dir)
        
        if not pdf_files:
            console.print(f"\n[bold yellow]⚠ No PDF files found in {input_dir}[/bold yellow]")
            sys.exit(0)
        
        console.print(f"[bold green]✓ Found {len(pdf_files)} PDF file(s)[/bold green]\n")
        
        # Display files to be processed
        files_table = Table(title="Files to Process", show_header=True)
        files_table.add_column("#", style="cyan", width=4)
        files_table.add_column("Filename", style="green")
        
        for idx, pdf_file in enumerate(pdf_files[:10], 1):  # Show first 10
            files_table.add_row(str(idx), os.path.basename(pdf_file))
        
        if len(pdf_files) > 10:
            files_table.add_row("...", f"and {len(pdf_files) - 10} more")
        
        console.print(files_table)
        
        # Prepare options
        options = {}
        if operation == 'pages':
            options['prefix'] = prefix or 'page'
            options['padding'] = padding
        elif operation == 'chunks':
            if not size:
                console.print("\n[bold red]✗ Error:[/bold red] --size is required for chunks operation")
                sys.exit(1)
            options['chunk_size'] = size
            options['prefix'] = prefix or 'chunk'
        elif operation == 'ranges':
            if not ranges:
                console.print("\n[bold red]✗ Error:[/bold red] --ranges is required for ranges operation")
                sys.exit(1)
            options['ranges'] = ranges
            options['prefix'] = prefix or 'range'
        
        # Process with progress bar
        console.print(f"\n[bold cyan]Processing {len(pdf_files)} PDF(s) with operation: {operation}[/bold cyan]\n")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing PDFs", total=len(pdf_files))
            
            def update_progress(filename, current, total):
                progress.update(task, completed=current, description=f"Processing: {filename}")
            
            results = processor.process_directory(
                input_dir,
                operation,
                output_dir,
                options=options,
                progress_callback=update_progress
            )
        
        # Display summary
        console.print("\n[bold]Batch Processing Summary[/bold]")
        console.print("=" * 50)
        
        summary_table = Table(show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Files", str(results['total']))
        summary_table.add_row("✓ Successful", f"[green]{results['success']}[/green]")
        summary_table.add_row("✗ Failed", f"[red]{results['failure']}[/red]")
        summary_table.add_row("Output Directory", os.path.abspath(output_dir))
        
        console.print(summary_table)
        
        # Show detailed results
        if results['failure'] > 0:
            console.print("\n[bold red]Failed Files:[/bold red]")
            for result in results['results']:
                if result['status'] == 'failure':
                    console.print(f"  ✗ {os.path.basename(result['file'])}: {result['error']}")
        
        # Show success details
        if results['success'] > 0:
            console.print("\n[bold green]Successfully Processed:[/bold green]")
            for result in results['results'][:5]:  # Show first 5
                if result['status'] == 'success':
                    console.print(f"  ✓ {os.path.basename(result['file'])} → {result['files_created']} file(s)")
            
            if results['success'] > 5:
                console.print(f"  ... and {results['success'] - 5} more")
        
        console.print()
        
        # Exit with appropriate code
        sys.exit(0 if results['failure'] == 0 else 1)
        
    except FileNotFoundError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
