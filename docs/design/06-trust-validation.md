# Trust Validation

## Status

Draft — Phase 1 Scaffold

---

## 1. Problem

When AI-based or automated systems reason about complex codebases, they can:

- **Hallucinate**: Invent APIs, services, or dependencies that don't exist in the code
- **Omit**: Miss critical dependencies because they weren't in the parsed scope
- **Over-generalize**: Apply patterns from one service incorrectly to another
- **Drift**: Produce recommendations that were accurate at parse time but the codebase has since changed

In an enterprise context, an architectural document that incorrectly lists a dependency or misses a consumer can lead to production incidents. Trust in the system's output is a **hard requirement**.

---

## 2. Approach: Evidence-Backed Reasoning

Every claim in Professor v10's output must be **traceable to a specific code artifact**. The system never invents a relationship — it only reports what it found.

### Core Principle

```
No claim without evidence.
No evidence without a source location (file, line, repo, commit).
No output document without a confidence score.
```

---

## 3. Validation Mechanisms

### 3.1 Source Tracing

Every `CodeEntity`, `DependencyEdge`, and graph node carries:

```python
{
    "source_location": {
        "repo": "coupon-engine",
        "file_path": "src/main/java/clients/FeedServiceClient.java",
        "line_number": 34,
        "commit_sha": "abc123"  # when available
    }
}
```

When the document generator includes a claim like "feed-service calls coupon-engine", it appends the evidence link.

### 3.2 Confidence Scoring

Each claim receives a confidence score based on the detection method:

| Detection Method | Confidence |
|---|---|
| Explicit annotation (`@FeignClient`, `@KafkaListener`) | 0.95 |
| Naming convention match (`*Client`, `*Repository`) | 0.75 |
| Import analysis | 0.80 |
| String constant match (Kafka topic name) | 0.70 |
| Structural inference (API URL matching) | 0.65 |
| Manual override in config | 1.00 |

Low-confidence claims (below configurable threshold, default: 0.60) are **flagged for human review** rather than included as facts.

### 3.3 Graph Completeness Checks

Before generating output, the validator runs completeness checks:

| Check | Description | Failure Mode |
|---|---|---|
| Orphan nodes | Nodes with no edges | May indicate parsing gap |
| Unresolved Feign clients | `@FeignClient` with no matching controller | Missing service in scope |
| Missing DTO mappings | Java DTO with no corresponding Dart/TS model | Cross-language gap |
| Broken Kafka chains | `PRODUCES` edge with no `CONSUMES` | Consumer not in scope |
| Dead endpoints | Controller endpoint with no Feign client callers | Possibly deprecated |

### 3.4 Validation Rules

| Rule ID | Rule | Severity |
|---|---|---|
| VR-001 | Every `@FeignClient` must have a corresponding `@RestController` | HIGH |
| VR-002 | Every Kafka producer topic must have at least one consumer | MEDIUM |
| VR-003 | Every API endpoint DTO must have a frontend model mapping | MEDIUM |
| VR-004 | Every `@Cacheable` key must be traceable to a cache node | LOW |
| VR-005 | No circular service dependencies (A→B→C→A) | HIGH |
| VR-006 | Every field in the impact report must have a source location | HIGH |

### 3.5 Human-in-the-Loop Review Checkpoints

For claims below the confidence threshold or validation rule failures, the system inserts **review checkpoints**:

```markdown
⚠️ REVIEW REQUIRED:
Claim: "analytics-pipeline consumes from feed.events.topic"
Confidence: 0.58 (below threshold)
Reason: Topic name matched by string constant, not annotation
Action: Verify manually in analytics-pipeline repo
Evidence: feed-service/FeedEventProducer.java:67
```

---

## 4. Evidence-Backed Output Format

Every claim in the architectural document includes an evidence footnote:

```markdown
## Affected Services

### feed-service
The feed service will require updates to include `estimatedSavings` in the
feed response DTO.

**Evidence**: `feed-service/src/main/java/dto/FeedResponse.java:45`
— `FeedResponse` returned by `GET /api/feed` which maps to `CouponResponseDto`
via `CouponEngineClient.java:23` [confidence: 0.95]
```

---

## 5. Confidence Report

The final output document includes a **Trust Summary**:

```python
{
    "overall_confidence": 0.87,
    "total_claims": 24,
    "high_confidence_claims": 19,
    "low_confidence_claims": 3,
    "review_required_claims": 2,
    "validation_failures": [],
    "completeness_warnings": [
        "analytics-pipeline repo not included in parse scope — may have additional consumers"
    ]
}
```

---

## 6. Scope Limitations (Phase 1)

The validator can only verify what was parsed. If a service is not included in the configured repo list, it will not appear in the graph and its dependencies will not be validated. The output document explicitly states:

```
Parsing scope: coupon-engine, feed-service, flutter-app, angular-admin
Out of scope: analytics-pipeline, notification-service
Note: Dependencies to out-of-scope services are marked as UNVERIFIED.
```

---

## 7. Implementation Notes

- Evidence validation is implemented in `src/validators/evidence.py`
- Validation rules are configurable in `src/config/settings.py`
- The trust summary is rendered as a section in the output document
- Future: integrate with git blame to surface last-modified timestamps and owners
