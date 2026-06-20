# odoo-cli developer tasks. Run `make help` for the list.
# All targets shell out to `uv run`, so tool versions follow uv.lock.

.DEFAULT_GOAL := help
.PHONY: help setup ruff format pyright test check pre-commit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Sync dev environment and install git hooks
	uv sync --dev
	uv run pre-commit install --install-hooks

ruff: ## Lint with ruff (auto-fix)
	uv run ruff check --fix .

format: ## Auto-format with ruff
	uv run ruff format .

pyright: ## Type-check with pyright
	uv run pyright

test: ## Run the unit test suite
	uv run pytest

check: ## Run every pre-commit hook on all files
	uv run pre-commit run --all-files
