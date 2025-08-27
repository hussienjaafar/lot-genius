# API Reference

FastAPI server exposing lot optimization and report generation endpoints with streaming progress support.

## Server Setup

```cmd
# Start development server
uvicorn backend.app.main:app --port 8787 --reload

# Production mode
uvicorn backend.app.main:app --host 0.0.0.0 --port 8787
```

**Base URL**: `http://localhost:8787`

## Authentication

API key authentication via environment variable (optional):

```cmd
set LOTGENIUS_API_KEY=your_secret_key_here
```

When set, all requests must include:

```http
X-API-Key: your_secret_key_here
```

## CORS Configuration

The backend allows the following origins in development:

- `http://localhost:3000` (Next.js frontend default)
- `http://localhost:3001` (Alternative frontend port)

Configured via `CORSMiddleware` in FastAPI application.

## ID Resolution and Evidence Processing

### Resolver Precedence

The ID resolution system uses the following precedence order:

1. **direct:asin** - Items with explicit ASIN values in manifest
2. **keepa:code** - UPC/EAN resolution via Keepa API (with valid UPC-A check digit)
3. **keepa:code** - EAN resolution via Keepa API
4. **upc_ean_asin** - Fallback composite field

### Evidence Ledger Metadata

All resolution attempts include metadata in JSONL evidence logs:

- `identifier_source` - Resolution method ("direct:asin", "keepa:code", etc.)
- `identifier_type` - ID type used ("asin", "upc", "ean")
- `identifier_used` - Actual identifier value used for resolution

### Confidence-Aware Evidence Gating

Evidence requirements adapt based on data quality:

**Base Requirements:** 3 sold comparables + secondary signals (rank/offers)

**Ambiguity Adjustments:** +1 comp required per flag, capped at 5 total

- `generic:title` - Title contains generic terms (bundle, lot, damaged, etc.)
- `ambiguous:brand` - Missing or empty brand information
- `ambiguous:condition` - Unknown or unspecified condition

**Configuration:**

- `EVIDENCE_MIN_COMPS_BASE`: Base comp requirement (default 3)
- `EVIDENCE_AMBIGUITY_BONUS_PER_FLAG`: Extra comps per flag (default 1)
- `EVIDENCE_MIN_COMPS_MAX`: Maximum comp requirement (default 5)

### Caching Behavior

- **SQLite cache**: 7-day TTL for Keepa lookups (configurable)
- **Separate cache keys**: Product lookups vs stats lookups
- **Cache bypass**: High-trust IDs (confident ASIN matches) bypass evidence gates
- **eBay scraper cache**: Result caching with deterministic fingerprinting
- **Cache metrics**: Optional performance tracking with hit/miss ratios

## Core Endpoints

### Health Check

```http
GET /healthz
```

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Report Generation (End-to-End)

Generate decision reports from items CSV with optimization.

#### Blocking Request

```http
POST /v1/report
Content-Type: application/json
X-API-Key: your_api_key

{
  "items_csv": "data/samples/manifest.csv",
  "opt_json_path": "data/samples/optimizer.json",
  "out_markdown": "reports/lot_report.md"
}
```

#### Streaming Request

```http
POST /v1/report/stream
Content-Type: application/json
X-API-Key: your_api_key

{
  "items_csv": "data/samples/manifest.csv",
  "opt_json_inline": {
    "roi_target": 1.25,
    "risk_threshold": 0.80,
    "sims": 2000
  }
}
```

**SSE Events:**

- `start` - Processing initiated
- `generate_markdown` - Markdown generation complete
- `html` - HTML conversion (if requested)
- `pdf` - PDF conversion (if requested)
- `done` - All processing complete
- `error` - Processing failed

### Pipeline Upload Stream

Complete manifest analysis pipeline with file upload: parse + enrich + price + optimize + report.

```http
POST /v1/pipeline/upload/stream
Content-Type: multipart/form-data
X-API-Key: your_api_key

items_csv=@manifest.csv
opt_json_inline={"roi_target": 1.25, "risk_threshold": 0.80}
```

**SSE Events:**

