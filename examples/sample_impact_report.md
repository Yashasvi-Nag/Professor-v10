# FEAT-001: Add Estimated Savings to Coupon Feed

**Generated**: 2024-01-16 09:30 UTC  
**Status**: Draft — Pending Engineering Review  
**Overall Confidence**: 91%

---

## Overview

**Feature**: Add estimated savings to coupon feed

**Original Request**:
> We want to add an estimated savings amount to the coupon feed. When users browse 
> available coupons, they should see how much they'll save before clicking into the 
> coupon detail page.

**Change Summary**: Add `estimatedSavings` field (nullable BigDecimal) to `CouponResponseDto`

**Scope**:
- Affected Repositories: `coupon-engine`, `feed-service`, `flutter-app`, `angular-admin`
- Affected Languages: Java, Dart, TypeScript
- Total Impacted Components: **8**

---

## Technical Constraints

- **SCOPE**: India (country=IN) only for initial launch *(Source: clarification_answer)*
- **BACKWARD_COMPAT**: Field is nullable (`BigDecimal?` / `double?` / `number | undefined`); old app versions receive `null` *(Source: clarification_answer)*
- **CACHING**: Include in cached feed response; cache key unchanged (savings is per-coupon, not per-user-session); TTL remains 5 minutes *(Source: clarification_answer)*
- **FEATURE_FLAG**: Guard with `ESTIMATED_SAVINGS_ENABLED` feature flag; default `false` *(Source: clarification_answer)*
- **ROLLOUT**: Phase 1 — India only; Phase 2 — global after 2-week monitoring *(Source: clarification_answer)*

---

## Affected Services

### coupon-engine (coupon-engine)

- **Type**: service
- **Language**: java
- **Impact Severity**: 🟡 ADDITIVE
- **Reason**: Source of truth for `estimatedSavings`; must expose the field in the API response
- **Evidence**: `src/main/java/service/CouponService.java:67`

### feed-service (feed-service)

- **Type**: service
- **Language**: java
- **Impact Severity**: 🟡 ADDITIVE
- **Reason**: Consumes coupon-engine API and re-exposes feed; must pass through `estimatedSavings`
- **Evidence**: `src/main/java/clients/CouponEngineClient.java:23`

---

## API Changes

### `GET /api/coupons/{userId}`

- **Service**: coupon-engine
- **Impact**: 🟡 ADDITIVE
- **Change**: Response body gains optional field `estimatedSavings: BigDecimal?`
- **Backward Compatible**: Yes — nullable field, existing consumers unaffected
- **Evidence**: `src/main/java/controller/CouponController.java:45`

### `GET /api/feed/{userId}`

- **Service**: feed-service
- **Impact**: 🟡 ADDITIVE
- **Change**: Feed items in response gain `estimatedSavings` passthrough
- **Evidence**: `src/main/java/controller/FeedController.java:31`

---

## DTO / Contract Changes

### CouponResponseDto (java)

- **Repository**: coupon-engine
- **File**: `src/main/java/dto/CouponResponseDto.java`
- **Change**: Add field `private BigDecimal estimatedSavings;` (nullable)
- **Impact**: 🟡 ADDITIVE
- **Evidence**: `src/main/java/dto/CouponResponseDto.java:5`

### FeedItemDto (java)

- **Repository**: feed-service
- **File**: `src/main/java/dto/FeedItemDto.java`
- **Change**: Add field `private BigDecimal estimatedSavings;` (nullable, passthrough)
- **Impact**: 🟡 ADDITIVE
- **Evidence**: `src/main/java/dto/FeedItemDto.java:12`

---

## Frontend Changes

### Flutter (Dart)

- **CouponModel** (`lib/models/coupon_model.dart`) — 🟡 Add `estimatedSavings` field: `double? estimatedSavings;`, update `fromJson`/`toJson`
- **FeedItemModel** (`lib/models/feed_item_model.dart`) — 🟡 Add `estimatedSavings` field: `double? estimatedSavings;`
- **CouponCard widget** (`lib/widgets/coupon_card.dart`) — 🟡 Display `estimatedSavings` if non-null

### Angular (TypeScript)

