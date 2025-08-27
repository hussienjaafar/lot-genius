# Stage 1: External Comps Hardening - Run Log

**Date:** 2025-08-22
**Agent:** Claude Code
**Objective:** Safely enable and harden external comps as a secondary pricing signal with caching and clear evidence outputs.

## Summary

Successfully implemented external comps hardening with caching, evidence consolidation, and proper source weighting integration.

## What Changed

### Files Modified

1. **backend/lotgenius/datasources/ebay_scraper.py**
   - Added cache integration (check cache before fetch, store after fetch)
   - Improved error handling to return empty list on network errors
   - Fixed datetime.utcnow() deprecation warning

2. **backend/lotgenius/datasources/external_comps_cache.py** (NEW)
   - Created SQLite-based caching system for external comps
   - Normalized query signature using MD5 hash of sorted parameters
   - TTL-based expiration with configurable days
   - Thread-safe operations with WAL mode

3. **backend/lotgenius/pricing/external_comps.py**
   - Consolidated evidence writing to single record per item
   - Improved error handling with error collection
   - All errors included in single evidence record under "errors" key

4. **backend/lotgenius/pricing.py**
   - Integrated external comps as a pricing source
   - Added to build_sources_from_row when flags enabled
   - Uses 1.5x CV multiplier for external sources (higher uncertainty)

5. **backend/lotgenius/config.py**
   - Added `EXTERNAL_COMPS_CACHE_TTL_DAYS: int = 7` setting
   - Exported as top-level constant

### New Settings and Defaults

- `EXTERNAL_COMPS_CACHE_TTL_DAYS = 7` - Cache validity in days
- External comps CV multiplier = 1.5x base CV (higher uncertainty)
- External comps prior weight = 0.25 (from existing settings)

## How the Cache Works

### Cache Key Generation

- Normalizes query parameters (title, brand, model, UPC, ASIN, condition)
- Sorts components for consistency
- Creates MD5 hash for compact storage key
- Separate keys per source (eBay, Google Search, etc.)

### Cache Behavior

1. **Read-before-fetch**: Check cache with TTL validation
2. **Write-after-fetch**: Store results with timestamp
3. **TTL enforcement**: Configurable via EXTERNAL_COMPS_CACHE_TTL_DAYS
4. **Corruption handling**: Fallback to no cache on errors

### Database Structure

- SQLite with WAL journaling for concurrency
- Table: `comps_cache` with columns:
  - `query_sig` (PRIMARY KEY)
  - `data` (JSON serialized comps)
  - `source` (ebay, google_search, etc.)
  - `timestamp` (Unix timestamp)

## Tests Added/Updated

### New Test Files

1. **backend/tests/test_external_comps_cache.py**
   - Query signature normalization tests
   - Cache set/get operations
   - TTL expiration validation
   - Multi-source separation
   - eBay scraper cache integration

2. **backend/tests/test_external_comps_evidence.py**
   - Single evidence record per item validation
   - Multi-source consolidation
   - Error handling in evidence
   - Disabled scraper behavior

### Test Results

- Core functionality tests pass
- Evidence consolidation verified
- Cache behavior validated
- Flag gating confirmed working

## Commands Run

```bash
# Test external comps specifically
pytest -q backend/tests/test_external_comps*

# Run all backend tests
pytest -q backend

# Individual test verification
pytest backend/tests/test_external_comps.py::test_default_scrapers_off -v
```

## Caveats and Next Steps

### Current Limitations

1. **FB Marketplace**: Still stubbed, not implemented
2. **Google Search**: Module referenced but not implemented
3. **Cache cleanup**: No automatic expired entry cleanup (manual clear_expired_cache() available)
4. **Import structure**: lotgenius.pricing is a module, not a package - imports must reference it directly

### Next Follow-ups

1. Implement Google Search enrichment module
2. Add scheduled cache cleanup job
3. Add metrics/monitoring for cache hit rates
4. Consider implementing FB Marketplace when ToS allows
5. Add more sophisticated match scoring algorithms

## Default Behavior

- **No changes unless flags explicitly enabled**
- Requires both `SCRAPER_TOS_ACK=true` AND `ENABLE_EBAY_SCRAPER=true`
- When disabled, no network calls, no external comps in sources
- Evidence ledger still gets summary with 0 comps when disabled

## Evidence Ledger Format

Single consolidated `external_comps_summary` record per item:

```json
{
  "source": "external_comps_summary",
  "meta": {
    "num_comps": 5,
    "by_source": {
      "ebay": 3,
      "google_search": 2
    },
    "sample": [...first 8 comps...],
    "errors": {
      "ebay": "Network error"  // Only if errors occurred
    }
  }
}
```

## Performance Considerations

- Cache reduces API calls significantly
- SQLite WAL mode enables concurrent reads
- Thread-safe with minimal lock contention
- Network failures don't crash pricing pipeline
