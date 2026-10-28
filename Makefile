.PHONY: check format lint test typecheck rust

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
