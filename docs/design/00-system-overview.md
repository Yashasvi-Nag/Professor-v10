# System Overview — Professor v10

## Status

Draft — Phase 1 Scaffold

---

## 1. Purpose

Professor v10 is a deterministic architectural intelligence system for large, multi-repository enterprise codebases. It acts as a **Principal Architect on demand**, transforming unstructured feature ideas into fully validated, evidence-backed architectural change documents.

---

## 2. Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Professor v10                               │
│                                                                     │
│  Input: Feature Request (natural language)                          │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────┐                                               │
│  │  PRD Clarifier   │ ← Identifies ambiguities, generates           │
│  │  (src/prd/)      │   structured clarification questions          │
│  └────────┬─────────┘                                               │
│           │ Structured PRD                                           │
│           ▼                                                         │
│  ┌──────────────────┐     ┌────────────────────────────────────┐   │
│  │  Code Parsers    │────▶│         Architecture Graph         │   │
│  │  (src/parsers/)  │     │         (src/graph/)               │   │
│  │                  │     │                                    │   │
│  │  Java Parser     │     │  Nodes: Services, Endpoints, DTOs, │   │
│  │  Dart Parser     │     │         Models, Caches, DBs,       │   │
│  │  TS Parser       │     │         Topics, Integrations       │   │
│  └──────────────────┘     │                                    │   │
│                            │  Edges: CALLS, CONSUMES, PRODUCES,│   │
│                            │         USES_CACHE, READS_DB,     │   │
│                            │         WRITES_DB, MAPS_TO,       │   │
│                            │         DEPENDS_ON                │   │
│                            └───────────────┬────────────────────┘  │
│                                            │                        │
│                                            ▼                        │
│                            ┌───────────────────────────────┐       │
│                            │   Impact Analysis Engine      │       │
│                            │   (src/analysis/)             │       │
│                            │                               │       │
│                            │   - Impact propagation        │       │
│                            │   - Contract checking         │       │
│                            │   - Severity classification   │       │
│                            └───────────────┬───────────────┘       │
│                                            │                        │
│                                            ▼                        │
│                            ┌───────────────────────────────┐       │
│                            │   Validators                  │       │
│                            │   (src/validators/)           │       │
│                            │                               │       │
│                            │   - Evidence linking          │       │
│                            │   - Confidence scoring        │       │
│                            │   - Completeness checks       │       │
│                            └───────────────┬───────────────┘       │
│                                            │                        │
│                                            ▼                        │
│                            ┌───────────────────────────────┐       │
│                            │   Document Generator          │       │
│                            │   (src/output/)               │       │
│                            │                               │       │
│                            │   - Architectural solution    │       │
│                            │     document (Markdown)       │       │
│                            └───────────────────────────────┘       │
│                                                                     │
│  Output: Validated Architectural Change Document                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

```
Feature Request (natural language)
        │
        ▼ [PRD Clarifier]
Structured PRD (with technical constraints)
        │
        ├──▶ [Code Parsers] ──▶ Architecture Graph
        │                               │
        └──────────────────────────────▶│
                                        ▼
                             [Impact Analysis Engine]
                                        │
                                        ▼
                                  [Validators]
                                        │
                                        ▼
                          Validated Architecture Document
```

### Detailed Flow

1. **Input**: A natural language feature request (e.g., "Add estimated savings to coupon feed")
2. **PRD Clarification**: The clarifier identifies missing constraints and generates targeted questions
3. **Structured PRD**: After clarification, a fully specified PRD with technical constraints is produced
4. **Code Parsing**: Language-specific parsers analyze multi-repo source code
5. **Graph Construction**: Parsed entities become nodes and edges in the architecture graph
6. **Impact Seeding**: The structured PRD identifies seed nodes (directly affected components)
7. **Impact Propagation**: Graph traversal computes the full transitive impact set
8. **Contract Checking**: Validators verify DTO alignment, endpoint consistency, cache contracts
9. **Evidence Linking**: All claims are linked to specific code artifacts (file, line, repo)
10. **Document Generation**: A validated architectural change document is rendered from a template

---

## 4. System Boundaries and Constraints

### Phase 1 Scope (Static Analysis Only)

**In Scope:**
- Multi-repository source code (Java/Spring Boot, Dart/Flutter, TypeScript/Angular)
- Static structure: classes, methods, annotations, interfaces, imports
- Explicit dependencies: Feign clients, Kafka annotations, JPA annotations, HTTP clients
- Configuration: application.properties / application.yml files
- Feature flags: annotation/enum-based detection

**Out of Scope (Phase 1):**
- Runtime telemetry or logs
- Kubernetes topology
- Dynamic dependency injection resolution (complex cases)
- Database schema migrations
- Performance profiling data
- CI/CD pipeline integration

### System Assumptions

- Source code is accessible as local filesystem paths (via git clone or mount)
- Repos follow standard project layouts (Maven for Java, pub for Dart, npm for TypeScript)
- Kafka topics are declared via annotations or explicit strings (no dynamic topic generation)
- Cache keys follow discoverable patterns (annotated or declared in service methods)

---

## 5. Phase 1 vs Future Phases

| Capability | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Static code parsing | ✅ | ✅ | ✅ |
| Architecture graph | ✅ | ✅ | ✅ |
| Impact analysis | ✅ | ✅ | ✅ |
| PRD clarification | ✅ | ✅ | ✅ |
| Evidence-backed docs | ✅ | ✅ | ✅ |
| Runtime telemetry | ❌ | ✅ | ✅ |
| K8s topology | ❌ | ✅ | ✅ |
| DB schema diffing | ❌ | ✅ | ✅ |
| Continuous monitoring | ❌ | ❌ | ✅ |
| Auto-PR generation | ❌ | ❌ | ✅ |

---

## 6. Design Document Index

| Doc | Topic |
|---|---|
| [01-code-graph-extraction.md](01-code-graph-extraction.md) | How source code is parsed into the architecture graph |
| [02-cross-language-schema-alignment.md](02-cross-language-schema-alignment.md) | How Java/Dart/TypeScript schemas are unified |
| [03-dependency-modeling.md](03-dependency-modeling.md) | How dependencies are modeled as a multi-layer graph |
| [04-prd-clarification-engine.md](04-prd-clarification-engine.md) | How vague feature requests become structured PRDs |
| [05-change-impact-propagation.md](05-change-impact-propagation.md) | How changes are traced through the architecture graph |
| [06-trust-validation.md](06-trust-validation.md) | How outputs are validated and evidence-backed |
