# Glossary — Lot Genius

## Key Terms

**Investment gate:** Minimum decision rule — ROI ≥ `MIN_ROI_TARGET` within `SELLTHROUGH_HORIZON_DAYS`; if unmet at any bid, result is **DO NOT BID**.

**VaR80:** Value at Risk - 20th percentile of ROI distribution (downside risk metric).

**CVaR:** Conditional Value at Risk - Mean ROI in the worst 20% of outcomes.

**p60:** Probability that an item sells within 60 days.

**Evidence ledger:** Per-item record of all data sources, match scores, statistics, and trust levels used in valuation.

**Manifest:** CSV file containing inventory details from B-Stock or other liquidation sources.

**Canonical schema:** Standardized data structure for items across all input sources.

**Header mapping:** Process of matching varied CSV column names to canonical fields.

**Ensemble pricing:** Weighted combination of multiple price sources with precision-based weights.

**Survival model:** Statistical model predicting time-to-sale probability.

**Monte Carlo optimization:** Simulation-based approach to find optimal bid under uncertainty.

**Trust level:** Confidence rating for data sources (high for APIs, low for scrapers).

**Recency decay:** Time-based weighting where older price data receives less weight (λ=0.03/day).

**Quantity explode:** Converting multi-quantity line items into individual unit rows.

**Brand gating:** Marketplace restrictions on selling certain brands without authorization.

**Sell-through horizon:** Time window for expected sales (default 60 days).

**ROI Target:** Minimum acceptable return on investment (default 1.25x).

**Risk Threshold:** Minimum probability of achieving ROI Target (default 80%).

**Cash floor:** Minimum expected cash recovery by horizon date.
