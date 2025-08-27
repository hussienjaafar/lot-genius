# Lot Genius Documentation

Complete documentation for the Lot Genius B-Stock analysis platform.

## Quick Navigation

### Getting Started

- [Architecture Overview](architecture.md) - System design and data flow
- [Dev Setup](operations/runbooks/dev.md) - Local development environment

### Backend

- [API Reference](backend/api.md) - HTTP endpoints, request/response schemas
- [CLI Commands](backend/cli.md) - Command-line tools and examples
- [ROI & Optimization](backend/roi.md) - Monte Carlo simulation parameters
- [Calibration Guide](backend/calibration.md) - Prediction logging and analysis

### Frontend

- [UI Components](frontend/ui.md) - React components and user interface

### Operations

- [Development Runbook](operations/runbooks/dev.md) - Local setup and workflows
- [Lot Optimization](operations/runbooks/optimize-lot.md) - End-to-end optimization process
- [Calibration Cycle](operations/runbooks/calibration-cycle.md) - Logging, gathering, reporting
- [Troubleshooting](operations/runbooks/troubleshooting.md) - Common issues and solutions

### Reference

- [Contributing Guide](../CONTRIBUTING.md) - Development guidelines and PR process
- [Example Files](../examples/) - Sample configurations and data files

## Documentation Structure

```
docs/
+-- INDEX.md                    # This file - main navigation
+-- architecture.md             # High-level system design
+-- backend/
|   +-- api.md                 # FastAPI endpoints and schemas
|   +-- cli.md                 # Command-line interface guide
|   +-- roi.md                 # ROI simulation and optimization
|   +-- calibration.md         # Prediction tracking and analysis
+-- frontend/
|   +-- ui.md                  # User interface and components
+-- operations/
    +-- runbooks/
        +-- dev.md             # Development environment setup
        +-- optimize-lot.md    # Lot optimization procedures
        +-- calibration-cycle.md # Calibration workflow
        +-- troubleshooting.md # Common problems and fixes
```

## Key Concepts

**Investment Pipeline**: Raw manifest -> Parse -> Enrich -> Price -> Survival -> Optimize -> Report

**Risk Framework**: Configurable ROI targets, confidence thresholds, and evidence requirements

**Audit Trails**: JSONL logging for predictions, evidence gathering, and decision tracking

**Calibration Loop**: Prediction logging -> Outcome collection -> Metrics computation -> Model refinement

---

**New to Lot Genius?** Start with the [Architecture Overview](architecture.md) to understand the system design, then follow the [Development Runbook](operations/runbooks/dev.md) for hands-on setup.

**Need help?** Check [Troubleshooting](operations/runbooks/troubleshooting.md) for common issues or the [Contributing Guide](../CONTRIBUTING.md) for development questions.
