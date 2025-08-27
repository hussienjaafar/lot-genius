# Lot Genius - Product Requirements Document (v0.2)

Owner: Hussein / Ryze Media
Editor: Lot Genius Architect (Claude Code)
Last updated: 2025-08-23

## 0. North Star

Input: One or more messy B-Stock manifest CSVs.
Output: A decision-ready report with (1) lot resale value, (2) recommended maximum bid, (3) sell-through rate - each with confidence intervals, risk metrics (VaR/CVaR), and an evidence ledger.

Investment gate (configurable): Only consider bids that satisfy ROI >= `MIN_ROI_TARGET` within `SELLTHROUGH_HORIZON_DAYS`.
Defaults: `MIN_ROI_TARGET=1.25`, `SELLTHROUGH_HORIZON_DAYS=60` (2 months).

## 0.1 Delivered To Date (Stages 01-07)

This PRD reflects existing functionality delivered incrementally; see `multi_agent/runlogs/` for details.

- External comps foundation (Stage 01)
  - SQLite cache with TTL/WAL; eBay scraper (opt-in, low-trust); consolidated external comps evidence
  - External comps integrated in pricing with appropriate uncertainty weighting
- Condition normalization and seasonality (Stage 02)
  - Normalize condition to buckets; apply price and velocity factors; optional seasonality file
- Survival default and ladder (Stage 03)
  - Default survival model: log-logistic; category alpha scaling; payout-lag aware cash within horizon; pricing ladder based on daily hazards
- ROI extensions (Stage 04)
  - Manifest risk: defect/missing/grade-mismatch with recovery/discount knobs
  - Ops labor (mins per unit) and storage/holding costs integrated into cash and revenue
  - Evidence gate (Two-Source Rule) applied; upside tracking summarized
- Calibration scaffold (Stage 05 + 05b)
  - Prediction logging to JSONL (append mode) with nested `context` and `predicted_*` aliases
  - Outcomes analysis via CLI (`backend/cli/calibration_report.py`); metrics: Brier, MAE/MAPE/RMSE, calibration bins
  - Frontend calibration page for client-side analysis
- UI/UX upgrades (Stage 06)
  - Next.js app with reusable components, SSE console, optimize form, calibration view; inline SVG charts
- Docs + runbooks (Stage 07 + 07b)
  - API/CLI/architecture docs aligned with code; runbooks for dev, optimize, calibration, troubleshooting

## 1. Problem & Why Now

Liquidation manifests are messy; price signals vary by channel; operational constraints (gating, labor, cashflow) often invalidate naive valuations. Lot Genius turns manifests into risk-aware bidding decisions grounded in verifiable evidence.

## 2. Users & Jobs-to-be-Done

- Owner/Buyer: Decide the max bid for a lot quickly and safely.
- Lister/Ops: See throughput impact (mins/unit, capacity), gated brands, hazmat flags.
- Finance: Verify assumptions, cashflow timing, and downside risk.

## 3. Scope

### MVP (shipped)

- Ingest CSV and canonicalize items; header mapping with memory. (DONE)
- Enrichment (Keepa-first): Amazon price/rank/offer history via Keepa API. (DONE)
- External comps (low-trust): Optional eBay (and others) via cache-first scrapers behind flags and ToS checks; manual feeds allowed. Marked low-trust; never used alone. (DONE)
- Pricing: robust per-source stats and precision-weighted ensemble price per item (Amazon > Others prior); floors at category priors. (DONE)
- Survival: default log-logistic; daily hazards; payout-lag aware cash. (DONE)
- Monte Carlo ROI: returns/fees; manifest risk (defect/missing/mismatch); ops labor minutes; storage/holding costs. (DONE)
  - Optimizer finds the highest bid such that `P(ROI >= MIN_ROI_TARGET) >= RISK_THRESHOLD` and `E[cash_by_day(SELLTHROUGH_HORIZON_DAYS)] >= CASHFLOOR`. Reports VaR/CVaR. If infeasible, returns DO NOT BID.
- Evidence gate (Two-Source Rule) with upside tracking; summary in outputs. (DONE)
- Throughput constraints (mins/unit and capacity) and brand/hazmat policy knobs. (DONE)
- Exports + evidence ledger; API and CLI entrypoints; frontend UI for optimize/report and calibration. (DONE)

### v0.2 (in progress)

- Calibration loop (operationalized): scheduled logging, outcomes joins, metric reports; apply bounded adjustments for condition factors and category scaling; monitoring thresholds.
- Scenario diffs & stress tests surfaced in UI; sensitivity sliders for key ROI knobs.
- Additional marketplace feeds and watchlists (non-scraping) with data import guidance.
- Enhanced CSV parsing in frontend (quoted fields) or server-side parsing route.

### v1.0 (future)

- Additional marketplaces via feed imports; watchlists; backtests with conformal intervals; drift monitors; governance (what changed since last run).

## 4. Non-Goals (for now)

Arbitrage on gray channels; auto-listing; scraping that violates site ToS.

## 5. Key Requirements

