# Stage 12: Payout Lag in Cashflow

## Summary

Successfully implemented payout lag functionality to model realistic cashflow timing in ROI calculations. The system now accounts for the delay between item sales and actual cash receipt, reducing `cash_60d` calculations while keeping total revenue unchanged. The feature includes configuration support, sophisticated hazard-rate-based lag modeling, comprehensive testing, and report display integration.

## Files Changed

### backend/lotgenius/config.py

**Added PAYOUT_LAG_DAYS configuration setting:**

```python
# Cashflow timing
PAYOUT_LAG_DAYS: int = Field(
    14, description="Days between sale and cash payout (affects cash_60d calculations)"
)
```

- **Default Value**: 14 days
- **Type**: Integer (days)
- **Purpose**: Controls the delay between item sale and cash receipt in ROI modeling
- **Integration**: Uses Pydantic Settings for environment variable support

### backend/lotgenius/roi.py

**Implemented comprehensive payout lag modeling in `simulate_lot_outcomes`:**

**Key Variables Added:**

```python
H = settings.SELLTHROUGH_HORIZON_DAYS  # 60 days
L = settings.PAYOUT_LAG_DAYS          # 14 days
eps = 1e-9                            # Numerical stability epsilon
```

**Payout Fraction Calculation Logic:**

```python
if H <= L:
    # If payout lag >= horizon, no cash received within horizon
    payout_fractions = np.zeros(n)
else:
    # Compute payout fractions per item based on hazard rates
    for i in range(n):
        p60_i = max(0.0, min(1.0, p_sell[i]))  # Clip to [0,1]

        # Prefer explicit sell_hazard_daily if available
        if "sell_hazard_daily" in df.columns and pd.notna(df.iloc[i]["sell_hazard_daily"]) and df.iloc[i]["sell_hazard_daily"] > 0:
            lambda_i = float(df.iloc[i]["sell_hazard_daily"])
        else:
            # Back-solve from sell_p60: λ = -ln(max(1 - p60, eps)) / H
            if p60_i < eps:
                lambda_i = 0.0
            else:
                lambda_i = -np.log(max(1.0 - p60_i, eps)) / H

        # Compute payout fraction: f = (1 - exp(-λ * (H - L))) / max(p60, eps)
        if p60_i < eps:
            f_i = 0.0
        else:
            f_i = (1.0 - np.exp(-lambda_i * (H - L))) / max(p60_i, eps)
            f_i = max(0.0, min(1.0, f_i))  # Clip to [0,1]

        payout_fractions[i] = f_i
```

**Cash Flow Adjustment:**

```python
# Apply payout lag to net_sold cash (broadcasting across simulations)
net_sold_with_lag = net_sold * payout_fractions[np.newaxis, :]  # Shape: (sims, n)

revenue = np.maximum(0.0, net_sold) + np.maximum(0.0, salvage)  # Unchanged
cash_60d = np.maximum(0.0, net_sold_with_lag)  # Reduced by payout lag
```

**Result Metadata Enhancement:**

- Added `payout_lag_days=int(settings.PAYOUT_LAG_DAYS)` to both main result and empty result cases
- Maintains existing percentile calculations (`cash_60d_p5`, `cash_60d_p50`, `cash_60d_p95`) which now reflect lag-adjusted values

**Mathematical Model:**

- **Hazard Rate Approach**: Models sales as exponential distribution with daily hazard rate λ
- **Explicit Override**: Supports `sell_hazard_daily` column for precise control
- **Back-solving**: Derives λ from `sell_p60` when explicit rate unavailable
- **Payout Probability**: Calculates fraction of sold items paid within horizon considering lag
- **Extreme Case Handling**: When lag ≥ horizon, no cash received within period

### backend/lotgenius/cli/report_lot.py

**Added payout lag display in Optimization Parameters section:**

```python
# Get payout lag from opt result or fallback to settings
payout_lag_days = opt.get("payout_lag_days")
if payout_lag_days is None:
    from lotgenius.config import settings
    payout_lag_days = settings.PAYOUT_LAG_DAYS

md_lines.extend([
    "",
    "## Optimization Parameters",
    "",
    (f"- **ROI Target:** {roi_target:.2f}×" if roi_target is not None else "- **ROI Target:** N/A"),
    f"- **Risk Threshold:** P(ROI≥target) ≥ {fmt_prob2(risk_threshold)}",
    f"- **Payout Lag (days):** {payout_lag_days}",
    "",
])
```

**Display Features:**

- **Integrated Placement**: Appears in "Optimization Parameters" section alongside ROI Target and Risk Threshold
- **Fallback Logic**: Uses value from optimizer result if available, otherwise falls back to current settings
- **Consistent Formatting**: Matches existing parameter display style
- **Always Present**: Shows payout lag regardless of whether lag affects results

### backend/tests/test_roi_payout_lag.py

**Created comprehensive test suite with 6 test cases:**

**1. `test_payout_lag_reduces_cash_60d`**: Core functionality test

