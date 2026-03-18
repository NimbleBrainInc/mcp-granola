# MCPB bundle configuration
BUNDLE_NAME = mcp-granola
VERSION ?= 0.2.0

.PHONY: help install dev-install format format-check lint lint-fix typecheck test test-cov clean run check all

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv pip install -e .

dev-install: ## Install the package with dev dependencies
	uv pip install -e ".[dev]"

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check code formatting with ruff
	uv run ruff format --check src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

lint-fix: ## Lint and fix code with ruff
	uv run ruff check --fix src/ tests/

typecheck: ## Type check code with ty
	uv run ty check src/

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/mcp_granola --cov-report=term-missing

clean: ## Clean up build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	rm -rf *.mcpb

run: ## Run the MCP server in stdio mode
	uv run python -m mcp_granola.server

bundle: ## Build MCPB bundle locally
	@./scripts/build-bundle.sh . $(VERSION)

check: format-check lint typecheck test ## Run all checks

all: clean install format lint typecheck test ## Clean, install, format, lint, type check, and test

bump: ## Bump version (usage: make bump VERSION=0.2.0)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make bump VERSION=x.y.z"; exit 1; fi
	jq --arg v "$(VERSION)" '.version = $$v' manifest.json > manifest.tmp.json && mv manifest.tmp.json manifest.json
	sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	sed -i '' 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/mcp_granola/__init__.py
	@echo "Bumped version to $(VERSION)"

# Development shortcuts
fmt: format
t: test
l: lint
tc: typecheck
