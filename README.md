# Lot Genius

Decision-ready bidding for liquidation lots from messy manifests.

## Overview

Lot Genius transforms complex B-Stock manifest CSVs into actionable investment decisions through automated analysis of product pricing, sell-through probability, and ROI optimization.

**Core Features:**

- **Intelligent parsing**: Handles varied manifest formats with header mapping and validation
- **ID resolution**: Preserves original ASIN/UPC/EAN fields with UPC-A check digit validation
- **Confidence-aware evidence gating**: Adaptive quality thresholds based on data ambiguity
- **Price estimation**: Multi-source ensemble pricing with conservative floors
- **Survival modeling**: 60-day sell-through probability using market data
- **ROI optimization**: Monte Carlo simulation with configurable risk thresholds
- **Calibration tracking**: JSONL logging with outcomes analysis
- **Web interface**: Next.js frontend with real-time progress streaming and upload modes
- **Windows compatibility**: UTF-8 file I/O and ASCII-safe console output

```mermaid
graph TB
    A[Raw Manifest CSV] --> B[Parse & Clean]
    B --> C[ID Resolution]
    C --> D[Price Estimation]
    D --> E[Sell-through Modeling]
    E --> F[ROI Optimization]
    F --> G[Decision Report]

    H[Keepa API] --> C
    H --> D
    I[Category Priors] --> D
    J[Survival Models] --> E
    K[Risk Constraints] --> F
```

**Investment Gate:** Only recommend bids satisfying ROI >= `roi_target` (default 1.25×) within `horizon_days` (default 60) at `risk_threshold` confidence (default 80%).

## Try It Now

### Quick Demo (No Setup Required)

Download the demo bundle for a guided introduction:

- **[Latest Demo Bundle](https://github.com/your-org/lot-genius/releases/latest/download/lotgenius_demo.zip)** - Self-contained demo with sample data
- **[Getting Started Guide](docs/GETTING_STARTED.md)** - Two quick paths: mock frontend demo & CLI report generation

### Live Demo Options

1. **Mock Frontend Demo**: Experience the full UI with `NEXT_PUBLIC_USE_MOCK=1`
2. **CLI Report Generation**: Generate analysis reports from command line using sample data

Both options work offline and include sample manifests with varied data quality scenarios.

## Quickstart

### Backend Setup (Windows)

```cmd
# Install Python 3.13 and create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -U pip pre-commit
pip install -e backend
pre-commit install

# Configure environment (optional for CLI usage)
copy infra\.env.example .env
# Edit .env and set KEEPA_API_KEY=your_key_here for API access

# Windows encoding support (optional)
set PYTHONUTF8=1
chcp 65001
```

### Frontend Setup

```cmd
cd frontend
npm install
npm run dev
# Visit http://localhost:3000
```

**Upload Modes:**

- **Proxy Mode** (default): Uses Next.js API route `/api/pipeline/upload/stream`
- **Direct Mode**: Connects directly to FastAPI backend `/v1/pipeline/upload/stream`

**Environment Variables:**

```cmd
# For direct backend mode
set NEXT_PUBLIC_BACKEND_URL=http://localhost:8787
set NEXT_PUBLIC_API_KEY=your_secret_key_here
```

### CLI Quick Start

```cmd
# Analyze a manifest CSV end-to-end
python -m backend.cli.report_lot data\samples\minimal.csv ^
  --opt-json data\samples\opt.json ^
  --out-markdown reports\lot_report.md

# Run calibration analysis
python -m backend.cli.calibration_report ^
  data\calibration\predictions.jsonl ^
  data\calibration\outcomes.csv ^
  --out-json reports\calibration_report.json
```

### API Server

```cmd
# Start FastAPI server
uvicorn backend.app.main:app --port 8787 --reload

# Optional: Set API key for authentication
set LOTGENIUS_API_KEY=your_secret_key_here

# Test endpoint
curl http://localhost:8787/healthz

# Test with API key (if set)
curl -H "X-API-Key: your_secret_key_here" http://localhost:8787/v1/optimize
```

## Architecture

- **Backend:** Python 3.13, FastAPI, scikit-learn, scipy
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Data Sources:** Keepa API (primary), manifest CSVs
- **Storage:** SQLite (caching), JSONL (audit trails)
- **ML/Stats:** Monte Carlo simulation, survival analysis, price ensembles

**Key Modules:**

- `lotgenius.parsing` - Manifest header mapping and validation
- `lotgenius.pricing` - Multi-source price estimation with floors
- `lotgenius.survivorship` - Sell-through probability modeling
- `lotgenius.roi` - Monte Carlo ROI optimization
- `lotgenius.calibration` - Prediction logging and outcomes analysis

## Environment Configuration

**Required:**

- `KEEPA_API_KEY` - Your Keepa API key for product data

**Key Settings:**

- `SELLTHROUGH_HORIZON_DAYS` (default 60) - Sell-through time window
- `MIN_ROI_TARGET` (default 1.25) - Minimum ROI threshold
- `RISK_THRESHOLD` (default 0.80) - Risk tolerance (80% confidence)
- `CASHFLOOR` (default 0) - Minimum cash recovery constraint
- `HEADER_COVERAGE_MIN` (default 0.70) - Manifest validation threshold
- `SURVIVAL_MODEL` (default "ladder") - Survival model variant ("ladder", "default")

**Evidence Gating (Confidence-Aware):**

- `EVIDENCE_MIN_COMPS_BASE` (default 3) - Base minimum sold comparables
- `EVIDENCE_AMBIGUITY_BONUS_PER_FLAG` (default 1) - Extra comps required per ambiguity flag
- `EVIDENCE_MIN_COMPS_MAX` (default 5) - Maximum required comparables cap
- `EVIDENCE_LOOKBACK_DAYS` (default 180) - Comp search window
- `EVIDENCE_REQUIRE_SECONDARY` (default true) - Require rank/offer signals

**Scraper Configuration:**

- `SCRAPER_SIMILARITY_MIN` - Minimum similarity threshold for query results
- `PRICE_OUTLIER_K` (default 3.5) - MAD K-factor for price outlier detection

## Testing

**Run targeted tests (recommended):**

```cmd
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest -q backend\tests\test_roi_mc.py
python -m pytest backend\tests\test_calibration_log.py -v
```

**Common pytest patterns:**

```cmd
# Quick smoke tests
python -m pytest backend\tests\test_api_*.py -q

# Specific module with coverage
python -m pytest backend\tests\test_survivorship_*.py --cov=lotgenius.survivorship

# Integration tests (requires KEEPA_API_KEY)
python -m pytest backend\tests\test_*_integration.py -v
```

## Documentation

📖 **[Complete Documentation](docs/INDEX.md)**

- **[Architecture Guide](docs/architecture.md)** - System design and data flow
- **[API Reference](docs/backend/api.md)** - HTTP endpoints and schemas
- **[CLI Commands](docs/backend/cli.md)** - Command-line tools and examples
- **[ROI & Optimization](docs/backend/roi.md)** - Simulation parameters and constraints
- **[Calibration Guide](docs/backend/calibration.md)** - Logging and outcomes analysis
- **[Frontend Components](docs/frontend/ui.md)** - UI components and SSE streaming
- **[Windows Encoding Guide](docs/operations/windows-encoding.md)** - Windows compatibility and UTF-8 setup
- **[Operational Runbooks](docs/operations/runbooks/)** - Step-by-step procedures
- **[Validation Guide](docs/operations/runbooks/validation.md)** - E2E testing and validation

**Gap Fix Run Logs:**

- [Gap Fix 01: Header Mapping](multi_agent/runlogs/gapfix_01_header_mapping.md)
- [Gap Fix 02: UPC Check Digit](multi_agent/runlogs/gapfix_02_upc_check_digit.md)
- [Gap Fix 03: ID Resolution Ledger](multi_agent/runlogs/gapfix_03_id_resolution_ledger.md)
- [Gap Fix 04: Frontend Upload](multi_agent/runlogs/gapfix_04_frontend_upload.md)
- [Gap Fix 05: Scraper Query Filtering](multi_agent/runlogs/gapfix_05_scraper_query_filtering.md)
- [Gap Fix 06: Confidence Gating](multi_agent/runlogs/gapfix_06_confidence_gating.md)
- [Gap Fix 07: E2E Validation](multi_agent/runlogs/gapfix_07_e2e_validation.md)
- [Gap Fix 08: Windows Encoding](multi_agent/runlogs/gapfix_08_windows_encoding.md)

## Key Features Detail

### ID Resolution and Precedence

**Field Preservation:** Original `asin`, `upc`, `ean` fields are preserved; `upc_ean_asin` is populated using precedence: asin > upc > ean.

**Resolver Precedence:** Resolution engine uses: asin > upc (valid check digit) > ean > upc_ean_asin.

**UPC-A Validation:** UPC codes are validated using check digit algorithm before resolution.

**Evidence Ledger:** All resolution attempts logged with `identifier_source`, `identifier_type`, `identifier_used` metadata.

### Confidence-Aware Evidence Gating

**Adaptive Thresholds:** Evidence requirements increase based on data quality:

- **Clean items**: 3 sold comps + secondary signals (base threshold)
- **Ambiguous items**: Up to 5 sold comps based on ambiguity flags:
  - `generic:title` - Contains generic terms (bundle, lot, damaged, etc.)
  - `ambiguous:brand` - Missing or empty brand information
  - `ambiguous:condition` - Unknown or unspecified condition

**High-trust ID Bypass:** Items with confident ASIN/UPC/EAN matches bypass evidence gates.

### Scraper Query Strategy

**Query Priority:**

1. Exact UPC lookup
2. Exact ASIN lookup
3. "Brand" "Model" targeted search
4. Filtered title fallback

**Quality Filtering:** Similarity matching, recency filters, model validation, condition filtering, and price outlier detection (MAD K=3.5).

## Legacy CLI Examples

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
- `--include-samples/--no-include-samples` (default off): include raw Monte Carlo arrays in JSON output (can make JSON large for big --sims)

Random seed & tolerance controllable.

`cash_60d_p5` available for risk-aware cash constraints via `--min-cash-60d-p5`.

Optimizer JSON is compact by default (no per-simulation arrays). Use `--include-samples` to include `roi`, `revenue`, and `cash_60d` arrays; files may be large for big `--sims`.

**NOTE:** ROI Target is configurable (not hard-coded). Defaults reflect your "≥1.25× within ~60 days" minimum.

### Niceties (Step 9.1)

- **Bid sweep**: generate `sweep_bid.csv` with columns:
  `bid, prob_roi_ge_target, roi_p5, roi_p50, roi_p95, expected_cash_60d, cash_60d_p5, meets_constraints`.

  ```bash
  python -m backend.cli.sweep_bid data/out/estimated_sell.csv \
    --out-csv data/out/sweep_bid.csv --lo 0 --hi 5000 --step 100 \
    --roi-target 1.25 --risk-threshold 0.80 --sims 1000
  ```

- **Optimizer evidence**: one-line NDJSON for audit:

  ```bash
  python -m backend.cli.optimize_bid ... --evidence-out data/evidence/optimize_evidence.jsonl
  ```

- **Join recommended bid**: produce a single-row lot summary or broadcast to items:
  ```bash
  python -m backend.cli.join_bid --items-csv data/out/estimated_sell.csv \
    --opt-json data/out/optimize_bid.json --out-csv data/out/lot_summary.csv --mode one-row
  ```

**Notes**: Arrays are compact by default (`--include-samples` to embed them). Sweep runs the same feasibility check as the optimizer across a grid of bids.

**Quick visualization (optional)**
Turn `sweep_bid.csv` into a simple chart (requires `matplotlib`):

```bash
python - <<'PY'
import pandas as pd, matplotlib.pyplot as plt
df = pd.read_csv("data/out/sweep_bid.csv")
ax = df.plot(x="bid", y="prob_roi_ge_target", legend=False)
ax.set_ylabel("P(ROI ≥ target)")
ax2 = ax.twinx()
df.plot(x="bid", y="roi_p50", ax=ax2, legend=False, style="--")
ax2.set_ylabel("ROI P50")
plt.title("Lot Genius — Bid sensitivity")
plt.savefig("data/out/sweep_bid.png", dpi=150, bbox_inches="tight")
print("Wrote data/out/sweep_bid.png")
PY
```

(Optional) Makefile helper:

```make
plot-sweep:
\tpython - <<'PY'
import pandas as pd, matplotlib.pyplot as plt
df = pd.read_csv("data/out/sweep_bid.csv")
ax = df.plot(x="bid", y="prob_roi_ge_target", legend=False)
ax.set_ylabel("P(ROI ≥ target)")
ax2 = ax.twinx()
df.plot(x="bid", y="roi_p50", ax=ax2, legend=False, style="--")
ax2.set_ylabel("ROI P50")
plt.title("Lot Genius — Bid sensitivity")
plt.savefig("data/out/sweep_bid.png", dpi=150, bbox_inches="tight")
print("Wrote data/out/sweep_bid.png")
PY
```

## Step 9.2 — Mini-Report Generator (Concise Decision Report)

Generate a concise, decision-ready Markdown report that consolidates per-unit analysis and optimizer results into an executive summary. Optionally produces HTML and PDF outputs.

**GOAL:** Produce a concise Lot Genius report that:

- Reads per-unit items CSV (from Step 8 output) and optimizer JSON (from Step 9)
- Emits a Markdown report (always). Optionally also HTML and PDF.
- Optionally references the sweep CSV/PNG and optimizer evidence NDJSON.

If `meets_constraints` is absent, the report shows **N/A** and sets decision to **🟡 REVIEW**. **ROI Target** / **Risk Threshold** are taken from `opt.json` or, if missing, from the last record in `--evidence-jsonl` (only when the file is provided and exists). "Supporting Artifacts" are included only when the referenced files exist. The "Optimization Parameters" section always appears with N/A fallbacks when values are missing.

```bash
# Generate markdown report with artifact references
python -m backend.cli.report_lot \
  --items-csv data/out/estimated_sell.csv \
  --opt-json data/out/optimize_bid.json \
  --out-markdown data/out/lot_report.md \
  --sweep-csv data/out/sweep_bid.csv \
  --sweep-png data/out/sweep_bid.png \
  --evidence-jsonl data/evidence/optimize_evidence.jsonl

# With optional HTML output (requires pandoc)
python -m backend.cli.report_lot \
  --items-csv data/out/estimated_sell.csv \
  --opt-json data/out/optimize_bid.json \
  --out-markdown data/out/lot_report.md \
  --out-html data/out/lot_report.html

# With optional PDF output (requires pandoc + LaTeX)
python -m backend.cli.report_lot \
  --items-csv data/out/estimated_sell.csv \
  --opt-json data/out/optimize_bid.json \
  --out-markdown data/out/lot_report.md \
  --out-pdf data/out/lot_report.pdf

# Or use the Makefile shortcut
make report-lot
```

**Report Structure:**

- **Executive Summary:** Recommended bid, ROI, probability of success, 60-day cash recovery
- **Lot Overview:** Item count, total estimated value, average sell-through probability
- **Optimization Parameters:** ROI Target, Risk Threshold
- **Investment Decision:** Clear proceed/pass recommendation with reasoning
- **Supporting Artifacts:** References to sweep analysis, charts, and audit trails (if provided)

**Contents:**

- Now always shows 'Meets constraints' as Yes/No/N/A
- ROI Target and Risk Threshold are highlighted near the top when present

**Features:**

- **Decision-focused:** Clear proceed/pass recommendation based on constraint satisfaction
- **Defensive formatting:** Handles missing data gracefully with "N/A" fallbacks
- **Artifact linking:** Optional references to sweep CSV/PNG and evidence JSONL
- **Multi-format output:** Markdown (always), HTML/PDF (optional, requires pandoc)
- **Concise format:** Designed for executive consumption, not exhaustive technical detail

**Notes:**

- HTML/PDF conversion requires `pandoc` to be installed
- PDF conversion additionally requires LaTeX (e.g., `pdflatex`)
- If pandoc is unavailable, conversion is skipped with a warning (markdown is always generated)
- Report focuses on investment decision; detailed technical analysis is available in referenced artifacts
- Report now renders Meets All Constraints as Yes/No/N/A when missing, and wires ROI Target/Risk Threshold from optimizer JSON (or evidence NDJSON if provided)

## Step 10 — FastAPI Report API (Experimental)

Expose the existing lot report generator as an HTTP API with basic streaming progress events.

**Start the API server:**

```bash
# Start development server
make api
# Or directly:
uvicorn backend.app.main:app --reload --port 8787
```

**CORS:** Configured for localhost origins by default.

**Security:** If `LOTGENIUS_API_KEY` environment variable is set, requests must include `X-API-Key` header. Otherwise, API is open.

**Endpoints:**

- `GET /healthz` → Health check
- `POST /v1/report` → Generate report (blocking)
- `POST /v1/report/stream` → Generate report with SSE progress events

**Blocking report generation:**

```bash
curl -X POST http://localhost:8787/v1/report \
  -H 'Content-Type: application/json' \
  -d '{
    "items_csv": "data/out/estimated_sell.csv",
    "opt_json_path": "data/out/optimize_bid.json",
    "out_markdown": "data/out/api_report.md"
  }'
```

**Streaming report generation:**

```bash
curl -N -X POST http://localhost:8787/v1/report/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "items_csv": "data/out/estimated_sell.csv",
    "opt_json_path": "data/out/optimize_bid.json"
  }'
```

**Using inline optimizer JSON:**

```bash
curl -X POST http://localhost:8787/v1/report \
  -H 'Content-Type: application/json' \
  -d '{
    "items_csv": "data/out/estimated_sell.csv",
    "opt_json_inline": {"bid": 100.0, "roi_target": 1.25, "meets_constraints": true}
  }'
```

**Response format:**

```json
{
  "status": "ok",
  "markdown_path": "data/out/api_report.md",
  "html_path": null,
  "pdf_path": null,
  "markdown_preview": "# Lot Genius Report\n\n## Executive Summary..."
}
```

**Streaming events:**

- `start` — Validated inputs
- `generate_markdown` — Markdown generation complete
- `html` — HTML conversion (if requested)
- `pdf` — PDF conversion (if requested)
- `done` — All processing complete

**Features:**

- **Direct Python calls:** No subprocess overhead; imports report_lot functions directly
- **File validation:** Checks existence of items_csv, opt_json_path, evidence_jsonl
- **Temporary files:** Inline JSON data written to `data/api/tmp/` with cleanup
- **Progress streaming:** Server-Sent Events for real-time progress updates
- **Preview included:** Response includes truncated markdown content for quick review
- **HTML/PDF support:** Reuses existing pandoc conversion utilities from CLI

**Notes:**

- API reuses all existing business logic from `lotgenius.cli.report_lot`
- Report content matches CLI output for identical inputs
- No eBay usage; maintains Keepa-only constraints
- HTML/PDF conversion requires pandoc (same as CLI)

### Optimizer API

**Blocking:**

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -X POST http://localhost:8787/v1/optimize \
  -H 'Content-Type: application/json' \
  -d '{
        "items_csv":"data/samples/minimal.csv",
        "opt_json_inline":{"lo":0,"hi":1000,"roi_target":1.25,"risk_threshold":0.80}
      }' | jq .
