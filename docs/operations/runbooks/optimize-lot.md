# Lot Optimization Runbook

End-to-end procedure for analyzing and optimizing liquidation lot investments.

## Overview

This runbook covers the complete workflow from raw manifest CSV to decision-ready investment recommendation, including evidence validation, risk assessment, and calibration logging.

## Prerequisites

### System Setup

- [ ] Backend environment configured (see [dev.md](dev.md))
- [ ] `KEEPA_API_KEY` environment variable set
- [ ] API server running (if using web interface)
- [ ] Sufficient API credits for manifest size

### Input Requirements

- [ ] **Manifest CSV**: B-Stock lot manifest with item details
- [ ] **Optimizer Config**: ROI targets and risk constraints (optional)
- [ ] **Category Priors**: Price floors by category (optional)

### Expected Timeline

- **Small Lot** (< 100 items): 2-5 minutes
- **Medium Lot** (100-500 items): 5-15 minutes
- **Large Lot** (500+ items): 15-60 minutes

## Method 1: Web Interface (Recommended)

### Step 1: Start Web Interface

```cmd
# Terminal 1: Start API server
uvicorn backend.app.main:app --port 8787 --reload

# Terminal 2: Start frontend (optional)
cd frontend
npm run dev
```

**Verification**:

- API: Visit `http://localhost:8787/docs`
- Frontend: Visit `http://localhost:3000`

### Step 2: Prepare Input Files

**Manifest CSV Requirements**:

- Headers containing item identifiers (UPC, EAN, ASIN, Title)
- Condition information (New, Used, Refurbished, etc.)
- Quantity per item (will be exploded to individual rows)
- Optional: Category, Brand, Model information

**Example Manifest**:

```csv
sku_local,title,condition,qty,upc,brand
ITEM-001,"Bluetooth Headphones",New,5,123456789012,SoundCorp
ITEM-002,"USB Cable 6ft",Used,10,234567890123,TechBrand
ITEM-003,"Phone Case iPhone",Refurbished,3,345678901234,CasePro
```

**Optimizer Configuration** (optional):

```json
{
  "roi_target": 1.25,
  "risk_threshold": 0.8,
  "lo": 0,
  "hi": 5000,
  "sims": 2000,
  "calibration_log_path": "logs/predictions_2024-01-15.jsonl"
}
```

### Step 3: Upload and Configure

**Using Frontend**:

1. Navigate to `http://localhost:3000`
2. Choose "Pipeline (SSE)" tab for real-time progress
3. Upload manifest CSV via drag-and-drop
4. Configure optimizer parameters (or use defaults)
5. Set calibration log path (recommended)
6. Click "Run Pipeline"

**Using API Directly**:

```bash
curl -N -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@manifest.csv \
  -F opt_json_inline='{"roi_target": 1.25, "calibration_log_path": "logs/predictions.jsonl"}' \
  http://localhost:8787/v1/pipeline/upload/stream
```

### Step 4: Monitor Progress

**SSE Events to Watch For**:

1. `start` - Processing initiated
2. `parse` - Manifest parsing (check coverage %)
3. `resolve` - ID resolution (watch for high failure rates)
4. `price` - Price estimation (check source counts)
5. `sell` - Sell-through modeling (survival model applied)
6. `optimize` - ROI optimization (constraint satisfaction)
7. `report` - Report generation
8. `done` - Processing complete

**Key Metrics During Processing**:

- **Header Coverage**: Should be >=70% for reliable results
- **ID Resolution Rate**: Higher is better (aim for >60%)
- **Evidence Pass Rate**: Items passing evidence gate (aim for >50%)

### Step 5: Review Results

**Decision Metrics**:

- **Recommended Bid**: Maximum investment amount
- **Expected ROI**: P50 return multiple (e.g., 1.34 = 34% return)
- **Risk Confidence**: P(ROI >= target) should equal risk_threshold
- **Meets Constraints**: Boolean decision indicator
- **60-Day Cash**: Expected liquidity timeline

