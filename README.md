# Lot Genius

Decision-ready bidding for liquidation lots from messy manifests.

## North Star

Input: one or more B-Stock manifest CSVs (messy/varied).
Output: a decision-ready report with lot resale value, recommended maximum bid, and 60-day sell-through — each with confidence, risk, and an evidence ledger.

**Investment gate (configurable):** only consider bids that satisfy
ROI ≥ `MIN_ROI_TARGET` within `SELLTHROUGH_HORIZON_DAYS`.
_Defaults: 1.25 over 60 days._

## Quickstart

```bash
# Python 3.11 recommended
pip install -U pip pre-commit
pre-commit install
# create .env from template and set KEEPA_KEY
cp infra/.env.example .env
```

## Stack

- **Backend:** Python 3.11, FastAPI, Postgres, DuckDB
- **Data:** Keepa API (primary), optional scrapers (low-trust)
- **ML:** scikit-learn, scipy (survival models), Monte Carlo optimization
- **Observability:** Sentry, Prometheus/Grafana, OpenTelemetry
- **CI/CD:** GitHub Actions, pre-commit hooks

## Decision Policy (env)

- `MIN_ROI_TARGET` (default 1.25)
- `SELLTHROUGH_HORIZON_DAYS` (default 60)
- `RISK_THRESHOLD` (default 0.80)
- `CASHFLOOR` (default 0)
- `HEADER_COVERAGE_MIN` (default 0.70) — minimum header coverage for manifest validation

## Data Sources

- Keepa API (Amazon price/rank/offer history)
- Optional scrapers (low-trust; behind `ENABLE_SCRAPERS=false` by default)
- Optional manual CSV imports for comps

## 60-Second Map Preview (Step 2)

```bash
# from repo root
python -m pip install -e backend
python -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv
# Optional: persist an alias if something didn't map
python -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv --save-alias "Cond." condition
```

**Show suggestions for unmapped headers**

```bash
python -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv --show-candidates --top-k 5
```

**Detect duplicate mappings**

```bash
# Show warnings if multiple source headers map to the same canonical field
python -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv --show-candidates
# Make it a hard failure (CI-friendly)
python -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv --fail-on-duplicates
```

## Validate Manifests (Step 3)

```bash
# Install backend once
python -m pip install -e backend

# Validate one file (JSON output)
python -m backend.cli.validate_manifest data/golden_manifests/01_basic.csv

# Validate the whole golden set
make validate-golden
# Validate only good files (skip bad manifests)
make validate-golden-good
```

**Validate a single file (strict)**

```bash
make validate FILE=data/golden_manifests/01_basic.csv
```

**Show human-friendly coverage in JSON**

```bash
python -m backend.cli.validate_manifest data/golden_manifests/01_basic.csv --show-coverage
```

## Parse → Clean → Explode (Step 4)

```bash
# From repo root
python -m pip install -e backend

# Run parser (map→clean→explode) and write CSV
python -m backend.cli.parse_clean backend/tests/fixtures/manifest_multiqty.csv --explode --out csv --output /tmp/lotgenius_exploded.csv

# JSON summary only (no file written)
python -m backend.cli.parse_clean backend/tests/fixtures/manifest_multiqty.csv --no-explode
```

## ID Resolution → ASIN (Step 5)

```bash
# From repo root
python -m pip install -e backend

# Set up your Keepa API key  # pragma: allowlist secret
export KEEPA_API_KEY="your_keepa_api_key_here"  # pragma: allowlist secret

# Resolve IDs for a test fixture
make resolve-test

# Resolve IDs for a custom CSV file
make resolve FILE=data/your_manifest.csv

# Alternatively, use the CLI directly
python -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv

# Custom output paths
python -m backend.cli.resolve_ids input.csv --output-csv enriched.csv --output-ledger evidence.jsonl

# Override API key via CLI  # pragma: allowlist secret
python -m backend.cli.resolve_ids input.csv --keepa-key your_key_here  # pragma: allowlist secret
```

**Features:**

- **Keepa Integration:** Uses UPC/EAN/ASIN to resolve canonical ASINs
- **Evidence Ledger:** JSONL audit trail for every resolution attempt
- **Caching:** SQLite-based cache with configurable TTL (default: 7 days)
- **Retry Logic:** Exponential backoff for rate limits and server errors
- **Fallback Strategy:** Title search stub (to be implemented in future steps)

## Next Steps

- ✅ Canonical schema & header mapping
- ✅ Golden manifests & Great Expectations
- ✅ Parser/cleaner with quantity explode
- ✅ Keepa client with caching & retries
- ✅ ID resolver with evidence ledger
- Ensemble pricing & survival models
- Monte Carlo optimizer with configurable gates

## Step 5 — ID Resolution (Keepa)

```bash
export KEEPA_API_KEY="sk_live_xxx"  # your key  # pragma: allowlist secret
# Dry run (no network):
python -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --no-network
# With Keepa:
python -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --network \
  --out-enriched data/out/resolved_enriched.csv \
  --out-ledger data/evidence/keepa_ledger.jsonl
```

Evidence ledger is JSONL; each record includes source, cached, and minimal payload summary.

- The summary now includes `source_counts`, e.g.:
  - `direct:asin` — rows that provided an ASIN in the manifest
  - `keepa:code:fresh` — UPC/EAN resolved via Keepa (fresh network hit)
  - `keepa:code:cached` — UPC/EAN resolved via Keepa (cache hit)
  - `fallback:*` — rows that didn't resolve yet (brand/model or title stub)
