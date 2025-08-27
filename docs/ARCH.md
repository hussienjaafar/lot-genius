# Architecture Notes (v0.1) - Lot Genius

## Services

- **Ingestor:** CSV parsing, header mapping, canonical transformation
- **Resolver:** Entity matching, deduplication, ID resolution
- **Clients:** Keepa API, optional scrapers (Playwright)
- **Price Engine:** Ensemble pricing, robust statistics, recency weighting
- **Sell-Through:** Survival models, p60 estimation
- **Optimizer:** Monte Carlo simulation, bid optimization
- **Reporting:** Export generation, evidence aggregation

## Storage

- **Postgres:** OLTP + evidence ledger
- **DuckDB/Parquet:** Analytics on object store
- **Redis:** TTL cache for API responses

## Orchestration

- **Prefect/Dagster:** Workflow management
- Job idempotency keys: `(lot_id, step, source)`

## APIs

FastAPI endpoints:

- `POST /lots` - Upload manifest
- `POST /lots/{id}/run` - Process lot
- `GET /lots/{id}/report` - Get results
- `GET /items/{id}/evidence` - View evidence

## Observability

- **Sentry:** Error tracking
- **Prometheus/Grafana:** Metrics
- **OpenTelemetry:** Distributed tracing tagged with `lot_id`

## Security

- Secrets via environment variables
- Signed URLs for uploads
- PII-safe logging

## MCP Integration

- filesystem, process, fetch/http
- postgres, duckdb, redis
- git, playwright (low-trust)
- jsonschema validation

## Feature Flags / Config (env-backed)

- `ENABLE_SCRAPERS`
- `MIN_ROI_TARGET`
- `SELLTHROUGH_HORIZON_DAYS`
- `RISK_THRESHOLD`
- `CASHFLOOR`
- `CLEARANCE_VALUE_AT_HORIZON`
- `SOURCE_PRIORS`
- `RECENCY_DECAY_LAMBDA`
