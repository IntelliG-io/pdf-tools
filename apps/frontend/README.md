# IntelliPDF Frontend

A lightweight Next.js dashboard that interacts with the FastAPI backend to
trigger PDF workflows exposed by the shared `intellipdf` library.

## Getting started

```bash
cd apps/frontend
npm install
npm run dev
```

The development server defaults to <http://127.0.0.1:3000>. Configure the API
URL by exporting `NEXT_PUBLIC_BACKEND_URL` before starting the dev server.