```

**Note**: Optimization only supports blocking requests. Use pipeline upload stream for SSE progress.

### Pipeline API (end-to-end)

**Blocking:**

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -X POST http://localhost:8787/v1/report \
  -H 'Content-Type: application/json' \
  -d '{
        "items_csv":"data/samples/minimal.csv",
        "opt_json_inline":{"lo":0,"hi":1000,"roi_target":1.25,"risk_threshold":0.80}
      }' | jq .
```

**Streaming:**

```bash
curl -N -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -X POST http://localhost:8787/v1/report/stream \
  -H 'Content-Type: application/json' \
  -d '{"items_csv":"data/samples/minimal.csv","opt_json_inline":{"lo":0,"hi":1000,"roi_target":1.25,"risk_threshold":0.80}}'
```

### Upload Endpoints

For web clients that need to upload files directly instead of using server paths:

**Note:** Either `opt_json` (file) or `opt_json_inline` (JSON string) is required.

**Blocking (pipeline):**

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json=@data/samples/opt.json \
  http://localhost:8787/v1/pipeline/upload | jq .
```

**Streaming (pipeline):**

```bash
curl -N -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json=@data/samples/opt.json \
  http://localhost:8787/v1/pipeline/upload/stream
```

**Blocking (optimizer):**

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json=@data/samples/opt.json \
  http://localhost:8787/v1/optimize/upload | jq .
```

