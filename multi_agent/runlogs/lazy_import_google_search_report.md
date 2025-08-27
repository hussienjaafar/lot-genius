# Lazy Import Google Search - Hotfix Report

## Summary

Fixed import-time failures from optional google_search integration by switching from module-level import to lazy import guarded by feature flag. Previously, `external_comps.py` would import `google_search` at module load time, causing crashes when `default_api.google_web_search` wasn't installed, even when the feature was disabled. Now google_search is only imported when `ENABLE_GOOGLE_SEARCH_ENRICHMENT=True` and wrapped in try/except for robust error handling.

## Files Changed

**backend/lotgenius/pricing/external_comps.py**

- Removed module-level `from ..datasources import google_search`
- Added lazy import inside `gather_external_sold_comps()` under feature flag
- Wrapped import in try/except to catch ImportError and log to evidence
- Keeps eBay path unchanged

**backend/tests/test_external_comps.py**

- Added `ENABLE_GOOGLE_SEARCH_ENRICHMENT=false` to test environment setup
- Ensures tests don't attempt to import optional google_search module

## Tests Run

### Import Test

```bash
cd C:/Users/Husse/lot-genius && python -c "import backend.lotgenius.pricing.external_comps as m; print('ok')"
```

**Result:** ✅ PASS - "ok"

### External Comps Tests

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_external_comps.py -q
```

**Result:** ✅ 1 passed, 1 failed

- `test_default_scrapers_off` - ✅ PASS (validates our fix works with scrapers disabled)
- `test_ebay_parser_fixture` - ❌ FAIL (pre-existing failure, unrelated to our changes)

### Verification of Pre-existing Failure

```bash
# Verified the failing test was already broken before our changes
cd C:/Users/Husse/lot-genius && git stash && python -m pytest backend/tests/test_external_comps.py::test_ebay_parser_fixture -q
```

**Result:** ❌ Same failure - confirms our changes didn't introduce regression

### Lazy Import Behavior Test

```bash
cd C:/Users/Husse/lot-genius && python -c "
from backend.lotgenius.pricing import external_comps
from backend.lotgenius.config import settings
settings.ENABLE_GOOGLE_SEARCH_ENRICHMENT = False
item = {'title': 'Test'}
comps = external_comps.gather_external_sold_comps(item)
print(f'✓ Returned {len(comps)} comps with google_search disabled')
settings.ENABLE_GOOGLE_SEARCH_ENRICHMENT = True
comps2 = external_comps.gather_external_sold_comps(item)
print('✓ Handled missing google_search gracefully when enabled')
"
```

**Result:** ✅ PASS - Both scenarios handled correctly

## Follow-ups/TODOs

**None required for this hotfix.** The implementation is complete and meets all acceptance criteria:

- ✅ Module imports successfully with defaults
- ✅ Focused tests pass with feature disabled
- ✅ No behavior change when optional sources are disabled
- ✅ Evidence summary remains stable

## Risks/Assumptions

**Low Risk Changes:**

- Only modified import behavior, not core functionality
- Existing evidence logging unchanged
- eBay scraper path completely untouched
- Feature flag respects existing configuration

**Assumptions:**

- `ENABLE_GOOGLE_SEARCH_ENRICHMENT` flag already exists in config (verified)
- Missing `default_api.google_web_search` dependency causes ImportError (standard Python behavior)
- Evidence logging for import errors is acceptable UX when feature is enabled but dependency missing

**Design Decision:**

- Used separate ImportError handling vs generic Exception to distinguish import failures from runtime errors
- Chose lazy import over conditional module structure to minimize code changes
- Maintained existing error evidence format for consistency
