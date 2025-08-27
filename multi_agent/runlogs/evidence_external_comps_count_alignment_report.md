# Evidence External Comps Count Alignment - Report

## Summary

Aligned the evidence gate's external comps counting logic with the current writer format from `external_comps.py`. Previously, `_count_external_comps()` looked for `total_comps` but the writer uses `num_comps`, causing undercounting. Updated the function to prefer `num_comps`, fallback to summing `by_source` values, and maintain legacy `total_comps` support for backward compatibility. This ensures the Two-Source Rule evidence gate correctly counts external comps for inclusion decisions.

## Files Changed

**backend/lotgenius/evidence.py**

- Updated `_count_external_comps()` function with robust counting logic:
  - Primary: Uses `external_comps_summary["num_comps"]` when present and valid
  - Fallback: Sums integer values in `external_comps_summary["by_source"]` if num_comps missing
  - Legacy: Falls back to `external_comps_summary["total_comps"]` for older records
  - Defensive against missing keys, wrong types, and negative values

**backend/tests/test_evidence_external_comps_count.py (NEW FILE)**

- Comprehensive test coverage for all counting scenarios:
  - Case A: `num_comps` present - correctly returns the value
  - Case B: `by_source` fallback - correctly sums ebay + google_search counts
  - Case C: Missing/invalid structures - returns 0 gracefully
  - Edge cases: invalid values, mixed records, preference order, non-numeric handling

## Tests Run

### New External Comps Count Tests

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_evidence_external_comps_count.py -q
```

**Result:** ✅ 9/9 PASSED

- `test_count_external_comps_num_comps_present` - ✅ PASS (Case A: num_comps=4)
- `test_count_external_comps_by_source_fallback` - ✅ PASS (Case B: by_source sum=3)
- `test_count_external_comps_missing_invalid_structure` - ✅ PASS (Case C: returns 0)
- `test_count_external_comps_preference_order` - ✅ PASS (prefers num_comps over by_source)
- Additional edge case tests all pass

### Existing Evidence Gate Tests (No Regressions)

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_evidence_gate.py -q
```

**Result:** ✅ 4/4 PASSED

- All existing evidence gate logic continues to work correctly

### Combined Test Run

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_evidence_gate.py backend/tests/test_evidence_external_comps_count.py -v
```

**Result:** ✅ 13/13 PASSED - Full test suite verification

## Follow-ups/TODOs

**None required.** The implementation is complete and robust:

- ✅ Handles current writer format (`num_comps` + `by_source`)
- ✅ Maintains backward compatibility with legacy `total_comps`
- ✅ Defensive against all edge cases (missing keys, wrong types, negative values)
- ✅ Comprehensive test coverage validates all scenarios
- ✅ No breaking changes to existing evidence gate behavior

## Risks/Assumptions

**Low Risk Implementation:**

- Only modified reader logic, no changes to writer format or evidence structure
- Maintains full backward compatibility with legacy `total_comps` format
- Existing evidence gate tests demonstrate no regressions
- Function is defensive against malformed data

**Key Design Decisions:**

- **Priority Order:** `num_comps` > `by_source` sum > `total_comps` (legacy)
- **Type Safety:** Validates integer conversion and non-negative values before counting
- **Robustness:** Graceful handling of missing keys, wrong types, and edge cases
- **Continue Pattern:** Uses `continue` to skip to next record once valid count found, preventing double-counting

**Assumptions Validated:**

- Writer format consistently uses `{"num_comps": N, "by_source": {...}}` structure (verified in external_comps.py)
- Evidence ledger contains list of dicts with `external_comps_summary` keys (verified in existing code)
- Lookback_days parameter not used for external comps filtering (consistent with current behavior)

**Edge Case Handling:**

- Non-dict summary structures → skip gracefully
- Invalid/negative numeric values → attempt fallback methods
- Mixed valid/invalid records → sum only valid counts
- Multiple evidence records → correctly sum across all records