**Note**: Optimizer upload only supports blocking requests. Use pipeline upload stream for SSE progress.

**With inline optimizer config:**

Blocking optimizer:

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json_inline='{"bid":100,"risk_threshold":0.8}' \
  http://localhost:8787/v1/optimize/upload | jq .
```

Streaming pipeline with inline:

```bash
curl -N -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json_inline='{"bid":100}' \
  http://localhost:8787/v1/pipeline/upload/stream
```

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json_inline='{"lo":0,"hi":1000,"roi_target":1.25,"risk_threshold":0.80,"sims":100}' \
  http://localhost:8787/v1/pipeline/upload | jq .
```

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json_inline='{"lo":0,"hi":1000,"roi_target":1.25,"risk_threshold":0.80,"sims":100}' \
  http://localhost:8787/v1/optimize/upload | jq .
```

**With output files:**

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/minimal.csv \
  -F opt_json=@data/samples/opt.json \
  -F out_markdown=/tmp/report.md \
  http://localhost:8787/v1/pipeline/upload | jq .
```

**Features:**

- Accepts `multipart/form-data` uploads via `-F` flag
- Same security validation as path-based endpoints
- Temporary files auto-deleted after processing
- Optional output file paths (validated for security)
- Same response structure as existing endpoints

## Path Safety