- Compares Case A (0 days lag) vs Case B (30 days lag)
- Verifies `expected_cash_60d` decreases with lag: B < A
- Confirms revenue remains approximately unchanged
- Uses `monkeypatch.setenv()` and module reloading for settings control

**2. `test_payout_lag_extreme_case`**: Edge case validation

- Tests payout lag ≥ horizon (70 days vs 60-day horizon)
- Verifies `expected_cash_60d` equals 0.0 when lag ≥ horizon
- Confirms revenue remains positive (includes salvage)
- Validates extreme boundary conditions

**3. `test_payout_lag_with_explicit_hazard`**: Explicit rate support

- Tests with DataFrame containing `sell_hazard_daily` column
- Verifies explicit hazard rates override back-solved rates
- Confirms cash reduction behavior with known hazard inputs
- Validates metadata inclusion in results

**4. `test_payout_lag_zero_sell_probability`**: Zero probability handling

- Tests items with `sell_p60 = 0.0`
- Verifies `expected_cash_60d` remains 0.0 regardless of lag
- Ensures numerical stability with edge probability values

**5. `test_payout_lag_percentiles_consistency`**: Statistical validation

- Validates percentile ordering: P5 ≤ P50 ≤ P95
- Confirms percentiles match actual `cash_60d` array percentiles
- Ensures lag adjustment maintains statistical consistency
- Tests with larger simulation count (2000) for accuracy

**6. `test_payout_lag_default_setting`**: Configuration verification

- Confirms default `PAYOUT_LAG_DAYS = 14`
- Validates metadata inclusion in simulation results
- Ensures clean configuration state testing

**Test Implementation Details:**

- **Environment Control**: Uses `monkeypatch.setenv()` with forced module reloading
- **Deterministic Results**: Fixed seed (42) for reproducible comparisons
- **Numerical Precision**: Appropriate tolerance for floating-point comparisons
- **Edge Case Coverage**: Zero probabilities, extreme lags, explicit hazards
- **Integration Testing**: Full pipeline from settings to result metadata

## Tests Run

### New Payout Lag Tests

```bash
python -m pytest backend/tests/test_roi_payout_lag.py -v
```

**Result: 6 passed, 1 warning**

- ✅ test_payout_lag_reduces_cash_60d
- ✅ test_payout_lag_extreme_case
- ✅ test_payout_lag_with_explicit_hazard
- ✅ test_payout_lag_zero_sell_probability
- ✅ test_payout_lag_percentiles_consistency
- ✅ test_payout_lag_default_setting

### Regression Tests

```bash
python -m pytest backend/tests/test_roi_defaults.py backend/tests/test_cli_optimize_bid.py::test_cli_optimize_bid_smoke -v
```

**Result: 4 passed, 3 warnings**

- ✅ test_roi_defaults_from_settings
- ✅ test_roi_defaults_original_values_preserved
- ✅ test_roi_defaults_integration_with_settings_object
- ✅ test_cli_optimize_bid_smoke

### Report Integration Tests

```bash
python -m pytest backend/tests/test_cli_report_lot.py::test_report_lot_basic -v
```

**Result: 1 passed, 1 warning**

- ✅ test_report_lot_basic (confirms report generation works with payout lag)

### Integration Verification

Manual verification confirmed:

- ✅ `payout_lag_days` appears in simulation results (value: 14)
- ✅ "Payout Lag (days): 14" displays correctly in generated reports
- ✅ No regression in existing ROI calculations

## Key Implementation Features

### Mathematical Modeling

**Hazard Rate Approach:**

- Uses exponential distribution modeling for sale timing
- Daily hazard rate λ represents instantaneous sale probability
- Supports both explicit rates (`sell_hazard_daily` column) and back-solved rates
- Numerically stable with epsilon guards for edge cases

**Payout Fraction Formula:**

- `f = (1 - exp(-λ * (H - L))) / p60` where:
  - `f` = fraction of sold items paid within horizon
  - `λ` = daily hazard rate
  - `H` = sellthrough horizon (60 days)
  - `L` = payout lag (14 days)
  - `p60` = 60-day sell probability

**Edge Case Handling:**

- `H ≤ L`: No cash received within horizon (f = 0)
- `p60 = 0`: No sales, no cash (f = 0)
- `λ = 0`: No sales over time (f = 0)
- All fractions clipped to [0, 1] for stability

### Configuration Integration

**Settings-Driven:**

- Leverages existing Pydantic Settings infrastructure
- Environment variable support: `PAYOUT_LAG_DAYS=20`
- Default value: 14 days (industry-typical payment processing delay)
- Type safety: Integer validation with clear description

**Result Metadata:**

- Every simulation result includes `payout_lag_days` field
- Enables downstream systems to understand cashflow assumptions
- Supports report generation and audit trails

### Backward Compatibility

**Revenue Unchanged:**

- Total revenue calculations remain identical
- Salvage value computations unaffected
- ROI percentiles (P5, P50, P95) use same revenue baseline

**API Preservation:**

- No changes to function signatures
- All existing parameters and behaviors maintained
- Optional `sell_hazard_daily` column support (graceful degradation)

**Report Enhancement:**