### Functional

- Schema: `Item(sku_local,title,brand,model,upc/ean/asin,condition,quantity,est_cost_per_unit,notes,category_hint,msrp,color/size/variant,lot_id)`
- Header mapper: RapidFuzz + alias dict; remap memory per seller.
- Parser/cleaner: type inference, unit normalization, quantity explode to 1 row per unit.
- Dedup: ID-first (UPC/EAN/ASIN), else title+brand embeddings + cluster.
- Enrichment: Keepa API; optional scrapers (low-trust) and/or manual CSV feeds; freshness + caching; evidence ledger with URLs, timestamps, match scores, trust level.
- Pricing: robust trimmed medians; MAD/IQR; recency decay lambda=0.03/day; ensemble priors (Amazon>Others); floors at category priors.
- Sell-through: p60 from survival; features include price-to-market z, rank quantile, #active, offers, seasonality, condition, brand/category (when available). Default model: log-logistic with category scaling; payout-lag support.
- Uncertainty: Manifest variance priors (missing, misgraded, DOA, unscannable) by seller/category; ROI simulation includes defect/missing/mismatch events with recovery/discount knobs.
- Constraints: Brand gating/IP (Amazon/eBay), hazmat/battery flags; throughput mins/unit & capacity; cashflow disbursement lags.
- Optimizer: Monte Carlo. Find the highest bid with:
  (a) `P(ROI >= MIN_ROI_TARGET) >= RISK_THRESHOLD`,
  (b) `E[cash_by_day(SELLTHROUGH_HORIZON_DAYS)] >= CASHFLOOR`.
  Solve by bisection; if infeasible, return DO NOT BID and show drivers. Expose ROI target and horizon as user controls; 1.25x @ 60d is a minimum gate, not a hard-coded target.
- Risk: Stress tests (price shocks, returns, shipping, rank shocks).
- Reporting: Lot summary, ROI distribution, recommended max bid, sell-through, time-to-cash; evidence panel; exports (CSV/PDF/JSON). Frontend UI with metrics, SSE console, and calibration page with charts.

### Non-Functional

- Reproducibility (pinned seeds and data snapshots; MLflow optional).
- Observability (future: Sentry, Prometheus/Grafana, OTel).
- Idempotency, retry, rate-limited clients; PII-safe logs.
- Test-first (golden manifests + contract tests + CI); targeted pytest with plugin autoload disabled.

## 6. Success Metrics

- Decision latency: < 5 min for ~1k lines.
- Calibration: price P50 coverage ~50% (+/-5%); Brier score <= target.
- Risk: recommended bids satisfy the investment gate; no capital-loss in >=95% backtested lots at recommended bids.
- Ops: <2% manual remap after alias learning.

## 7. Data Model (high level)

- `items(item_id, lot_id, canonical fields...)`
- `evidence(item_id, source, url, trust_level, match_score, stats, ts)`
- `price_estimates(item_id, source_mu, source_sigma, n, recency_days)`
- `survival_features(item_id, features...; p60)`
- `optimizer_runs(lot_id, bid, VaR, CVaR, cash60, seed, version)`
- `calibration_logs(item_id, context, predicted_price, sell_p60, hazard, factors, ts)`

## 8. Defaults

- `MIN_ROI_TARGET = 1.25`
- `SELLTHROUGH_HORIZON_DAYS = 60`
- `RISK_THRESHOLD = 0.80` # probability constraint
- `CASHFLOOR = 0` # expected cash recovered by horizon (can be >0)
- `CLEARANCE_VALUE_AT_HORIZON = 0.50`
- Returns/write-off: electronics 8-12%, apparel 3-6%, salvage 25-40%
- Fees: marketplace pct + 3% + $0.40/order
- `RECENCY_DECAY_LAMBDA = 0.03/day`
- Source priors: Amazon 0.7 / Others 0.3

## 9. Risks & Mitigations

- Entity mismatch -> embeddings + rerank + manual review + evidence ledger.
- Scrapers -> `ENABLE_SCRAPERS` flag, robots/ToS checks, polite delays; scraped data marked low-trust and used only as corroboration.
- Seasonality/shocks -> decay old comps; rolling retrains; stress tests.
- Ops variance -> throughput & cashflow modeled; scenario diffs.

## 10. Milestones

MVP (Stages 01-07), v0.2 (operational calibration + UI stress tools), v1.0 (feeds, backtests, monitors, governance).

## 11. Acceptance (MVP)

Golden manifests parse/clean; GE suites pass; Keepa client under rate limits; ensemble/survival calibrated on sample; optimizer respects `MIN_ROI_TARGET` and `SELLTHROUGH_HORIZON_DAYS` from config (not hard-coded); exports stable. Calibration JSONL logging and CLI report operational; UI builds and serves optimize + calibration pages; docs/runbooks current and aligned with code.

## 12. Open Questions

- Source-of-truth list for gated brands?
- Category-specific labor mins?
- Cashflow lag priors per channel?

## 13. Glossary

See `docs/GLOSSARY.md`.
