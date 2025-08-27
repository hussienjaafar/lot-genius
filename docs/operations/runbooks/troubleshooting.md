# Troubleshooting Guide

Common issues and solutions for Lot Genius development and operations.

## Environment & Setup Issues

### Python Environment Problems

#### ModuleNotFoundError: No module named 'lotgenius'

**Symptoms**:

```
ImportError: No module named 'lotgenius'
ModuleNotFoundError: No module named 'lotgenius.roi'
```

**Solutions**:

```cmd
# 1. Verify virtual environment is activated
.venv\Scripts\activate

# 2. Install backend package in editable mode
pip install -e backend

# 3. Verify installation
python -c "import lotgenius; print('OK')"

# 4. Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

#### Virtual Environment Issues

**Symptoms**:

- Command not found errors
- Wrong Python version
- Package conflicts

**Solutions**:

```cmd
# Recreate virtual environment
rmdir /s .venv
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e backend

# Verify environment
where python
python --version
```

### API Key Configuration

#### KEEPA_API_KEY not set

**Error**: `ValueError: KEEPA_API_KEY environment variable not set`

**Solutions**:

```cmd
# 1. Check current value
echo %KEEPA_API_KEY%

# 2. Set temporarily
set KEEPA_API_KEY=your_key_here

# 3. Add to .env file for persistence
echo KEEPA_API_KEY=your_key_here >> .env

# 4. Verify .env loading
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Key loaded:', bool(os.getenv('KEEPA_API_KEY')))
"
```

#### API Key Validation Issues

**Error**: `Invalid API key` or `403 Forbidden`

**Diagnostics**:

```cmd
# Test API key directly
curl "https://api.keepa.com/product?key=YOUR_KEY&domain=1&asin=B08N5WRWNW"

# Check credits remaining
curl "https://api.keepa.com/token?key=YOUR_KEY"
```

**Solutions**:

- Verify key is correct (no extra spaces/characters)
- Check credit balance on Keepa dashboard
- Ensure key has proper permissions
- Contact Keepa support if key appears valid

## File & Path Issues

### Windows Path Problems

#### FileNotFoundError with backslashes

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'data\file.csv'`

**Solutions**:

```cmd
# Use forward slashes (preferred)
python -m backend.cli.command "data/file.csv"

# Use double backslashes
python -m backend.cli.command "data\\file.csv"

# Use raw strings in Python
python -c "print(r'C:\Users\path\file.csv')"

# Use Path objects
python -c "from pathlib import Path; print(Path('data') / 'file.csv')"
```

#### Path Safety Validation Errors

**Error**: `Path safety validation failed: C:\Windows\System32`

**Explanation**: Lot Genius blocks access to system directories for security.

**Solutions**:

```cmd
# Use allowed paths
# OK Repo directory: data/file.csv
# OK Temp directory: C:\Users\user\AppData\Local\Temp\file.csv

# For testing, use temp directory
set TMPDIR=%TEMP%
python -c "
import tempfile, json
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
test_file = tmp / 'test.json'
test_file.write_text(json.dumps({'test': True}))
print('Test file:', test_file)
"
```

### File Permission Issues

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solutions**:

```cmd
# Check file permissions
icacls data\file.csv

# Ensure directory is writable
icacls data /grant %USERNAME%:(F)

# For logs directory
mkdir logs
icacls logs /grant %USERNAME%:(F)

# Run as administrator if needed (last resort)
```

## Manifest Processing Issues

### Header Mapping Problems

#### Low Header Coverage

**Error**: `Header coverage below threshold (45% < 70%)`

**Diagnosis**:

```cmd
# Check header mapping details
python -m backend.cli.map_preview manifest.csv --show-candidates --top-k 5

# View unmapped headers
python -m backend.cli.validate_manifest manifest.csv --show-coverage
```

**Solutions**:

```cmd
# Add manual aliases for non-standard headers
python -m backend.cli.map_preview manifest.csv --save-alias "Item Desc" title
python -m backend.cli.map_preview manifest.csv --save-alias "Cond." condition

# Request better manifest format from seller
# Lower threshold temporarily (not recommended)
python -m backend.cli.validate_manifest manifest.csv --min-coverage 0.50
```

#### Duplicate Header Mappings

