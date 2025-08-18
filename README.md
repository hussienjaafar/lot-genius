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

## Data Sources

- Keepa API (Amazon price/rank/offer history)
- Optional scrapers (low-trust; behind `ENABLE_SCRAPERS=false` by default)
- Optional manual CSV imports for comps

## Next Steps

- Canonical schema & header mapping
- Golden manifests & Great Expectations
- Parser/cleaner with quantity explode
- Keepa client with rate limiting
- Ensemble pricing & survival models
- Monte Carlo optimizer with configurable gates
