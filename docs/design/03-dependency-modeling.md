# Dependency Modeling

## Status

Draft — Phase 1 Scaffold

---

## 1. Problem

In large enterprise systems, dependencies are:

- **Implicit** — A Flutter app calls an API that internally calls three other services; none of this is visible from the Flutter layer
- **Hidden** — A cache key is shared between two services without explicit documentation
- **Multi-dimensional** — Dependencies exist at service, API, DTO, data, messaging, and configuration levels
- **Cross-language** — Java service → Kafka topic → Java consumer → database → TS admin reads same DB
- **Undocumented** — Engineers know about these links; the codebase does not formally encode them

Without a formalized dependency model, impact analysis is impossible and change propagation is a manual, error-prone process.

---

## 2. Approach: Multi-Layer Dependency Graph

We model dependencies as a **multi-layer directed graph** where each layer captures a different dimension of coupling.

```
┌────────────────────────────────────────────────────────────────────┐
│                   Multi-Layer Dependency Graph                     │
│                                                                    │
│  Layer 1: Service → Service                                        │
│  ┌──────────────┐    CALLS     ┌──────────────────┐               │
│  │ feed-service │ ──────────── │  coupon-engine   │               │
│  └──────────────┘              └──────────────────┘               │
│                                                                    │
│  Layer 2: Service → Kafka Topic                                    │
│  ┌──────────────┐  PRODUCES   ┌─────────────────────┐             │
│  │ order-svc    │ ──────────── │ order.placed.topic  │             │
│  └──────────────┘              └─────────────────────┘             │
│         ▲ CONSUMES                                                 │
│  ┌──────────────┐                                                  │
│  │ notif-svc    │                                                  │
│  └──────────────┘                                                  │
│                                                                    │
│  Layer 3: Service → Cache                                          │
│  ┌──────────────┐  USES_CACHE  ┌─────────────────────┐            │
│  │ feed-service │ ──────────── │ cache:feed:{userId} │            │
│  └──────────────┘              └─────────────────────┘            │
│                                                                    │
│  Layer 4: API → DTO → Frontend Model                               │
│  ┌────────────────┐  RETURNS  ┌──────────────┐  MAPS_TO           │
│  │ GET /api/feed  │ ───────── │ FeedResponse │ ──────────────     │
│  └────────────────┘           └──────────────┘   ┌───────────┐   │
│                                                   │FeedModel  │   │
│                                                   │(Dart)     │   │
│                                                   └───────────┘   │
│                                                                    │
│  Layer 5: Service → Database                                       │
│  ┌──────────────┐  READS_DB  ┌─────────────────┐                  │
│  │ user-service │ ────────── │ users table     │                  │
│  └──────────────┘            └─────────────────┘                  │
│         │         WRITES_DB  ┌─────────────────┐                  │
│         └───────────────────▶│ user_events     │                  │
│                               └─────────────────┘                 │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Graph Layers

### Layer 1: Service-to-Service (Synchronous)

- **Mechanism**: Feign clients (Java), HTTP clients (Dart/TS)
- **Edge type**: `CALLS`
- **Metadata**: HTTP method, endpoint URL, request/response DTO types
- **Detection**: `@FeignClient` annotation, `RestTemplate`, `WebClient`, `http.get/post` calls

### Layer 2: Service-to-Service (Asynchronous / Kafka)

- **Mechanism**: Kafka topics
- **Edge types**: `PRODUCES`, `CONSUMES`
- **Metadata**: topic name, message schema (if available), consumer group
- **Detection**: `@KafkaListener(topics=...)`, `KafkaTemplate.send(topic, ...)`, string constants

### Layer 3: Service-to-Cache

- **Mechanism**: Redis, Aerospike
- **Edge type**: `USES_CACHE`
- **Metadata**: cache key pattern, TTL (if discoverable), read/write operation
- **Detection**: `@Cacheable`, `@CacheEvict`, `RedisTemplate.opsForValue()`, key strings

### Layer 4: API-to-Contract-to-Frontend

- **Mechanism**: REST API contract chain
- **Edge types**: `EXPOSES`, `RETURNS`, `MAPS_TO`
- **Metadata**: HTTP method + path, DTO class name, field list
- **Detection**: Controller annotations + Dart API client calls + TS HttpClient calls

### Layer 5: Service-to-Database

- **Mechanism**: JPA, JDBC, raw queries
- **Edge types**: `READS_DB`, `WRITES_DB`
- **Metadata**: table name, entity class, operation type
- **Detection**: `@Entity`, `@Table`, `@Query`, repository method names

### Layer 6: External Integrations

- **Mechanism**: Third-party APIs, payment gateways, notification services
- **Edge type**: `CALLS`
- **Metadata**: external service name, endpoint, protocol
- **Detection**: HTTP client calls to non-internal hostnames, `@ExternalService` custom annotations

---

## 4. Graph Storage Model

### Adjacency List with Typed Edges

```python
# Node
{
    "id": "feed-service",
    "type": "SERVICE",
    "language": "java",
    "repo": "feed-service-repo",
    "file_path": "src/main/java/FeedServiceApplication.java"
}

# Edge
{
    "id": "edge-001",
    "source": "feed-service",
    "target": "coupon-engine",
    "edge_type": "CALLS",
    "metadata": {
        "http_method": "GET",
        "endpoint": "/api/coupons/{userId}",
        "feign_client": "CouponEngineClient",
        "file_path": "src/main/java/clients/CouponEngineClient.java",
        "line_number": 15
    }
}
```

See `src/graph/models.py` for the full type definitions.

---

## 5. Impact Propagation Queries

Given the multi-layer graph, the core query is:

> **"Given node X is changed, what nodes are transitively affected?"**

### Algorithm (BFS/DFS Traversal)

```
1. Start at seed nodes (directly changed entities)
2. Follow all outgoing edges (forward impact)
3. Follow all incoming edges to changed nodes (reverse impact — who depends on this?)
4. Filter by edge type based on change type:
   - DTO field added: follow MAPS_TO, RETURNS
   - API signature changed: follow CALLS, EXPOSES
   - Cache key changed: follow USES_CACHE
   - Kafka topic schema changed: follow PRODUCES, CONSUMES
5. Classify each reached node by impact severity
6. Stop traversal at configurable depth limit
```

### Example Query

```python
# Who is affected if CouponResponseDto changes?
impact = graph.impact_analysis(
    node_id="CouponResponseDto",
    change_type="FIELD_ADDED",
    field_name="estimatedSavings"
)
# Returns: feed-service, FeedResponse, CouponModel (Dart), CouponDto (TS),
#          feed cache key, analytics event schema
```

---

## 6. Implementation Notes

- Graph is stored in memory (Phase 1) as a `networkx.DiGraph`
- Nodes are keyed by a deterministic ID: `{repo}/{language}/{type}/{name}`
- Edge metadata preserves source location for evidence linking
- Graph export to JSON is supported for persistence and debugging
- Future: migrate to a proper graph database (Neo4j) for production scale
