# Calibration Guide

Prediction logging and outcomes analysis for model accuracy improvement and decision confidence.

## Overview

Calibration tracking enables:

- **Prediction Logging**: JSONL records of price and sell-through predictions
- **Outcomes Matching**: Join predictions with realized results
- **Accuracy Metrics**: Brier scores, price MAE/RMSE, calibration curves
- **Model Improvement**: Identify bias patterns and adjustment opportunities

## Enabling Prediction Logging

Prediction logging is enabled via optimizer configuration only. The `calibration_log_path` parameter must be specified in the optimizer JSON:

**Via optimizer configuration**:

```json
{
  "roi_target": 1.25,
  "risk_threshold": 0.8,
  "calibration_log_path": "logs/predictions.jsonl"
}
```

### API Requests

**Pipeline with logging**:

```json
{
  "items_csv": "data/manifest.csv",
  "opt_json_inline": {
    "roi_target": 1.25,
    "calibration_log_path": "logs/predictions.jsonl"
  }
}
```

## JSONL Schema

### Prediction Record Format

Each logged prediction contains item-level forecasts with context:

```json
{
  "sku_local": "ITEM-001", // Local item identifier
  "asin": "B08N5WRWNW", // Amazon ASIN (if resolved)
  "upc": "123456789012", // UPC identifier (if available)
  "ean": "1234567890123", // EAN identifier (if available)
  "upc_ean_asin": "B08N5WRWNW", // Best available identifier

  // Core Predictions
  "est_price_mu": 25.5, // Price mean estimate
  "est_price_sigma": 5.2, // Price standard deviation
  "est_price_p50": 25.0, // Median price estimate
  "sell_p60": 0.72, // P(sold within 60 days)
  "sell_hazard_daily": 0.0185, // Daily hazard rate (if present)

  // Condition and seasonality factors
  "condition_bucket": "new",
  "sell_condition_factor": 1.0,
  "sell_seasonality_factor": 1.0,

  // Throughput and operational
  "mins_per_unit": 15.0,
  "quantity": 1,

  // Downstream Compatibility Aliases
  "predicted_price": 25.5, // Alias for est_price_mu
  "predicted_sell_p60": 0.72, // Alias for sell_p60

  // Nested Context Object
  "context": {
    "roi_target": 1.25,
    "risk_threshold": 0.8,
    "horizon_days": 60,
    "lot_id": "LOT-2024-001",
    "opt_source": "run_pipeline", // "run_optimize" or "run_pipeline"
    "opt_params": {
      "roi_target": 1.25,
      "risk_threshold": 0.8,
      "sims": 2000,
      "salvage_frac": 0.5
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },

  // Flattened Fields (backward compatibility)
  "roi_target": 1.25,
  "risk_threshold": 0.8,
  "horizon_days": 60,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Key Fields

**Item Identification**:

- `sku_local` - Primary key for matching outcomes
- `asin` - Amazon identifier (if available)
- `upc` / `ean` / `upc_ean_asin` - Product identifiers

**Price Predictions**:

- `est_price_mu` / `predicted_price` - Expected selling price
- `est_price_sigma` - Price uncertainty
- `est_price_p50` - Median price estimate

**Survival Predictions**:

- `sell_p60` / `predicted_sell_p60` - Sell-through probability
- `sell_hazard_daily` - Daily hazard rate (if present)

**Condition and Factors**:

- `condition_bucket` - Normalized condition grouping
- `sell_condition_factor` - Condition adjustment factor
- `sell_seasonality_factor` - Seasonal adjustment factor

**Operational**:

- `mins_per_unit` - Processing time estimate
- `quantity` - Item quantity

**Context Metadata**:

- `opt_source` - Source of prediction ("run_optimize", "run_pipeline")
- `opt_params` - Configuration parameters used
- `timestamp` - Prediction generation time

## Outcomes Data Format

### Required CSV Schema

Create outcomes CSV with realized results:

```csv
sku_local,realized_price,sold_within_horizon,days_to_sale
ITEM-001,27.50,True,42
ITEM-002,15.75,False,60
ITEM-003,35.00,True,28
ITEM-004,22.00,True,55
ITEM-005,0.00,False,60
```

**Required Columns**:

- `sku_local` - Matches prediction records
- `realized_price` - Actual sale price (0 if unsold)
- `sold_within_horizon` - Boolean: sold within timeframe
- `days_to_sale` - Days until sale (horizon if unsold)

**Optional Columns**:

- `sale_date` - Actual sale timestamp
- `marketplace` - Where item sold (eBay, Amazon, etc.)
- `final_condition` - Condition at sale
- `return_occurred` - Boolean: was item returned

### Data Collection Methods

**Manual Entry**:

```cmd
# Template generation
echo sku_local,realized_price,sold_within_horizon,days_to_sale > outcomes_template.csv
# Manual completion with realized data
```

**Automated Export**:

```python
# From marketplace APIs or internal systems
import pandas as pd

