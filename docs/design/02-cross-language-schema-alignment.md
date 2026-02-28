# Cross-Language Schema Alignment

## Status

Draft — Phase 1 Scaffold

---

## 1. Problem

The same business domain concept — say, a "Coupon" — is represented differently across every layer of the stack:

| Layer | Representation | Example |
|---|---|---|
| Java Spring Boot | `CouponResponseDto.java` | `private BigDecimal estimatedSavings;` |
| Dart Flutter | `CouponModel.dart` | `final double? estimatedSavings;` |
| TypeScript Angular | `coupon.interface.ts` | `estimatedSavings?: number;` |

These representations:
- Use different naming conventions (camelCase vs snake_case)
- Have different type systems (Java generics vs Dart nullability vs TypeScript optional)
- Evolve independently, causing contract drift
- Have no formal linkage — alignment relies entirely on developer memory

**Without a unified schema map, it is impossible to:**
- Detect when a field added to a Java DTO is missing from the Dart model
- Identify TypeScript interfaces that are out of sync with backend contracts
- Trace a PRD field change through all three representations

---

## 2. Approach: Canonical Schema Representation

We define a **Canonical Schema** as the authoritative representation of a domain entity, independent of any specific language.

```
┌───────────────────────────────────────────────┐
│           Canonical Entity: Coupon             │
│                                               │
│  Field: estimatedSavings                      │
│  Type: decimal/number/float                   │
│  Nullable: true                               │
│  Source: coupon-service/CouponResponseDto.java │
│                                               │
│  Mappings:                                    │
│  ├── Java: CouponResponseDto.estimatedSavings │
│  ├── Dart: CouponModel.estimatedSavings       │
│  └── TypeScript: CouponDto.estimatedSavings   │
└───────────────────────────────────────────────┘
```

---

## 3. Mapping Strategies

### 3.1 Name Matching

The primary strategy is name-based matching — field names that are identical or differ only by case convention are treated as candidates for alignment.

```
Java: estimatedSavings     → Dart: estimatedSavings   ✅ exact match
Java: estimated_savings    → Dart: estimatedSavings   ✅ snake_case → camelCase
Java: EstimatedSavings     → TS: estimatedSavings     ✅ PascalCase → camelCase
```

### 3.2 Structural Matching

When names don't directly match, structural similarity is used:

- Compare field sets of two models — if >70% of fields match by name, they are likely the same entity
- Match based on the API endpoint that produces/consumes the schema
- Cross-reference imports (Dart model that imports from a service that maps to a Java DTO)

### 3.3 API Contract Tracing

The strongest alignment signal comes from tracing the API:

```
Java Controller: GET /api/coupons → returns CouponResponseDto
        ↓
Dart API client: GET /api/coupons → parses into CouponModel
        ↓
TypeScript service: GET /api/coupons → maps to CouponInterface
```

By tracing through the API URL, we can confidently link the three representations.

---

## 4. Type System Mapping

| Java Type | Dart Type | TypeScript Type | Notes |
|---|---|---|---|
| `String` | `String` | `string` | |
| `Integer` / `int` | `int` | `number` | |
| `Long` | `int` | `number` | Dart has no long |
| `Double` / `Float` | `double` | `number` | |
| `BigDecimal` | `double` | `number` | Precision loss risk |
| `Boolean` | `bool` | `boolean` | |
| `List<T>` | `List<T>` | `T[]` | |
| `Map<K,V>` | `Map<K,V>` | `Record<K,V>` | |
| `Optional<T>` | `T?` | `T \| undefined` | |
| `LocalDate` | `DateTime` | `string` (ISO) | Date encoding varies |
| `Enum` | `enum` | `enum` or `string` | |

---

## 5. Output: Unified Cross-Language Entity Map

The cross-language schema alignment produces an **entity map** stored as part of the architecture graph:

```python
{
    "canonical_name": "Coupon",
    "source_of_truth": "coupon-service/CouponResponseDto",
    "fields": [
        {
            "name": "estimatedSavings",
            "canonical_type": "decimal",
            "nullable": True,
            "mappings": {
                "java": {"class": "CouponResponseDto", "type": "BigDecimal", "file": "..."},
                "dart": {"class": "CouponModel", "type": "double?", "file": "..."},
                "typescript": {"interface": "CouponDto", "type": "number | undefined", "file": "..."}
            }
        }
    ],
    "alignment_confidence": 0.95,
    "drift_detected": False
}
```

---

## 6. Drift Detection

Schema drift occurs when representations fall out of sync. Detection rules:

| Rule | Condition | Severity |
|---|---|---|
| Missing field | Field exists in Java DTO but not in Dart model | HIGH |
| Type mismatch | `BigDecimal` in Java, `int` in Dart | MEDIUM |
| Nullability mismatch | Non-null in Java, nullable in Dart | LOW |
| Renamed field | Same API endpoint, similar field with different name | MEDIUM |
| Missing model | Java DTO has no corresponding Dart or TS representation | HIGH |

---

## 7. Implementation Notes

- Schema alignment runs as a post-processing step after all parsers complete
- Alignment is keyed on API endpoint URLs as the primary linking mechanism
- Manual override mappings can be specified in `sample_repo_config.yaml`
- Confidence scores are propagated to the evidence validator
