.PHONY: setup test lint format build clean run help

help: ## Show this help message
	@echo "Professor v10 — Enterprise Architecture Intelligence System"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Create virtual environment and install dependencies
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

test: ## Run tests with pytest
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-report=html

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Format code with black
	black src/ tests/

format-check: ## Check formatting without making changes
	black --check src/ tests/

type-check: ## Run mypy type checker
	mypy src/

build: ## Build distribution packages
	python -m build

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

run: ## Run the system (requires --config argument)
	@echo "Usage: python -m src.main --config examples/sample_repo_config.yaml"
	@echo "Note: Full run capability will be available in Phase 1 implementation."

docs: ## Open design docs index
	@echo "Design docs are in docs/design/"
	@ls docs/design/
	@echo ""
	@echo "ADRs are in docs/adr/"
	@ls docs/adr/
