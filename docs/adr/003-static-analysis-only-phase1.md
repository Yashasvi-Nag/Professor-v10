# ADR 003: Static Analysis Only in Phase 1

## Status

Accepted

## Date

2024-01-01

---

## Context

Professor v10's goal is to provide architectural intelligence about an enterprise codebase. There are two broad categories of information that could feed into this intelligence:

1. **Static information**: Source code structure, annotations, class hierarchies, import graphs, configuration files — derived from the code as written
2. **Runtime information**: Actual API call volumes, latency metrics, actual Kafka message rates, live service topology from service mesh, runtime feature flag states, actual database query patterns

Both sources provide valuable signal. The question is which to prioritize in Phase 1.

---

## Decision

**Phase 1 is limited to static code analysis only. No runtime telemetry, logs, Kubernetes topology, or performance data will be ingested in Phase 1.**

### Rationale

#### Foundation Before Augmentation

The core challenge — **reliably extracting architectural structure from multi-language, multi-repo source code** — is already a significant engineering problem. Solving it well with static analysis provides a solid foundation.

Runtime data can be layered on top of a complete graph, but a poor graph with runtime data is worse than a complete graph without runtime data (the graph would be misleading).

#### Reduced Operational Complexity

Runtime data ingestion requires:
- Access to production metrics systems (Prometheus, Datadog, etc.)
- Service mesh integration (Istio, Linkerd)
- Log aggregation access (ELK, Splunk)
- Kubernetes API access

These dependencies complicate deployment, security review, and onboarding significantly. Static analysis requires only read access to source code repositories.

#### Surprising Coverage

Static analysis, done well, can reveal:
- ~85-90% of explicit service-to-service dependencies (Feign clients, HTTP calls)
- 100% of Kafka topics declared via annotations
- 100% of cache keys used via annotations (`@Cacheable`)
- All DTO contracts and their frontend mappings
- All API endpoint signatures

This is sufficient for the primary use case: understanding the impact of a proposed feature change.

---

## Consequences

### Positive
- Simpler deployment (only source code access needed)
- No production system access required (better security posture)
- Faster to build and validate
- Results are deterministic (no runtime variability)
- Establishes a solid foundation for Phase 2 augmentation

### Negative
- Cannot detect runtime-only dependencies (dynamic routing, reflection-based injection)
- Cannot validate whether an API is actually called in production (vs declared in code)
- Cannot surface performance-related architectural concerns
- Dead code (declared but never called APIs) will appear as live dependencies

### Mitigations
- Document the static-only limitation prominently in all output documents
- Flag low-confidence edges (e.g., Feign clients with no matching controller) for human review
- Phase 2 roadmap: enrich static graph with runtime call data to prune dead edges and add actual call frequencies

### Future Phases

| Phase | Runtime Data Added |
|---|---|
| Phase 2 | Service mesh topology (Istio/Linkerd sidecars) |
| Phase 2 | API call volume from metrics (Prometheus/Datadog) |
| Phase 3 | Log-based dependency discovery |
| Phase 3 | Database query pattern analysis |
