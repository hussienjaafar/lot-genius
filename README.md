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
- ✅ Keepa stats enrichment (prices, rank, offers)
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

- To compress the evidence ledger as `.jsonl.gz`, use:
  ```bash
  python -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --network \
    --gzip-ledger \
    --out-enriched data/out/resolved_enriched.csv \
    --out-ledger data/evidence/keepa_ledger.jsonl
  # Output JSON will report the final .gz path
  ```

## Step 6 — Keepa Stats Enrichment

Extend the ID resolution pipeline with Keepa price/rank/offer statistics:

```bash
# Set your Keepa API key  # pragma: allowlist secret
export KEEPA_API_KEY="sk_live_xxx"  # pragma: allowlist secret

# Run with stats enrichment
python -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv \
  --network --with-stats \
  --out-enriched data/out/resolved_with_stats.csv \
  --out-ledger data/evidence/keepa_stats_ledger.jsonl

# Or use the Makefile shortcut
make resolve-with-stats
```

**Features:**

- **Stats Columns:** Adds `keepa_price_new_med`, `keepa_price_used_med`, `keepa_salesrank_med`, `keepa_offers_count` to output CSV
- **Evidence Ledger:** Creates `keepa:stats` records for audit trail of stats lookups
- **Dual Lookup:** Fetches stats by ASIN (preferred) or UPC/EAN code when ASIN unavailable
- **Compact Extraction:** Defensive parsing of Keepa stats payload with median values
- **Cache-Aware:** Uses separate cache keys for stats vs regular product lookups
- **Optional:** Only runs when `--with-stats` flag is provided

**Output Summary includes:**

- `with_stats`: boolean indicating if stats enrichment was requested
- `stats_columns_present`: list of stats columns that were added to the output CSV
- Price medians are auto-normalized from cents when detected; a `scaled_from_cents` boolean is recorded in the ledger's `keepa:stats.meta.compact`.
- CLI summary includes `with_stats_requested`, `with_stats`, and `stats_reason` to clarify when stats were requested but skipped (e.g., `--no-network`).

## Step 7 — Price Estimation (Ensemble)

Compute per-item price distributions using available sources (Keepa today), with inverse-variance weighting and source priors.

```bash
# Input: enriched CSV from Step 6 (has keepa_* columns)
python -m backend.cli.estimate_price data/out/resolved_with_stats.csv \
  --cv-fallback 0.20 \
  --prior-keepa 0.50 --prior-ebay 0.35 --prior-other 0.15 \
  --out-csv data/out/estimated_prices.csv \
  --ledger-out data/evidence/price_ledger.jsonl

# Or use the Makefile shortcut
make estimate-prices
```

**New columns:**

- `est_price_mu`, `est_price_sigma`, `est_price_p5`, `est_price_p50`, `est_price_p95`
- `est_price_sources` (JSON array with per-source μ, cv, n, prior, recency, weight)

**Notes:**

- Currently uses Keepa medians (new vs used) and offers as a strength proxy
- CV fallback defaults to 0.20; adjust per category once you have richer data
- Percentiles use a normal approximation and are clipped at 0
- Condition-aware: prefers `new` median for New/Like-New items, `used` median otherwise

## Step 7.1 — Category Floors & Price Evidence (Conservative Pricing)

Apply conservative floors to P5 estimates using category priors and export compact price evidence for UI consumption.

```bash
# Input: enriched CSV from Step 6 (has keepa_* columns)
python -m backend.cli.estimate_price data/out/resolved_with_stats.csv \
  --cv-fallback 0.20 \
  --prior-keepa 0.50 --prior-ebay 0.35 --prior-other 0.15 \
  --out-csv data/out/estimated_prices_floored.csv \
  --ledger-out data/evidence/price_ledger_floored.jsonl \
  --category-priors backend/lotgenius/data/category_priors.example.json \
  --salvage-floor-frac 0.10 \
  --price-evidence-out data/out/price_evidence.ndjson \
  --gzip-evidence

# Or use the Makefile shortcut
make estimate-prices-with-floors
```

**New columns:**

- `est_price_p5_floored` — P5 after applying conservative floor (if any)
- `est_price_floor_rule` — Which floor rule was applied ("category_abs", "category_frac", "salvage", null)
- `est_price_category` — Category detected from row (used for floor lookup)

**Category Priors Schema:**

```json
{
  "Electronics": {
    "p20_floor_abs": 5.0,
    "p20_floor_frac_of_mu": 0.15
  },
  "Books": {
    "p20_floor_abs": null,
    "p20_floor_frac_of_mu": 0.1
  }
}
```

**Features:**

- **Category-based floors:** Uses category priors JSON to apply absolute or μ-fraction floors
- **Salvage floor:** Optional fallback floor as fraction of μ (e.g., 0.10 = 10%)
- **Conservative logic:** Applies highest available floor when P5 falls below
- **Compact evidence export:** NDJSON with essential price data for fast UI reads
- **Backward compatible:** All new columns/flags are optional

**Price Evidence NDJSON Schema:**