**Error**: `Multiple headers map to the same field: 'title'`

**Diagnosis**:

```cmd
# Show duplicate mappings
python -m backend.cli.map_preview manifest.csv --fail-on-duplicates
```

**Solutions**:

- Remove duplicate columns from source CSV
- Rename conflicting headers
- Update header mapping rules

### CSV Parsing Issues

#### Quote/Comma Issues

**Error**: `Invalid CSV format` or incorrect column counts

**Symptoms**:

- Columns split incorrectly
- Missing data in parsed results
- Unexpected number of columns

**Solutions**:

```cmd
# Check for embedded commas in text fields
grep -n "," manifest.csv | head -5

# Use alternative delimiter if possible
# Convert CSV to use semicolons or tabs

# For complex CSVs, use robust parser
python -c "
import pandas as pd
df = pd.read_csv('manifest.csv', quoting=1, escapechar='\\\\')
df.to_csv('cleaned_manifest.csv', index=False)
"
```

## API & Network Issues

### Keepa API Problems

#### Rate Limiting

**Error**: `Too Many Requests` or `Rate limit exceeded`

**Symptoms**:

- HTTP 429 status codes
- Slow processing with frequent pauses
- "Rate limit" in error messages

**Solutions**:

```cmd
# Wait for rate limit reset (check Keepa docs)
# Typical reset periods: hourly or daily

# Reduce request volume
python -m backend.cli.resolve_ids manifest.csv --batch-size 10

# Check credit usage
curl "https://api.keepa.com/token?key=YOUR_KEY"

# Implement exponential backoff in custom scripts
```

#### Network Timeouts

**Error**: `Timeout occurred` or `Connection timed out`

**Solutions**:

```cmd
# Increase timeout values in scripts
python -m backend.cli.resolve_ids manifest.csv --timeout 30

# Check network connectivity
ping api.keepa.com
curl -I https://api.keepa.com

# Use caching to reduce API calls
# Cache is enabled by default (7-day TTL)
```

### Frontend API Connection Issues

#### CORS Errors

**Error**: `CORS policy: Request has been blocked`

**Solutions**:

```javascript
// Check if API server is running
fetch("http://localhost:8787/healthz")
  .then((r) => r.json())
  .then((data) => console.log("API OK:", data))
  .catch((err) => console.error("API Error:", err));
```

```cmd
# Ensure API server includes CORS headers (already configured)
# Check server logs for CORS issues
```

#### SSE Connection Problems

**Error**: SSE stream stops or never starts

**Diagnosis**:

```javascript
// Test SSE connection directly
const evtSource = new EventSource(
  "http://localhost:8787/v1/pipeline/upload/stream",
);
evtSource.onmessage = (e) => console.log("Event:", e.data);
evtSource.onerror = (e) => console.error("SSE Error:", e);
```

**Solutions**:

- Check API server logs for errors
- Verify upload file format and size
- Test with smaller manifest files
- Check browser dev tools Network tab

## Data Quality Issues

### Evidence Gate Failures

#### Low Evidence Pass Rate

**Warning**: `Low evidence pass rate: 23% of items excluded`

**Investigation**:

```cmd
# Check ID resolution success
python -m backend.cli.resolve_ids manifest.csv --no-network

# Review evidence gate settings
echo $EVIDENCE_MIN_COMPS
echo $EVIDENCE_REQUIRE_SECONDARY

# Analyze failed items
grep "evidence_gate.*false" logs/audit.jsonl | head -5
```

**Solutions**:

```cmd
# Improve manifest quality
# - Better UPC/EAN data
# - More complete product information

# Adjust evidence thresholds (carefully)
set EVIDENCE_MIN_COMPS=2
set EVIDENCE_REQUIRE_SECONDARY=false

# Focus on high-evidence subset for analysis
```

#### Missing Product Identifiers

**Issue**: Many items lack UPC/EAN/ASIN codes

**Solutions**:

```cmd
# Check identifier column presence
python -c "
import pandas as pd
df = pd.read_csv('manifest.csv')
id_cols = ['upc', 'ean', 'asin', 'isbn']
for col in id_cols:
    if col in df.columns:
        non_null = df[col].notna().sum()
        print(f'{col}: {non_null}/{len(df)} ({100*non_null/len(df):.1f}%)')
"

# Request better manifest data from seller
# Consider manual lookup for high-value items
# Use title-based matching as fallback (future enhancement)
```

