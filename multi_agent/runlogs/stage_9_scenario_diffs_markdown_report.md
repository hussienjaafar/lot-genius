# Stage 9: Add "Scenario Diffs" to the Markdown report

## Summary

Successfully integrated optimizer stress-scenario results into the Markdown report generation as an optional "Scenario Diffs" section. The implementation accepts stress CSV/JSON outputs from the stress_scenarios CLI and renders a concise comparison table showing baseline vs stressed metrics with calculated deltas for bid, probability, and cash recovery.

## Files Changed

### backend/lotgenius/cli/report_lot.py

**Extended report generation with stress scenario support:**

- Updated `_mk_markdown()` signature to accept `stress_csv` and `stress_json` parameters
- Added stress data parsing and validation logic supporting both CSV and JSON formats
- Built "Scenario Diffs" section with markdown table showing:
  - Scenario name | Bid | Δ Bid | Prob ≥ Target | Δ Prob | 60d Cash | Δ Cash
  - Baseline row (no deltas) plus stressed scenarios with positive/negative deltas
- Added CLI options `--stress-csv` and `--stress-json` with Click decorators
- Updated main function to accept and pass stress parameters
- Enhanced output summary to include stress artifact references

**Key implementation details:**

```python
# Parse stress scenario data if provided
stress_df = None
if stress_csv and Path(stress_csv).exists():
    try:
        stress_df = pd.read_csv(stress_csv)
    except Exception:
        pass
elif stress_json and Path(stress_json).exists():
    try:
        stress_data = json.loads(Path(stress_json).read_text(encoding="utf-8"))
        if isinstance(stress_data, list) and stress_data:
            stress_df = pd.DataFrame(stress_data)
    except Exception:
        pass

# Validate stress data has required columns
if stress_df is not None:
    required_cols = ["scenario", "bid", "prob_roi_ge_target", "expected_cash_60d"]
    if not all(col in stress_df.columns for col in required_cols):
        stress_df = None
```

**Delta formatting functions:**

```python
def fmt_delta_currency(x):
    if x is None or pd.isna(x):
        return "N/A"
    if x >= 0:
        return f"+{fmt_currency(x)}"
    else:
        return f"-{fmt_currency(abs(x))}"

def fmt_delta_pct(x):
    if x is None or pd.isna(x):
        return "N/A"
    if x >= 0:
        return f"+{fmt_pct(x)}"
    else:
        return f"-{fmt_pct(abs(x))}"
```

### backend/lotgenius/api/schemas.py

**Extended API schemas to support stress inputs:**

- Added `stress_csv: Optional[str] = None` to `ReportRequest`
- Added `stress_json: Optional[str] = None` to `ReportRequest`
- Added `stress_csv: Optional[str] = None` to `PipelineRequest`
- Added `stress_json: Optional[str] = None` to `PipelineRequest`

### backend/lotgenius/api/service.py

**Updated service functions to pass stress parameters:**

- Extended `generate_report()` to pass `req.stress_csv` and `req.stress_json` to `_mk_markdown()`
- Extended `report_stream()` to pass stress parameters in streaming generation
- Updated `run_pipeline()` signature to accept `stress_csv` and `stress_json` parameters
- Updated `run_pipeline()` call to `_mk_markdown()` with stress parameters

### backend/app/main.py

**Enhanced API endpoints to handle stress file uploads:**

- Added stress file extraction in both blocking and streaming pipeline upload endpoints:

  ```python
  stress_csv_path: Optional[str] = None
  stress_json_path: Optional[str] = None
  stress_csv_file = form.get("stress_csv")
  stress_json_file = form.get("stress_json")

  if stress_csv_file:
      stress_csv_path = str(save_upload_temp(stress_csv_file, suffix=".csv"))
  if stress_json_file:
      stress_json_path = str(save_upload_temp(stress_json_file, suffix=".json"))
  ```

- Updated `run_pipeline()` calls to include stress parameters
- Enhanced cleanup sections to remove stress temp files after processing

### backend/tests/test_cli_report_stress.py

**Created comprehensive test suite with 6 test cases:**

- `test_report_basic_no_stress` - Baseline report without stress data
- `test_report_with_stress_csv` - Report with stress CSV showing Scenario Diffs table
- `test_report_with_stress_json` - Report with stress JSON showing Scenario Diffs table
- `test_report_with_invalid_stress_csv` - Graceful handling of malformed stress data
- `test_report_with_missing_baseline_stress` - No table when baseline scenario missing
- `test_report_stress_csv_precedence` - CSV takes precedence over JSON when both provided

## Tests Run

### New Stress Report Tests

```bash
python -m pytest backend/tests/test_cli_report_stress.py -v
```

**Result: 6 passed**

- ✅ test_report_basic_no_stress
- ✅ test_report_with_stress_csv
- ✅ test_report_with_stress_json
- ✅ test_report_with_invalid_stress_csv
- ✅ test_report_with_missing_baseline_stress
- ✅ test_report_stress_csv_precedence

### Regression Tests

```bash
python -m pytest backend/tests/test_api_report.py -q
```

**Result: 10 passed, 1 warning**

```bash
python -m pytest backend/tests/test_cli_stress_scenarios.py -q
```

