# IntelliPDF

IntelliPDF is now organised as a small monorepo that bundles everything
required to build PDF-centric workflows:

- **`packages/intellipdf`** – the core Python toolkit that provides PDF
  splitting, merging, compression, and PDF→DOCX conversion utilities on top
  of [`pypdf`](https://pypi.org/project/pypdf/).
- **`apps/backend`** – a FastAPI service that exposes the library’s
  functionality over HTTP for automation or browser clients.
- **`apps/frontend`** – a Next.js dashboard that talks to the backend for a
  user-friendly experience.

The shared library remains a production-ready, well-typed, and well-tested
foundation for the services that sit on top of it.

## Features

- Split PDFs into page ranges or explicit page selections while preserving
  metadata.
- Extract specific pages into a standalone PDF document.
- Merge multiple PDFs, optionally optimising the result with `qpdf` when
  available.
- Compress PDFs using configurable optimisation backends and surface detailed
  compression metrics.
- Convert PDFs into lightweight DOCX documents that retain page ordering,
  paragraph structure, and semantic roles when working with tagged PDFs, while
  rebuilding PDF outlines as Word bookmarks and linked tables of contents.
- Flatten interactive form fields into readable DOCX tables with checkbox,
  dropdown, and signature placeholders.
- Validate documents and query document information before operating on them.
- Protect documents with passwords or remove encryption when authorised.

## Installation

```bash
pip install intellipdf
```

## Usage

```python
from pathlib import Path

from intellipdf import (
    compress_document,
    is_document_encrypted,
    extract_document_pages,
    merge_documents,
    protect_document,
    split_document,
    convert_document,
    unprotect_document,
)

source = Path("document.pdf")
output_dir = Path("output")

# Split into ranges: pages 1-3 and 4-6.
parts = split_document(source, output_dir, mode="range", ranges="1-3,4-6")

# Extract individual pages to a single file.
extract_document_pages(source, [1, 4, 8], Path("highlights.pdf"))

# Merge multiple PDFs into one.
merge_documents([Path("a.pdf"), Path("b.pdf")], Path("combined.pdf"))

# Compress a document and inspect the resulting metrics.
result = compress_document(source, Path("compressed.pdf"))
print(result.compressed_size, result.backend)

# Convert the PDF into a DOCX file. The converter can accept either a path or
# the primitives returned by IntelliPDF's core parser.
conversion = convert_document(source, Path("document.docx"))
print(conversion.output_path, conversion.tagged_pdf)

# Using primitives that might come from a custom parser.
from intellipdf.pdf2docx import BoundingBox, Page, PdfDocument, TextBlock

page = Page(
    number=0,
    width=200,
    height=200,
    text_blocks=[
        TextBlock(text="Hello", bbox=BoundingBox(0, 0, 200, 20), role="P"),
    ],
    images=[],
    lines=[],
)
doc = PdfDocument(pages=[page], tagged=True)
convert_document(doc, Path("primitives.docx"))

# Streaming mode keeps memory usage predictable by processing PDF pages one at a
# time. Disable it via `ConversionOptions(stream_pages=False)` if you need to
# re-use intermediate page structures.
# Protect a document with a password and later remove it with the correct key.
secure = protect_document(source, Path("secure.pdf"), "s3cr3t")
print(is_document_encrypted(secure))
plain = unprotect_document(secure, Path("plain.pdf"), "s3cr3t")
print(is_document_encrypted(plain))
```

Set the environment variable `INTELLIPDF_SPLIT_OPTIMIZE=1` (or the more general
`INTELLIPDF_OPTIMIZE=1`) to enable optional `qpdf`-based optimisation after
splitting.

## Development

| Area      | How to get started |
|-----------|--------------------|
| Library   | `pip install -e packages/intellipdf[dev]` then `pytest` |
| Backend   | Follow the setup steps in `apps/backend/README.md` and run `uvicorn app.main:app --reload` |
| Frontend  | Follow `apps/frontend/README.md` and run `npm run dev` |

The repository root still includes a `pyproject.toml` so the library can be
installed with `pip install .` if required.

## Containerisation

The backend service is now packaged as a Docker image so it can be run locally
or in production with the same configuration. Build and run it with Docker
Compose:

```bash
docker compose up --build
```

The command exposes the FastAPI app on `http://localhost:8000`. Hot reloading
is not enabled inside the container yet, so use the existing `uvicorn`
instructions in `apps/backend/README.md` for iterative development.

## Deployment pipeline

The repository ships with a GitHub Actions workflow (`.github/workflows/deploy.yml`)
that builds the backend image and deploys it to a DigitalOcean droplet whenever
changes land on the `main` or `dev` branches. The pipeline performs the
following steps:

1. Build a backend image from the monorepo Dockerfile and push it to the GitHub
   Container Registry (GHCR) using tags derived from the branch name (for
   example `production` for `main`, `dev` for the development branch).
2. Connect to the droplet over SSH and run `docker compose` with a branch-aware
   configuration so each environment is updated automatically.

### One-time server preparation

On the droplet, provision directories for both environments and copy the
provided Compose files from `deploy/`:

```bash
sudo mkdir -p /opt/pdf-tools/prod /opt/pdf-tools/dev
cd /opt/pdf-tools
sudo cp ~/pdf-tools/deploy/docker-compose.prod.yml prod/docker-compose.yml
sudo cp ~/pdf-tools/deploy/docker-compose.dev.yml dev/docker-compose.yml
```

Each Compose file expects a `BACKEND_IMAGE` environment variable. The workflow
exports this automatically, but you can test locally by setting it manually:

```bash
BACKEND_IMAGE=ghcr.io/your-user/pdf-tools-backend:production   docker compose -f /opt/pdf-tools/prod/docker-compose.yml up -d
```

Expose the containers behind Nginx using the sample configuration in
`deploy/nginx/pdfspoint.conf`. Update the upstream ports if you prefer different
bindings (the defaults are `9000` for production, `9001` for development, and an
optional `9002` placeholder for the legacy app). Remember to request TLS
certificates—`certbot` can re-use this server block and expand it with HTTPS
settings.

### Required GitHub secrets

Add the following secrets to the repository so the workflow can authenticate and
log into the droplet:

| Secret | Description |
|--------|-------------|
| `DEPLOY_SSH_KEY` | Private key that matches the droplet user’s public key. |
| `DEPLOY_USER` | SSH user name (for example `root` or a dedicated deploy user). |
| `DEV_HOST` | Hostname or IP address for the development deployment (can match the production IP). |
| `PRODUCTION_HOST` | Hostname or IP address for the production deployment. |
| `GHCR_USERNAME` | Account name with read access to the GHCR repository. |
| `GHCR_PASSWORD` | Personal access token with the `read:packages` scope for GHCR. |

With the secrets in place, merging to `main` updates `pdfspoint.com`, merging to
`dev` updates `dev.pdfspoint.com`, and the legacy service can continue to run on
`legacy.pdfspoint.com` until you retire it.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