- `start` - Processing initiated
- `parse` - Manifest parsing complete
- `validate` - Validation complete
- `enrich_keepa` - ID resolution complete
- `price` - Price estimation complete
- `sell` - Sell-through modeling complete
- `optimize` - ROI optimization complete
- `render_report` - Report generation complete
- `ping` - Keep-alive signals
- `done` - Processing finished

**Curl Example:**

```bash
curl -N -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/manifest.csv \
  -F opt_json_inline='{"roi_target": 1.3, "sims": 1000}' \
  http://localhost:8787/v1/pipeline/upload/stream
```

### Optimization Only

ROI optimization without full pipeline (requires pre-processed CSV).

#### Blocking Request

```http
POST /v1/optimize
Content-Type: application/json
X-API-Key: your_api_key

{
  "items_csv": "data/processed/estimated_sell.csv",
  "opt_json_inline": {
    "roi_target": 1.25,
    "risk_threshold": 0.80,
    "lo": 0,
    "hi": 5000,
    "sims": 2000
  }
}
```

#### Upload Variants

For web clients uploading files:

**Blocking Upload**:

```bash
curl -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/processed.csv \
  -F opt_json=@configs/optimizer.json \
  http://localhost:8787/v1/optimize/upload
```

**Streaming Upload**:

```bash
curl -N -H "X-API-Key: $LOTGENIUS_API_KEY" \
  -F items_csv=@data/samples/processed.csv \
  -F opt_json_inline='{"roi_target": 1.25, "sims": 2000}' \
  http://localhost:8787/v1/optimize/upload/stream
```

## Request Schemas

### Pipeline Request

```json
{
  "items_csv": "string", // Required: path to manifest CSV
  "opt_json_path": "string", // Optional: path to optimizer JSON
  "opt_json_inline": {
    // Optional: inline optimizer config
    "roi_target": 1.25,
    "risk_threshold": 0.8,
    "sims": 2000,
    "lo": 0,
    "hi": 5000,
    "calibration_log_path": "string" // Optional: prediction logging
  },
  "out_markdown": "string", // Optional: output report path
  "out_html": "string", // Optional: HTML output path
  "out_pdf": "string" // Optional: PDF output path
}
```

### Optimizer Configuration

```json
{
  "roi_target": 1.25, // ROI threshold (e.g., 1.25 = 25% return)
  "risk_threshold": 0.8, // Confidence level (80%)
  "lo": 0, // Minimum bid to consider
  "hi": 5000, // Maximum bid to consider
  "sims": 2000, // Monte Carlo simulations
  "salvage_frac": 0.5, // Salvage value as fraction of price
  "marketplace_fee_pct": 0.13, // Marketplace fee percentage
  "payment_fee_pct": 0.029, // Payment processing fee
  "per_order_fee_fixed": 0.3, // Fixed fee per order
  "shipping_per_order": 8.5, // Shipping cost per order
  "packaging_per_order": 1.0, // Packaging cost per order
  "refurb_per_order": 5.0, // Refurbishment cost per order
  "return_rate": 0.08, // Return rate (8%)
  "lot_fixed_cost": 0.0, // Fixed lot acquisition cost
  "min_cash_60d": 0, // Minimum 60-day cash recovery
  "min_cash_60d_p5": 0, // Minimum P5 cash recovery (VaR)
  "calibration_log_path": "logs/predictions.jsonl" // Optional prediction logging
}
```

## Response Schemas

### Optimization Response

```json
{
  "status": "ok",
  "bid": 1250.5, // Recommended maximum bid
  "roi_p50": 1.34, // Median ROI
  "roi_p5": 1.12, // 5th percentile ROI (conservative)
  "roi_p95": 1.67, // 95th percentile ROI (optimistic)
  "prob_roi_ge_target": 0.85, // P(ROI >= target)
  "expected_cash_60d": 1450.75, // Expected 60-day cash
  "cash_60d_p5": 950.25, // Conservative 60-day cash (when present)
  "meets_constraints": true, // Whether lot satisfies constraints
  "iterations": 12, // Bisection iterations
  "core_items_count": 45, // Items passing evidence gate
  "upside_items_count": 3, // Items excluded from core analysis
  "calibration_log_path": "logs/predictions.jsonl" // If logging enabled
}
```

