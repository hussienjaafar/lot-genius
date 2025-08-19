.PHONY: init lint test format clean run-dev run-prod docker-build docker-up help

# Variables
PYTHON := python3.11
PIP := $(PYTHON) -m pip
VENV := venv
PROJECT_NAME := lot-genius

# Default target
.DEFAULT_GOAL := help

## Install backend package
install:
	@echo "Installing backend package..."
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e backend
	@echo "Installed editable backend package."

## Initialize development environment
init:
	@echo "Initializing development environment..."
	$(PIP) install -U pip
	$(PIP) install pre-commit
	pre-commit install
	@echo "Environment initialized successfully!"

## Run linters
lint:
	@echo "Running linters..."
	@if [ -f "backend/requirements.txt" ]; then \
		cd backend && ruff check . && black --check . && isort --check-only .; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Run tests
test:
	@echo "Running tests..."
	pytest

## Format code
format:
	@echo "Formatting code..."
	@if [ -d "backend" ]; then \
		cd backend && black . && isort .; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

## Run development server
run-dev:
	@echo "Starting development server..."
	@if [ -f "backend/main.py" ]; then \
		cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Run production server
run-prod:
	@echo "Starting production server..."
	@if [ -f "backend/main.py" ]; then \
		cd backend && gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000; \
	else \
		echo "Backend not yet initialized (stub)"; \
	fi

## Build Docker image
docker-build:
	@echo "Building Docker image..."
	@if [ -f "Dockerfile" ]; then \
		docker build -t $(PROJECT_NAME):latest .; \
	else \
		echo "Dockerfile not yet created (stub)"; \
	fi

## Run Docker containers
docker-up:
	@echo "Starting Docker containers..."
	@if [ -f "docker-compose.yml" ]; then \
		docker-compose up -d; \
	else \
		echo "Docker Compose not yet configured (stub)"; \
	fi

## Preview header mappings
map-preview:
	@echo "Running header mapping preview..."
	$(PYTHON) -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv

## Preview header mappings with candidates
map-preview-candidates:
	@echo "Running header mapping preview with suggestions..."
	$(PYTHON) -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv --show-candidates

## Preview header mappings with strict duplicate checking
map-preview-strict:
	@echo "Running header mapping preview with strict duplicate checking..."
	$(PYTHON) -m backend.cli.map_preview backend/tests/fixtures/manifest_sample.csv --fail-on-duplicates

## Validate one golden manifest
validate-one:
	@echo "Validating single golden manifest..."
	$(PYTHON) -m backend.cli.validate_manifest data/golden_manifests/01_basic.csv