### Price Estimation Issues

#### Unrealistic Price Estimates

**Symptoms**:

- Extremely high/low price predictions
- Price distributions with excessive variance
- Negative price estimates (should be clipped)

**Diagnosis**:

```cmd
# Check price estimation results
python -c "
import pandas as pd
df = pd.read_csv('priced_items.csv')
print('Price Statistics:')
print(df[['est_price_mu', 'est_price_sigma', 'est_price_p5', 'est_price_p95']].describe())
print('\nOutliers (>$500):')
print(df[df['est_price_mu'] > 500][['sku_local', 'title', 'est_price_mu']])
"
```

**Solutions**:

```cmd
# Apply category floors to prevent unrealistic low prices
python -m backend.cli.estimate_price items.csv \
  --category-priors configs/category_priors.json \
  --salvage-floor-frac 0.10

# Review Keepa data quality for outliers
# Consider manual price overrides for known high-value items
```

## Optimization & Simulation Issues

### Monte Carlo Problems

#### Memory Issues with Large Simulations

**Error**: `MemoryError` or system slowdown

**Solutions**:

```cmd
# Reduce simulation count
python -m backend.cli.optimize_bid items.csv --sims 500

# Process in smaller batches
split -l 200 large_manifest.csv batch_

# Use streaming processing for large datasets
# Increase system memory if possible
```

#### Optimization Convergence Issues

**Warning**: `Bisection did not converge` or `No feasible solution found`

**Diagnosis**:

```cmd
# Check constraint feasibility
python -m backend.cli.sweep_bid items.csv \
  --out-csv sweep.csv --lo 0 --hi 2000 --step 100

# Review sweep results for feasible region
python -c "
import pandas as pd
df = pd.read_csv('sweep.csv')
feasible = df[df['meets_constraints']]
print('Feasible bids:', len(feasible))
if len(feasible) > 0:
    print('Min feasible bid:', feasible['bid'].min())
    print('Max feasible bid:', feasible['bid'].max())
else:
    print('No feasible solutions found')
"
```

**Solutions**:

```cmd
# Relax constraints
python -m backend.cli.optimize_bid items.csv \
  --roi-target 1.20 --risk-threshold 0.75

# Expand search range
python -m backend.cli.optimize_bid items.csv \
  --lo 0 --hi 10000

# Check for data quality issues causing unrealistic constraints
```

### ROI Calculation Issues

#### Negative or Unrealistic ROI

**Symptoms**:

- ROI values < 0 (indicating losses)
- ROI values > 10 (unrealistically high)
- `meets_constraints = false` unexpectedly

**Investigation**:

```cmd
# Check cost parameters
python -c "
import json
with open('optimization_result.json') as f:
    result = json.load(f)
print('Cost breakdown in optimization:')
for key, value in result.items():
    if 'fee' in key or 'cost' in key:
        print(f'{key}: {value}')
"

# Review individual item contributions
# High-cost items may dominate ROI calculation
```

**Solutions**:

- Review fee structure for accuracy
- Check for data entry errors in costs
- Verify bid range is appropriate for item values
- Consider excluding extreme outliers

## Performance Issues

### Slow Processing

#### Long API Response Times

**Symptoms**:

- Commands take > 5 minutes for small manifests
- Frequent timeouts
- High CPU usage

**Solutions**:

```cmd
# Check cache effectiveness
dir data\.cache\keepa.db
# Large cache file indicates good reuse

# Monitor network requests
# Add debug logging to see API call frequency

# Use smaller batch sizes
python -m backend.cli.resolve_ids items.csv --batch-size 5

# Check Keepa API status page for service issues
```

#### Memory Usage Problems

**Error**: System becomes unresponsive during processing

**Solutions**:

```cmd
# Monitor memory usage
tasklist /fi "imagename eq python.exe" /fo table

# Process in smaller chunks
split -l 100 large_manifest.csv chunk_

# Clear cache periodically
del data\.cache\keepa.db

# Increase virtual memory if needed
```

### Frontend Performance

#### Slow Page Loading

**Symptoms**:

- Frontend pages load slowly
- Components not rendering
- Build errors

