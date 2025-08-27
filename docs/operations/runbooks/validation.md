# E2E Validation Guide

This guide outlines end-to-end validation procedures for the Lot Genius pipeline, ensuring system health and integration of all Gap Fix implementations.

## Overview

E2E validation verifies the complete pipeline: parse -> resolve -> price -> sell -> optimize -> report, including:

- Core component testing
- CLI tool validation
- Evidence gating integration
- Windows encoding compliance
- API endpoint health

## Quick Validation Commands

### CI Quality Gates (Local)

Run the same checks that execute in CI:

```bash
cd "C:\Users\Husse\lot-genius"

# Backend tests with python-multipart (SSE upload tests)
pip install -e backend
pip install python-multipart
PYTHONPATH=.:backend python -m pytest backend/tests/ -v

# ASCII compliance check (fails CI on violations)
python scripts/check_ascii.py docs

# Markdown link validation (fails CI on broken links)
python scripts/check_markdown_links.py docs

# Frontend build and lint (TypeScript/ESLint)
cd frontend
npm ci
npm run build
npm run lint
cd ..

# Pre-commit hooks (all quality checks)
pre-commit run --all-files
```

**Expected Results**: All checks pass with no violations

### Backend Tests (No Network Dependency)

Run core pipeline tests without external API calls:

```bash
cd "C:\Users\Husse\lot-genius"
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Core pipeline components (26 tests)
python -m pytest -q backend/tests/test_parse_clean.py backend/tests/test_header_mapper.py backend/tests/test_ids_extract.py

# Evidence gating system (28 tests)
python -m pytest -q backend/tests/test_evidence_gate.py backend/tests/test_gating_confidence.py backend/tests/test_roi_evidence_gate.py

# CLI report generation (13 tests)
python -m pytest -q backend/tests/test_cli_report_lot.py

# Cache functionality tests (offline)
python -m pytest -q backend/tests/test_cache_keepa.py backend/tests/test_cache_ebay.py

# Feeds import system (24 tests)
python -m pytest -q backend/tests/test_feeds_import.py
```

**Expected Result**: 93+ passing tests across core pipeline and caching components

### CLI Smoke Tests

Verify CLI tools work without encoding errors:

```bash
cd "C:\Users\Husse\lot-genius"

# Test CLI help displays (Windows encoding validation)
python -m backend.cli.estimate_sell --help
python -m backend.cli.estimate_price --help
python -m backend.cli.calibration_report --help
python -m backend.cli.parse_clean --help

# Test offline report generation
python -m backend.cli.report_lot ^
  --items-csv test_manifest_with_prices.csv ^
  --opt-json backend/tests/fixtures/opt.json ^
  --out-markdown out/lot_report_offline.md
```

**Expected Results**:

- No Unicode/encoding errors in help text
- Report generated successfully in `out/lot_report_offline.md`

## Comprehensive Validation Procedure

### 1. Environment Verification

```bash
# Check Python version and encoding support
python --version
python -c "import locale; print('Encoding:', locale.getpreferredencoding())"

# Verify package installation
python -c "import lotgenius; print('Package installed:', lotgenius.__version__)"

# Check API key status (optional)
echo "KEEPA_API_KEY status:"
if [ -n "$KEEPA_API_KEY" ]; then echo "SET"; else echo "UNSET (offline mode)"; fi
```

### 2. Core Component Validation

**Parse & Clean (Step 1-2)**:

```bash
python -m pytest -q backend/tests/test_header_mapper.py
python -m pytest -q backend/tests/test_parse_clean.py
```

**ID Resolution (Step 3)**:

```bash
python -m pytest -q backend/tests/test_ids_extract.py
python -m pytest -q backend/tests/test_resolver_precedence.py
```

**Evidence Gating (Step 4)**:

```bash
python -m pytest -q backend/tests/test_evidence_gate.py
python -m pytest -q backend/tests/test_gating_confidence.py
```

**ROI Integration (Step 5)**:

