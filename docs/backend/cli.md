# CLI Commands

Command-line interface for Lot Genius analysis pipeline. All commands support `--help` for detailed usage.

## Installation

```cmd
pip install -e backend
```

**Windows Encoding Support**: All CLI tools use UTF-8 file I/O and ASCII-safe console output for Windows compatibility. See [Windows Encoding Guide](../operations/windows-encoding.md) for details.

## ID Resolution and Evidence Processing

### Field Preservation and Precedence

**Preserved Fields:** Original `asin`, `upc`, `ean` fields are maintained in output; `upc_ean_asin` is populated with precedence: asin > upc > ean.

**Resolver Precedence:** Engine uses: asin > upc (valid check digit) > ean > upc_ean_asin.

**UPC-A Validation:** UPC codes validated using check digit algorithm before Keepa resolution.

### Confidence-Aware Evidence Gating

Evidence requirements scale with data quality:

- **Clean items**: Base 3 sold comps + secondary signals
- **Ambiguous items**: Up to 5 comps based on ambiguity flags:
  - `generic:title` - Generic terms (bundle, lot, damaged)
  - `ambiguous:brand` - Missing brand information
  - `ambiguous:condition` - Unknown condition
- **High-trust IDs**: ASIN/UPC/EAN matches bypass gates

**Configuration Variables:**

- `EVIDENCE_MIN_COMPS_BASE=3` - Base requirement
- `EVIDENCE_AMBIGUITY_BONUS_PER_FLAG=1` - Extra per flag
- `EVIDENCE_MIN_COMPS_MAX=5` - Maximum cap

## Core Commands

### report_lot - End-to-End Analysis

Generate complete lot analysis report from manifest CSV.

```cmd
python -m backend.cli.report_lot data\samples\manifest.csv ^
  --opt-json configs\optimizer.json ^
  --out-markdown reports\lot_report.md ^
  --out-html reports\lot_report.html
```

**Key Options:**

- `--opt-json PATH` - Optimizer configuration file
- `--out-markdown PATH` - Markdown report output
- `--out-html PATH` - HTML report output (requires pandoc)
- `--out-pdf PATH` - PDF report output (requires pandoc + LaTeX)
- `--sweep-csv PATH` - Reference to bid sweep analysis
- `--evidence-jsonl PATH` - Reference to optimization evidence

**Example with inline config:**

```cmd
python -m backend.cli.report_lot manifest.csv ^
  --roi-target 1.3 --risk-threshold 0.85 ^
  --out-markdown decision.md
```

**Report Structure:**

The markdown report includes the following sections:

- **Executive Summary**: Recommended bid, ROI metrics, constraint evaluation
- **Lot Overview**: Item counts, total values, average sell probabilities
- **Item Details**: Table with SKU, Title, Price, Sell P60, and Product Confidence (when available)
- **Cache Metrics**: Cache performance statistics (when `CACHE_METRICS=1` is set)
- **Constraints**: ROI targets, risk thresholds, cashfloor, payout lag
- **Gating/Hazmat**: Evidence requirements and hazmat policy status
- **Investment Decision**: PROCEED/PASS/REVIEW recommendation with rationale
- **Scenario Analysis**: Stress test results (when available)
- **Supporting Artifacts**: Links to sweep analysis, evidence trails

**Product Confidence Column**: The Item Details table includes a Product Confidence score (0-1 range) when evidence metadata contains product matching signals. Higher scores indicate stronger product identification confidence.

**Cache Metrics Section**: When enabled via `CACHE_METRICS=1` environment variable, displays:

- Overall cache hit ratio and operation counts
- Per-cache breakdown for Keepa, eBay, and other data sources
- Hit/miss statistics for performance monitoring

### optimize_bid - ROI Optimization

Find optimal bid for pre-processed items CSV.

```cmd
python -m backend.cli.optimize_bid data\processed\estimated_sell.csv ^
  --out-json results\optimization.json ^
  --roi-target 1.25 --risk-threshold 0.80 ^
  --lo 0 --hi 5000 --sims 2000
```

**Core Parameters:**

- `--roi-target FLOAT` - Target ROI threshold (default: 1.25)
- `--risk-threshold FLOAT` - Confidence level (default: 0.80)
- `--lo FLOAT` - Minimum bid (default: 0)
- `--hi FLOAT` - Maximum bid (default: 10000)
- `--sims INT` - Monte Carlo simulations (default: 2000)

**Cost Parameters:**

- `--marketplace-fee-pct FLOAT` - Marketplace fee % (default: 0.13)
- `--payment-fee-pct FLOAT` - Payment processing % (default: 0.029)
- `--shipping-per-order FLOAT` - Shipping cost (default: 8.50)
- `--return-rate FLOAT` - Return rate (default: 0.08)
- `--salvage-frac FLOAT` - Salvage value fraction (default: 0.50)

**Constraints:**

