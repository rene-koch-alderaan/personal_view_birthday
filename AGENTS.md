# Repository Guidelines

## Project Structure & Module Organization
- `app/main.py`: FastAPI application entrypoint; mounts API routers.
- `app/routers/`: Route handlers (`astro.py`, `radix.py`, `radix_kerykeion.py`).
- `app/models/schemas.py`: Pydantic v2 models shared across endpoints.
- `app/services/`: Ephemeris providers and persistence helpers.
- `app/config.py`: Settings via `.env` (pydantic-settings).
- `app/db.py`: Optional PostgreSQL pool (requires `DATABASE_URL`).
- `ephe/` and `app/ephe/`: Swiss Ephemeris data files.
- `Dockerfile`, `.env`, `radix.html`, `radix.svg`: Container, config, and sample assets.

## Build, Test, and Development Commands
- Run locally: `uvicorn app.main:app --reload --port 8000`
  - Open docs: `http://localhost:8000/docs` (Swagger UI)
- Docker build: `docker build -t personalview-api .`
- Docker run: `docker run --rm -p 8000:8000 --env-file .env -v $(pwd)/ephe:/app/ephe personalview-api`

## Coding Style & Naming Conventions
- Python 3.11, FastAPI, Pydantic v2; use type hints everywhere.
- Indentation: 4 spaces; line length ~88–100 chars.
- Modules: `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`.
- Routers live in `app/routers/` with `APIRouter(prefix="/v1/...", tags=[...])`.
- Models go in `app/models/schemas.py`; avoid circular imports.

## Testing Guidelines
- Framework: pytest (recommended). Place tests under `tests/` mirroring `app/`.
- Name tests `test_*.py`; use factory data for `CalcRequest` and endpoints.
- Run tests: `pytest -q` (add `--cov=app` when coverage is configured).

## Commit & Pull Request Guidelines
- Commits: imperative mood, scoped and focused, e.g., `feat(radix): add SVG renderer`.
- PRs: include purpose, linked issue, run instructions, and screenshots of `/docs` or sample SVG/HTML output when relevant.
- Ensure CI or local checks pass (lint/tests if present) and update docs when behavior changes.

## Security & Configuration Tips
- Configure via `.env` (examples in repo): `ASTRO_BACKEND`, `SE_EPHE_PATH`, `DEFAULT_HOUSE_SYSTEM`, `TZ_DEFAULT`, `APP_PORT`, optional `DATABASE_URL` for persistence.
- Do not commit secrets or private ephemeris data; mount `ephe/` at runtime if large.
- If using persistence, set `DATABASE_URL=postgresql://user:pass@host:5432/db`.
- Swiss Ephemeris: ensure `SE_EPHE_PATH` points to available data (e.g., `/app/ephe`).

