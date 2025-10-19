# Financial Report Extractor

FastAPI service that ingests uploaded Excel financial reports, extracts the tabular data, and persists processed metrics using an LLM-powered pipeline.

## Quick Start
- Copy `.env.example` to `.env` and adjust secrets and configuration values.
- Set `OPENAI_API_KEY` (and, if needed, `FIN_REPORT_EXTRACTOR_API_KEY`) in your environment.
- Bring up the full application stack with Docker Compose:
  ```bash
  docker-compose up --build
  ```
- Once the containers are running, the API is available at `http://localhost:8000`.

## Developer Notes
- **Run with Docker Compose**: Use Docker Compose for a parity development environment that starts the API and any backing services together (`docker-compose up --build` on first run, then `docker-compose up`).
- **Makefile commands**:
  - `make dev`: launch FastAPI locally via `uv run fastapi dev ./src/app/main.py` for rapid reloads.
  - `make test`: execute the test suite with `uv run pytest`.
  - `make lint`: run static analysis with `uv run ruff check`.

For additional configuration, inspect `docker-compose.yml` and `.env` variables referenced in `src/app/main.py`.