**Solutions**:

```cmd
# Check build status
cd frontend
npm run build

# Clear build cache
del /q .next\cache\*
npm run build

# Check for TypeScript errors
npm run lint
```

#### Large File Upload Issues

**Error**: Upload fails or times out

**Solutions**:

```cmd
# Check file size limits (default 20MB)
echo File size: %~z1 bytes

# Increase backend upload limit if needed
set MAX_UPLOAD_BYTES=52428800  # 50MB

# Split large manifests into smaller files
# Use API upload instead of frontend for very large files
```

## Calibration & Analysis Issues

### Calibration File Problems

#### JSONL Format Issues

**Error**: `JSON decode error` when analyzing calibration logs

**Diagnosis**:

```cmd
# Check file format
python -c "
import json
with open('predictions.jsonl') as f:
    for i, line in enumerate(f):
        try:
            json.loads(line)
        except Exception as e:
            print(f'Line {i+1}: {e}')
            if i > 10: break
"
```

**Solutions**:

- Re-run optimization with proper calibration logging
- Check for truncated files (disk space issues)
- Verify file wasn't corrupted during transfer

#### Outcome Matching Issues

**Error**: `No matching records found between predictions and outcomes`

**Diagnosis**:

```cmd
# Check SKU overlap
python -c "
import json, pandas as pd
# Load predictions
pred_skus = set()
with open('predictions.jsonl') as f:
    for line in f:
        record = json.loads(line)
        pred_skus.add(record['sku_local'])

# Load outcomes
outcome_df = pd.read_csv('outcomes.csv')
outcome_skus = set(outcome_df['sku_local'])

print(f'Prediction SKUs: {len(pred_skus)}')
print(f'Outcome SKUs: {len(outcome_skus)}')
print(f'Overlap: {len(pred_skus & outcome_skus)}')
print(f'Sample prediction SKUs: {list(pred_skus)[:5]}')
print(f'Sample outcome SKUs: {list(outcome_skus)[:5]}')
"
```

**Solutions**:

- Ensure `sku_local` values match exactly (case-sensitive)
- Check for extra spaces or formatting differences
- Verify outcomes file covers the same time period as predictions

## Recovery Procedures

### Corrupted Cache

**Symptoms**: Inconsistent results, cache errors

**Recovery**:

```cmd
# Clear cache database
del data\.cache\keepa.db

# Re-run with fresh cache
python -m backend.cli.resolve_ids manifest.csv --with-stats
```

### Failed Optimization

**Recovery Steps**:

```cmd
# 1. Check inputs are valid
python -m backend.cli.validate_manifest manifest.csv

# 2. Test with smaller sample
head -20 manifest.csv > test_sample.csv
python -m backend.cli.optimize_bid test_sample.csv --sims 100

# 3. Use intermediate outputs for debugging
python -m backend.cli.parse_clean manifest.csv --out csv --output debug_clean.csv
python -m backend.cli.resolve_ids debug_clean.csv --output-csv debug_resolved.csv --no-network
```

### Log Analysis

**Check System Logs**:

```cmd
# API server logs (if running via uvicorn)
# Check console output for error traces

# Windows Event Viewer (for system-level issues)
eventvwr.msc

# Check disk space
dir C:\ | findstr "bytes free"
```

## Getting Help

### Information to Collect

When reporting issues, include:

1. **Error message** (full traceback)
2. **Command used** (with sanitized paths/keys)
3. **System info**: Windows version, Python version
4. **File sizes**: Manifest size, memory usage
5. **Timing**: When issue started, duration
6. **Environment**: Virtual environment, API key status

### Debug Commands

```cmd
# System information
python --version
pip list | findstr lotgenius
echo %KEEPA_API_KEY% | findstr "."
dir data\ /s

# Test basic functionality
python -c "import lotgenius; print('Import OK')"
curl http://localhost:8787/healthz
python -m backend.cli.validate_manifest --help
```

### Escalation Path

1. **Documentation**: Check relevant runbook section
2. **GitHub Issues**: Search existing issues for similar problems
3. **Team Slack**: Post in #lot-genius-support with debug info
4. **Email Support**: technical-support@lotgenius.com

---

**Back to**: [Documentation Index](../../INDEX.md) for complete navigation