### Report Response

```json
{
  "status": "ok",
  "markdown_path": "reports/lot_report.md",
  "html_path": null,
  "pdf_path": null,
  "markdown_preview": "# Lot Genius Report\n\n## Executive Summary..."
}
```

### Error Response

```json
{
  "status": "error",
  "error": "File not found: data/nonexistent.csv",
  "details": {
    "error_type": "ValidationError",
    "field": "items_csv",
    "message": "Path validation failed"
  }
}
```

## Calibration Logging

Prediction logging is enabled when `calibration_log_path` is specified in the optimizer configuration:

**JSONL Schema (per prediction):**

```json
{
  "sku_local": "ITEM-001",
  "asin": "B08N5WRWNW",
  "est_price_mu": 25.5,
  "est_price_sigma": 5.2,
  "est_price_p50": 25.0,
  "sell_p60": 0.72,
  "sell_hazard_daily": 0.0185, // If present
  "condition_bucket": "new",
  "sell_condition_factor": 1.0,
  "sell_seasonality_factor": 1.0,
  "mins_per_unit": 15.0,
  "quantity": 1,
  "predicted_price": 25.5, // Alias for est_price_mu
  "predicted_sell_p60": 0.72, // Alias for sell_p60
  "context": {
    // Nested context object
    "roi_target": 1.25,
    "risk_threshold": 0.8,
    "horizon_days": 60,
    "lot_id": "LOT-2024-001",
    "opt_source": "run_pipeline", // "run_optimize" or "run_pipeline"
    "opt_params": {
      "roi_target": 1.25,
      "risk_threshold": 0.8,
      "sims": 2000
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "roi_target": 1.25, // Flattened for backward compatibility
  "risk_threshold": 0.8,
  "horizon_days": 60,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Outcomes CSV Format:**

```csv
sku_local,realized_price,sold_within_horizon,days_to_sale
ITEM-001,27.50,True,42
ITEM-002,15.75,False,60
ITEM-003,35.00,True,28
```

## Path Validation

All file paths undergo security validation:

**Allowed Roots:**

- Repository directory (auto-detected)
- System temp directory (Windows: `%TEMP%`, Unix: `/tmp`)

**Blocked Patterns:**

- Windows drives: `C:\`, `D:\`, etc.
- UNC paths: `\\server\share`
- System directories: `/etc`, `/root`, `C:\Windows`, `C:\Program Files`

**Example Safe Paths:**

```
data/samples/manifest.csv         OK Relative to repo
C:\Users\user\lot-genius\data\    OK Within repo root
C:\Users\user\AppData\Local\Temp\ OK System temp
/tmp/lotgenius_12345.csv         OK Unix temp directory
```

**Blocked Paths:**

```
C:\Windows\System32\config       X System directory
\\server\share\data.csv         X UNC path
/etc/passwd                     X System configuration
../../../etc/shadow             X Path traversal attempt
```

## Error Handling

### Common HTTP Status Codes

- **200**: Success
- **400**: Bad Request (validation error, path safety violation)
- **401**: Unauthorized (missing/invalid API key)
- **404**: Not Found (file doesn't exist)
- **422**: Unprocessable Entity (schema validation failed)
- **500**: Internal Server Error (processing exception)

### Example Error Responses

**Path Safety Violation:**

```json
{
  "status": "error",
  "error": "Path safety validation failed: C:\\Windows\\System32",
  "details": {
    "error_type": "PathValidationError",
    "blocked_pattern": "windows_system_dir"
  }
}
```

**Missing File:**

```json
{
  "status": "error",
  "error": "File not found: data/nonexistent.csv",
  "details": {
    "error_type": "FileNotFoundError",
    "path": "data/nonexistent.csv"
  }
}
```

**Schema Validation:**

```json
{
  "status": "error",
  "error": "Validation error in request body",
  "details": {
    "error_type": "ValidationError",
    "field": "roi_target",
    "message": "ensure this value is greater than 0"
  }
}
```

## Performance & Caching

### Cache Configuration

The backend provides comprehensive caching for external API calls and scraper results:

**Environment Variables:**

- `KEEPA_CACHE_TTL_DAYS`: Keepa cache TTL in days (default: 7)
- `KEEPA_CACHE_TTL_SEC`: Keepa cache TTL override in seconds (for testing)
- `EBAY_CACHE_TTL_SEC`: eBay scraper cache TTL in seconds (default: 86400 = 24 hours)
- `CACHE_METRICS`: Enable cache metrics in API responses (default: 0, set to 1 to enable)

### Cache Implementation

**Keepa Client Cache:**

- **Storage**: SQLite database with WAL mode and timestamp indexing
- **Keys**: Separate cache keys for different operation types (`product:domain:code`, `product_stats:asin:domain:asin`)
- **TTL**: Configurable via environment variables, supports seconds override for testing
- **Metrics**: Records hits, misses, stores, and evictions
- **Cleanup**: Automatic cleanup of expired entries with eviction tracking

**eBay Scraper Cache:**

- **Storage**: Separate SQLite database with fingerprint-based keys
- **Fingerprinting**: Deterministic hash of normalized query parameters (query, brand, model, UPC, ASIN, conditions, limits)
- **TTL**: Configurable via `EBAY_CACHE_TTL_SEC` environment variable
- **Collision avoidance**: Different parameter combinations generate different fingerprints
- **Backward compatibility**: Maintains compatibility with existing cache system

### Cache Metrics

When `CACHE_METRICS=1` is set, API responses include cache performance statistics:

```json
{
  "cache_stats": {
    "hits": 45,
    "misses": 12,
    "stores": 12,
    "evictions": 3,
    "hit_ratio": 0.789,
    "total_operations": 72
  }
}
```

### Observing Cache Performance

**Registry Access:**

```python
from lotgenius.cache_metrics import get_all_cache_stats

