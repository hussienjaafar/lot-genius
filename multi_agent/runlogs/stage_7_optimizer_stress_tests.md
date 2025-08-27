# Stage 7: Optimizer stress tests and scenario sweeps

## Summary

Successfully implemented a CLI tool for running optimizer stress tests across multiple scenarios, enabling analysis of how the bid optimizer responds to adverse conditions like price drops, increased returns, higher shipping costs, and reduced sell-through rates. The tool generates concise CSV/JSON summaries suitable for reports and review.

## Key Changes

### 1. New CLI Tool (`backend/cli/stress_scenarios.py`)

- **Purpose**: Orchestrate optimizer stress testing across multiple scenarios
- **Key Features**:
  - Click-based CLI with configurable parameters
  - Built-in scenario registry with 5 default stress scenarios
  - CSV and optional JSON output formats
  - Environment-driven defaults from `roi.DEFAULTS`
  - Immutable data transformations (copy-based)

### 2. Scenario Transformations Implemented

- **baseline**: No changes (control scenario)
- **price_down_15**: Reduces `est_price_mu`, `est_price_sigma`, and price percentiles by 15%
- **returns_up_30**: Increases `return_rate` by 30%, capped at 1.0
- **shipping_up_20**: Increases `shipping_per_order` by 20%
- **sell_p60_down_10**: Reduces `sell_p60` by 10%, clipped to [0,1]

### 3. Test Suite (`backend/tests/test_cli_stress_scenarios.py`)

- **Coverage**: 5 test cases covering CLI functionality, output formats, and scenario transformations
- **Validation**: Confirms scenario differentiation and proper CSV/JSON output structure
- **Performance**: Uses reduced simulation counts for fast test execution

### 4. Sample Data (`backend/tests/fixtures/estimated_sample.csv`)

- **Purpose**: Test data with required fields for optimizer (est_price_mu, est_price_sigma, sell_p60, etc.)
- **Content**: 3 sample items with realistic pricing and sell-through estimates

## Technical Implementation

### CLI Interface

```bash
python -m backend.cli.stress_scenarios INPUT_CSV --out-csv OUTPUT.csv [OPTIONS]
```

**Key Options:**

- `--out-json`: Optional JSON output
- `--scenarios`: Comma-separated scenario names or "default"
- `--roi-target`, `--risk-threshold`: Override env-driven defaults
- `--lo`, `--hi`, `--tol`, `--sims`: Optimizer search parameters

### Output Format

**CSV Columns:**

- `scenario`: Scenario name
- `recommended_bid`: Optimal bid from optimizer
- `roi_p50`: Median ROI
- `prob_roi_ge_target`: Probability of meeting ROI target
- `expected_cash_60d`: Expected 60-day cash flow
- `meets_constraints`: Whether solution meets risk constraints
- `roi_p5`, `roi_p95`, `cash_60d_p5`: Additional risk metrics

### Data Transformation Logic

Each scenario applies specific transformations to a copy of the input DataFrame:

```python
def apply_scenario_price_down_15(df: pd.DataFrame) -> pd.DataFrame:
    df_copy = df.copy()
    # Multiply price fields by 0.85, clip at 0
    for field in ['est_price_mu', 'est_price_sigma']:
        if field in df_copy.columns:
            df_copy[field] = np.maximum(0, df_copy[field] * 0.85)
    return df_copy
```

## Testing Results

### Test Coverage: ✅ 5/5 tests passing

```bash
pytest -q backend/tests/test_cli_stress_scenarios.py
```

### Acceptance Criteria Validation

```bash
# Command specified in acceptance criteria:
python -m backend.cli.stress_scenarios backend/tests/fixtures/estimated_sample.csv --out-csv out/stress.csv
```

**Sample Output:**
| scenario | recommended_bid | prob_roi_ge_target | meets_constraints |
|----------|----------------|-------------------|------------------|
| baseline | 117.31 | 0.800 | True |
| price_down_15 | 97.80 | 0.830 | True |
| sell_p60_down_10 | 107.56 | 0.850 | True |

### Scenario Differentiation Validation

- ✅ **price_down_15**: Lower recommended bid (97.80 vs 117.31)
- ✅ **sell_p60_down_10**: Different bid and probability metrics
- ✅ **JSON output**: Identical data in structured format

## Files Changed

1. **`backend/cli/stress_scenarios.py`** (NEW)
   - Complete CLI implementation with Click
   - 5 scenario transformation functions
   - CSV/JSON output logic with directory creation

2. **`backend/tests/test_cli_stress_scenarios.py`** (NEW)
   - Comprehensive test suite (5 test functions)
   - CLI integration testing with CliRunner
   - Scenario transformation unit tests

3. **`backend/tests/fixtures/estimated_sample.csv`** (NEW)
   - Sample data with optimizer-required fields
   - 3 items with realistic pricing estimates

## Regression Testing

### Core Functionality: ✅ All tests passing

```bash
pytest backend/tests/test_roi_defaults.py backend/tests/test_evidence_gate.py -v
# 7 passed, 2 warnings
```

### No Breaking Changes

- Optimizer logic in `roi.py` unchanged (as required)
- Uses existing `roi.DEFAULTS` for environment-driven configuration
- Maintains compatibility with existing CLI patterns

## Implementation Notes

### Design Decisions

1. **Immutable Transformations**: Always work on `df.copy()` to prevent data mutation
2. **Parameter Override Logic**: Scenario-transformed DataFrame values take precedence over CLI defaults
3. **Robust Output**: Automatic directory creation with `mkdir(parents=True, exist_ok=True)`
4. **Validation**: Input validation for scenario names with helpful error messages

### Performance Optimizations

- Test suite uses reduced simulation counts (50-200 vs default 2000)
- Scenario transformations are lightweight (no network calls, no heavy computation)
- Efficient pandas operations with vectorized transformations

### Edge Case Handling

- Clips probabilities to [0,1] range (sell_p60 scenarios)
- Prevents negative prices (price_down scenarios)
- Handles missing columns gracefully
- Manages rate multiplications with caps (returns scenarios)

## Follow-ups/TODOs: None

All acceptance criteria met. Implementation is complete and tested.

## Risks/Assumptions

### Assumptions

1. Input CSV contains required optimizer fields (`est_price_mu`, `est_price_sigma`, `sell_p60`)
2. Scenario parameter changes (15% price drop, 30% returns increase) represent realistic stress conditions
3. Current optimizer constraints and thresholds provide sufficient sensitivity to detect scenario impacts

### Low Risk Items

- Scenario transformations are simple mathematical operations
- Uses existing, well-tested optimizer infrastructure
- CLI follows established patterns from existing tools
- Comprehensive test coverage with multiple validation layers

## Status: ✅ COMPLETE

All tasks completed successfully:

- ✅ CLI implementation with all required features
- ✅ 5 scenario transformations with proper data handling
- ✅ CSV/JSON output functionality
- ✅ Comprehensive test suite (5/5 passing)
- ✅ Acceptance criteria validation
- ✅ Regression testing (no breaking changes)
- ✅ Documentation and reporting

**Command Ready for Use:**

```bash
python -m backend.cli.stress_scenarios INPUT.csv --out-csv OUTPUT.csv --out-json OUTPUT.json
```
