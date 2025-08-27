# Example Files

Sample configurations and data files for Lot Genius analysis and calibration.

## Files

### optimizer.json

**Purpose**: Complete optimizer configuration template with all available parameters

**Usage**:

```cmd
# CLI with configuration file
python -m backend.cli.optimize_bid items.csv --opt-json examples/optimizer.json

# API with file reference
curl -X POST http://localhost:8787/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"items_csv": "data/items.csv", "opt_json_path": "examples/optimizer.json"}'
```

**Key Features**:

- Comprehensive parameter documentation with inline comments
- Example profiles (conservative, standard, aggressive)
- Category-specific cost structures
- ROI and cash flow constraints
- Calibration logging configuration

**Parameter Categories**:

- **Risk Framework**: `roi_target`, `risk_threshold`, `sims`
- **Cost Structure**: Marketplace fees, shipping, returns, refurbishment
- **Constraints**: Cash flow, lot fixed costs, salvage assumptions
- **Operational**: Storage costs, payout timing, risk discounts

### synthetic_outcomes.csv

**Purpose**: Sample outcomes data for calibration analysis walkthrough

**Format**: Standard outcomes CSV matching prediction JSONL records

**Contents**:

- 25 synthetic outcome records
- Mix of sold and unsold items (60% sell-through rate)
- Various sale prices and timing
- Return occurrences included
- Multiple marketplace examples

**Column Definitions**:

- `sku_local`: Item identifier (matches prediction records)
- `realized_price`: Actual sale price (0.00 if unsold)
- `sold_within_horizon`: Boolean (sold within 60 days)
- `days_to_sale`: Days until sale (60 if unsold)
- `sale_date`: ISO date format (empty if unsold)
- `marketplace`: Where sold (eBay, Amazon, None)
- `return_occurred`: Boolean return flag

**Usage**:

```cmd
# Calibration analysis (assuming matching predictions exist)
python -m backend.cli.calibration_report \
  logs/predictions.jsonl \
  examples/synthetic_outcomes.csv \
  --out-json calibration_analysis.json

# Frontend calibration page
# Upload predictions JSONL + synthetic_outcomes.csv files
```

**Statistics**:

- Total records: 25
- Sold within horizon: 15 (60%)
- Unsold: 10 (40%)
- Returns: 2 (13% of sold items)
- Average days to sale: 34.5 (sold items only)
- Average sale price: $27.92 (sold items only)

## Integration Examples

### Complete Workflow

**1. Generate Predictions** (creates matching prediction log):

```cmd
# Create synthetic prediction log that matches outcomes
python -c "
import json
from datetime import datetime

# Generate predictions matching synthetic outcomes
items = []
for i in range(1, 26):
    sku = f'ITEM-{i:03d}'
    # Realistic predictions based on outcomes pattern
    price = 20 + (i % 15) * 2  # Varying prices
    prob = 0.65 + (i % 5) * 0.05  # Varying probabilities

    record = {
        'sku_local': sku,
        'asin': f'B08N{i:04d}W',
        'est_price_mu': price,
        'est_price_sigma': price * 0.2,
        'predicted_price': price,
        'sell_p60': prob,
        'predicted_sell_p60': prob,
        'context': {
            'roi_target': 1.25,
            'risk_threshold': 0.80,
            'timestamp': '2024-01-15T10:30:00Z'
        },
        'roi_target': 1.25,
        'timestamp': '2024-01-15T10:30:00Z'
    }
    items.append(record)

# Write JSONL
with open('synthetic_predictions.jsonl', 'w') as f:
    for item in items:
        f.write(json.dumps(item) + '\n')

print('Generated synthetic_predictions.jsonl with 25 records')
"
```

**2. Run Calibration Analysis**:

```cmd
python -m backend.cli.calibration_report \
  synthetic_predictions.jsonl \
  examples/synthetic_outcomes.csv \
  --out-json synthetic_calibration.json \
  --out-html synthetic_calibration.html
```

**Expected Results**:

- Brier Score: ~0.16-0.20 (synthetic data with realistic noise)
- Price MAE: ~$5-8 (varies based on prediction accuracy)
- Calibration bins: Some overconfidence in mid-range probabilities

### Custom Configuration Examples

**Conservative Investment**:

```json
{
  "roi_target": 1.15,
  "risk_threshold": 0.9,
  "min_cash_60d": 800,
  "manifest_risk_discount": 0.9,
  "return_rate": 0.1,
  "salvage_frac": 0.4
}
```

**Aggressive Growth**:

```json
{
  "roi_target": 1.6,
  "risk_threshold": 0.65,
  "sims": 3000,
  "salvage_frac": 0.25,
  "lot_fixed_cost": 200
}
```

**Cash Flow Focus**:

```json
{
  "roi_target": 1.2,
  "min_cash_60d": 1500,
  "min_cash_60d_p5": 1000,
  "payout_lag_days": 7,
  "return_rate": 0.06
}
```

## Customization

### Creating Your Own Examples

**Optimizer Configuration**:

1. Start with `examples/optimizer.json`
2. Modify parameters for your use case
3. Test with small lot first
4. Document assumptions and rationale

**Outcomes Data**:

1. Export from your sales system in required CSV format
2. Ensure `sku_local` values match prediction logs
3. Include all required columns
4. Validate data quality before analysis

**Manifest Data**:
Create test manifests for development:

```cmd
python -c "
import pandas as pd

# Create test manifest
df = pd.DataFrame([
    {'sku_local': 'TEST-001', 'title': 'Bluetooth Headphones', 'condition': 'New', 'qty': 2, 'upc': '123456789012'},
    {'sku_local': 'TEST-002', 'title': 'USB Cable', 'condition': 'Used', 'qty': 5, 'upc': '234567890123'},
    {'sku_local': 'TEST-003', 'title': 'Phone Case', 'condition': 'Refurb', 'qty': 1, 'asin': 'B08N5WRWNW'}
])

df.to_csv('test_manifest.csv', index=False)
print('Created test_manifest.csv')
"
```

## Documentation References

- **[ROI Parameters](../docs/backend/roi.md)**: Detailed parameter explanations
- **[Calibration Guide](../docs/backend/calibration.md)**: Outcomes format and analysis
- **[CLI Commands](../docs/backend/cli.md)**: Command-line usage examples
- **[API Reference](../docs/backend/api.md)**: HTTP endpoint documentation

---

These examples provide a starting point for Lot Genius analysis. Customize parameters based on your specific use case, cost structure, and risk tolerance.