# Get all cache statistics
all_stats = get_all_cache_stats()
print(f"Keepa hit ratio: {all_stats['keepa']['hit_ratio']:.2%}")
print(f"eBay hit ratio: {all_stats['ebay']['hit_ratio']:.2%}")
```

**API Integration:**

- Keepa client includes cache stats in response when `CACHE_METRICS=1`
- eBay scraper adds cache stats to SoldComp metadata when enabled
- Metrics are thread-safe and persist across requests

### Common Troubleshooting

**Cache not working:**

1. Check file permissions for `data/cache/` directory
2. Verify SQLite database files can be created/accessed
3. Check TTL configuration - very low values may cause frequent misses
4. Monitor metrics to confirm hits vs misses

**Performance issues:**

1. Enable cache metrics to identify low hit ratios
2. Increase TTL values for stable data sources
3. Monitor eviction counts - high evictions may indicate insufficient TTL
4. Check database WAL files aren't growing excessively

**Test TTL overrides:**

```bash
# Test with short TTL for rapid testing
set KEEPA_CACHE_TTL_SEC=10
set EBAY_CACHE_TTL_SEC=30
set CACHE_METRICS=1
python -m pytest backend/tests/test_cache_keepa.py -v
```

### Performance Notes

- **Streaming recommended** for large manifests (>1000 items)
- **File upload limits**: 20MB default (configurable via `MAX_UPLOAD_BYTES`)
- **Timeout handling**: Long-running optimizations may timeout (adjust server config)
- **Caching**: ID resolution and price lookups cached with configurable TTLs
- **Concurrency**: Single-threaded Monte Carlo (CPU-bound workload)

## Importing Feeds/Watchlists

The backend supports importing user-supplied feeds and watchlists from CSV files, with automatic normalization and conversion to pipeline-ready format.

### Feed CSV Schema

**Required Columns:**

- `title` - Product title/name (required, non-empty)
- At least one ID field: `brand`, `asin`, `upc`, `ean`, or `upc_ean_asin`

**Optional Columns:**

- `model` - Product model/SKU
- `condition` - Item condition (auto-normalized to standard buckets)
- `quantity` - Item quantity (defaults to 1)
- `notes` - Additional notes or description
- `category` - Product category
- `color_size_variant` - Variant description
- `lot_id` - Lot identifier
- `sku_local` - Local SKU (auto-generated if missing)
- `est_cost_per_unit` - Estimated cost per unit
- `msrp` - Manufacturer's suggested retail price

### Example Feed CSV

```csv
title,brand,condition,upc,quantity,notes,category
"iPhone 14 Pro 128GB","Apple","New","194253413141","1","Unlocked","Electronics"
"Galaxy S23 Ultra","Samsung","Used - Good","887276632166","2","Minor scratches","Electronics"
"AirPods Pro 2nd Gen","Apple","Like New","","1","Open box","Audio"
"USB-C Cable 6ft","","Used","","10","Bulk lot","Accessories"
```

### CLI Import Tool

Convert feed CSV to pipeline-ready format:

```cmd
# Basic import (outputs to data/feeds/out/)
python -m backend.cli.import_feed my_feed.csv