**Result: 5 passed, 1 warning**

## Key Implementation Features

### Stress Data Integration

- **Flexible Input**: Accepts both CSV and JSON stress scenario outputs
- **Robust Parsing**: Graceful error handling for malformed or missing files
- **Column Validation**: Requires `scenario`, `bid`, `prob_roi_ge_target`, `expected_cash_60d`
- **CSV Precedence**: When both CSV and JSON provided, CSV takes precedence

### Scenario Diffs Table

- **Baseline Reference**: Finds baseline scenario and shows deltas relative to it
- **Clear Formatting**: Uses proper currency and percentage formatting with signs
- **Delta Calculations**: Shows positive/negative changes with `+`/`-` prefixes
- **Table Structure**: Markdown table with scenario name, absolute values, and deltas

### API Integration

- **Multipart Support**: Handles stress file uploads in pipeline endpoints
- **Streaming Compatible**: Works with both blocking and SSE streaming endpoints
- **Cleanup**: Proper temp file cleanup for uploaded stress files
- **Schema Validation**: Pydantic schemas updated to include optional stress paths

### Error Handling

- **Graceful Degradation**: Missing or invalid stress data doesn't break reports
- **File Validation**: Checks file existence before attempting to parse
- **Missing Baseline**: No table rendered if baseline scenario not found
- **Exception Safety**: Try/catch blocks prevent stress parsing errors from failing reports

## Example Output

When stress data is provided, the report includes a new section:

```markdown
## Scenario Diffs

| Scenario          | Bid    | Δ Bid  | Prob ≥ Target | Δ Prob | 60d Cash | Δ Cash |
| ----------------- | ------ | ------ | ------------- | ------ | -------- | ------ |
| **baseline**      | $30.00 | -      | 85.0%         | -      | $35.00   | -      |
| **price_down_15** | $25.50 | -$4.50 | 72.0%         | -13.0% | $29.80   | -$5.20 |
| **returns_up_30** | $28.00 | -$2.00 | 78.0%         | -7.0%  | $32.10   | -$2.90 |
```

## CLI Usage Examples

### Basic Report (No Stress)

```bash
python -m lotgenius.cli.report_lot \
  --items-csv data/items.csv \
  --opt-json data/optimizer.json \
  --out-markdown report.md
```

### Report with Stress CSV

```bash
python -m lotgenius.cli.report_lot \
  --items-csv data/items.csv \
  --opt-json data/optimizer.json \
  --out-markdown report.md \
  --stress-csv data/stress_scenarios.csv
```

### Report with Stress JSON

```bash
python -m lotgenius.cli.report_lot \
  --items-csv data/items.csv \
  --opt-json data/optimizer.json \
  --out-markdown report.md \
  --stress-json data/stress_scenarios.json
```

## API Usage Examples

### Report Request with Stress

```json
{
  "items_csv": "/path/to/items.csv",
  "opt_json_path": "/path/to/optimizer.json",
  "stress_csv": "/path/to/stress_scenarios.csv",
  "out_markdown": "/path/to/report.md"
}
```

### Pipeline Upload with Stress Files

```bash
curl -X POST http://localhost:8000/v1/pipeline/upload \
  -H "X-API-Key: your-key" \
  -F "items_csv=@items.csv" \
  -F "opt_json=@optimizer.json" \
  -F "stress_csv=@stress_scenarios.csv"
```

## Acceptance Criteria Met

✅ **CLI Integration**: Added `--stress-csv` and `--stress-json` options to report_lot CLI

✅ **Scenario Diffs Section**: Optional markdown section appears when stress data provided

✅ **Baseline Comparison**: Table shows baseline scenario with deltas for stressed scenarios

✅ **Delta Formatting**: Proper `+`/`-` prefixes for currency and percentage changes

✅ **API Support**: Extended ReportRequest and PipelineRequest schemas with stress paths

✅ **Error Handling**: Graceful degradation when stress data missing or malformed

✅ **File Validation**: Required columns validated before rendering table

✅ **Test Coverage**: Comprehensive test suite covering all scenarios and edge cases

✅ **Documentation**: Clear examples and usage patterns provided

## Follow-ups/TODOs

None - all requirements implemented and tested successfully.

## Risks/Assumptions

### Assumptions

- Stress scenario data follows the format output by `stress_scenarios.py` CLI
- Baseline scenario is always named "baseline" in stress data
- Required columns are: scenario, bid, prob_roi_ge_target, expected_cash_60d
- Users want to see absolute values alongside deltas in the comparison table

### Mitigations

- Robust error handling prevents malformed stress data from breaking reports
- Column validation ensures required data is present before rendering table
- CSV precedence over JSON provides clear priority when both are provided
- Graceful degradation means reports work fine without stress data

## Status: ✅ COMPLETE

All Stage 9 requirements have been successfully implemented:

- CLI stress data integration with new command-line options
- Scenario Diffs markdown table with baseline comparisons and deltas
- API schema extensions and service layer updates
- Comprehensive test coverage with 6 test cases
- Proper error handling and graceful degradation
- Full backward compatibility with existing report functionality

The feature is now ready for production use and integrates seamlessly with the existing stress_scenarios CLI from Stage 7.
