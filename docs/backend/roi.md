# ROI & Optimization Guide

Monte Carlo ROI simulation with configurable risk constraints and operational cost modeling.

## Overview

The ROI optimizer uses Monte Carlo simulation to find the maximum bid satisfying:

1. **ROI Constraint**: P(ROI >= roi_target) >= risk_threshold
2. **Cash Constraint**: Expected 60-day cash >= min_cash_60d (optional)
3. **VaR Constraint**: P5 cash recovery >= min_cash_60d_p5 (optional)

**ROI Formula**: `(total_revenue - total_costs) / (bid + lot_fixed_cost)`

Where:

- `total_revenue = sold_net + salvage_value`
- `total_costs = fees + shipping + packaging + refurb + returns`

## Core Parameters

### Risk Framework

| Parameter        | Default | Description                        |
| ---------------- | ------- | ---------------------------------- |
| `roi_target`     | 1.25    | Minimum ROI threshold (25% return) |
| `risk_threshold` | 0.80    | Confidence level (80% probability) |
| `sims`           | 2000    | Monte Carlo simulation count       |
| `lo`             | 0       | Minimum bid to consider            |
| `hi`             | 10000   | Maximum bid to consider            |

**Example**:

```json
{
  "roi_target": 1.3,
  "risk_threshold": 0.85,
  "sims": 3000
}
```

### Cost Structure

**Marketplace Fees**:

```json
{
  "marketplace_fee_pct": 0.13, // 13% marketplace commission
  "payment_fee_pct": 0.029, // 2.9% payment processing
  "per_order_fee_fixed": 0.3 // $0.30 fixed fee per transaction
}
```

**Operational Costs** (per order):

```json
{
  "shipping_per_order": 8.5, // Shipping cost
  "packaging_per_order": 1.0, // Packaging materials
  "refurb_per_order": 5.0, // Refurbishment/prep
  "return_rate": 0.08 // 8% return rate
}
```

**Manifest Risk** (Step 4 enhancement):

```json
{
  "manifest_risk_discount": 0.95, // 5% discount for manifest uncertainty
  "ops_storage_cost_daily": 0.15 // $0.15/day storage cost per item
}
```

### Revenue Components

**Sold Revenue**:

- Price drawn from item's estimated distribution
- Net of marketplace fees, payment fees, operational costs
- Adjusted for returns (refund + restocking cost)

**Salvage Value**:

```json
{
  "salvage_frac": 0.5 // 50% of estimated price for unsold items
}
```

**Payout Lag** (affects cash flow):

```json
{
  "payout_lag_days": 14 // Days from sale to cash receipt
}
```

## Cash Constraints

### Expected Cash Constraint

Minimum expected cash recovery within horizon:

```json
{
  "min_cash_60d": 1000 // Minimum expected cash at 60 days
}
```

**Use Case**: Ensure sufficient liquidity for ongoing operations.

### Value-at-Risk Constraint

Conservative cash recovery (5th percentile):

```json
{
  "min_cash_60d_p5": 800 // Minimum P5 cash recovery
}
```

**Use Case**: Risk management for conservative portfolios.

### Lot Fixed Costs

Additional acquisition costs beyond bid price:

```json
{
  "lot_fixed_cost": 150.0 // Fixed costs (inspection, transport, etc.)
}
```

Affects ROI calculation: `ROI = revenue / (bid + lot_fixed_cost)`

## Simulation Details

### Monte Carlo Process

For each simulation run:

1. **Draw Samples**: Price and sell-through for each item
2. **Compute Revenue**: Sold items net revenue + salvage for unsold
3. **Apply Costs**: Marketplace fees, operational costs, returns
4. **Calculate ROI**: Total net revenue / total investment
5. **Track Cash Flow**: Time-adjusted cash recovery curves

### Bisection Optimization

Finds optimal bid using bisection search:

1. **Initial Bounds**: [lo, hi] bid range
2. **Constraint Check**: For each bid, simulate ROI distribution
3. **Feasibility Test**: P(ROI >= target) >= threshold AND cash constraints
4. **Bisection Step**: Narrow search range based on feasibility
5. **Convergence**: Continue until bid precision < $1.00

**Tolerance**: Default $1.00 bid precision (configurable)

## Output Interpretation

### Core Metrics

```json
{
  "bid": 1250.5, // Recommended maximum bid
  "roi_p5": 1.12, // Conservative ROI (5th percentile)
  "roi_p50": 1.34, // Expected ROI (median)
  "roi_p95": 1.67, // Optimistic ROI (95th percentile)
  "prob_roi_ge_target": 0.85, // P(ROI >= target) - should equal risk_threshold
  "meets_constraints": true // Whether lot satisfies all constraints
}
```

### Cash Flow Metrics

```json
{
  "cash_60d_p5": 950.25, // Conservative 60-day cash (VaR)
  "cash_60d_p50": 1450.75, // Expected 60-day cash
  "cash_60d_p95": 2150.3, // Optimistic 60-day cash
  "expected_cash_60d": 1450.75 // Same as p50
}
```

### Portfolio Metrics

```json
{
  "core_items_count": 45, // Items passing evidence gate
  "total_items_count": 48, // All items in manifest
  "evidence_pass_rate": 0.9375, // 45/48 = 93.75%
  "total_estimated_value": 3250.75 // Sum of estimated values
}
```

## Risk Scenarios

### Conservative Profile

High certainty, lower returns:

```json
{
  "roi_target": 1.2, // 20% minimum return
  "risk_threshold": 0.9, // 90% confidence
  "min_cash_60d_p5": 800, // VaR constraint
  "manifest_risk_discount": 0.9 // 10% uncertainty discount
}
```