Lot Genius validates all user-supplied file paths:

- **Allowed roots:** the repo/workdir and the system temp directory
  (Linux/macOS: `/tmp`/`/private/tmp`; Windows: `%TEMP%`).
- **Early rejection across platforms:** Windows drive/UNC patterns
  (e.g., `C:\Windows\…`, `\\server\share\…`) are blocked even on non-Windows hosts.
- **Sensitive prefixes blocked:** `/etc`, `/root`, device/proc/sys dirs, `C:\Windows`, `C:\Program Files`, etc.
- **Fail-closed:** absolute paths outside allowed roots return **HTTP 400**.

Use temp files for programmatic runs in tests/CI:

```bash
TMPDIR=$(mktemp -d)
python - << 'PY'
from pathlib import Path; import json, pandas as pd, os
p = Path(os.environ["TMPDIR"])
items = p/"items.csv"; opt = p/"opt.json"
pd.DataFrame([{"sku_local":"A"}]).to_csv(items, index=False)
opt.write_text(json.dumps({"bid":100}), encoding="utf-8")
print(items, opt)
PY
```

### Suppressing Noisy Runtime Warnings

By default, the API process installs a tiny warning filter to hide a benign
`ddtrace … vmstat` `RuntimeWarning` that can appear in some containers.

Control via env (on by default):

```bash
# enable (default)
export LOTGENIUS_SUPPRESS_NOISY_WARNINGS=1

# disable (show everything)
export LOTGENIUS_SUPPRESS_NOISY_WARNINGS=0
```

This does not affect pytest (which already filters these in pytest.ini).
