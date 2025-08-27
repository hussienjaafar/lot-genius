# Release Notes - v0.1.0

This release includes 23 Gap Fix implementations that enhance the Lot Genius platform with improved functionality, reliability, and developer experience.

## What's New

### Backend Infrastructure

- **End-to-End Pipeline Validation** (Gap Fix 07) [[gapfix_07_e2e_validation.md](multi_agent/runlogs/gapfix_07_e2e_validation.md)]
- **Gap Fix 12 - Keepa Integration Tests** (Gap Fix 12) [[gapfix_12_keepa_integration_tests.md](multi_agent/runlogs/gapfix_12_keepa_integration_tests.md)]
- **Gap Fix 13 - Feeds/Watchlists CSV Import** (Gap Fix 13) [[gapfix_13_feeds_watchlists.md](multi_agent/runlogs/gapfix_13_feeds_watchlists.md)]
- **Report Polish + Confidence/Cache Visibility** (Gap Fix 16) [[gapfix_16_report_polish.md](multi_agent/runlogs/gapfix_16_report_polish.md)]
- **Frontend Confidence + Cache UI** (Gap Fix 17): Surface Product Confidence and Cache Metrics in the frontend results summary, wired to existing report/API outputs. Keep ASCII-safe UI text and avoid network dependencies. [[gapfix_17_frontend_confidence_cache_ui.md](multi_agent/runlogs/gapfix_17_frontend_confidence_cache_ui.md)]

### Frontend & UI

- **Frontend File Upload Fix** (Gap Fix 04) [[gapfix_04_frontend_upload.md](multi_agent/runlogs/gapfix_04_frontend_upload.md)]
- **Documentation Updates - Run Log** (Gap Fix 09) [[gapfix_09_docs_updates.md](multi_agent/runlogs/gapfix_09_docs_updates.md)]
- **Gap Fix 11c - Frontend Mock Submission Fix** (Gap Fix 11) [[gapfix_11c_frontend_mock_submission_fix.md](multi_agent/runlogs/gapfix_11c_frontend_mock_submission_fix.md)]
- **Backend Pipeline Resilience + Small UX** (Gap Fix 18): Add resilience improvements to streaming pipeline and minor UX touches - make SSE worker emit clear "error" events with ASCII messages when exceptions occur, ensure cleanup of temp files always happens, and add optional "Copy Report Path" button in UI when markdown_path is returned. [[gapfix_18_pipeline_resilience.md](multi_agent/runlogs/gapfix_18_pipeline_resilience.md)]

### Documentation & Quality

- **UPC Check Digit Validation** (Gap Fix 02) [[gapfix_02_upc_check_digit.md](multi_agent/runlogs/gapfix_02_upc_check_digit.md)]
- **Windows Console Encoding Hardening** (Gap Fix 08) [[gapfix_08_windows_encoding.md](multi_agent/runlogs/gapfix_08_windows_encoding.md)]
- **Gap Fix 15c: Documentation Cleanup - Final ASCII Cleanup** (Gap Fix 15): Finish Unicode cleanup in docs by removing remaining non-ASCII characters (box-drawing, arrows, garbled sequences) and add a deterministic relative-link check. [[gapfix_15c_docs_cleanup_finish.md](multi_agent/runlogs/gapfix_15c_docs_cleanup_finish.md)]

### Development & CI

- **Frontend E2E Test Stabilization** (Gap Fix 11) [[gapfix_11_frontend_e2e_fix.md](multi_agent/runlogs/gapfix_11_frontend_e2e_fix.md)]
- **CI + Quality Gates** (Gap Fix 19): Add a minimal CI pipeline and local quality gates to keep the repo healthy: [[gapfix_19_ci_quality_gates.md](multi_agent/runlogs/gapfix_19_ci_quality_gates.md)]

### Bug Fixes & Polish

- **Header Mapping and ID Field Separation** (Gap Fix 01) [[gapfix_01_header_mapping.md](multi_agent/runlogs/gapfix_01_header_mapping.md)]
- **ID Resolution Precedence + Evidence Ledger** (Gap Fix 03) [[gapfix_03_id_resolution_ledger.md](multi_agent/runlogs/gapfix_03_id_resolution_ledger.md)]
- **Scraper Query & Filtering Improvements** (Gap Fix 05) [[gapfix_05_scraper_query_filtering.md](multi_agent/runlogs/gapfix_05_scraper_query_filtering.md)]
- **Confidence Scoring + Evidence Gating** (Gap Fix 06) [[gapfix_06_confidence_gating.md](multi_agent/runlogs/gapfix_06_confidence_gating.md)]
- **Multi-Source Product Confirmation & Confidence Score** (Gap Fix 10) [[gapfix_10_product_confirmation.md](multi_agent/runlogs/gapfix_10_product_confirmation.md)]
- **Gap Fix 11b: Frontend E2E Polish** (Gap Fix 11) [[gapfix_11b_frontend_e2e_polish.md](multi_agent/runlogs/gapfix_11b_frontend_e2e_polish.md)]
- **Gap Fix 13b: Feeds CLI Polish - Run Log** (Gap Fix 13) [[gapfix_13b_feeds_cli_polish.md](multi_agent/runlogs/gapfix_13b_feeds_cli_polish.md)]
- **Performance & Caching - Run Log** (Gap Fix 14) [[gapfix_14_performance_caching.md](multi_agent/runlogs/gapfix_14_performance_caching.md)]
- **Documentation Unicode Cleanup** (Gap Fix 15) [[gapfix_15_docs_unicode_cleanup.md](multi_agent/runlogs/gapfix_15_docs_unicode_cleanup.md)]

## Release Artifacts

This release includes the following downloadable artifacts:

- **Backend Packages**: Python wheel and source distribution for lotgenius package
- **Frontend Build**: Production-ready Next.js application bundle
- **Documentation Bundle**: Complete offline documentation with validation scripts

## Installation & Usage

**Backend Package**:

```bash
pip install lotgenius-0.1.0-py3-none-any.whl
```

**Frontend Deployment**:

```bash
unzip frontend-build.zip
npm start  # or deploy .next/ directory to your hosting platform
```

**Documentation**:

```bash
unzip docs-bundle.zip
# Browse docs/ directory or run validation scripts
python scripts/check_ascii.py docs/
```

## System Requirements

- **Backend**: Python 3.11+ with dependencies listed in requirements
- **Frontend**: Node.js 18+ for development, static files for deployment
- **Documentation**: Python 3.11+ for validation scripts (optional)

For detailed implementation notes, see the complete run logs in [multi_agent/runlogs/](multi_agent/runlogs/).
