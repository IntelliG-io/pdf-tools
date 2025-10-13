# Repository Guidelines

## Project Structure & Module Organization
- `packages/intellipdf/`: plugin-based toolkit; add tools under `tools/<domain>` and share helpers via `core/`.
- `apps/backend/`: FastAPI layer inside `app/`; keep `requirements.txt` current with runtime changes.
- `apps/frontend/`: Vite + React dashboard with code in `src/`, static assets in `public/`, and UX notes in `docs/`.
- `tests/`: pytest suites mirroring the Python package; infrastructure assets live under `docker/`, `deploy/`, and `compose.local.yml`.

## Build, Test, and Development Commands
- Library: `pip install -e packages/intellipdf[dev]` then `pytest -vv --cov=intellipdf`; maintain the `--cov-fail-under=90` threshold.
- Backend: in `apps/backend`, activate a venv, `pip install -r requirements.txt`, and run `uvicorn app.main:app --reload` to serve on `127.0.0.1:8000`.
- Frontend: run `npm install`, `npm run dev`, and `npm run build`; `npm run lint` enforces the shared ESLint profile.
- End-to-end: `docker compose -f compose.local.yml up` launches the stack for manual QA before publishing changes.

## Coding Style & Naming Conventions
- Python uses PEP 8, four-space indentation, type hints, and `snake_case` modules; register new tools with `intellipdf.tools.common.pipeline.register_tool` and keep classes in `PascalCase`.
- Keep business logic in pure functions that return explicit results; store configuration defaults in `core/config.py` instead of scattering literals.
- Frontend code is TypeScript-first: React components in `PascalCase`, hooks as `useCamelCase`, Tailwind utilities for styling, and component assets co-located with their source.

## Testing Guidelines
- Add library tests under `tests/` mirroring the feature path (for example `tests/tools/test_merger.py`).
- The pytest defaults in `pyproject.toml` enforce coverage ≥90%; address regressions or explain the exception in the PR.
- Backend changes should gain `httpx` contract tests in `apps/backend/tests/`; otherwise, document manual API checks.
- Frontend work needs screenshots and manual QA notes until a formal runner ships; add automated tests once tooling is introduced.

## Commit & Pull Request Guidelines
- Use conventional commits (`feat:`, `fix:`, `refactor:`) scoped to a single logical change set.
- Before pushing, run `pytest`, `npm run lint`, and `npm run build`; include failing output when seeking review help.
- PRs need a concise summary, linked issues, UI captures where relevant, and disclosure of new environment variables such as `INTELLIPDF_OPTIMIZE`.
- Tag owners for the touched area and list follow-up tasks to keep context visible.

## Environment & Configuration Tips
- Enable `INTELLIPDF_OPTIMIZE=1` or `INTELLIPDF_SPLIT_OPTIMIZE=1` when profiling compression locally and mention it in docs if required.
- Never commit sensitive PDFs; rely on the `sample-local-*.pdf` placeholders or document synthetic fixtures under `docs/`.
