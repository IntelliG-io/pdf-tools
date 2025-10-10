# Quick Start Guide

## Installation (30 seconds)

```bash
cd pdf-splitter-cli
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Common Commands

### Split all pages
```bash
pdf-splitter split-pages document.pdf
```

### Split with custom output
```bash
pdf-splitter split-pages document.pdf -o my_output -p page
```

### Extract specific pages
```bash
pdf-splitter split-range document.pdf -s 5 -e 10
```

### Split by custom ranges
```bash
pdf-splitter split-ranges document.pdf -r '1-10,11-20,21-30'
```

### Split into equal chunks
```bash
pdf-splitter split-chunks document.pdf -s 5
```

### Extract specific pages
```bash
pdf-splitter extract document.pdf -p '1,3,5,7-10' -o selected.pdf
```

### View PDF info
```bash
pdf-splitter info document.pdf
```

## Quick Test

```bash
# Create test PDF
python create_test_pdf.py

# Split it
pdf-splitter split-pages test_10pages.pdf

# Check output
ls output/
```

That's it! 🎉
