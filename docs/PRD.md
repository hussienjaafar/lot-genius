# Lot Genius — Product Requirements Document (v0.1)

**Owner:** Hussein / Ryze Media
**Editor:** Lot Genius Architect (Claude Code)
**Last updated:** 2025-08-18

## 0. North Star

**Input:** One or more messy B-Stock manifest CSVs.
**Output:** A decision-ready report with (1) lot resale value, (2) recommended maximum bid, (3) sell-through rate — each with confidence intervals, risk metrics (VaR/CVaR), and an evidence ledger.

**Investment gate (configurable):** Only consider bids that satisfy
ROI ≥ `MIN_ROI_TARGET` within `SELLTHROUGH_HORIZON_DAYS`.
_Defaults: `MIN_ROI_TARGET=1.25`, `SELLTHROUGH_HORIZON_DAYS=60` (2 months)._

## 1. Problem & Why Now

Liquidation manifests are messy; price signals vary by channel; operational constraints (gating, labor, cashflow) often invalidate naïve valuations. Lot Genius turns manifests into risk-aware bidding decisions grounded in verifiable evidence.

## 2. Users & Jobs-to-be-Done

- **Owner/Buyer:** Decide the max bid for a lot quickly and safely.
- **Lister/Ops:** See throughput impact (mins/unit, capacity), gated brands, hazmat flags.
- **Finance:** Verify assumptions, cashflow timing, and downside risk.

## 3. Scope

### MVP (ship first)

- Ingest CSV → canonical items; header mapping with memory.
- **Enrichment (Keepa-first):** Amazon price/rank/offer history via Keepa API.
- **Comps without APIs:** Optional Playwright scrapers for public pages (e.g., eBay sold/active search URLs) behind `ENABLE_SCRAPERS` and ToS/robots checks; or manual CSV imports. All scraper data is flagged low-trust and never used alone.
- Robust per-source stats → precision-weighted ensemble price per item (Amazon>Others prior).
- Simple survival proxy (category sold/active if available) → interim p60.
- **Monte Carlo ROI** with manifest uncertainty + returns/fees.
  Optimizer finds the highest bid such that `P(ROI ≥ MIN_ROI_TARGET) ≥ RISK_THRESHOLD` and `E[cash_recovered_by(SELLTHROUGH_HORIZON_DAYS)] ≥ CASHFLOOR`.
  Report VaR/CVaR. If no feasible bid, return **DO NOT BID**.
- CSV/PDF/JSON exports + evidence ledger.

### v0.2

- Full survival model (log-logistic or Cox/GBS) + isotonic calibration.
- Throughput capacity, brand gating/IP checks, pricing ladder (P50 day0, −10% day21, clearance day45), cashflow timing.
- Stress tests, scenario diffs, sensitivity sliders.

### v1.0

- Additional marketplaces via feed imports; watchlists; backtests with conformal intervals; drift monitors; governance ("what changed since last run").

## 4. Non-Goals (for now)

Arbitrage on gray channels; auto-listing; scraping that violates site ToS.

## 5. Key Requirements

### Functional

