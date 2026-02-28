# Change Impact Propagation

## Status

Draft — Phase 1 Scaffold

---

## 1. Problem

In interconnected enterprise systems, even a small change to a single field can trigger a cascade of required changes across multiple services, languages, and infrastructure components. This cascade is:

- **Non-obvious**: The full impact is not visible from any single service's perspective
- **Cross-layer**: Changes to a DTO affect the API contract, which affects clients, caches, frontend models, analytics events
- **Cross-language**: A Java field addition requires Dart and TypeScript model updates
- **Risk-laden**: Missing even one downstream consumer causes runtime contract violations

**Without automated impact propagation**, teams rely on institutional knowledge and manual review — both of which are incomplete and unscalable.

---

## 2. Approach: Graph Traversal-Based Impact Analysis

Impact analysis operates on the architecture graph using **bidirectional BFS traversal**:
- **Forward traversal**: What does this change affect downstream?
- **Reverse traversal**: What depends on this component and will break?

```
┌──────────────────────────────────────────────────────────────┐
│                  Impact Analysis Algorithm                    │
│                                                              │
│  1. IDENTIFY SEED NODES                                      │
│     ├── Parse change description                             │
│     ├── Match to graph nodes (entity name, service, field)   │
│     └── Seed set = directly changed entities                 │
│                                                              │
│  2. FORWARD TRAVERSAL (what this change affects)             │
│     ├── Follow CALLS edges (downstream service consumers)    │
│     ├── Follow MAPS_TO edges (frontend models)               │
│     ├── Follow USES_CACHE edges (cache invalidation)         │
│     ├── Follow PRODUCES/CONSUMES edges (Kafka consumers)     │
│     └── Follow RETURNS edges (API contract)                  │
│                                                              │
│  3. REVERSE TRAVERSAL (what depends on the changed node)     │
│     ├── Follow incoming CALLS edges (who calls this?)        │
│     ├── Follow incoming DEPENDS_ON edges                     │
│     └── Follow incoming MAPS_TO edges                        │
│                                                              │
│  4. CLASSIFY IMPACT SEVERITY                                 │
│     ├── BREAKING: Required field added, type changed         │
│     ├── ADDITIVE: Optional field added, no contract change   │
│     └── TRANSPARENT: Internal impl change, no API change     │
│                                                              │
│  5. GENERATE IMPACT REPORT                                   │
│     └── Structured report with evidence links               │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Algorithm Detail

### Step 1: Seed Node Identification

Given a change description like `"Add estimatedSavings field to CouponResponseDto"`:

```python
seed_nodes = graph.find_nodes(
    name_contains="CouponResponseDto",
    node_type="DTO",
    change_type="FIELD_ADDED",
    field_name="estimatedSavings"
)
```

Multiple seed nodes may exist if the same concept appears in multiple repos.

### Step 2: Typed Edge Traversal

Different change types follow different edge traversal rules:

| Change Type | Edges to Follow | Rationale |
|---|---|---|
| Field added to DTO | `MAPS_TO`, `RETURNS`, `CALLS` | Frontend models and API consumers |
| API endpoint path changed | `CALLS`, `EXPOSES` | Feign clients, HTTP clients |
| Cache key changed | `USES_CACHE` | All services using that cache key |
| Kafka topic schema changed | `PRODUCES`, `CONSUMES` | All producers and consumers |
| Service renamed/removed | All edge types | Complete dependency analysis |
| DB table schema changed | `READS_DB`, `WRITES_DB` | All services touching that table |

### Step 3: Impact Classification

Each reached node is classified:

| Severity | Definition | Example |
|---|---|---|
| `BREAKING` | Consumer cannot function without code change | Required field added to request DTO |
| `ADDITIVE` | Consumer can function but should be updated | Optional field added to response DTO |
| `TRANSPARENT` | No visible change to consumer | Internal refactor, same public API |
| `INFORMATIONAL` | No code change needed, but team should be aware | Cache key updated, no logic change |

### Step 4: Transitive Closure

The algorithm continues traversal until:
- No new nodes are discovered
- Maximum depth limit is reached (configurable, default: 10 hops)
- All edge types relevant to the change type have been traversed

---

## 4. Example: "Add `estimatedSavings` to Feed"

```
Seed Node: CouponResponseDto (Java, coupon-engine)
        │
        ▼ MAPS_TO
CouponModel.dart (Flutter) ──── ADDITIVE impact
        │
        ▼ MAPS_TO
CouponDto.ts (Angular admin) ── ADDITIVE impact
        │
        ▼ RETURNS (via /api/coupons endpoint)
FeedResponse.java (feed-service) ── ADDITIVE impact
        │
        ▼ USES_CACHE
cache:feed:{userId} ──────────── INFORMATIONAL (cache refresh needed)
        │
        ▼ via feed-service
FeedApiService.ts (admin panel) ── ADDITIVE impact
        │
        ▼ CONSUMES (analytics Kafka topic)
AnalyticsEvent.java ──────────── INFORMATIONAL (event schema may expand)
```

---

## 5. Impact Report Structure

```python
{
    "feature_id": "FEAT-001",
    "change_summary": "Add estimatedSavings field to CouponResponseDto",
    "total_affected_nodes": 7,
    "impact_breakdown": {
        "BREAKING": [],
        "ADDITIVE": [
            {
                "node_id": "CouponModel.dart",
                "node_type": "MODEL",
                "language": "dart",
                "repo": "flutter-app",
                "reason": "Maps to CouponResponseDto via /api/coupons",
                "evidence": {"file": "lib/models/coupon_model.dart", "line": 12},
                "action_required": "Add estimatedSavings field (nullable double)"
            },
            # ... more affected nodes
        ],
        "TRANSPARENT": [],
        "INFORMATIONAL": [
            {
                "node_id": "cache:feed:{userId}",
                "node_type": "CACHE",
                "reason": "Cached feed response will now include estimatedSavings",
                "action_required": "Consider cache invalidation strategy"
            }
        ]
    },
    "affected_repos": ["coupon-engine", "feed-service", "flutter-app", "angular-admin"],
    "affected_languages": ["java", "dart", "typescript"],
    "risks": [
        "Old Flutter app versions may receive unexpected field (nullable, so safe)",
        "Cache entries will serve stale data until TTL expires"
    ]
}
```

---

## 6. Edge Case Handling

- **Circular dependencies**: Detected and short-circuited; noted in report
- **Orphan nodes**: Nodes with no edges are flagged as potentially incomplete graph
- **Multiple paths**: All paths are reported; the shortest path is highlighted
- **Unresolved Feign clients**: Feign clients with no matching controller are flagged for manual review

---

## 7. Implementation Notes

- Implemented in `src/analysis/impact.py` using `networkx` BFS
- Traversal is configurable: max depth, edge type filters, severity threshold
- Output is a structured `ImpactReport` Pydantic model
- Reports are rendered via Jinja2 templates into Markdown documents
