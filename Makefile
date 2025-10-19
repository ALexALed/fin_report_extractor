.PHONY: test lint dev

test:
	uv run pytest

lint:
	uv run ruff check

dev:
	uv run fastapi dev ./src/app/main.py
