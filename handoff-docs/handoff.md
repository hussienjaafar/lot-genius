# Lot Genius — Engineering Handoff (GPT <-> Claude Code Workflow)

Date: 2025-08-25
Owner: Hussein / Ryze Media
Location: C:\Users\Husse\lot-genius

## Purpose

Continue the Gap Fix initiative using the same workflow: GPT authors precise Claude Code prompts, Claude implements and publishes run logs, GPT reviews code/tests/logs, then proceeds to the next scoped step.

## Workflow Protocol (repeat every step)

- Plan -> Prompt -> Execute -> Review
- GPT creates a “Claude Code Prompt” with:
  - Objective, Scope, Target files, Specific changes, Acceptance criteria, Tests, Deliverables
  - Explicit run log path: `multi_agent/runlogs/gapfix_XX_<slug>.md`
- Claude executes, commits small, focused diffs, and publishes the run log at the given path
- GPT reviews:
  - Open the run log; inspect changed files and tests
  - Run targeted tests (Windows tip: `set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`)
  - Summarize results; mark step complete; propose next step

## Completed Steps (Gap Fix 01–09)

1. Header Mapping & IDs Separation

- Preserved `asin`, `upc`, `ean`; still compute `upc_ean_asin`
- Files: `backend/lotgenius/headers.py`, `parse.py`, `ids.py`, `schema.py`
- Run log: `multi_agent/runlogs/gapfix_01_header_mapping.md`

2. UPC-A Check Digit Validation

- Validate 12-digit UPCs in `extract_ids`; tests added
- Files: `backend/lotgenius/ids.py`; tests: `backend/tests/test_ids_upc_check_digit.py`
- Run log: `multi_agent/runlogs/gapfix_02_upc_check_digit.md`

3. Resolver Precedence + Evidence Ledger Meta

- Precedence: `asin > upc > ean > upc_ean_asin`
- Evidence meta added: `identifier_source`, `identifier_type`, `identifier_used`
- Files: `backend/lotgenius/resolve.py`; tests: `backend/tests/test_resolver_precedence.py`
- Run log: `multi_agent/runlogs/gapfix_03_id_resolution_ledger.md`

4. Frontend Upload + SSE (Proxy & Direct)

- Fixed multipart upload; added CORS; working SSE console
- Files: `frontend/app/...`, `frontend/lib/api.ts`, `frontend/app/api/pipeline/upload/stream/route.ts`, `backend/app/main.py`
- Run log: `multi_agent/runlogs/gapfix_04_frontend_upload.md`

5. Scraper Query & Filtering (eBay)

- Targeted queries (UPC/ASIN/"Brand" "Model"/filtered title)
- Filters: similarity (RapidFuzz), recency, model presence, condition (for parts/etc.), MAD price outliers
- Cache filtered results
- Files: `backend/lotgenius/datasources/ebay_scraper.py`; tests: `backend/tests/test_ebay_query_and_filtering.py`
- Run log: `multi_agent/runlogs/gapfix_05_scraper_query_filtering.md`

6. Confidence-Aware Evidence Gating

- Adaptive thresholds by ambiguity flags (`generic:title`, `ambiguous:brand`, `ambiguous:condition`), capped at 5; high-trust ID bypass preserved
- NaN handling fixes in evidence/secondary signal checks
- Files: `backend/lotgenius/gating.py`, `backend/lotgenius/evidence.py`; tests: `backend/tests/test_gating_confidence.py`
- Run log: `multi_agent/runlogs/gapfix_06_confidence_gating.md`

7. End-to-End Validation

- Backend pipeline and CLI smoke pass (offline); frontend E2E tests brittle; API tests skipped without Keepa key
- Run log: `multi_agent/runlogs/gapfix_07_e2e_validation.md`

8. Windows Encoding Hardening

- UTF-8 file I/O; ASCII-safe console; CLI help cleaned; Windows guide added
- Files: CLI under `backend/cli/*`; `docs/operations/windows-encoding.md`
- Run log: `multi_agent/runlogs/gapfix_08_windows_encoding.md`

9. Documentation Updates

- README, API, CLI, Architecture, Frontend UI, Validation runbook updated; run logs linked
- Files: `README.md`, `docs/backend/api.md`, `docs/backend/cli.md`, `docs/architecture.md`, `docs/frontend/ui.md`, `docs/operations/runbooks/validation.md`
- Run log: `multi_agent/runlogs/gapfix_09_docs_updates.md`