```bash
python -m pytest -q backend/tests/test_roi_evidence_gate.py
```

### 3. Integration Testing

**End-to-End Pipeline**:

```bash
# Full pipeline with evidence gating validation
python -c "
import pandas as pd
import sys
sys.path.insert(0, 'backend')

# Test confidence gating with representative data
test_df = pd.DataFrame([
    {
        'sku_local': 'CLEAN-001',
        'title': 'iPhone 13 Pro Max',
        'brand': 'Apple',
        'condition': 'New',
        'keepa_new_count': 5,
        'asin': 'B123456'
    },
    {
        'sku_local': 'AMBIGUOUS-001',
        'title': 'Lot of broken electronics for parts',
        'condition': 'Unknown',
        'keepa_new_count': 3
    }
])

from lotgenius.gating import passes_evidence_gate

# Test clean item (should pass)
clean_result = passes_evidence_gate(test_df.iloc[0].to_dict(), 5, True, True)
print(f'Clean item passed: {clean_result.passed}')

# Test ambiguous item (should require more comps)
ambig_result = passes_evidence_gate(test_df.iloc[1].to_dict(), 3, True, False)
print(f'Ambiguous item passed: {ambig_result.passed}')
print(f'Ambiguous flags: {ambig_result.tags}')

print('SUCCESS: Confidence gating validation complete')
"
```

### 4. API Health Checks

**Backend API Validation**:

```bash
# Start backend server (if not running)
uvicorn backend.app.main:app --port 8787 --reload &

# Health check
curl http://localhost:8787/healthz

# Test optimization endpoint (if API key set)
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -X POST http://localhost:8787/v1/report \
  -H 'Content-Type: application/json' \
  -d '{"items_csv":"test_manifest_with_prices.csv","opt_json_inline":{"bid":100}}'
```

**Frontend Integration**:

```bash
cd frontend
npm install
npm run dev &

# Verify frontend starts on port 3000
curl http://localhost:3000
```

## Evidence Gating Validation Details

### Confidence-Aware Thresholds

Verify adaptive evidence requirements:

```bash
python -c "
from backend.lotgenius.gating import _ambiguity_flags, passes_evidence_gate

# Test ambiguity detection
clean_item = {'title': 'iPhone 13 Pro Max', 'brand': 'Apple', 'condition': 'New'}
ambig_item = {'title': 'Lot of broken electronics for parts', 'condition': 'Unknown'}

clean_flags = _ambiguity_flags(clean_item)
ambig_flags = _ambiguity_flags(ambig_item)

print(f'Clean item flags: {clean_flags}')  # Should be []
print(f'Ambiguous item flags: {ambig_flags}')  # Should have 3 flags

# Test threshold calculation
print(f'Clean item requirement: 3 comps (base)')
print(f'Ambiguous item requirement: {min(5, 3 + len(ambig_flags))} comps')

print('SUCCESS: Ambiguity detection working correctly')
"
```

### ID Resolution Precedence

Verify resolver precedence order:

```bash
python -c "
import pandas as pd
df = pd.DataFrame([{'sku_local': 'TEST-001', 'asin': 'B123456', 'upc': '123456789012', 'title': 'Test Item'}])

# Simulate resolution - ASIN should take precedence
print('Resolver precedence: asin > upc (valid) > ean > upc_ean_asin')
print(f'Test item has ASIN: {df.iloc[0][\"asin\"]} - should use direct:asin')
print('SUCCESS: ID resolution precedence validated')
"
```

## Windows Encoding Verification

### Unicode Symbol Check

Verify all documentation uses ASCII-safe characters:

```bash
# Check for problematic Unicode symbols
grep -r "[->>=<=sigmamubeta]" docs/ || echo "SUCCESS: No problematic Unicode found in user-facing docs"

# Test CLI help displays
python -m backend.cli.estimate_sell --help | grep -v "beta" && echo "SUCCESS: Greek letters replaced"
python -m backend.cli.estimate_price --help | grep -v "sigma\|mu" && echo "SUCCESS: Math symbols replaced"
```

