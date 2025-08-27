# Stage 04 — ROI: Manifest Risk + Ops/Storage Costs

Summary

- Added manifest risk knobs to ROI simulation: `defect_rate`, `missing_rate`, `grade_mismatch_rate`, with recovery/discount params.
- Added ops labor and storage/holding costs into Monte Carlo outputs; subtracted from revenue and cash.
- Wired API optimize paths to accept and forward new knobs from optimizer JSON.
- Added targeted tests validating effects of manifest risk and ops/storage costs.

Files Changed

- `backend/lotgenius/roi.py`
  - New params: `defect_rate`, `missing_rate`, `grade_mismatch_rate`, `defect_recovery_frac`, `missing_recovery_frac`, `mismatch_discount_frac`.
  - New params: `ops_cost_per_min`, `storage_cost_per_unit_per_day`.
  - Logic: apply Bernoulli masks per item/sim on sold revenue; compute ops minutes and expected holding days; subtract fixed totals from revenue and cash; expose `ops_cost_total` and `storage_cost_total` in results.
- `backend/lotgenius/api/service.py`
  - Forward new ROI knobs in both `run_optimize` and `run_pipeline` optimize calls.
- Tests added:
  - `backend/tests/test_roi_manifest_risk.py`
  - `backend/tests/test_roi_ops_storage.py`

New Optimizer JSON Knobs (examples)

```json
{
  "defect_rate": 0.05,
  "missing_rate": 0.02,
  "grade_mismatch_rate": 0.03,
  "defect_recovery_frac": 0.5,
  "missing_recovery_frac": 0.0,
  "mismatch_discount_frac": 0.15,
  "ops_cost_per_min": 0.6,
  "storage_cost_per_unit_per_day": 0.05
}
```

Tests Run

- Targeted:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; py -3 -m pytest -q backend/tests/test_roi_manifest_risk.py backend/tests/test_roi_ops_storage.py`
- Adjacent sanity (suggested):
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; py -3 -m pytest -q backend/tests/test_survivorship_basic.py backend/tests/test_pricing_core.py`

Notes

- Manifest risk events are applied independently; for `missing_rate`, revenue is dropped with optional recovery fraction. For `defect_rate`, revenue is scaled by `defect_recovery_frac`. For `grade_mismatch_rate`, revenue is discounted by `mismatch_discount_frac`.
- Ops/storage are subtracted post-aggregation as fixed totals (not stochastic) and reported in result summary.