## Validate all golden manifests
validate-golden:
	@echo "Validating all golden manifests..."
	@for f in data/golden_manifests/*.csv; do \
	  echo "Validating $$f"; \
	  $(PYTHON) -m backend.cli.validate_manifest "$$f" --strict || exit 1; \
	done

## Validate only good golden manifests (skip bad files)
validate-golden-good:
	@echo "Validating good golden manifests (skipping bad files)..."
	@for f in data/golden_manifests/*.csv; do \
	  if [[ ! $$f =~ .*bad.* ]]; then \
	    echo "Validating $$f"; \
	    $(PYTHON) -m backend.cli.validate_manifest "$$f" --strict || exit 1; \
	  else \
	    echo "Skipping bad file $$f"; \
	  fi; \
	done

## Validate a single file (strict)
validate:
	@if [ -z "$(FILE)" ]; then echo 'Usage: make validate FILE=path/to.csv'; exit 2; fi
	$(PYTHON) -m backend.cli.validate_manifest $(FILE) --strict

## Parse and clean manifest (explode to CSV)
parse-one:
	@echo "Running parser with explode to CSV..."
	$(PYTHON) -m backend.cli.parse_clean backend/tests/fixtures/manifest_multiqty.csv --explode --out csv --output /tmp/lotgenius_exploded.csv

## Parse and clean manifest (explode to JSON)
parse-json:
	@echo "Running parser with explode to JSON..."
	$(PYTHON) -m backend.cli.parse_clean backend/tests/fixtures/manifest_multiqty.csv --explode --out json --output /tmp/lotgenius_exploded.json

## Resolve IDs to ASINs (test fixture)
resolve-test:
	@echo "Running ID resolution on test fixture..."
	$(PYTHON) -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --output-csv /tmp/resolved_test.csv --output-ledger /tmp/resolved_test_ledger.jsonl

## Resolve IDs for custom file
resolve:
	@if [ -z "$(FILE)" ]; then echo 'Usage: make resolve FILE=path/to.csv'; exit 2; fi
	$(PYTHON) -m backend.cli.resolve_ids $(FILE)

## Resolve IDs (dry run - no network)
resolve-dryrun:
	$(PYTHON) -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --no-network

## Resolve IDs with Keepa network lookups
resolve-with-keepa:
	$(PYTHON) -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --network --out-enriched data/out/resolved_enriched.csv --out-ledger data/evidence/keepa_ledger.jsonl

## Resolve IDs with Keepa stats enrichment
resolve-with-stats:
	$(PYTHON) -m backend.cli.resolve_ids backend/tests/fixtures/manifest_multiqty.csv --network --with-stats --out-enriched data/out/resolved_with_stats.csv --out-ledger data/evidence/keepa_stats_ledger.jsonl

## Estimate prices from enriched CSV (Step 7)
estimate-prices:
	$(PYTHON) -m backend.cli.estimate_price data/out/resolved_with_stats.csv --out-csv data/out/estimated_prices.csv --ledger-out data/evidence/price_ledger.jsonl

## Estimate prices with category floors and price evidence (Step 7.1)
estimate-prices-with-floors:
	$(PYTHON) -m backend.cli.estimate_price data/out/resolved_with_stats.csv --out-csv data/out/estimated_prices_floored.csv --ledger-out data/evidence/price_ledger_floored.jsonl --category-priors backend/lotgenius/data/category_priors.example.json --salvage-floor-frac 0.10 --price-evidence-out data/out/price_evidence.ndjson --gzip-evidence

## Estimate sell-through ≤60 days (Step 8)
estimate-sell:
	$(PYTHON) -m backend.cli.estimate_sell data/out/estimated_prices.csv --out-csv data/out/estimated_sell.csv --evidence-out data/evidence/sell_evidence.jsonl --days 60 --list-price-mode p50 --list-price-multiplier 1.0

## Optimize bid using ROI constraints (Step 9)
optimize-bid:
	$(PYTHON) -m backend.cli.optimize_bid data/out/estimated_sell.csv --out-json data/out/optimize_bid.json --lo 0 --hi 5000 --roi-target 1.25 --risk-threshold 0.80 --sims 2000

## Sweep bids between [lo,hi] and record P(ROI≥target), ROI quantiles, cash stats (Step 9.1)
sweep-bid:
	$(PYTHON) -m backend.cli.sweep_bid data/out/estimated_sell.csv --out-csv data/out/sweep_bid.csv --lo 0 --hi 5000 --step 100 --roi-target 1.25 --risk-threshold 0.80 --sims 1000

## Optimize bid with evidence NDJSON for audit trail (Step 9.1)
optimize-bid-evidence:
	$(PYTHON) -m backend.cli.optimize_bid data/out/estimated_sell.csv --out-json data/out/optimize_bid.json --lo 0 --hi 5000 --roi-target 1.25 --risk-threshold 0.80 --sims 2000 --evidence-out data/evidence/optimize_evidence.jsonl

## Join recommended bid to produce single-row lot summary or broadcast to items (Step 9.1)
join-bid:
	$(PYTHON) -m backend.cli.join_bid --items-csv data/out/estimated_sell.csv --opt-json data/out/optimize_bid.json --out-csv data/out/lot_summary.csv --mode one-row

## Create bid sensitivity visualization from sweep_bid.csv (optional, requires matplotlib)
plot-sweep:
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

## Generate concise Lot Genius report from per-unit CSV and optimizer JSON (Step 9.2)
report-lot:
	$(PYTHON) -m backend.cli.report_lot data/out/estimated_sell.csv data/out/optimize_bid.json --out-markdown data/out/lot_report.md --sweep-csv data/out/sweep_bid.csv --sweep-png data/out/sweep_bid.png --evidence-jsonl data/evidence/optimize_evidence.jsonl

## Show available commands
help:
	@echo "Available commands:"
	@echo "  make install     - Install backend package"
	@echo "  make init        - Initialize development environment"
	@echo "  make lint        - Run code linters"
	@echo "  make test        - Run test suite"
	@echo "  make format      - Format code with black/isort"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make map-preview - Preview header mappings"
	@echo "  make map-preview-candidates - Preview with suggestions"
	@echo "  make map-preview-strict - Preview with strict duplicate checking"
	@echo "  make validate-one - Validate single golden manifest"
	@echo "  make validate-golden - Validate all golden manifests"
	@echo "  make validate-golden-good - Validate good golden manifests (skip bad files)"
	@echo "  make validate FILE=path/to.csv - Validate single file (strict)"
	@echo "  make parse-one   - Parse and explode manifest to CSV"
	@echo "  make parse-json  - Parse and explode manifest to JSON"
	@echo "  make resolve-test - Resolve IDs to ASINs (test fixture)"
	@echo "  make resolve FILE=path/to.csv - Resolve IDs for custom file"
	@echo "  make resolve-dryrun - Resolve IDs (dry run - no network)"
	@echo "  make resolve-with-keepa - Resolve IDs with Keepa network lookups"
	@echo "  make resolve-with-stats - Resolve IDs with Keepa stats enrichment"
	@echo "  make estimate-prices - Estimate prices from enriched CSV (Step 7)"
	@echo "  make estimate-prices-with-floors - Estimate prices with category floors and price evidence (Step 7.1)"
	@echo "  make estimate-sell - Estimate sell-through ≤60 days (Step 8)"
	@echo "  make run-dev     - Start development server"
	@echo "  make run-prod    - Start production server"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up   - Start Docker containers"
	@echo "  make help        - Show this help message"
