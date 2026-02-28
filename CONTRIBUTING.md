# Contributing to Professor v10

Thank you for your interest in contributing to Professor v10! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Issues

- Search existing issues before opening a new one.
- Provide a clear title and description.
- Include steps to reproduce for bug reports.
- For feature requests, explain the use case and expected behavior.

### Submitting Pull Requests

1. Fork the repository and create your branch from `main`.
2. Run `make setup` to install dependencies.
3. Make your changes following the coding standards below.
4. Add or update tests as needed.
5. Run `make lint` and `make test` to ensure everything passes.
6. Submit a pull request with a clear description of the changes.

### Branch Naming

- `feature/short-description` — new features
- `fix/short-description` — bug fixes
- `docs/short-description` — documentation updates
- `refactor/short-description` — code refactoring

## Coding Standards

### Python Style

- Target Python 3.11+.
- Use type hints throughout.
- Use Pydantic for data models.
- Follow [PEP 8](https://pep8.org/) style guidelines.
- Run `make format` (black) before committing.
- Run `make lint` (ruff) before committing.

### Documentation

- All public classes and functions must have docstrings.
- Explain *why*, not just *what*.
- Add architectural context where relevant.

### Tests

- Write tests for all new functionality.
- Use `pytest` with fixtures defined in `tests/conftest.py`.
- Aim for meaningful coverage, not 100% line coverage.

### TODO Markers

When adding skeleton code, use:

```python
# TODO: Implement <description>
# See design doc: docs/design/<relevant-doc>.md
```

## Adding a New Parser

1. Create `src/parsers/<language>_parser.py`.
2. Inherit from `src/parsers/base.py::BaseParser`.
3. Implement all abstract methods.
4. Add tests in `tests/test_parsers/test_<language>_parser.py`.
5. Register the parser in `src/parsers/__init__.py`.
6. Update `docs/design/01-code-graph-extraction.md` if needed.

## Adding a New Graph Node Type

1. Add the node model in `src/graph/models.py`.
2. Update `src/graph/builder.py` to construct the new node type.
3. Update query utilities in `src/graph/query.py` if needed.
4. Add tests in `tests/test_graph/`.

## Development Setup

```bash
# Full setup
make setup

# Run tests
make test

# Lint
make lint

# Format
make format
```

## Questions?

Open a GitHub issue with the `question` label.