**Example Results**:

```json
{
  "status": "ok",
  "bid": 1250.5,
  "roi_p50": 1.34,
  "prob_roi_ge_target": 0.8,
  "meets_constraints": true,
  "core_items_count": 45,
  "total_items_count": 48
}
```

## Method 2: Command Line Interface

### Step 1: One-Command Analysis

**Complete Pipeline**:

```cmd
python -m backend.cli.report_lot data\manifests\lot_sample.csv ^
  --roi-target 1.25 --risk-threshold 0.80 ^
  --calibration-log-path logs\predictions.jsonl ^
  --out-markdown reports\lot_decision.md ^
  --out-html reports\lot_decision.html
```

**With Custom Configuration**:

```cmd
python -m backend.cli.report_lot data\manifests\lot_sample.csv ^
  --opt-json configs\conservative_optimizer.json ^
  --out-markdown reports\lot_report.md
```

### Step 2: Step-by-Step Analysis (Advanced)

**For debugging or customization**:

```cmd
# 1. Validate manifest
python -m backend.cli.validate_manifest manifest.csv --show-coverage

# 2. Parse and clean
python -m backend.cli.parse_clean manifest.csv --out csv --output clean.csv --explode

# 3. Resolve IDs with stats
python -m backend.cli.resolve_ids clean.csv --with-stats --output-csv enriched.csv

# 4. Estimate prices
python -m backend.cli.estimate_price enriched.csv --out-csv priced.csv

# 5. Model sell-through
python -m backend.cli.estimate_sell priced.csv --out-csv processed.csv

# 6. Optimize bid
python -m backend.cli.optimize_bid processed.csv --out-json optimization.json

# 7. Generate report
python -m backend.cli.report_lot processed.csv --opt-json optimization.json ^
  --out-markdown decision.md
```

## Method 3: Python Script Integration

### Custom Analysis Script

```python
#!/usr/bin/env python3
"""
Custom lot analysis script with additional business logic.
"""
import json
import pandas as pd
from pathlib import Path
from lotgenius.api.service import run_pipeline

def analyze_lot(manifest_path: str, config: dict) -> dict:
    """Run complete lot analysis with custom post-processing."""

    # Run standard pipeline
    result = run_pipeline(
        items_csv_path=manifest_path,
        opt_dict=config
    )

    # Custom business logic
    if result['meets_constraints']:
        # Add custom risk adjustments
        adjusted_bid = result['bid'] * 0.95  # 5% safety margin
        result['adjusted_bid'] = adjusted_bid
        result['safety_margin'] = 0.05

    # Add portfolio context
    result['portfolio_impact'] = calculate_portfolio_impact(result)

    return result

def calculate_portfolio_impact(result: dict) -> dict:
    """Calculate impact on existing portfolio."""
    return {
        'category_concentration': 'Low',  # Based on existing positions
        'liquidity_impact': 'Neutral',   # Based on cash flow
        'risk_correlation': 'Low'        # Based on existing risk exposure
    }

if __name__ == "__main__":
    config = {
        'roi_target': 1.30,  # Higher target for safety
        'risk_threshold': 0.85,
        'calibration_log_path': 'logs/custom_analysis.jsonl'
    }

    result = analyze_lot('data/lot_manifest.csv', config)

    # Save results
    with open('results/custom_analysis.json', 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Analysis complete. Recommended bid: ${result.get('bid', 'N/A')}")
```

## Evidence Gate Analysis

### Understanding Evidence Requirements

Items must pass evidence validation to be included in core ROI analysis:

**Primary Requirements**:

- [ ] **Valid Identifier**: UPC, EAN, or ASIN that resolves via Keepa
- [ ] **Sufficient Comparables**: >=3 sold items within 180 days
- [ ] **Secondary Signal**: Sales rank trend OR offer presence (if enabled)