## Current Status & Notes

- Backend: Healthy across targeted tests; resolver precedence & gating validated
- Frontend: Upload/SSE working; E2E UI tests flaky (selectors)
- Docs: Updated; minor Unicode remnants (>=, <=, mu, sigma, beta) can be normalized
- Keepa: Live tests skipped without `KEEPA_API_KEY`; offline path validated

## Backlog (Proposed Next Steps)

10. Multi-Source Product Confirmation & Confidence Score

- Compute per-item product match confidence from Keepa + filtered scrapers
- Factors: title similarity, model presence, brand match, price consistency (z to Keepa), multiple sources, recency
- Output: `product_confidence` in evidence meta; optionally influence gating/weights
- Tests: deterministic unit tests; no network
- Run log: `multi_agent/runlogs/gapfix_10_product_confirmation.md`

11. Frontend E2E Test Stabilization

- Update Playwright selectors; add data-testids; stub data routes
- Run log: `multi_agent/runlogs/gapfix_11_frontend_e2e_fix.md`

12. Keepa Integration Tests (with API key)

- If `KEEPA_API_KEY` present, run `backend/tests/test_api_*` + pipeline network tests
- Run log: `multi_agent/runlogs/gapfix_12_keepa_integration_tests.md`

13. Additional Feeds / Watchlists (non-scraping)

- CSV import and enrichment hooks
- Run log: `multi_agent/runlogs/gapfix_13_feeds_watchlists.md`

14. Performance & Caching Review

- Batch scraping, cache coverage/TTL, SQLite tuning
- Run log: `multi_agent/runlogs/gapfix_14_performance_caching.md`

15. Docs Unicode Cleanup

- Normalize remaining non-ASCII symbols to ASCII; link-check
- Run log: `multi_agent/runlogs/gapfix_15_docs_unicode_cleanup.md`

## Claude Code Prompt Template (copy/paste)

- Objective: <one sentence outcome>
- Scope: <modules/components>
- Target files: <paths>
- Changes:
  - <precise implementation bullets>
- Acceptance criteria:
  - <clear pass/fail conditions>
- Tests:
  - <files to add/run; commands>
- Deliverables:
  - Code + tests
  - Run log: `multi_agent/runlogs/gapfix_XX_<slug>.md` (summary, diffs, test outputs)

Example header to Claude: "Please publish the run logs for this step in `multi_agent/runlogs/gapfix_10_product_confirmation.md`."

## Review Checklist (for GPT)

- Open run log: `type multi_agent\runlogs\gapfix_XX_<slug>.md`
- Inspect changed files and tests
- Run targeted tests:
  - `set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
  - `python -m pytest -q backend\tests\<target>.py`
- Optional CLI smoke:
  - `python -m backend.cli.report_lot <csv> --opt-json <opt.json> --out-markdown out\<file>.md`
- Confirm acceptance criteria; summarize findings; propose next step

## Environment & Commands

- Backend install:
  - `python -m venv .venv && .venv\Scripts\activate && pip install -U pip && pip install -e backend`
- Run tests:
  - `set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && python -m pytest -q backend\tests\<pattern>.py`
- API server:
  - `uvicorn backend.app.main:app --port 8787 --reload`
- Frontend:
  - `cd frontend && npm install && npm run dev`
- Keepa key (optional for live tests):
  - Set `KEEPA_API_KEY` in `.env` or shell

## Key Paths

- Backend: `backend/lotgenius/*`, `backend/cli/*`, `backend/app/main.py`
- Frontend: `frontend/app/*`, `frontend/lib/*`, `frontend/app/api/*`
- Docs: `docs/backend/*.md`, `docs/architecture.md`, `docs/frontend/ui.md`, `docs/operations/*`
- Run logs: `multi_agent/runlogs/gapfix_XX_*.md`
- Tests: `backend/tests/*`

## Risks & Guidelines

- Respect scraper ToS flags (`ENABLE_EBAY_SCRAPER`, `SCRAPER_TOS_ACK`)
- Windows consoles: keep console output ASCII-only; file I/O UTF-8
- Without `KEEPA_API_KEY`, use offline fixtures; skip networked tests

---

If you want to start immediately, begin with Backlog Step 10 using the template above.
