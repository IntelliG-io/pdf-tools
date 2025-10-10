# IntelliPDF Backend

This FastAPI application exposes a thin HTTP layer over the shared
`intellipdf` library so web clients can orchestrate PDF workflows.

## Getting started

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Once running, the service will be available at <http://127.0.0.1:8000>.

### Example workflow

1. Send a `POST` request to `/merge` with multiple `files` form fields.
2. Receive the merged PDF as the binary response.

The `/health` endpoint returns a JSON payload and can be used for liveness
checks.
