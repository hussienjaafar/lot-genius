# Gap Fix 10: Multi-Source Product Confirmation & Confidence Score

Date: 2025-08-26

## Objective

Compute a deterministic `product_confidence` (0–1) from Keepa + filtered scraper evidence signals and surface it in the evidence meta without breaking existing behavior.

## Scope

- Backend scoring utility and evidence meta wiring.
- Non-breaking optional use by callers; no network in tests.

## Changes

- Added `backend/lotgenius/scoring.py`
  - `product_confidence(signals)` combines: title similarity, brand match, model presence, price consistency (|z| vs baseline), corroborating sources, recency, and high-trust ID.
  - `derive_signals_from_item(item, keepa_blob, sold_comps, high_trust_id)` builds signals from available fields.
- Extended `EvidenceResult` with `meta: Dict[str, Any] | None` and default `{}` in `compute_evidence()`.
- `evidence_to_dict()` now includes `meta` field (if present).
- Integrated in pipeline: `api/service.py` populates `ev.meta["product_confidence"]` using the new scoring util before writing to the ledger.
- Added tests: `backend/tests/test_product_confirmation.py`.

## Acceptance Criteria

- Score in [0,1] with monotone responses per factor: PASS.
- Deterministic, offline tests: PASS.
- Existing tests unchanged still pass: targeted subset PASS.
- Evidence meta includes `product_confidence`: wired and tested via roundtrip.

## Test Output (targeted)

```
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q backend\tests\test_product_confirmation.py
...
3 passed, 1 warning in 0.34s
```

Additional spot checks around impacted areas:

```
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q \
  backend\tests\test_gating_confidence.py \
  backend\tests\test_ebay_query_and_filtering.py \
  backend\tests\test_sse_events.py \
  backend\tests\test_sse_phase_order_evidence.py

...................................
35 passed, 3 warnings in 3.93s
```

## Files Changed

- Modified: `backend/lotgenius/evidence.py` (add `meta` to `EvidenceResult`, default meta)
- Modified: `backend/lotgenius/api/service.py` (attach `product_confidence` to evidence meta)
- Added: `backend/lotgenius/scoring.py` (scoring and signal derivation)
- Added: `backend/tests/test_product_confirmation.py` (unit tests)

## Notes

- Scoring is additive with conservative weights and clamps to [0,1].
- High-trust ID provides a small boost but does not override other signals; core gating behavior remains unchanged.
- This step does not alter thresholds in `gating.py`. Optional future work could incorporate `product_confidence` into adaptive gates after field validation.

## Next

- If desired, wire `product_confidence` into report rendering and optionally display per-item in the UI.
- Proceed to Backlog Step 11 (Frontend E2E test stabilization) or Step 12 (Keepa integration tests with key).
