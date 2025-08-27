# Stage 5: Feedback Loop + Calibration Scaffold

**Goal:** Add lightweight calibration scaffold and feedback loop to log model predictions, ingest realized outcomes, compute calibration/accuracy metrics, generate adjustment suggestions, and provide a clean seam for later automation.

## Implementation Summary

### Core Components Created

#### 1. Calibration Module (`backend/lotgenius/calibration.py`)

- **log_predictions()**: Logs model predictions to JSONL format with timestamp, context, and prediction values
- **load_predictions()**: Loads and validates prediction logs from JSONL files
- **load_outcomes()**: Loads realized outcomes from CSV with required columns (sku_local, realized_price, sold_within_horizon, days_to_sale)
- **join_predictions_outcomes()**: Inner joins predictions and outcomes on sku_local
- **compute_metrics()**: Calculates price accuracy (MAE, MAPE, RMSE) and probability calibration (Brier score, calibration bins)
- **suggest_adjustments()**: Generates bounded adjustment suggestions for condition price factors (0.3-1.5 range)
- **write_suggestions()**: Outputs adjustment suggestions to JSON file

#### 2. API Integration (`backend/lotgenius/api/service.py`)

- Added **\_validate_calibration_path()** for secure path validation (prevents directory traversal)
- Modified **run_optimize()** to include calibration logging when `calibration_log_path` is provided
- Modified **run_pipeline()** to include calibration logging capability
- Maintains backward compatibility - calibration logging is optional

#### 3. CLI Helper (`backend/cli/calibration_report.py`)

- Command-line tool for generating calibration reports
- Supports both console and markdown output formats
- Usage: `python -m cli.calibration_report predictions.jsonl outcomes.csv --output report.md`

#### 4. Example Data (`backend/lotgenius/data/calibration_example_outcomes.csv`)

- Sample outcomes CSV demonstrating expected format
- Includes realistic data for testing and documentation

#### 5. Test Suite

- **`backend/tests/test_calibration_scaffold.py`**: Comprehensive tests for calibration module
- **`backend/tests/test_api_optimize_calibration_log.py`**: Tests API integration with calibration logging

## Technical Implementation Details

### Security Considerations

- Path validation prevents directory traversal attacks
- Calibration log paths are validated to ensure they stay within safe boundaries
- Bounded adjustment suggestions prevent extreme parameter changes

### Data Flow

1. **Prediction Logging**: During optimization, predictions are logged to JSONL with context
2. **Outcome Ingestion**: Realized outcomes loaded from CSV format
3. **Data Joining**: Predictions and outcomes matched on sku_local identifier
4. **Metrics Computation**: Accuracy and calibration metrics calculated
5. **Adjustment Generation**: Data-driven suggestions for model parameter tuning

### File Formats

- **Predictions**: JSONL format for append-friendly logging
- **Outcomes**: CSV format with columns: sku_local, realized_price, sold_within_horizon, days_to_sale
- **Suggestions**: JSON format for structured adjustment recommendations

### Integration Points

- Seamlessly integrates with existing optimizer without changing core pricing/sell logic
- Optional calibration logging activated via `calibration_log_path` parameter
- Maintains all existing API contracts and backward compatibility

## Files Created/Modified

### Created Files

1. `backend/lotgenius/calibration.py` - Core calibration module (281 lines)
2. `backend/lotgenius/data/calibration_example_outcomes.csv` - Example outcomes data
3. `backend/cli/calibration_report.py` - CLI reporting tool (127 lines)
4. `backend/tests/test_calibration_scaffold.py` - Calibration tests (259 lines)
5. `backend/tests/test_api_optimize_calibration_log.py` - API integration tests (124 lines)

### Modified Files

1. `backend/lotgenius/api/service.py` - Added calibration integration and path validation

## Quality Assurance

### Testing Coverage

- Unit tests for all calibration functions
- Integration tests for API calibration logging
- Edge case testing (empty data, malformed inputs, security attacks)
- Path validation security testing

### Error Handling

- Comprehensive input validation
- Graceful handling of missing data
- Clear error messages for debugging
- Security-focused path validation

## Future Enhancement Points

### Automation Ready

- Clean interface for automated calibration runs
- Structured suggestion format for programmatic consumption
- Event-based triggers ready for implementation

### Monitoring Integration

- Structured logging format compatible with monitoring systems
- Metrics suitable for dashboard visualization
- Alert-ready calibration drift detection

### Scalability Considerations

- JSONL format supports large-scale logging
- Efficient data processing with pandas
- Memory-efficient streaming capabilities

## Verification Status

### Implementation Complete ✓

- [x] Core calibration module
- [x] API integration
- [x] CLI helper tool
- [x] Test coverage
- [x] Documentation
- [x] Security validation

### Ready for Testing

- All components implemented and tested
- Integration points verified
- Security measures in place
- Backward compatibility maintained

---

**Implementation Date:** 2025-08-23
**Environment:** Windows, Python 3.13, pytest
**Constraints Met:** Surgical changes, existing layout respected, no lotgenius/pricing package reintroduction
