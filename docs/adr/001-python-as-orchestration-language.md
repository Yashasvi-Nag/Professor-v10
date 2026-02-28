# ADR 001: Python as the Orchestration Language

## Status

Accepted

## Date

2024-01-01

---

## Context

Professor v10 requires an orchestration layer that:

1. Coordinates multi-language AST parsing
2. Constructs and queries a graph data structure
3. Integrates with NLP/AI components for PRD clarification
4. Generates structured output documents from templates
5. Is extensible enough to add new parsers and analysis modules over time

Multiple language options were evaluated: Python, Go, Java, TypeScript.

---

## Decision

**Python (3.11+) is chosen as the primary orchestration language.**

### Rationale

| Requirement | Python Support |
|---|---|
| AST parsing | `tree-sitter` bindings for all target languages |
| Graph processing | `networkx` — mature, feature-rich graph library |
| NLP / AI integration | Best-in-class ecosystem (spaCy, transformers, LangChain) |
| Template generation | `Jinja2` — battle-tested document generation |
| Data validation | `Pydantic` — excellent schema validation and settings management |
| YAML/JSON handling | Native `pyyaml`, `json` |
| Type hints | Full support since 3.5, improved significantly in 3.11 |
| Developer familiarity | Widest enterprise developer familiarity for tooling/scripting |
| Iteration speed | Fast prototyping and iteration cycle |

### Language-Specific Parsing Strategy

Python does not need to natively parse Java, Dart, or TypeScript — it orchestrates native tools:

- **Java**: `tree-sitter-java` Python bindings, or subprocess calls to `javap`/`javac` for reflection
- **TypeScript**: `tree-sitter-typescript` Python bindings
- **Dart**: `tree-sitter` or subprocess to Dart analyzer

This means Python acts as the **orchestrator and graph builder** — the actual AST parsing delegates to the appropriate native capability.

---

## Consequences

### Positive
- Rich ecosystem for all required capabilities
- Fast iteration and development
- Easy integration with AI/LLM APIs
- Strong type hint support with Pydantic for data modeling

### Negative
- Python is not the primary language of the target codebase (Java/Dart/TS)
- Performance is not optimal for very large codebases (millions of lines) — may need incremental parsing
- Requires Python 3.11+ runtime in the deployment environment

### Mitigations
- Use `tree-sitter` (C-based) for performance-critical parsing operations
- Design parsers to be incremental (parse only changed files on re-runs)
- Package with standard `pyproject.toml` / `pip` for simple deployment