**Evidence Categories**:

- **PASS**: Included in core ROI calculation
- **REVIEW**: Excluded from core ROI, shown as upside potential
- **FAIL**: Insufficient data for reliable prediction

### Interpreting Evidence Results

**High Evidence Pass Rate (>80%)**:

- OK Strong confidence in results
- OK Proceed with recommended bid
- OK Consider aggressive risk parameters

**Medium Evidence Pass Rate (50-80%)**:

- ! Moderate confidence in results
- ! Consider conservative adjustments
- ! Review failed items manually

**Low Evidence Pass Rate (<50%)**:

- X Low confidence in results
- X Consider passing on lot
- X Investigate manifest quality issues

### Improving Evidence Quality

**Manifest Enhancement**:

```cmd
# Check header mapping quality
python -m backend.cli.map_preview manifest.csv --show-candidates --top-k 3

# Look for unmapped identifier columns
# Consider manual aliases for non-standard headers
python -m backend.cli.map_preview manifest.csv --save-alias "Item Code" upc
```

**Alternative Approaches**:

- Request better manifest data from seller
- Focus analysis on high-evidence subset
- Adjust evidence thresholds for unique categories

## Risk Assessment Guidelines

### Conservative Profile

**Use When**:

- First-time analysis of new seller/category
- Large investment amounts (>$5,000)
- Tight cash flow constraints

**Parameters**:

```json
{
  "roi_target": 1.2, // Lower return expectation
  "risk_threshold": 0.9, // Higher confidence requirement
  "min_cash_60d": 1000, // Cash flow protection
  "manifest_risk_discount": 0.9 // 10% uncertainty discount
}
```

### Standard Profile

**Use When**:

- Established seller relationship
- Familiar product categories
- Moderate investment amounts ($1,000-$5,000)

**Parameters**:

```json
{
  "roi_target": 1.25, // Standard 25% return
  "risk_threshold": 0.8, // 80% confidence
  "sims": 2000 // Standard simulation count
}
```

### Aggressive Profile

**Use When**:

- High-confidence opportunities
- Small test investments (<$1,000)
- Strong evidence quality (>90% pass rate)

**Parameters**:

```json
{
  "roi_target": 1.5, // Higher return target
  "risk_threshold": 0.7, // Accept more risk
  "salvage_frac": 0.3 // Conservative salvage assumption
}
```

## Decision Framework

### Go/No-Go Criteria

**PROCEED** if all conditions met:

- [ ] `meets_constraints = true`
- [ ] Evidence pass rate > 50%
- [ ] Expected ROI > personal threshold
- [ ] 60-day cash timeline acceptable
- [ ] Lot size within operational capacity

**REVIEW** if any condition met:

- [ ] Evidence pass rate 30-50%
- [ ] ROI close to threshold (+/-5%)
- [ ] Large upside in REVIEW items
- [ ] Unfamiliar product categories

**PASS** if any condition met:

- [ ] `meets_constraints = false`
- [ ] Evidence pass rate < 30%
- [ ] Expected cash timeline too slow
- [ ] Operational capacity constraints

### Risk Mitigation

**Bid Adjustments**:

```python
# Apply safety margins based on uncertainty
final_bid = recommended_bid * adjustment_factor

adjustment_factors = {
    'high_evidence': 1.00,      # No adjustment
    'medium_evidence': 0.95,    # 5% reduction
    'low_evidence': 0.85,       # 15% reduction
    'unknown_seller': 0.90,     # 10% reduction
    'tight_timeline': 0.95      # 5% reduction
}
```

**Position Sizing**:

- **Test Position**: 10-20% of recommended bid for new relationships
- **Standard Position**: Full recommended bid for established patterns
- **Large Position**: 110-120% of recommended bid for high-confidence opportunities

## Calibration Logging

### Enable Prediction Tracking

**Always recommended** for decision audit trail and model improvement:

