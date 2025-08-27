# Calibration Cycle Runbook

**Purpose**: Monthly calibration review and adjustment cycle for lot-genius pricing models.

**Frequency**: Monthly (first week of each month)

**Owner**: Data Science Team

**Duration**: ~2-3 hours

## Overview

The calibration cycle reviews model performance, identifies bias patterns, and applies bounded adjustments to improve accuracy. This process is automated but requires human review for safety.

## Prerequisites

- [ ] Predictions data from previous month available in JSONL format
- [ ] Outcomes data from previous month available in CSV format
- [ ] Access to `backend/lotgenius/data/calibration/` directory
- [ ] Environment configured for CLI execution

## Monthly Checklist

### Phase 1: Data Collection

- [ ] **Collect Predictions Data**

  ```bash
  # Locate predictions JSONL file for previous month
  # Expected location: backend/lotgenius/data/predictions/predictions_YYYYMM.jsonl
  ls backend/lotgenius/data/predictions/predictions_*.jsonl
  ```

- [ ] **Collect Outcomes Data**

  ```bash
  # Locate outcomes CSV file for previous month
  # Expected location: backend/lotgenius/data/outcomes/outcomes_YYYYMM.csv
  ls backend/lotgenius/data/outcomes/outcomes_*.csv
  ```

- [ ] **Verify Data Quality**

  ```bash
  # Check predictions file structure
  head -n 3 backend/lotgenius/data/predictions/predictions_YYYYMM.jsonl

  # Check outcomes file structure
  head -n 5 backend/lotgenius/data/outcomes/outcomes_YYYYMM.csv
  ```

### Phase 2: Calibration Analysis

- [ ] **Run Calibration Analysis**

  ```bash
  py -3 -m backend.cli.calibration_run \
    backend/lotgenius/data/predictions/predictions_YYYYMM.jsonl \
    backend/lotgenius/data/outcomes/outcomes_YYYYMM.csv
  ```

- [ ] **Review Overall Metrics**

  ```bash
  # Check latest metrics file
  cat backend/lotgenius/data/calibration/history/metrics_*.json | tail -n 50
  ```

  **Key Metrics to Review:**
  - Overall MAE (target: < 0.10)
  - Overall RMSE (target: < 0.15)
  - Overall Bias (target: -0.05 to +0.05)
  - Condition-specific biases

- [ ] **Review Suggestions**

  ```bash
  # Check canonical suggestions
  cat backend/lotgenius/data/calibration_suggestions.json
  ```

  **Review Criteria:**
  - Are suggested factors reasonable (0.5 - 1.2 range)?
  - Do suggestions align with observed bias patterns?
  - Are there any extreme adjustments (>20% change)?

### Phase 3: Apply Adjustments

- [ ] **Generate Overrides (Dry Run First)**

  ```bash
  # Preview what would be applied
  py -3 -m backend.cli.calibration_apply \
    --suggestions backend/lotgenius/data/calibration_suggestions.json \
    --out-overrides backend/lotgenius/data/calibration_overrides.json \
    --dry-run
  ```

- [ ] **Review Dry Run Output**
  - Verify all factors are within bounds [0.5, 1.2]
  - Check that adjustments make business sense
  - Document any concerns or exceptions

- [ ] **Apply Overrides**

  ```bash
  # Generate actual overrides file
  py -3 -m backend.cli.calibration_apply \
    --suggestions backend/lotgenius/data/calibration_suggestions.json \
    --out-overrides backend/lotgenius/data/calibration_overrides.json \
    --min-factor 0.5 \
    --max-factor 1.2
  ```

- [ ] **Enable Overrides**

  ```bash
  # Windows
  set LOTGENIUS_CALIBRATION_OVERRIDES=backend/lotgenius/data/calibration_overrides.json

  # Linux/Mac
  export LOTGENIUS_CALIBRATION_OVERRIDES=backend/lotgenius/data/calibration_overrides.json
  ```

### Phase 4: Validation

- [ ] **Run Smoke Test**

  ```bash
  # Test pricing with sample data
  py -3 -m backend.cli.estimate_prices \
    backend/tests/fixtures/sample_input.csv \
    backend/tests/fixtures/sample_output_calibrated.csv
  ```

- [ ] **Compare Before/After**

  ```bash
  # Temporarily disable overrides to compare
  set LOTGENIUS_CALIBRATION_OVERRIDES=
  py -3 -m backend.cli.estimate_prices \
    backend/tests/fixtures/sample_input.csv \
    backend/tests/fixtures/sample_output_baseline.csv

  # Re-enable overrides
  set LOTGENIUS_CALIBRATION_OVERRIDES=backend/lotgenius/data/calibration_overrides.json
  ```

