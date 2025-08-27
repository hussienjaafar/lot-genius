# Lot Genius - PRD Alignment TODO

Purpose: Track gaps, bugs, and planned stages to align the app with the PRD. We will check these off as we complete work and reference this file during runs to avoid losing context.

Refs: `docs/PRD.md`, `backend/`, `multi_agent/runlogs/`

## Process

- [ ] After each stage, Claude Code writes a run log in `multi_agent/runlogs/` describing changes, tests, and outcomes.
- [ ] We review diffs and run logs, then check off items here.
- [ ] Keep changes small and test-driven; default behavior remains backward compatible.

## Gaps vs PRD

- [ ] Survival model v0.2 (log-/log-logistic) with calibration; keep proxy as default.
- [ ] Throughput/capacity exposure in CLI/API and reporting.
- [ ] Brand gating & hazmat policies exposed in CLI/API and summarized in reports.
- [ ] Pricing ladder (P50 day0, -10% day21, clearance day45) in modeling and report.
- [ ] Cashflow timing (payout lag) impacting expected cash within horizon.
- [ ] Report constraints section (ROI target, risk threshold, cashfloor, throughput, payout lag, gated/hazmat counts).
- [ ] Non-functional (repro/observability) scaffolding (deferred).

## Bugs/Issues

- [ ] Normalize report formatting (ASCII-safe for >=, emojis, etc.); update tests accordingly.
- [x] Align `roi.DEFAULTS['salvage_frac']` with `settings.CLEARANCE_VALUE_AT_HORIZON`. (stage_10_defaults_cashfloor.md)
- [x] Ensure `CASHFLOOR` default flows through CLI/API to optimizer when not specified. (stage_10_defaults_cashfloor.md)
- [ ] Avoid duplicated evidence-gate logic paths drifting (centralize or document flow).

## Improvement Plan - Stages

### Stage 10 - Defaults & Cashfloor Gate

- [x] In `backend/lotgenius/roi.py`, set `DEFAULTS['salvage_frac'] = settings.CLEARANCE_VALUE_AT_HORIZON`. (stage_10_defaults_cashfloor.md)
- [x] In `backend/cli/optimize_bid.py`, if `--min-cash-60d` not provided, pass `settings.CASHFLOOR`. (stage_10_defaults_cashfloor.md)
- [x] In `backend/lotgenius/api/service.py`, if `min_cash_60d` missing in `opt_dict`, inject `settings.CASHFLOOR` for optimize/pipeline calls. Also default `salvage_frac` to `settings.CLEARANCE_VALUE_AT_HORIZON`. (stage_10_defaults_cashfloor.md)
- [ ] Update README/config notes to reflect defaults.
- [x] Tests: ensure salvage default + default `CASHFLOOR` usage (CLI/API). (stage_10_defaults_cashfloor.md)
- [x] Run log: `multi_agent/runlogs/stage_10_defaults_cashfloor.md`.

### Stage 11 - Throughput Capacity Integration

- [ ] CLI `backend/cli/optimize_bid.py`: add `--mins-per-unit`, `--capacity-mins-per-day` and pass through to optimizer.
- [ ] API: accept `mins_per_unit`, `capacity_mins_per_day` (via schema or `opt_dict`) and plumb to optimizer.
- [ ] Report: add "Throughput" section (mins/unit, capacity/day, total mins required, available mins, pass/fail).
- [ ] Tests: throughput pass/fail affects `meets_constraints`; report contains Throughput section.
- [ ] Run log: `multi_agent/runlogs/stage_11_throughput_capacity.md`.

### Stage 12 - Payout Lag in Cashflow

- [ ] `config.py`: add `PAYOUT_LAG_DAYS` (default 14).
- [ ] `roi.simulate_lot_outcomes`: compute lambda from `sell_hazard_daily` or back-solve from `sell_p60`; scale `cash_60d` by fraction with lag (H-L).
- [ ] Report/API: surface payout lag in constraints/summary.
- [ ] Tests: increasing lag reduces `expected_cash_60d` for same inputs.
- [ ] Run log: `multi_agent/runlogs/stage_12_payout_lag.md`.

### Stage 13 - Brand Gating & Hazmat Policies

- [ ] CLI: add `--gated-brands`, `--hazmat-policy` (or opt JSON keys) to set `settings`/env.
- [ ] API: accept `gated_brands_csv`, `hazmat_policy` and apply for run scope.
- [ ] Report/API summary: counts and tags for brand-gated/hazmat (core vs review).
- [ ] Tests: gating behavior for exclude/review; tags present.
- [ ] Run log: `multi_agent/runlogs/stage_13_brand_hazmat_gating.md`.

### Stage 14 - Pricing Ladder

- [ ] New `backend/lotgenius/ladder.py` with price schedule helper.
- [ ] `cli/estimate_sell.py`: `--use-pricing-ladder`; piecewise sell-through across day segments.
- [ ] Report: "Pricing Ladder" table when enabled.
- [ ] Tests: ladder math and uplift vs flat price.
- [ ] Run log: `multi_agent/runlogs/stage_14_pricing_ladder.md`.

### Stage 15 - Survival Model Scaffold (v0.2)

- [ ] New `backend/lotgenius/survivorship.py` (log-logistic expected sell-within).
- [ ] Config: `SURVIVAL_MODEL`, `SURVIVAL_ALPHA`, `SURVIVAL_BETA`.
- [ ] `estimate_sell.py`: toggle to use survivorship model; keep proxy default.
- [ ] Tests: survivorship math and toggle behavior.
- [ ] Run log: `multi_agent/runlogs/stage_15_survival_model.md`.

### Stage 16 - Report Polish

- [ ] Consolidated "Constraints" section (ROI Target, Risk Threshold, Cashfloor, Payout Lag, Throughput, Gated/Hazmat counts).
- [ ] Optional: normalize report symbols/emojis; update tests.
- [ ] Tests: report contains new sections/fields.
- [ ] Run log: `multi_agent/runlogs/stage_16_report_polish.md`.

---

Maintenance Note: When marking items as complete, include the run log filename and commit hashes in parentheses for traceability.