```json
{
  "calibration_log_path": "logs/predictions_YYYY-MM-DD.jsonl"
}
```

**Log File Management**:

```cmd
# Create logs directory
mkdir logs

# Monitor log file growth
dir logs\*.jsonl

# Compress old logs
powershell Compress-Archive logs\*.jsonl logs\archived_predictions.zip
```

### Prediction Schema Verification

**Check logged predictions**:

```cmd
# View first prediction record
python -c "
import json
with open('logs/predictions.jsonl') as f:
    record = json.loads(f.readline())
    print(json.dumps(record, indent=2))
"
```

**Expected fields**:

- `sku_local`, `asin`, `title`, `condition`
- `est_price_mu`, `predicted_price` (alias)
- `sell_p60`, `predicted_sell_p60` (alias)
- `context` object with optimization parameters

## Troubleshooting

### Common Issues

#### Low Header Coverage

**Error**: `Header coverage below threshold (XX% < 70%)`

**Solutions**:

1. Review unmapped columns with `--show-candidates`
2. Add manual aliases for non-standard headers
3. Request better manifest format from seller
4. Lower coverage threshold (not recommended)

#### API Rate Limiting

**Error**: `Too many requests` or `Rate limit exceeded`

**Solutions**:

1. Wait for rate limit reset (typically hourly)
2. Reduce batch size for large manifests
3. Implement exponential backoff in scripts
4. Contact Keepa for rate limit increase

#### Evidence Gate Failures

**Warning**: `Low evidence pass rate: XX% of items excluded`

**Investigation**:

```cmd
# Check ID resolution success rate
python -m backend.cli.resolve_ids manifest.csv --no-network --show-summary

# Review failed items manually
grep '"evidence_gate": false' audit_log.jsonl | head -5
```

**Solutions**:

1. Improve manifest quality (better UPC/EAN data)
2. Adjust evidence thresholds for unique categories
3. Manual research for high-value failed items

#### Memory Issues (Large Manifests)

**Error**: `MemoryError` or slow processing

**Solutions**:

```cmd
# Process in smaller batches
split -l 500 large_manifest.csv batch_

# Use lower simulation count initially
python -m backend.cli.optimize_bid items.csv --sims 500

# Increase system memory or use server with more RAM
```

### Performance Optimization

**Speed Improvements**:

```json
{
  "sims": 1000, // Reduce for faster results
  "evidence_min_comps": 2, // Lower threshold
  "cache_ttl_hours": 168 // Use 7-day cache
}
```

**Quality vs Speed Trade-offs**:

- **Development**: 500-1000 sims, relaxed evidence
- **Production**: 2000+ sims, standard evidence
- **High-Stakes**: 5000+ sims, strict evidence

## Verification Checklist

### Pre-Analysis

- [ ] Manifest CSV format validated
- [ ] Required environment variables set
- [ ] Keepa API credits sufficient
- [ ] Output directories exist and writable

### During Analysis

- [ ] Header coverage >= 70%
- [ ] ID resolution rate > 50%
- [ ] No critical errors in SSE stream
- [ ] Evidence pass rate acceptable

### Post-Analysis

- [ ] `meets_constraints` status reviewed
- [ ] ROI metrics within expectations
- [ ] Cash flow timeline acceptable
- [ ] Calibration log created (if enabled)
- [ ] Decision documented with rationale

### Decision Documentation

**Record Key Information**:

```json
{
  "analysis_date": "2024-01-15",
  "manifest_file": "lot_sample.csv",
  "recommended_bid": 1250.5,
  "decision": "PROCEED",
  "rationale": "High evidence quality (85%), meets ROI target with 20% margin",
  "risk_factors": ["Unknown seller", "Electronics concentration"],
  "calibration_log": "logs/predictions_2024-01-15.jsonl"
}
```

---

**Next**: [Calibration Cycle Runbook](calibration-cycle.md) for prediction tracking and model improvement