outcomes = pd.DataFrame({
    'sku_local': ['ITEM-001', 'ITEM-002'],
    'realized_price': [27.50, 0.00],
    'sold_within_horizon': [True, False],
    'days_to_sale': [42, 60]
})
outcomes.to_csv('outcomes.csv', index=False)
```

## Analysis Commands

### Generate Calibration Report

**CLI Command**:

```cmd
python -m backend.cli.calibration_report ^
  logs\predictions.jsonl ^
  data\outcomes.csv ^
  --out-json reports\calibration_metrics.json ^
  --out-html reports\calibration_report.html
```

The calibration_report CLI command handles analysis. There is no API endpoint for calibration analysis.

### Report Contents

**Probability Calibration**:

- **Brier Score**: Overall probability accuracy (lower = better)
- **Calibration Bins**: Predicted vs actual rates by probability range
- **Reliability Curve**: Isotonic calibration visualization

**Price Accuracy**:

- **MAE**: Mean Absolute Error for price predictions
- **RMSE**: Root Mean Square Error for price predictions
- **MAPE**: Mean Absolute Percentage Error
- **Coverage**: Percentage of outcomes within predicted intervals

**Sample Output**:

```json
{
  "brier_score": 0.1847, // Lower is better (perfect = 0)
  "samples": 1247, // Number of predictions analyzed
  "price_metrics": {
    "mae": 8.32, // $8.32 average price error
    "rmse": 12.15, // $12.15 RMS price error
    "mape": 24.7, // 24.7% average percentage error
    "samples": 892 // Price predictions with outcomes
  },
  "calibration_bins": [
    {
      "label": "0.0-0.1", // Probability range
      "count": 125, // Number of predictions
      "pred": 0.052, // Average predicted probability
      "actual": 0.048, // Actual outcome rate
      "bias": 0.004 // Prediction - actual (positive = overconfident)
    }
  ]
}
```

## Frontend Integration

### Calibration Page

The frontend `/calibration` page provides client-side analysis:

**File Upload**:

- Predictions JSONL file
- Outcomes CSV file
- Drag-and-drop interface with validation

**Real-time Analysis**:

- Client-side parsing and computation
- No backend dependencies for analysis
- Interactive calibration charts

**Metrics Display**:

- Brier score interpretation
- Price accuracy metrics
- Calibration bin visualization
- Downloadable JSON reports

### CSV Parsing Limitations

The client-side CSV parser has limitations:

! **Simple Parser**: Expects comma-separated values without quoted commas
! **No Escape Support**: Cannot handle embedded commas in quoted fields
! **Header Requirements**: First row must contain column headers

**Workarounds**:

- Export outcomes without embedded commas
- Use semicolon delimiters if needed
- Pre-process complex CSVs before upload

## Calibration Lifecycle

### 1. Prediction Phase

**Enable Logging** (append mode automatically used):

```json
{
  "calibration_log_path": "logs/2024-01-15_predictions.jsonl"
}
```

**Monitor Logging**:

```cmd
# Check log file growth
dir logs\*.jsonl

# View recent predictions (Windows)
powershell "Get-Content logs\predictions.jsonl -Tail 5"
```

### 2. Outcome Collection

**Track Sales** (30-90 days post-prediction):

- Monitor marketplace sales
- Record realized prices and timing
- Note returns and condition changes

**Export Outcomes**:

```cmd
# From sales system to outcomes CSV
python scripts\export_outcomes.py --start-date 2024-01-15 --format csv
```

### 3. Analysis & Reporting

**Generate Metrics**:

```cmd
python -m backend.cli.calibration_report ^
  logs\predictions.jsonl outcomes\2024-01-15.csv ^
  --out-json metrics\calibration_2024-01-15.json
```

**Review Results**:

- Brier score trends over time
- Price accuracy by category
- Calibration bias patterns

### 4. Model Refinement

**Identify Bias Patterns**:

- Systematic overconfidence in high-probability predictions
- Price estimation errors by category or condition
- Seasonal or temporal drift in accuracy

**Apply Corrections**:

```json
{
  "calibration_adjustments": {
    "probability_scaling": 0.95, // Scale down overconfident predictions
    "price_category_bias": {
      // Category-specific price adjustments
      "Electronics": 0.92,
      "Books": 1.05
    }
  }
}
```

## Interpretation Guidelines

### Brier Score Benchmarks

- **< 0.10**: Excellent calibration
- **0.10 - 0.15**: Good calibration
- **0.15 - 0.20**: Acceptable calibration
- **0.20 - 0.25**: Poor calibration
- **> 0.25**: Very poor calibration (needs attention)

### Price Accuracy Targets

**MAPE Benchmarks**:

- **< 15%**: Excellent price accuracy
- **15% - 25%**: Good accuracy
- **25% - 35%**: Acceptable accuracy
- **35% - 50%**: Poor accuracy
- **> 50%**: Very poor accuracy (review required)

### Calibration Bin Analysis

**Well-Calibrated**: Predicted and actual rates closely match
**Overconfident**: Predicted > actual (positive bias)
**Underconfident**: Predicted < actual (negative bias)

**Action Thresholds**:

- **|bias| < 0.05**: No action needed
- **|bias| 0.05-0.10**: Monitor trend
- **|bias| > 0.10**: Apply calibration correction

## Troubleshooting

### Common Issues

**Missing Outcomes**:

```
Error: No matching records found between predictions and outcomes
```

**Solution**: Verify `sku_local` values match exactly between files

**Date Format Issues**:

```
Error: Invalid date format in outcomes
```

**Solution**: Use ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`

