# Wire Config Defaults - Stage 4 Report

## Summary

Successfully wired runtime defaults for ROI and sell-through to derive from env-driven config (`lotgenius.config.settings`) rather than hard-coded literals. Updated ROI DEFAULTS in `roi.py` to use `settings.MIN_ROI_TARGET` and `settings.RISK_THRESHOLD`, modified sweep_bid CLI to use roi.DEFAULTS instead of literals, and changed estimate_sell CLI to use `settings.SELLTHROUGH_HORIZON_DAYS`. Environment variables now properly flow through to CLI defaults, ensuring consistent behavior across all components.

## Files Changed

**backend/lotgenius/roi.py**

- **Line ~22:** Changed `roi_target=1.25` → `roi_target=settings.MIN_ROI_TARGET`
- **Line ~23:** Changed `risk_threshold=0.80` → `risk_threshold=settings.RISK_THRESHOLD`
- **Line ~21:** Changed `horizon_days=60` → `horizon_days=settings.SELLTHROUGH_HORIZON_DAYS`
- **Rationale:** Centralize ROI-related defaults to respect environment configuration

**backend/cli/sweep_bid.py**

- **Line ~5:** Added import `from lotgenius.roi import feasible, DEFAULTS`
- **Line ~17:** Changed `default=1.25` → `default=DEFAULTS['roi_target']`
- **Line ~18:** Changed `default=0.80` → `default=DEFAULTS['risk_threshold']`
- **Rationale:** Use centralized defaults instead of duplicated literals for CLI options

**backend/cli/estimate_sell.py**

- **Line ~6:** Added import `from lotgenius.config import settings`
- **Line ~38:** Changed `default=60` → `default=settings.SELLTHROUGH_HORIZON_DAYS`
- **Rationale:** Respect env-driven sell-through horizon for CLI default days parameter

**backend/tests/test_roi_defaults.py (NEW FILE)**

- Comprehensive tests for ROI defaults loading from environment settings
- Tests env var changes reflected in roi.DEFAULTS after module reload
- Validates non-overridden defaults remain unchanged

**backend/tests/test_cli_estimate_sell_env.py (NEW FILE)**

- Tests estimate_sell CLI respects SELLTHROUGH_HORIZON_DAYS from environment
- Validates evidence output contains correct days parameter
- Tests explicit --days parameter still overrides environment

## Tests Run

### New ROI Defaults Test

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_roi_defaults.py -q
```

**Result:** ✅ 3/3 PASSED

- `test_roi_defaults_from_settings` - ✅ PASS (env vars MIN_ROI_TARGET=1.40, RISK_THRESHOLD=0.85, SELLTHROUGH_HORIZON_DAYS=45 properly reflected)
- `test_roi_defaults_original_values_preserved` - ✅ PASS (unchanged defaults remain at original values)
- `test_roi_defaults_integration_with_settings_object` - ✅ PASS (DEFAULTS match settings values)

### New CLI Environment Test

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_cli_estimate_sell_env.py -q
```

**Result:** ✅ 3/3 PASSED

- `test_estimate_sell_cli_env_days_default` - ✅ PASS (CLI uses SELLTHROUGH_HORIZON_DAYS=45 from environment)
- `test_estimate_sell_cli_env_days_with_evidence` - ✅ PASS (evidence output shows days=45 in meta)
- `test_estimate_sell_cli_explicit_days_override` - ✅ PASS (explicit --days=90 overrides environment)

### Regression Tests (Existing Tests Still Pass)

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_cli_estimate_sell.py -q
```

**Result:** ✅ 3/3 PASSED - No regressions in existing estimate_sell functionality

```bash
cd C:/Users/Husse/lot-genius && python -m pytest backend/tests/test_cli_sweep_bid.py -q
```

**Result:** ✅ 1/1 PASSED - No regressions in existing sweep_bid functionality

## Follow-ups/TODOs

**None required.** All acceptance criteria met:

- ✅ ROI defaults in roi.py reflect config.settings values
- ✅ sweep_bid.py CLI defaults come from roi.DEFAULTS (no hard-coded literals)
- ✅ estimate_sell.py default --days comes from settings.SELLTHROUGH_HORIZON_DAYS
- ✅ New tests pass demonstrating environment variable integration
- ✅ No regressions in existing CLI/ROI/sell tests

## Risks/Assumptions

**Low Risk Changes:**

- Only modified default value sources, no functional logic changes
- Preserved all existing function signatures
- Maintained backward compatibility for explicit parameter overrides
- Changes are purely about where defaults are sourced from

**Key Design Decisions:**

- **Module reload approach:** Tests use importlib.reload() to ensure environment changes are reflected after setting env vars
- **Import timing:** Added necessary imports at module level to ensure settings are available during CLI option definition
- **Preserved override behavior:** Explicit CLI parameters still override environment defaults
- **No internal API changes:** estimate_sell_p60(days=60) internal default unchanged - CLI layer handles environment integration

**Assumptions Validated:**

- Settings are properly loaded and accessible at import time (verified by successful tests)
- Environment variables flow through pydantic_settings correctly (verified by test_roi_defaults_from_settings)
- CLI framework respects dynamic defaults from imported modules (verified by CLI tests)
- Evidence output correctly reflects the days parameter used (verified by evidence tests)

**Future Considerations:**

- Environment changes now automatically flow to CLI defaults without code changes
- Consistency maintained between ROI optimizer, sweep utility, and sell-through estimation
- Central configuration point makes it easier to manage default policies across components