- `--min-cash-60d FLOAT` - Minimum expected 60-day cash
- `--min-cash-60d-p5 FLOAT` - Minimum P5 cash recovery (VaR constraint)
- `--lot-fixed-cost FLOAT` - Fixed lot acquisition cost

**Example with constraints:**

```cmd
python -m backend.cli.optimize_bid items.csv ^
  --roi-target 1.4 --risk-threshold 0.85 ^
  --min-cash-60d 1000 --lot-fixed-cost 150 ^
  --evidence-out audit\optimization.jsonl
```

### sweep_bid - Sensitivity Analysis

Generate bid sensitivity sweep for analysis and visualization.

```cmd
python -m backend.cli.sweep_bid data\processed\estimated_sell.csv ^
  --out-csv analysis\sweep_results.csv ^
  --lo 0 --hi 5000 --step 100 ^
  --roi-target 1.25 --sims 1000
```

**Output Columns:**

- `bid` - Bid amount
- `prob_roi_ge_target` - P(ROI >= target)
- `roi_p5`, `roi_p50`, `roi_p95` - ROI percentiles
- `expected_cash_60d` - Expected 60-day cash
- `cash_60d_p5` - Conservative 60-day cash
- `meets_constraints` - Boolean constraint satisfaction

### estimate_sell - Survival Modeling

Compute sell-through probabilities using survival models.

```cmd
python -m backend.cli.estimate_sell data\priced\estimated_prices.csv ^
  --out-csv data\processed\estimated_sell.csv ^
  --days 60 --model ladder ^
  --evidence-out audit\survival_evidence.jsonl
```

**Model Options:**

- `--model {default,ladder}` - Survival model variant (default: ladder)
- `--days INT` - Sell-through horizon (default: 60)
- `--alpha FLOAT` - Base hazard scaling (ladder model)
- `--beta FLOAT` - Category scaling (ladder model)

**Price Sensitivity:**

- `--beta-price FLOAT` - Price sensitivity coefficient (default: 0.8)
- `--list-price-mode {p50,p95}` - Reference price for z-scores
- `--hazard-cap FLOAT` - Maximum daily hazard rate

**Example with custom parameters:**

```cmd
python -m backend.cli.estimate_sell items.csv ^
  --model ladder --alpha 2.5 --beta 1.2 ^
  --beta-price 0.9 --hazard-cap 0.8 ^
  --evidence-out logs\survival.jsonl
```

### estimate_price - Price Estimation

Generate price distributions using ensemble methods.

```cmd
python -m backend.cli.estimate_price data\enriched\resolved_with_stats.csv ^
  --out-csv data\priced\estimated_prices.csv ^
  --cv-fallback 0.20 --prior-keepa 0.50 ^
  --category-priors configs\category_priors.json
```

**Ensemble Weights:**

- `--prior-keepa FLOAT` - Keepa source weight (default: 0.50)
- `--prior-ebay FLOAT` - eBay source weight (default: 0.35)
- `--prior-other FLOAT` - Other sources weight (default: 0.15)
- `--cv-fallback FLOAT` - Coefficient of variation fallback (default: 0.20)

**Conservative Floors:**

- `--category-priors PATH` - Category floor configuration
- `--salvage-floor-frac FLOAT` - Salvage floor fraction (default: 0.10)
- `--price-evidence-out PATH` - Compact evidence export (NDJSON)
- `--gzip-evidence` - Compress evidence file

### resolve_ids - ID Resolution

Resolve UPC/EAN codes to ASINs using Keepa API.

```cmd
python -m backend.cli.resolve_ids data\clean\parsed_manifest.csv ^
  --output-csv data\enriched\resolved.csv ^
  --output-ledger audit\resolution.jsonl ^
  --with-stats --gzip-ledger
```

**Key Options:**

- `--with-stats` - Include price/rank statistics
- `--network / --no-network` - Enable/disable API calls
- `--keepa-key KEY` - Override API key
- `--gzip-ledger` - Compress audit ledger

**Cache Control:**

- `--cache-ttl-hours INT` - Cache TTL (default: 168 = 7 days)
- `--cache-path PATH` - Custom cache database location

### parse_clean - Manifest Processing

Parse and clean manifest CSVs with header mapping.

```cmd
python -m backend.cli.parse_clean data\raw\manifest.csv ^
  --out csv --output data\clean\parsed.csv ^
  --explode --min-coverage 0.70
```

**Output Formats:**

- `--out {json,csv}` - Output format
- `--explode / --no-explode` - Expand quantities to individual rows
- `--min-coverage FLOAT` - Minimum header coverage threshold

**Validation:**

- `--fail-on-low-coverage` - Exit with error if coverage too low
- `--show-mapping` - Display header mapping results

## Calibration Commands

### calibration_report - Outcomes Analysis

Generate calibration metrics from predictions and outcomes.

