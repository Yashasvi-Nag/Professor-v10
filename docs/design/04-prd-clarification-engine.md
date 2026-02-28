# PRD Clarification Engine

## Status

Draft — Phase 1 Scaffold

---

## 1. Problem

Feature requests from product managers and business stakeholders are systematically incomplete for technical implementation. A typical PRD contains:

- Business intent ("add estimated savings to the coupon feed")
- User story ("as a user, I want to see how much I'll save")
- Acceptance criteria (vague, UI-focused)

A typical PRD is **missing**:
- Which services own the data?
- Is this field already computed or does it require new logic?
- Should the response be cached? What's the cache TTL?
- Is this backward compatible? What about old mobile app versions?
- Which countries should this apply to?
- Does this change the database schema?
- Are there consumer services that read this DTO and must be updated?
- Are there feature flag requirements?

Without these technical constraints, engineers must gather this information manually — consuming hours of meetings and risking architectural oversights.

---

## 2. Approach: Graph-Informed Structured Clarification

The PRD Clarifier uses the **architecture graph** to generate **targeted, context-aware clarification questions** — not generic templates.

### Workflow

```
1. Accept natural language feature description
        │
        ▼
2. Extract intent, entities, and scope
   (What is being added/changed? Which domain? Which layer?)
        │
        ▼
3. Map to potentially affected code components
   (Query architecture graph: which services, DTOs, caches, 
    kafka topics are in scope?)
        │
        ▼
4. Generate targeted clarification questions
   (Template-based + graph-informed: questions depend on
    what the graph reveals about the affected components)
        │
        ▼
5. Collect answers (human input or automated inference)
        │
        ▼
6. Validate completeness
   (Are all required technical constraints specified?)
        │
        ▼
7. Output: Structured PRD with technical constraints
```

---

## 3. Intent Extraction

Given a feature description, the clarifier extracts:

| Attribute | Example |
|---|---|
| **Action** | "add", "modify", "remove", "expose" |
| **Entity** | "estimated savings", "coupon feed", "user profile" |
| **Domain** | "coupon", "user", "order", "payment" |
| **Layer** | "API", "UI", "notification", "analytics" |
| **Scope** | "all users", "specific country", "premium users" |

**Example extraction:**

Input: `"Add estimated savings to the coupon feed for Indian users"`

```python
{
    "action": "add",
    "entity": "estimated_savings",
    "domain": "coupon",
    "layer": ["api", "mobile", "admin"],
    "scope": {"country": "IN"},
    "affected_services_candidate": ["coupon-engine", "feed-service"]
}
```

---

## 4. Graph-Informed Question Generation

After mapping the feature to affected graph components, questions are generated based on what the graph reveals:

### Question Templates by Component Type

**If the graph shows a cache dependency:**
> "The feed response is currently cached with key `feed:{userId}:{country}` (TTL: 5 minutes). Should `estimatedSavings` be included in the cached response, or served fresh? If cached, does the cache key need updating?"

**If the graph shows multiple API consumers:**
> "The `/api/feed` endpoint is consumed by: feed-service, admin-service, analytics-pipeline. Are all of these consumers expected to handle the new `estimatedSavings` field?"

**If the graph shows Feign client dependencies:**
> "coupon-engine exposes `estimatedSavings` via the `CouponEngineClient` Feign interface. Is this field already available, or does it need to be computed and added to coupon-engine first?"

**If the graph shows frontend model dependencies:**
> "The feed response maps to `CouponModel.dart` (Flutter) and `CouponDto.ts` (Angular admin). Both will need to be updated. Are there app version constraints or backward compatibility requirements?"

**Standard questions (always asked):**
- Is this change backward compatible?
- Are there feature flag requirements?
- Is a database schema change required?
- What is the rollout strategy (all at once, phased, A/B test)?

---

## 5. Clarification Question Types

| Type | Description | Example |
|---|---|---|
| `CACHING` | Cache impact questions | "Should this be cached?" |
| `CONSUMERS` | Who consumes this API/data | "Which services must be updated?" |
| `BACKWARD_COMPAT` | Version compatibility | "Old mobile app versions?" |
| `DATA_SOURCE` | Where the data comes from | "Is this field computed or stored?" |
| `SCOPE` | Country/user/feature scope | "Which user segments?" |
| `SCHEMA` | Database schema changes | "Does this require a migration?" |
| `ROLLOUT` | Deployment strategy | "Phased or full rollout?" |
| `FEATURE_FLAG` | Feature flag requirements | "Should this be flag-guarded?" |
| `PERFORMANCE` | Performance implications | "Expected response size increase?" |

---

## 6. Output: Structured PRD

After clarification, the output is a `StructuredPRD` object:

```python
{
    "feature_id": "FEAT-001",
    "title": "Add estimatedSavings to coupon feed",
    "original_description": "Add estimated savings to the coupon feed for Indian users",
    "technical_constraints": [
        {
            "type": "SCOPE",
            "value": "country=IN only",
            "source": "clarification_answer"
        },
        {
            "type": "CACHING",
            "value": "Include in cache; update cache key to include savings flag",
            "source": "clarification_answer"
        },
        {
            "type": "BACKWARD_COMPAT",
            "value": "Field is nullable; old app versions receive null",
            "source": "clarification_answer"
        }
    ],
    "affected_components": [
        {"id": "coupon-engine", "type": "SERVICE", "reason": "computes estimatedSavings"},
        {"id": "feed-service", "type": "SERVICE", "reason": "exposes /api/feed"},
        {"id": "CouponResponseDto", "type": "DTO", "reason": "carries the field"},
        {"id": "CouponModel.dart", "type": "MODEL", "reason": "Flutter representation"},
        {"id": "CouponDto.ts", "type": "MODEL", "reason": "Angular admin representation"},
        {"id": "cache:feed:{userId}:{country}", "type": "CACHE", "reason": "cached response"}
    ],
    "completeness_score": 0.92,
    "missing_constraints": []
}
```

---

## 7. Implementation Notes

- Phase 1: Question generation uses template-based rules + graph queries (no LLM required)
- Phase 2: LLM-assisted intent extraction for richer natural language understanding
- The architecture graph must be built before PRD clarification can run (parsers must complete first)
- Clarification is interactive — the system can be run in CLI mode with human input
- All clarification answers are stored and linked to the structured PRD output
