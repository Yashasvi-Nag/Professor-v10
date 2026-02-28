# ADR 004: Multi-Parser Strategy with Unified Intermediate Representation

## Status

Accepted

## Date

2024-01-01

---

## Context

Professor v10 must parse source code in at least three languages: Java (Spring Boot), Dart (Flutter), and TypeScript (Angular). There are several strategies for multi-language parsing:

1. **Single universal parser**: One parser that handles all languages (e.g., tree-sitter with all language grammars)
2. **Language-native tools**: Delegate to each language's native toolchain (javac, dart analyze, tsc)
3. **Dedicated per-language parsers with shared output**: Each language has its own parser implementation, but all output the same intermediate representation (IR)
4. **Regex-only approach**: Pattern matching on source text without AST parsing

---

## Decision

**Each language gets a dedicated parser. All parsers output a unified intermediate representation (IR). The unified IR feeds the architecture graph.**

### Parser Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Parser Layer                             │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐  │
│  │   JavaParser    │  │   DartParser    │  │ TSParser   │  │
│  │                 │  │                 │  │            │  │
│  │ Spring Boot     │  │ Flutter/Dart    │  │ Angular/TS │  │
│  │ annotations     │  │ model classes   │  │ components │  │
│  │ Feign clients   │  │ API clients     │  │ services   │  │
│  │ Kafka listeners │  │ state mgmt      │  │ interfaces │  │
│  └────────┬────────┘  └────────┬────────┘  └─────┬──────┘  │
│           │                   │                  │         │
│           └───────────────────┴──────────────────┘         │
│                               │                            │
│                               ▼                            │
│          ┌────────────────────────────────────────┐        │
│          │   Unified Intermediate Representation  │        │
│          │   List[CodeEntity]                     │        │
│          └────────────────────────────────────────┘        │
│                               │                            │
│                               ▼                            │
│                        Graph Builder                       │
└─────────────────────────────────────────────────────────────┘
```

### Unified IR Design

The unified IR is a list of `CodeEntity` objects (see `src/graph/models.py`). Every parser — regardless of the source language — produces `CodeEntity` objects with a common schema:

```python
@dataclass
class CodeEntity:
    id: str                    # Deterministic unique ID
    name: str                  # Entity name
    entity_type: EntityType    # CONTROLLER, DTO, SERVICE, MODEL, etc.
    language: Language         # java, dart, typescript
    file_path: str             # Absolute path within repo
    line_number: int           # Declaration line
    repo: str                  # Repository name
    metadata: dict             # Language-specific additional data
    relationships: list        # Declared relationships (becomes graph edges)
```

### Why Dedicated Parsers?

- Java/Spring Boot patterns (annotations, class hierarchies) are fundamentally different from Dart idioms
- Each language benefits from language-specific heuristics and detection strategies
- Dedicated parsers can be developed, tested, and improved independently
- New languages can be added by implementing a new parser without touching existing ones

### Why Not Language-Native Tools?

- Requires installing Java SDK, Dart SDK, Node.js in the analysis environment
- Complicates Docker/deployment setup
- Adds version compatibility concerns
- `tree-sitter` provides sufficient coverage without requiring the full language toolchain

### Baseline: Regex + tree-sitter

Phase 1 implementation strategy:
1. **Regex-based detection** (fast, ~80% coverage): annotation scanning, naming convention detection
2. **tree-sitter AST** (precise, 95%+ coverage): added incrementally for complex cases

---

## Consequences

### Positive
- Each parser is independently testable
- Language-specific optimizations are possible
- New languages can be added by implementing `BaseParser`
- Unified IR means the graph builder is language-agnostic
- Parsers can be parallelized (each repo/language parsed independently)

### Negative
- More code to maintain (three parsers vs one)
- IR design must be expressive enough for all language patterns
- Ensuring IR completeness requires careful design of the `CodeEntity` schema

### Supported Languages (Phase 1)

| Language | Framework | Parser Class |
|---|---|---|
| Java | Spring Boot | `src/parsers/java_parser.py` |
| Dart | Flutter | `src/parsers/dart_parser.py` |
| TypeScript | Angular | `src/parsers/typescript_parser.py` |

### Future Languages

New language support (e.g., Go microservices, Python services) requires:
1. Implement `BaseParser` subclass
2. Register in `src/parsers/__init__.py`
3. Add tests in `tests/test_parsers/`