- **CouponDto** (`src/app/models/coupon.dto.ts`) — 🟡 Add `estimatedSavings?: number` to interface
- **Admin coupon list** (`src/app/components/coupon-list`) — ℹ️ Optionally show savings in admin view (separate ticket)

---

## Cache Impact

### feed-cache (feed:{userId})

- **Cache Key**: `feed:{userId}`
- **TTL**: 300s (5 minutes)
- **Impact**: ℹ️ INFORMATIONAL
- **Action Required**: No cache key change needed. Existing TTL of 300s means stale data for up to 5 minutes after deployment. Plan deployment during low-traffic window.
- **Evidence**: `src/main/java/service/FeedService.java:45`

---

## Database Changes

*No database schema changes required.*

The `estimatedSavings` field is computed in-memory by coupon-engine and is not persisted.

---

## Action Items

| # | Component | Action | Severity | File |
|---|---|---|---|---|
| 1 | CouponResponseDto | Add `estimatedSavings` field (nullable BigDecimal) | 🟡 ADDITIVE | `coupon-engine/src/main/java/dto/CouponResponseDto.java` |
| 2 | CouponService | Populate `estimatedSavings` in response mapping | 🟡 ADDITIVE | `coupon-engine/src/main/java/service/CouponService.java` |
| 3 | FeedItemDto | Add `estimatedSavings` passthrough field | 🟡 ADDITIVE | `feed-service/src/main/java/dto/FeedItemDto.java` |
| 4 | CouponModel.dart | Add `double? estimatedSavings`, update fromJson/toJson | 🟡 ADDITIVE | `flutter-app/lib/models/coupon_model.dart` |
| 5 | FeedItemModel.dart | Add `double? estimatedSavings`, update fromJson/toJson | 🟡 ADDITIVE | `flutter-app/lib/models/feed_item_model.dart` |
| 6 | CouponCard widget | Conditionally render savings badge if non-null | 🟡 ADDITIVE | `flutter-app/lib/widgets/coupon_card.dart` |
| 7 | CouponDto.ts | Add `estimatedSavings?: number` to interface | 🟡 ADDITIVE | `angular-admin/src/app/models/coupon.dto.ts` |
| 8 | Feature flag | Add `ESTIMATED_SAVINGS_ENABLED` flag | ℹ️ INFO | `coupon-engine/src/main/resources/application.yml` |

---

## Rollout Strategy

- Change is additive (no breaking impacts). Backend can deploy before frontend.
- Backend deployment order: `coupon-engine` → `feed-service` (feed-service depends on coupon-engine)
- Frontend deployments can proceed once backend is live and verified
- Feature flag `ESTIMATED_SAVINGS_ENABLED` defaults to `false`; enable for IN only after smoke testing
- Monitor cache hit rates and error rates for 48h before expanding scope
- Cache entries will contain stale data until TTL expires (5 minutes). Plan deployment during low traffic.

---

## Risks

> ⚠️ **Risk**: Mobile (Flutter) models are impacted. Ensure the new field is nullable to maintain backward compatibility with older app versions in production.

> ⚠️ **Risk**: Change spans 4 repositories (coupon-engine, feed-service, flutter-app, angular-admin). Cross-team coordination required. Suggest a shared deployment checklist.

> ⚠️ **Risk**: Cache entries will serve stale data for up to 5 minutes post-deployment. If `estimatedSavings` must appear immediately, a targeted cache invalidation script should be prepared.

---

## Trust Summary

| Metric | Value |
|---|---|
| Overall Confidence | **91%** |
| Total Claims | 8 |
| High Confidence | 7 |
| Low Confidence | 1 |
| Review Required | 0 |
| PRD Completeness | 96% |

> ℹ️ 1 low-confidence claim: `FeedItemDto` identified via naming convention rather than explicit annotation. Verify file path before implementation.

---

## Parsing Scope

The following repositories were analyzed to produce this document:

- `coupon-engine`
- `feed-service`
- `flutter-app`
- `angular-admin`

> **Note**: `analytics-pipeline` and `notification-service` were **not analyzed**. 
> If these services consume coupon or feed data, they may also require updates. 
> These dependencies are marked UNVERIFIED and require manual validation.

---

*Generated by Professor v10 — Enterprise Architecture Intelligence System*