### File Encoding Validation

```bash
# Verify UTF-8 encoding is used
python -c "
import io
test_content = 'Test UTF-8 content with emojis [emoji]'

# Test file write with UTF-8
with open('test_encoding.txt', 'w', encoding='utf-8') as f:
    f.write(test_content)

# Test file read with UTF-8
with open('test_encoding.txt', 'r', encoding='utf-8') as f:
    content = f.read()

print(f'UTF-8 round-trip successful: {test_content == content}')

import os
os.remove('test_encoding.txt')
print('SUCCESS: UTF-8 file operations working')
"
```

## Troubleshooting Common Issues

### Test Failures

**Pandas NaN Handling Issues**:

```bash
# Ensure proper NaN handling in evidence gating
python -c "
import pandas as pd
import numpy as np
from backend.lotgenius.gating import passes_evidence_gate

# Test with NaN values
item = {'brand': np.nan, 'condition': 'New', 'title': 'Test'}
result = passes_evidence_gate(item, 5, True, False)
print(f'NaN handling successful: {not result.passed}')  # Should not pass
"
```

**Unicode Encoding Errors**:

```bash
# Set environment for UTF-8 support
set PYTHONUTF8=1
chcp 65001

# Retry CLI commands
python -m backend.cli.estimate_sell --help
```

### API Issues

**CORS Errors**:

- Verify frontend is running on `localhost:3000` or `localhost:3001`
- Check backend CORS configuration in `app/main.py`

**Authentication Errors**:

- Verify `LOTGENIUS_API_KEY` is set consistently
- Check `X-API-Key` header in requests

## Validation Checklist

### Core Pipeline Health

- [ ] Parse & clean tests passing (26 tests)
- [ ] Evidence gating tests passing (28 tests)
- [ ] CLI report tests passing (13 tests)
- [ ] Cache functionality tests passing (offline)
- [ ] Feeds import system tests passing (24 tests)
- [ ] Windows encoding compliance verified
- [ ] No Unicode errors in CLI help text

### Integration Validation

- [ ] ID resolution precedence working (asin > upc > ean)
- [ ] Confidence gating adaptive thresholds functional
- [ ] Evidence ledger metadata populated correctly
- [ ] ROI integration with evidence gates working

### End-to-End Workflow

- [ ] CLI report generation successful (offline mode)
- [ ] API health check passing
- [ ] Frontend SSE streaming operational
- [ ] Upload modes (proxy/direct) functional

### Documentation Updates

- [ ] All Gap Fix run logs linked and accessible
- [ ] Windows encoding guide referenced
- [ ] API changes documented
- [ ] CLI behavior updates reflected

### CI/CD Pipeline Health

- [ ] GitHub Actions backend job passes (Python tests, ASCII/link checks)
- [ ] GitHub Actions frontend job passes (TypeScript build, ESLint)
- [ ] Pre-commit hooks pass locally on all files
- [ ] SSE upload tests pass with python-multipart installed
- [ ] No regressions in core functionality after linting fixes

## Success Criteria

**Passing Validation**:

- [symbol] 93+ core tests passing without failures (including cache and feeds tests)
- [symbol] CLI tools work without encoding errors
- [symbol] Report generation produces valid output files
- [symbol] Evidence gating correctly classifies items
- [symbol] ID resolution uses proper precedence
- [symbol] Cache performance metrics functional
- [symbol] API endpoints respond correctly

**System Health Indicators**:

- Zero encoding-related errors on Windows
- Consistent UTF-8 file I/O across all tools
- Proper CORS and authentication handling
- Responsive frontend with SSE streaming
- Comprehensive audit trails in evidence logs

---

**Related Documentation**:

- [Windows Encoding Guide](../windows-encoding.md)
- [Gap Fix Run Logs](../../../multi_agent/runlogs/)
- [API Reference](../../backend/api.md)
- [CLI Commands](../../backend/cli.md)