# Custom output paths
python -m backend.cli.import_feed feed.csv --output-csv normalized.csv --output-json items.json

# Validation only
python -m backend.cli.import_feed feed.csv --validate-only --quiet
```

**Output:**

- Normalized CSV compatible with existing pipeline
- JSON format for API consumption
- Summary statistics (ID distribution, conditions, brands)

### Feed Processing Features

**Automatic Normalization:**

- **Conditions**: Maps various condition strings to standard buckets (`New`, `Like New`, `Used - Good`, `Used - Fair`, `For Parts`)
- **Brands**: Lowercase normalization for consistency
- **IDs**: Applies existing ID extraction and validation via `extract_ids()`
- **Encoding**: Windows-safe CSV reading with UTF-8 BOM support

**Validation:**

- Required field presence and completeness
- At least one identifying field (brand, ASIN, UPC, EAN)
- Deterministic error reporting with row/column context
- Support for quoted CSV fields and CRLF line endings

### Feed -> Pipeline Flow

1. **Import**: `load_feed_csv()` reads and validates CSV
2. **Normalize**: Applies condition bucketing, brand normalization, field trimming
3. **Convert**: `feed_to_pipeline_items()` applies ID extraction and adds pipeline defaults
4. **Output**: Standard CSV/JSON ready for existing pipeline endpoints

The converted output integrates seamlessly with:

- `/v1/pipeline/upload/stream` - Direct pipeline processing
- `/v1/optimize` - Lot optimization analysis
- `/v1/report` - Report generation

## Testing

### Integration Tests with Live APIs

The backend includes integration tests that verify live API connections and functionality:

#### Keepa Integration Tests

**Requirements**:

- Valid Keepa API key
- Optional: `SCRAPER_TOS_ACK=1` for scraper-dependent tests

**Setup**:

```cmd
# Windows Command Prompt
set KEEPA_API_KEY=your_actual_keepa_api_key
set SCRAPER_TOS_ACK=1
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Run Keepa client tests
python -m pytest -q backend/tests/test_keepa_integration.py

# Run pipeline integration tests
python -m pytest -q backend/tests/test_pipeline_keepa_live.py
```

**Test Coverage**:

- `test_keepa_integration.py`: Tests Keepa client methods directly
  - Product lookup by UPC/EAN code
  - Caching behavior verification
  - Stats retrieval by ASIN
  - Error handling without API key
- `test_pipeline_keepa_live.py`: Tests full pipeline with live Keepa data
  - End-to-end SSE streaming with real Keepa enrichment
  - Phase order validation
  - Final results structure verification

**Skip Behavior**:

- Tests automatically skip when `KEEPA_API_KEY` is not set
- No failures or errors when API key is missing
- Clean test reports with skip counts

#### Running Existing Tests (Regression Check)

```cmd
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest -q backend/tests/test_product_confirmation.py
python -m pytest -q backend/tests/test_sse_events.py backend/tests/test_sse_phase_order_evidence.py
```

### Windows Testing Tips

- Use `set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to avoid plugin conflicts
- Use Command Prompt (`cmd`) rather than PowerShell for environment variables
- Run from repository root directory for proper import paths

---

**Next**: [CLI Commands](cli.md) for command-line usage examples