### Aggressive Profile

Higher returns, accept more risk:

```json
{
  "roi_target": 1.5, // 50% target return
  "risk_threshold": 0.7, // 70% confidence
  "salvage_frac": 0.3, // Lower salvage assumption
  "sims": 5000 // Higher simulation count
}
```

### Cash Flow Focus

Prioritize liquidity over returns:

```json
{
  "roi_target": 1.15, // Lower return threshold
  "min_cash_60d": 2000, // High cash requirement
  "payout_lag_days": 7, // Faster payout assumption
  "return_rate": 0.05 // Lower return rate
}
```

## Throughput Constraints

**Storage Capacity**:

```json
{
  "max_concurrent_items": 500, // Warehouse capacity limit
  "storage_cost_per_day": 0.15 // Daily storage cost per item
}
```

**Processing Limits**:

```json
{
  "max_orders_per_day": 50, // Daily order processing capacity
  "batch_processing_discount": 0.95 // 5% discount for batch efficiency
}
```

## Evidence Integration

### Quality Scoring

Items with stronger evidence get preferential weighting:

- **High Evidence**: Valid UPC/ASIN + >=5 comps + rank trend -> 100% weight
- **Medium Evidence**: Valid ID + >=3 comps + offers -> 85% weight
- **Low Evidence**: Fuzzy match + minimal comps -> 60% weight
- **Review Items**: Failed evidence gate -> Excluded from core ROI

### Evidence Adjustments

```json
{
  "evidence_weight_high": 1.0, // Full confidence multiplier
  "evidence_weight_medium": 0.85, // Medium confidence
  "evidence_weight_low": 0.6, // Low confidence
  "evidence_threshold_comps": 3 // Minimum comparables required
}
```

### Product Confidence Scoring

Product confidence scores (0-1 range) are computed for each item based on:

- **Title Similarity**: Fuzzy matching score with comparable products
- **Brand/Model Presence**: Extracted brand and model information quality
- **Price Consistency**: Z-score relative to comparable pricing
- **Data Recency**: Age of supporting evidence (Keepa, sold comps)
- **Source Count**: Number of independent data sources
- **High-Trust ID**: Presence of verified ASIN/UPC/EAN identifiers

**Confidence Factors:**

```json
{
  "title_similarity_weight": 0.3, // 30% from title matching
  "brand_model_weight": 0.25, // 25% from brand/model extraction
  "price_consistency_weight": 0.2, // 20% from price Z-score
  "data_recency_weight": 0.15, // 15% from evidence freshness
  "source_diversity_weight": 0.1 // 10% from source count
}
```

**Usage in Reports**: Product confidence appears in the Item Details table when available, helping assess the reliability of price estimates and ROI predictions for individual items.

## Calibration Integration

### Prediction Logging

When `calibration_log_path` is specified, predictions are logged:

```json
{
  "calibration_log_path": "logs/predictions.jsonl",
  "log_format": "append", // Append mode for continuous logging
  "include_context": true // Include optimization parameters
}
```

**Logged Fields**:

- Item identifiers (sku_local, asin)
- Price predictions (est_price_mu, predicted_price)
- Sell-through predictions (sell_p60, predicted_sell_p60)
- Context (roi_target, risk_threshold, timestamp)

### Outcome Integration

Calibration analysis uses outcomes to improve model accuracy:

**Required Outcomes**:

- `realized_price` - Actual sale price
- `sold_within_horizon` - Boolean (sold within 60 days)
- `days_to_sale` - Time to sale (if sold)

## Advanced Configuration

### Dynamic Risk Adjustment

Adjust risk tolerance based on portfolio composition:

```json
{
  "base_risk_threshold": 0.8,
  "evidence_quality_bonus": 0.05, // +5% threshold for high-evidence lots
  "diversification_bonus": 0.03, // +3% threshold for diverse categories
  "concentration_penalty": 0.1 // -10% threshold for single-category lots
}
```

### Seasonal Adjustments

Account for seasonal selling patterns:

```json
{
  "seasonal_multipliers": {
    "Q4": 1.15, // 15% boost for holiday season
    "Q1": 0.9, // 10% reduction post-holiday
    "Q2": 1.0, // Baseline
    "Q3": 0.95 // 5% reduction summer slowdown
  }
}
```

### Category-Specific Parameters

Different categories may have different cost structures:

```json
{
  "category_overrides": {
    "Electronics": {
      "return_rate": 0.12, // Higher return rate
      "refurb_per_order": 8.0 // Higher refurb cost
    },
    "Books": {
      "shipping_per_order": 4.5, // Lower shipping
      "salvage_frac": 0.2 // Lower salvage value
    }
  }
}
```

## Debugging & Analysis

### Constraint Analysis

When `meets_constraints = false`, check:

1. **ROI Constraint**: Is `prob_roi_ge_target < risk_threshold`?
2. **Cash Constraint**: Is expected cash below `min_cash_60d`?
3. **VaR Constraint**: Is P5 cash below `min_cash_60d_p5`?

### Sensitivity Testing

Use `sweep_bid` to analyze constraint sensitivity:

```cmd
python -m backend.cli.sweep_bid items.csv \
  --out-csv sensitivity.csv --lo 0 --hi 3000 --step 50
```

Plot results to visualize:

- ROI probability vs bid amount
- Cash recovery curves
- Constraint boundary locations

### Evidence Impact

Compare optimization with/without evidence gating:

```json
{
  "evidence_gating_enabled": true, // Standard run
  "evidence_gating_enabled": false // Include all items
}
```

Analyze difference in recommended bids and risk profiles.

---

**Next**: [Calibration Guide](calibration.md) for prediction tracking and analysis
