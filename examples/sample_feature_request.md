# Sample Feature Request: Add Estimated Savings to Coupon Feed

**Feature ID**: FEAT-001
**Requester**: Product Manager — Coupons Team
**Priority**: High
**Date**: 2024-01-15

---

## Business Description

> "We want to add an estimated savings amount to the coupon feed. When users browse 
> available coupons, they should see how much they'll save before clicking into the 
> coupon detail page. This will improve conversion rates by making the value 
> proposition immediately visible."

---

## User Story

**As a** user browsing available coupons on the app,  
**I want to** see how much I'll save for each coupon in the feed,  
**So that** I can quickly identify which coupons offer the most value without opening each one.

---

## Acceptance Criteria (Business View)

1. Each coupon card in the feed shows an "Estimated Savings" amount
2. The savings amount is displayed in the user's local currency
3. If the savings cannot be computed, the field is not shown (graceful degradation)
4. The feature should launch for Indian users first

---

## Known Constraints

- India-only for the initial launch
- Must not break existing app versions currently in production
- The coupon-engine team has indicated that `estimatedSavings` is already computed 
  internally but not currently exposed in the API response

---

## Questions Still Open (for PRD Clarifier)

1. Should `estimatedSavings` be included in the cached feed response? What is the 
   appropriate cache invalidation strategy?
2. Is the `estimatedSavings` field computed per-user or per-coupon? Does it vary 
   by user profile (e.g., purchase history)?
3. What is the rollout strategy — full India launch or phased by city/user segment?
4. Should this be behind a feature flag for A/B testing?
5. Does the admin panel (Angular) need to show estimated savings in the coupon 
   management view?
6. Are there analytics requirements? Should the estimated savings be included in 
   the coupon impression event?

---

## Related Tickets

- COUPON-456: Compute `estimatedSavings` in coupon-engine (already done, not exposed)
- FEED-789: Feed service API contract documentation
- APP-234: Flutter app coupon feed component