```cmd
python -m backend.cli.calibration_report ^
  logs\predictions.jsonl ^
  data\outcomes\realized_sales.csv ^
  --out-json reports\calibration_metrics.json ^
  --out-md reports\calibration_report.md
```

**Analysis Metrics:**

- **Brier Score**: Probability calibration accuracy
- **Price MAE/RMSE/MAPE**: Price prediction accuracy
- **Calibration Bins**: Prediction vs outcome rates by probability range
- **Reliability Curves**: Isotonic calibration analysis

**Output Options:**

- `--out-json PATH` - JSON metrics export
- `--out-md PATH` - Markdown report generation
- `--horizon-days INT` - Override horizon (default: 60)

## Validation Commands

### validate_manifest - Manifest Quality

Validate manifest CSV structure and content.

```cmd
python -m backend.cli.validate_manifest data\manifests\sample.csv ^
  --show-coverage --min-coverage 0.70 ^
  --fail-on-duplicates
```

**Validation Checks:**

- Header coverage percentage
- Required column presence
- Duplicate header mappings
- Data type consistency
- Value range validation

### map_preview - Header Mapping

Preview header mapping without processing.

```cmd
python -m backend.cli.map_preview data\manifests\sample.csv ^
  --show-candidates --top-k 5 ^
  --save-alias "Item Desc" title
```

**Options:**

- `--show-candidates` - Show mapping suggestions
- `--top-k INT` - Number of suggestions per unmapped header
- `--save-alias OLD NEW` - Save permanent header alias

## Utility Commands

### join_bid - Results Consolidation

Join optimization results with item-level data.

```cmd
python -m backend.cli.join_bid ^
  --items-csv data\processed\estimated_sell.csv ^
  --opt-json results\optimization.json ^
  --out-csv reports\lot_summary.csv ^
  --mode one-row
```

**Modes:**

- `one-row` - Single lot summary row
- `broadcast` - Broadcast bid to all items

## Environment Variables

Commands respect these environment variables:

**Required:**

- `KEEPA_API_KEY` - Keepa API authentication

**Optional:**

- `SELLTHROUGH_HORIZON_DAYS` - Default horizon (60)
- `MIN_ROI_TARGET` - Default ROI target (1.25)
- `RISK_THRESHOLD` - Default risk threshold (0.80)
- `SURVIVAL_MODEL` - Default model ("ladder")
- `LOTGENIUS_API_KEY` - API server authentication

## Common Workflows

### Complete Pipeline (Manual)

```cmd
# 1. Parse and clean manifest
python -m backend.cli.parse_clean manifest.csv --out csv --output clean.csv --explode

# 2. Resolve IDs with stats
python -m backend.cli.resolve_ids clean.csv --with-stats --output-csv enriched.csv

# 3. Estimate prices with floors
python -m backend.cli.estimate_price enriched.csv --out-csv priced.csv ^
  --category-priors configs\priors.json

# 4. Compute sell-through probabilities
python -m backend.cli.estimate_sell priced.csv --out-csv processed.csv

# 5. Optimize bid
python -m backend.cli.optimize_bid processed.csv --out-json results.json

# 6. Generate report
python -m backend.cli.report_lot processed.csv --opt-json results.json ^
  --out-markdown decision.md
```

### Calibration Workflow

```cmd
# 1. Enable prediction logging
python -m backend.cli.optimize_bid items.csv ^
  --opt-json configs\optimizer.json ^
  --out-json results.json

# 2. Collect outcomes (manual data entry/scraping)
# Create outcomes.csv with: sku_local,realized_price,sold_within_horizon,days_to_sale

# 3. Generate calibration report
python -m backend.cli.calibration_report ^
  logs\predictions.jsonl data\outcomes.csv ^
  --out-json calibration_metrics.json
```

### Development/Testing

```cmd
# Quick manifest validation
python -m backend.cli.validate_manifest test_data.csv --show-coverage

# Test header mapping
python -m backend.cli.map_preview test_data.csv --show-candidates --top-k 3

# Dry run ID resolution (no API calls)
python -m backend.cli.resolve_ids test_data.csv --no-network --output-csv dry_run.csv

# Small optimization test
python -m backend.cli.optimize_bid test_items.csv --sims 100 --out-json quick_test.json
```

## Tips & Best Practices

**Performance:**

- Use `--sims 100-500` for development/testing
- Use `--sims 2000+` for production decisions
- Enable `--gzip-ledger` for large audit files

**Debugging:**

- Add `--evidence-out` to capture audit trails
- Use `--show-coverage` to debug header mapping issues
- Check `--min-coverage` if manifests have non-standard formats

**Windows Paths:**

- Use `^` for line continuation in cmd.exe
- Use forward slashes or escaped backslashes in paths
- Wrap paths with spaces in quotes: `"path with spaces"`

---

**Next**: [ROI & Optimization Guide](roi.md) for detailed parameter explanations