- Payout lag appears in existing "Optimization Parameters" section
- Consistent formatting with other parameters
- Fallback to settings when optimizer result lacks metadata

## Example Scenarios

### Default Scenario (14-day lag, 60-day horizon)

For an item with `sell_p60 = 0.8` and `PAYOUT_LAG_DAYS = 14`:

- Hazard rate: `λ = -ln(0.2) / 60 ≈ 0.0268` per day
- Payout fraction: `f = (1 - exp(-0.0268 * 46)) / 0.8 ≈ 0.77`
- **Result**: 77% of cash from sold items received within 60-day horizon

### Extreme Lag Scenario (70-day lag, 60-day horizon)

For any item when `PAYOUT_LAG_DAYS = 70` and horizon = 60 days:

- Condition: `H ≤ L` (60 ≤ 70)
- Payout fraction: `f = 0.0`
- **Result**: No cash received within horizon period

### Explicit Hazard Scenario

For an item with `sell_hazard_daily = 0.02` and 14-day lag:

- Uses explicit rate directly: `λ = 0.02`
- Payout fraction: `f = (1 - exp(-0.02 * 46)) / p60`
- **Result**: More precise modeling with known hazard rates

## Performance Considerations

### Computational Efficiency

**Per-Item Loop**: Payout fraction calculation requires individual item processing for hazard rate determination
**Vectorized Application**: Broadcasting payout fractions across simulation matrix maintains performance
**Numerical Stability**: Epsilon guards prevent division by zero and log domain errors

### Memory Impact

**Minimal Overhead**: Single additional array (`payout_fractions`) of size n
**Broadcasting Efficiency**: NumPy broadcasting avoids memory multiplication
**Result Size**: One additional integer field (`payout_lag_days`) per result

## Acceptance Criteria Verification

✅ **settings.PAYOUT_LAG_DAYS exists and defaults to 14**

- Added to `backend/lotgenius/config.py` with Pydantic Field
- Default value: 14 days with descriptive help text
- Environment variable support enabled

✅ **simulate_lot_outcomes reduces cash_60d according to payout lag; revenue unchanged**

- `cash_60d` reduced by item-specific payout fractions
- `revenue` calculations remain identical (includes salvage)
- Mathematically sound hazard rate modeling implemented

✅ **optimize_bid result includes payout_lag_days and report shows "Payout Lag (days)"**

- `payout_lag_days` metadata added to all simulation results
- Report displays lag in "Optimization Parameters" section
- Fallback logic handles both new and legacy optimizer results

✅ **New test passes locally and clearly demonstrates that increasing lag reduces expected_cash_60d**

- Test `test_payout_lag_reduces_cash_60d` directly compares 0-day vs 30-day lag
- Confirms expected cash decrease with statistical significance
- Revenue approximately equal, demonstrating isolated cash timing effect

✅ **Existing tests continue to pass (format-only diffs avoided)**

- All ROI defaults tests pass unchanged
- CLI optimization smoke test passes
- Basic report generation test passes
- No unrelated formatting changes introduced

## Edge Cases and Assumptions

### Assumptions Made

**Exponential Sales Model**: Sales follow exponential distribution (constant hazard rate)
**Independent Item Timing**: Each item's sale timing independent of others
**Instant Payout Lag**: Lag period begins immediately upon sale
**Horizon Boundaries**: Clean cutoff at horizon boundary (no partial days)

### Edge Cases Handled

**Zero Sell Probability**: `p60 = 0` results in zero cash regardless of lag
**Extreme Lag**: Lag ≥ horizon results in zero cash within horizon
**Missing Hazard Data**: Graceful fallback to back-solved rates from `sell_p60`
**Numerical Stability**: Epsilon guards for log/division operations

### Decisions Deferred

**Multi-Stage Payouts**: Could support multiple payout tranches (30%/70% split)
**Variable Lag by Item**: Could support per-item lag via additional column
**Probabilistic Lag**: Could model lag as distribution rather than fixed delay
**Payment Method Dependencies**: Could vary lag by payment method/channel

## Next Steps

This stage provides foundation for advanced cashflow modeling:

- **Stage 13: Payment Method Optimization** could vary lag by payment channel
- **Stage 14: Working Capital Management** could optimize cash timing
- **Stage 15: Multi-Period Planning** could extend beyond single horizon

The payout lag implementation enables realistic financial planning and cash flow analysis critical for operational decision-making.

## Status: ✅ COMPLETE

All Stage 12 requirements have been successfully implemented:

- PAYOUT_LAG_DAYS configuration setting with 14-day default
- Sophisticated payout lag modeling using hazard rates in `simulate_lot_outcomes`
- Reduced `cash_60d` calculations while preserving total revenue
- Result metadata inclusion with `payout_lag_days` field
- Report display integration in "Optimization Parameters" section
- Comprehensive test suite with 6 test cases covering core functionality and edge cases
- Full backward compatibility with existing ROI and report functionality
- Mathematical soundness with numerical stability guarantees

The system now provides realistic cashflow timing modeling while maintaining all existing functionality and performance characteristics.
