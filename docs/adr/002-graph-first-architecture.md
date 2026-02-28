# ADR 002: Graph-First Architecture

## Status

Accepted

## Date

2024-01-01

---

## Context

Professor v10 must reason about complex, multi-dimensional relationships between software components across multiple repositories, languages, and infrastructure layers. There are several possible approaches to storing and querying this architectural knowledge:

1. **Relational database**: Tables for services, APIs, DTOs, with foreign keys
2. **Document store**: JSON documents per service/component
3. **Vector store + embeddings**: Semantic similarity-based retrieval
4. **Graph structure**: Nodes and edges representing entities and relationships

---

## Decision

**The architecture graph is the central data structure of the system. All reasoning operates on the graph, not on raw source code.**

### Graph as the Lingua Franca

After parsing, raw source code is never queried directly. All analysis — impact propagation, contract checking, dependency tracing — operates on the normalized, language-agnostic graph.

```
Raw Code → Parser → CodeEntity objects → Graph Builder → Architecture Graph
                                                                  │
                                          All reasoning ──────────┘
```

### Why Graph, Not Relations or Documents?

| Capability | Graph | Relational | Document |
|---|---|---|---|
| Arbitrary depth traversal | ✅ Native | ❌ Expensive JOINs | ❌ Manual |
| Typed relationships | ✅ Edge types | ⚠️ FK constraints | ❌ Manual |
| Impact propagation | ✅ BFS/DFS | ❌ Complex queries | ❌ Not feasible |
| Multi-hop queries | ✅ Natural | ❌ N self-joins | ❌ Not feasible |
| Flexible schema | ✅ Node metadata | ❌ Rigid schema | ✅ |
| Visualization | ✅ Direct | ❌ Complex | ❌ |
| Cross-language unification | ✅ Same graph | ⚠️ Schema merging | ⚠️ |

### Why Not Vector Store?

Vector similarity is powerful for semantic search but does not support:
- Deterministic traversal (required for impact analysis)
- Typed relationship semantics (CALLS vs MAPS_TO vs USES_CACHE have different meanings)
- Completeness guarantees (a BFS traversal guarantees all reachable nodes are found)

Vectors may be added in a future phase for semantic search over the graph, complementing rather than replacing the graph structure.

---

## Consequences

### Positive
- Enables deterministic, complete impact propagation via graph traversal
- Supports arbitrary query patterns: "find all services that consume topic X", "trace path from DTO to frontend"
- Language-agnostic: Java, Dart, TypeScript nodes coexist in the same graph
- Natural fit for visualization (architecture diagrams from graph)
- Supports confidence scoring per edge (weighted graph)

### Negative
- Graph construction requires well-structured parser output
- In-memory graph (Phase 1) has scalability limits for very large codebases
- Graph completeness depends on parser coverage — gaps in parsing create gaps in the graph

### Phase 1 Implementation
- In-memory `networkx.DiGraph` (sufficient for initial scale)
- Exported to JSON for persistence and sharing
- Phase 2: Migrate to Neo4j for production-scale querying and visualization