- **Schema:** `Item(sku_local,title,brand,model,upc/ean/asin,condition,quantity,est_cost_per_unit,notes,category_hint,msrp,color/size/variant,lot_id)`
- **Header mapper:** RapidFuzz + alias dict; remap UI memory per seller.
- **Parser/cleaner:** type inference, unit normalization, quantity explode to 1 row per unit.
- **Dedup:** ID-first (UPC/EAN/ASIN), else title+brand embeddings → cluster.
- **Enrichment:** Keepa API; optional Playwright scrapers (low-trust) and/or manual CSV feeds; freshness + caching; evidence ledger with URLs, timestamps, match scores, trust level.
- **Pricing:** robust trimmed medians; MAD/IQR σ; recency decay λ=0.03/day; ensemble priors (Amazon>Others); floor at category P20.
- **Sell-through:** p60 from survival; features include price-to-market z, rank quantile, #active, offers, seasonality, condition, brand/category (when available).
- **Uncertainty:** Manifest variance priors (missing, misgraded, DOA, unscannable) by seller/category.
- **Constraints:** Brand gating/IP (Amazon/eBay), hazmat/battery flags; throughput mins/unit & capacity; cashflow disbursement lags.
- **Optimizer:** Monte Carlo with correlation shocks.
  Find the highest bid with:
  (a) `P(ROI ≥ MIN_ROI_TARGET) ≥ RISK_THRESHOLD`,
  (b) `E[cash_by_day(SELLTHROUGH_HORIZON_DAYS)] ≥ CASHFLOOR`.
  Solve by bisection; if infeasible, return **DO NOT BID** and show drivers.
  Expose ROI target and horizon as user controls; 1.25× @ 60d is a minimum gate, not a hard-coded target.
- **Risk:** Stress tests (−15% price, +30% returns, +20% shipping, rank shocks).
- **Reporting:** Lot summary, ROI distribution, recommended max bid, sell-through, time-to-cash; evidence panel; exports (CSV/PDF/JSON).

### Non-Functional

- Reproducibility (MLflow + pinned feature snapshots).
- Observability (Sentry, Prometheus/Grafana, OTel).
- Idempotency, retry, rate-limited clients; PII-safe logs.
- Test-first (golden manifests + contract tests + CI).

## 6. Success Metrics

- **Decision latency:** < 5 min for ≤1k lines.
- **Calibration:** price P50 coverage ~50% (±5%); Brier score ≤ target.
- **Risk:** recommended bids satisfy the investment gate; no capital-loss in ≥95% backtested lots at recommended bids.
- **Ops:** <2% manual remap after alias learning.

## 7. Data Model (high level)

- `items(item_id, lot_id, canonical fields…)`
- `evidence(item_id, source, url, trust_level, match_score, stats, ts)`
- `price_estimates(item_id, source_mu, source_sigma, n, recency_days)`
- `survival_features(item_id, features…; p60)`
- `optimizer_runs(lot_id, bid, VaR, CVaR, cash60, seed, version)`

## 8. Defaults

- `MIN_ROI_TARGET = 1.25`
- `SELLTHROUGH_HORIZON_DAYS = 60`
- `RISK_THRESHOLD = 0.80` # probability constraint
- `CASHFLOOR = 0` # expected cash recovered by horizon (can be >0)
- `CLEARANCE_VALUE_AT_HORIZON = 0.50` # fraction of expected price
- **RETURNS/WRITE_OFF:** electronics 8–12%, apparel 3–6%, salvage 25–40%
- **FEES:** marketplace table + 3% + $0.40/order
- `RECENCY_DECAY_LAMBDA = 0.03/day`
- **SOURCE_PRIORS:** Amazon .7 / Others .3

## 9. Risks & Mitigations

- **Entity mismatch** → embeddings + rerank + manual review + evidence ledger.
- **Scrapers** → `ENABLE_SCRAPERS` flag, robots/ToS checks, polite delays, fingerprinting avoidance; scraped data marked low-trust and used only as corroboration.
- **Seasonality/shocks** → decay old comps; rolling retrains; stress tests.
- **Ops variance** → throughput & cashflow modeled; scenario diffs.

## 10. Milestones

MVP (steps 1–10), v0.2 (11–14), v1.0 (15–18). See Roadmap.

## 11. Acceptance (MVP)

Golden manifests parse/clean; GE suites pass; Keepa client under rate limits; ensemble/survival calibrated on sample; optimizer respects `MIN_ROI_TARGET` and `SELLTHROUGH_HORIZON_DAYS` from config (not hard-coded); exports stable.

## 12. Open Questions

- Source-of-truth list for gated brands?
- Category-specific labor mins?
- Cashflow lag priors per channel?

## 13. Glossary

(See `/docs/GLOSSARY.md`)