- [ ] **Validate Key Metrics**
  - Check that price estimates are reasonable
  - Verify condition factors are applied correctly
  - Ensure no extreme outliers or errors

### Phase 5: Documentation and Monitoring

- [ ] **Update Calibration Log**

  ```markdown
  ## YYYY-MM Calibration Cycle

  **Date**: YYYY-MM-DD
  **Analyst**: [Name]

  **Metrics Summary:**

  - Overall MAE: X.XXX
  - Overall Bias: X.XXX
  - Records Analyzed: X,XXX

  **Adjustments Applied:**

  - new: 1.00 -> 0.98 (2% reduction)
  - used_good: 0.85 -> 0.88 (3.5% increase)

  **Validation Results:**

  - Smoke test: PASS
  - Sample comparison: reasonable
  - No extreme outliers detected

  **Notes:**

  - [Any special observations or concerns]
  ```

- [ ] **Archive Data**

  ```bash
  # Create monthly archive directory
  mkdir backend/lotgenius/data/calibration/archive/YYYY-MM

  # Copy key files for archival
  cp backend/lotgenius/data/calibration_suggestions.json \
     backend/lotgenius/data/calibration/archive/YYYY-MM/
  cp backend/lotgenius/data/calibration_overrides.json \
     backend/lotgenius/data/calibration/archive/YYYY-MM/
  ```

- [ ] **Schedule Next Review**
  - Add calendar reminder for next month's cycle
  - Update any process improvements based on this cycle
  - Note any issues or areas for automation improvement

## Monitoring and Alerts

### Ongoing Monitoring

- [ ] **Weekly Spot Checks**

  ```bash
  # Check recent prediction accuracy
  tail -n 100 backend/lotgenius/logs/predictions.jsonl | \
    python -c "import json, sys; \
    preds = [json.loads(line) for line in sys.stdin]; \
    print(f'Recent predictions: {len(preds)}')"
  ```

- [ ] **Monthly Trend Review**
  ```bash
  # Review calibration history trends
  ls -la backend/lotgenius/data/calibration/history/metrics_*.json
  ```

### Alert Conditions

**Immediate Action Required:**

- MAE increases >50% month-over-month
- Absolute bias exceeds 0.10
- Any condition factor suggestions outside [0.3, 1.5] range

**Investigation Needed:**

- RMSE increases >25% month-over-month
- New extreme outliers in condition-specific metrics
- Significant changes in prediction volume

## Troubleshooting

### Common Issues

**Issue**: No matching records between predictions and outcomes

```bash
# Check data alignment
python -c "
import pandas as pd
import json
preds = [json.loads(line) for line in open('predictions.jsonl')]
outcomes = pd.read_csv('outcomes.csv')
print('Predictions SKUs:', len(set(p['sku_local'] for p in preds)))
print('Outcomes SKUs:', len(set(outcomes['sku_local'])))
print('Intersection:', len(set(p['sku_local'] for p in preds) & set(outcomes['sku_local'])))
"
```

**Issue**: Extreme adjustment suggestions

- Review raw bias metrics for the specific condition
- Check for data quality issues in outcomes
- Consider if market conditions changed significantly
- Apply more conservative bounds if needed

**Issue**: Override file not loading

```bash
# Verify environment variable
echo $LOTGENIUS_CALIBRATION_OVERRIDES

# Check file permissions and format
cat $LOTGENIUS_CALIBRATION_OVERRIDES
python -c "import json; print(json.load(open('$LOTGENIUS_CALIBRATION_OVERRIDES')))"
```

## Emergency Procedures

### Rollback Overrides

```bash
# Disable overrides immediately
set LOTGENIUS_CALIBRATION_OVERRIDES=

# Or restore previous version
cp backend/lotgenius/data/calibration/archive/YYYY-MM-prev/calibration_overrides.json \
   backend/lotgenius/data/calibration_overrides.json
```

### Data Recovery

```bash
# Restore from history if canonical files corrupted
cp backend/lotgenius/data/calibration/history/suggestions_YYYYMMDD_HHMMSS.json \
   backend/lotgenius/data/calibration_suggestions.json
```

## Success Criteria

**Completed Cycle:**

- [ ] All phases completed without errors
- [ ] Adjustments applied are reasonable and bounded
- [ ] Smoke tests pass with overrides enabled
- [ ] Documentation updated
- [ ] Next cycle scheduled

**Model Performance:**

- Overall MAE trending downward or stable
- Bias within acceptable range (-0.05 to +0.05)
- No significant performance regressions
- Condition-specific adjustments improving targeted areas

---

**Last Updated**: 2025-01-22
**Version**: 1.0
**Next Review**: First week of next month