| Field                  | Type         | Description                                                           |
| ---------------------- | ------------ | --------------------------------------------------------------------- |
| `row_index`            | int          | Zero-based row index from input CSV                                   |
| `sku_local`            | string\|null | Local SKU identifier                                                  |
| `asin`                 | string\|null | Amazon ASIN (if available and valid)                                  |
| `est_price_mu`         | float\|null  | Price estimate μ (mean)                                               |
| `est_price_sigma`      | float\|null  | Price estimate σ (std deviation)                                      |
| `est_price_p5`         | float\|null  | 5th percentile estimate                                               |
| `est_price_p5_floored` | float\|null  | P5 after applying conservative floor                                  |
| `est_price_floor_rule` | string\|null | Applied floor rule ("category_abs", "category_frac", "salvage", null) |
| `est_price_category`   | string\|null | Category used for floor lookup ("default" if fallback)                |
| `sources`              | array        | Parsed price sources with weights and metadata                        |

## Step 8 — Sell-through ≤60 days (proxy survival)

Compute per-item P(sold ≤ 60d) "p60" using a conservative, explainable proxy survival model derived from:

- Keepa rank (if present) → daily sales via power-law mapping
- Offers saturation (Keepa offers count)
- Price-to-market z-score using our estimated μ, σ and a chosen list price

```bash
# Input: enriched CSV from Step 7 (has est_price_* columns)
python -m backend.cli.estimate_sell data/out/estimated_prices.csv \
  --out-csv data/out/estimated_sell.csv \
  --evidence-out data/evidence/sell_evidence.jsonl \
  --days 60 --list-price-mode p50 --list-price-multiplier 1.0 \
  --baseline-daily-sales 0.00  # fallback daily market sales when rank is missing

# Or use the Makefile shortcut
make estimate-sell
```

**New columns:**

- `sell_p60` — probability item sells within the horizon (default 60d)
- `sell_hazard_daily` — per-item daily hazard λ used in survival calc
- `sell_ptm_z` — price-to-market z-score at chosen list price
- `sell_rank_used` — sales rank used (if available)
- `sell_offers_used` — offers count used for saturation

**Tuning knobs:**

- `--beta-price` (default 0.8): sensitivity of hazard to price premium via exp(-β·z))
- `--hazard-cap` (default 1.0): upper bound for daily hazard λ
- `--baseline-daily-sales` (default 0.00): nonzero fallback market sales when rank is missing
- `--rank-to-sales`: path to JSON power-law mapping (see backend/lotgenius/data/rank_to_sales.example.json)

**Features:**

- **Rank→sales power law:** Configurable via `backend/lotgenius/data/rank_to_sales.example.json`
- **Offers saturation:** Higher offer count reduces per-item sell probability
- **Price sensitivity:** Higher prices reduce sell probability via exp(-β·z) factor
- **Evidence export:** NDJSON with all inputs & parameters for transparency
- **Conservative defaults:** Tunable coefficients for different risk profiles

**Configuration:**

The rank-to-sales mapping uses power law: `daily_sales = a * rank^b`, bounded by min/max rank limits.

**Notes:**

This is a scaffold; coefficients are tunable. Later steps will calibrate from backtests (isotonic reliability curves & Brier score).

No hard-coded ROI logic here; the optimizer will consume `sell_p60` downstream.

## Step 9 — Lot ROI & Max-Bid Optimizer (Monte Carlo + Bisection)

Takes enriched, per-unit CSV with `est_price_mu`, `est_price_sigma`, and `sell_p60`. Simulates revenue under fees/costs, then finds the highest bid s.t. **P(ROI ≥ roi_target) ≥ risk_threshold** (and optional **expected cash ≤60d ≥ min_cash_60d**).

**ROI = total revenue (sold net + salvage) / (bid + optional lot fixed cost)**

**Run:**

```bash
python -m backend.cli.optimize_bid data/out/estimated_sell.csv \
  --out-json data/out/optimize_bid.json \
  --lo 0 --hi 5000 \
  --roi-target 1.25 --risk-threshold 0.80 \
  --sims 2000

# Or use the Makefile shortcut
make optimize-bid
```

**Knobs:**

- `--salvage-frac` (default 0.50): salvage as fraction of drawn price for unsold
- `--marketplace-fee-pct`, `--payment-fee-pct`, `--per-order-fee-fixed`
- `--shipping-per-order`, `--packaging-per-order`, `--refurb-per-order`
- `--return-rate` (default 0.08)
- `--min-cash-60d` (optional cash recovery constraint)
- `--min-cash-60d-p5` (optional P5 cash recovery constraint for VaR)
- `--lot-fixed-cost` (default 0.0): fixed cost added to bid in ROI denominator
- `--include-samples/--no-include-samples` (default --no-include-samples): include raw simulation arrays in JSON output

Random seed & tolerance controllable.

`cash_60d_p5` available for risk-aware cash constraints via `--min-cash-60d-p5`.

**NOTE:** ROI target is configurable (not hard-coded). Defaults reflect your "≥1.25× within ~60 days" minimum.
