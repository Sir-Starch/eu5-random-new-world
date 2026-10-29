.PHONY: check format lint test typecheck rust desktop

check: format lint typecheck test rust

format:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run basedpyright

test:
	uv run pytest -q

rust:
	cd native && uv run cargo fmt --check && uv run cargo clippy --all-targets -- -D warnings && uv run cargo test

# The Tauri window (ADR 0011): interface types, unit tests and the Rust shell.
desktop:
	cd desktop && npm ci && npm run check && npm test && npm run build
	cd desktop/src-tauri && cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test
