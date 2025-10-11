# PDF to Word Conversion

The PaperFlow API provides functionality to convert PDF documents to Word (.docx) format with both basic and advanced options. This functionality uses LibreOffice for high-quality conversions.

> **Note:** LibreOffice must be installed on the server for this functionality to work. See the README for installation instructions.

## Basic Conversion

The basic conversion provides a simple way to convert PDFs to Word documents with reasonable default settings.

### Endpoint

```
POST /api/pdf/convert/to-word/basic
```

### Request

- Form data with key `file` containing a PDF file.

### Response

```json
{
  "message": "PDF successfully converted to Word document",
  "convertedFilePath": "converted-1234567890.docx",
  "originalFileInfo": {
    "size": "1024 KB",
    "pageCount": 10
  }
}
```

## Advanced Conversion

The advanced conversion allows fine-grained control over the conversion process, including quality settings, font handling, and formatting options.

### Endpoint

```
POST /api/pdf/convert/to-word/advanced
```

### Request

- Form data with key `file` containing a PDF file.
- Optional form data with key `options` containing a JSON object with the following structure:

```json
{
  "quality": "standard",
  "fontHandling": "substitute",
  "formatting": {
    "preserveImages": true,
    "preserveLinks": true,
    "preserveTables": true,
    "preserveFormattingMarks": true,
    "defaultFontFamily": "Arial"
  },
  "advanced": {
    "detectLists": true,
    "detectHeadings": true,
    "detectTables": true,
    "preserveColorProfile": true,
    "optimizeForAccessibility": false,
    "includeDocumentProperties": true
  }
}
```

### Response

```json
{
  "message": "PDF successfully converted to Word document with advanced options",
  "convertedFilePath": "converted-advanced-1234567890.docx",
  "originalFileInfo": {
    "size": "1024 KB",
    "pageCount": 10
  },
  "appliedOptions": {
    "quality": "standard",
    "fontHandling": "substitute",
    "formatting": {
      "preserveImages": true,
      "preserveLinks": true,
      "preserveTables": true
    },
    "advanced": {
      "detectLists": true,
      "detectHeadings": true,
      "detectTables": true,
      "preserveColorProfile": true
    }
  }
}
```

## Download Converted Document

### Endpoint

```
GET /api/pdf/convert/download/:filename
```

### Request

- URL parameter `filename` is the name of the converted file (from the `convertedFilePath` response field).

### Response

- Word document (.docx) file download.

## Configuration Options

### Quality Levels

The `quality` option in advanced conversion controls the overall conversion quality and processing time:

- `basic`: Fastest conversion with minimal formatting. Focuses on text content only.
- `standard`: Good balance between speed and formatting quality. Preserves most formatting.
- `enhanced`: Better text layout preservation but slower. Preserves more document features.
- `precise`: Best formatting fidelity but slowest performance. Preserves most document features.

### Font Handling

The `fontHandling` option controls how fonts are managed during conversion:

- `substitute`: Use system fonts when original font is not available (default).
- `embed`: Embed fonts in the document when possible.
- `fallback_only`: Only substitute when absolutely necessary.

### Formatting Options

The `formatting` object controls document formatting preservation:

- `preserveImages`: Whether to include images in the converted document (default: `true`).
- `preserveLinks`: Whether to maintain hyperlinks (default: `true`).
- `preserveTables`: Whether to preserve table structures (default: `true`).
- `preserveFormattingMarks`: Whether to maintain special formatting marks (default: `true`).
- `defaultFontFamily`: Font family to use when the original font is not available.

### Advanced Options

The `advanced` object provides control over more specialized conversion features:

- `detectLists`: Automatically identify and format lists (default: `true`).
- `detectHeadings`: Automatically identify and format headings (default: `true`).
- `detectTables`: Automatically identify and format tables (default: `true`).
- `preserveColorProfile`: Maintain color information (default: `true`).
- `optimizeForAccessibility`: Make the document more accessible (default: `false`).
- `includeDocumentProperties`: Include metadata like title, author, etc. (default: `true`).

## Error Handling

The API returns appropriate HTTP status codes and error messages for different scenarios:

- `400 Bad Request`: If the file is not a valid PDF or the options are invalid.
- `404 Not Found`: If the requested file does not exist.
- `500 Internal Server Error`: If there's an issue during the conversion process.

Error response example:

```json
{
  "message": "Failed to convert PDF to Word: Document is encrypted"
}
```

## Limitations

- Password-protected or encrypted PDFs cannot be converted.
- Very large PDFs (>100MB) may take a long time to process or fail due to memory constraints.
- Complex formatting such as intricate layouts, annotations, or form fields may not convert perfectly.
- Some font types or styles may be substituted if not available.

## Performance Considerations

- Conversion time increases with document size and complexity.
- Higher quality settings result in longer processing times.
- The API will automatically optimize conversion settings based on document characteristics.