**CSV Parsing Errors**:

```
Error: Failed to parse CSV line: "Item with, comma"
```

**Solution**: Remove commas from item descriptions or use alternative delimiter

### Data Quality Checks

**Validate Predictions**:

```cmd
python -c "
import json
with open('predictions.jsonl') as f:
    for i, line in enumerate(f):
        try:
            json.loads(line)
        except:
            print(f'Invalid JSON on line {i+1}')
"
```

**Validate Outcomes**:

```cmd
python -c "
import pandas as pd
df = pd.read_csv('outcomes.csv')
print('Columns:', df.columns.tolist())
print('Missing values:', df.isnull().sum())
print('Data types:', df.dtypes)
"
```

## Automation

### Automated Calibration Pipeline

The calibration system provides automated CLIs for running calibration analysis and applying bounded adjustments.

#### calibration_run CLI

Consumes predictions JSONL and outcomes CSV to generate metrics and suggestions:

```bash
# Basic usage
py -3 -m backend.cli.calibration_run predictions.jsonl outcomes.csv

# With custom output paths
py -3 -m backend.cli.calibration_run predictions.jsonl outcomes.csv \
  --out-metrics metrics.json \
  --out-suggestions suggestions.json \
  --history-dir backend/lotgenius/data/calibration/history
```

**Features:**

- Writes timestamped metrics and suggestions to history directory
- Updates canonical `backend/lotgenius/data/calibration_suggestions.json`
- Shows summary metrics (MAE, RMSE, bias) in output
- Handles missing data gracefully

#### calibration_apply CLI

Converts suggestions into bounded condition factor overrides:

```bash
# Apply with default bounds [0.5, 1.2]
py -3 -m backend.cli.calibration_apply \
  --suggestions backend/lotgenius/data/calibration_suggestions.json \
  --out-overrides backend/lotgenius/data/calibration_overrides.json

# Custom bounds
py -3 -m backend.cli.calibration_apply \
  --suggestions suggestions.json \
  --out-overrides overrides.json \
  --min-factor 0.6 \
  --max-factor 1.1

# Dry run to preview changes
py -3 -m backend.cli.calibration_apply \
  --suggestions suggestions.json \
  --out-overrides overrides.json \
  --dry-run
```

**Safety Features:**

- Bounds enforcement: factors clamped to `[min-factor, max-factor]`
- Only processes `condition_price_factor` suggestions
- Shows bounded adjustments in output
- Dry run mode for preview

### Environment Variable Configuration

#### LOTGENIUS_CALIBRATION_OVERRIDES

Set this environment variable to enable automatic loading of condition factor overrides:

```bash
# Windows
set LOTGENIUS_CALIBRATION_OVERRIDES=backend/lotgenius/data/calibration_overrides.json

# Linux/Mac
export LOTGENIUS_CALIBRATION_OVERRIDES=backend/lotgenius/data/calibration_overrides.json
```

**Override File Format:**

```json
{
  "CONDITION_PRICE_FACTOR": {
    "new": 0.99,
    "used_good": 0.88,
    "like_new": 0.93
  }
}
```

**Safety Properties:**

- **Opt-in**: No file = no overrides, zero behavior change
- **Bounded**: Only factors within reasonable ranges should be applied
- **Selective**: Only `CONDITION_PRICE_FACTOR` overrides supported
- **Graceful**: Invalid/missing files silently ignored
- **Merge**: Overrides merge with defaults (partial updates supported)

### Automation Workflow

Complete monthly calibration cycle:

```bash
# 1. Run calibration analysis
py -3 -m backend.cli.calibration_run \
  predictions_month.jsonl outcomes_month.csv

# 2. Review suggestions
cat backend/lotgenius/data/calibration_suggestions.json

# 3. Generate bounded overrides
py -3 -m backend.cli.calibration_apply \
  --suggestions backend/lotgenius/data/calibration_suggestions.json \
  --out-overrides backend/lotgenius/data/calibration_overrides.json

# 4. Enable overrides
set LOTGENIUS_CALIBRATION_OVERRIDES=backend/lotgenius/data/calibration_overrides.json

# 5. Test with sample data
py -3 -m backend.cli.estimate_prices sample_input.csv sample_output.csv

# 6. Monitor results and history
dir backend/lotgenius/data/calibration/history/
```

### History and Monitoring

All calibration runs create timestamped files in `backend/lotgenius/data/calibration/history/`:

- `metrics_YYYYMMDD_HHMMSS.json`: Detailed accuracy metrics
- `suggestions_YYYYMMDD_HHMMSS.json`: Adjustment recommendations

Use these for:

- **Trend Analysis**: Track accuracy improvements over time
- **Regression Detection**: Identify performance degradations
- **Audit Trail**: Review what adjustments were suggested/applied

---

**Next**: [Frontend UI Guide](../frontend/ui.md) for web interface usage
