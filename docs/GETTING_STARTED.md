# Getting Started with Lot Genius

Welcome to Lot Genius! This guide provides two quick paths to explore the platform: a **mock demo** (no network required) and **CLI report generation** with sample data.

## Option 1: Mock Demo (Recommended for First-Time Users)

Experience the full Lot Genius workflow in your browser without needing API keys or network access.

### What You'll See

- **File Upload**: Upload CSV manifests and JSON optimizer configs
- **Real-time Streaming**: Watch progress as items are processed
- **Confidence Metrics**: See data quality scores and evidence gating
- **Cache Insights**: View external data source hit rates
- **Interactive Report**: Copy generated markdown reports
- **ASCII-Safe Output**: All content maintains Windows terminal compatibility

### Quick Setup

```bash
# 1. Clone and navigate to the repository
git clone https://github.com/your-org/lot-genius.git
cd lot-genius

# 2. Install frontend dependencies
cd frontend
npm install

# 3. Start mock mode
set NEXT_PUBLIC_USE_MOCK=1
npm run dev

# 4. Open browser
# Visit: http://localhost:3000
```

### Try the Demo

1. **Upload Test Data**: Use the demo files from `examples/demo/demo_manifest.csv`
2. **Configure Optimizer**: Upload `examples/demo/demo_opt.json` or use the inline editor
3. **Watch Processing**: Observe real-time progress through parsing, pricing, and optimization
4. **Review Results**: See confidence scores, cache metrics, and final recommendations
5. **Copy Report**: Use the "Copy Report" button to get the markdown output

### Demo Data Included

- **demo_manifest.csv**: 3-item sample manifest with varied data quality
- **demo_opt.json**: Conservative optimizer settings (1.25x ROI target, 80% confidence)
- **Expected Output**: ASCII-compliant markdown report with investment recommendation

## Option 2: Backend CLI Report Generation

Generate lot analysis reports directly from the command line using sample data.

### Prerequisites

```bash
# 1. Install Python 3.11+ and create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 2. Install backend package
pip install -e backend

# 3. Optional: Set environment for live data (demo works without)
# set KEEPA_API_KEY=your_key_here
```

### Quick CLI Demo

```bash
# Generate a complete lot analysis report using demo data
python -m backend.cli.report_lot examples/demo/demo_manifest.csv ^
  --opt-json examples/demo/demo_opt.json ^
  --out-markdown reports/demo_report.md

# View the generated report
type reports\demo_report.md
```

### What the CLI Produces

- **Markdown Report**: Executive summary with investment decision
- **Data Processing**: Automatic header mapping, ID resolution, pricing
- **Risk Analysis**: Monte Carlo ROI simulation with confidence intervals
- **ASCII Compliance**: All output safe for Windows terminals and documentation

### Sample CLI Output Structure

```
# Lot Genius Report

## Executive Summary
Recommended Maximum Bid: $XXX
Expected ROI: X.XX (XXX% probability >= 1.25x)
Investment Decision: [PROCEED/PASS/REVIEW]

## Lot Overview
Items: X | Est. Total Value: $XXX | Avg. Sell P60: XX%

## Optimization Parameters
ROI Target: 1.25x | Risk Threshold: 80%
```

## Understanding the Results

### Mock Demo Results

- **Confidence Scores**: Items show different quality levels based on available data
- **Evidence Gating**: Some items may require additional comparables
- **Cache Metrics**: Displays hit rates for external data sources
- **Streaming Progress**: Real-time updates through parsing, pricing, survival modeling, optimization

### CLI Report Results

- **Investment Decision**: Clear PROCEED/PASS/REVIEW recommendation
- **Risk Assessment**: Probability-based ROI analysis with confidence intervals
- **Data Quality**: Automatic handling of missing or ambiguous manifest data
- **Conservative Pricing**: Floor-adjusted price estimates with category priors

## Next Steps

### Production Usage

1. **Get Keepa API Key**: Required for live product data
2. **Configure Environment**: Set `KEEPA_API_KEY` in your `.env` file
3. **Upload Real Data**: Use your own B-Stock manifest CSVs
4. **Customize Parameters**: Adjust ROI targets and risk thresholds in optimizer JSON

### Advanced Features

- **Calibration Tracking**: Monitor prediction accuracy over time
- **Batch Processing**: Analyze multiple lots simultaneously
- **Custom Categories**: Define category-specific pricing floors
- **Evidence Logging**: Audit trail for all data resolution decisions

### Release Artifacts

Get the latest pre-built packages:

- **Backend Package**: `lotgenius-X.Y.Z-py3-none-any.whl`
- **Frontend Build**: `frontend-build.zip` (production Next.js bundle)
- **Documentation**: `docs-bundle.zip` (complete offline documentation)
- **Demo Bundle**: `lotgenius_demo.zip` (this guide + sample data)

Download from: [Latest Release](https://github.com/your-org/lot-genius/releases/latest)

### System Requirements

- **Backend**: Python 3.11+ with dependencies from requirements
- **Frontend**: Node.js 18+ for development, static deployment for production
- **Operating System**: Windows 10+, macOS 10.15+, or Linux
- **Memory**: 2GB RAM minimum for typical manifest processing
- **Storage**: 500MB for caches and temporary processing files

### ASCII Policy

All Lot Genius output maintains ASCII compatibility for:

- Windows Command Prompt and PowerShell
- Documentation systems and version control
- Email and text-based reporting
- Cross-platform terminal compatibility

Unicode characters in input data are automatically converted to ASCII-safe equivalents during processing.

## Troubleshooting

### Mock Demo Issues

- **Port 3000 in use**: Change port with `npm run dev -- -p 3001`
- **Build errors**: Run `npm ci` to clean install dependencies
- **Upload failures**: Check browser console and ensure demo files exist

### CLI Report Issues

- **Import errors**: Verify `pip install -e backend` completed successfully
- **File not found**: Use absolute paths or check current working directory
- **Permission denied**: Ensure write permissions for output directory

### Common Solutions

```bash
# Reset frontend dependencies
cd frontend && rm -rf node_modules package-lock.json && npm install

# Clean Python environment
pip uninstall lotgenius && pip install -e backend

# Check ASCII compliance
python scripts/check_ascii.py path/to/your/files
```

For additional help, see:

- [Complete Documentation](docs/INDEX.md)
- [API Reference](docs/backend/api.md)
- [Troubleshooting Guide](docs/operations/runbooks/troubleshooting.md)
- [Windows Setup Guide](docs/operations/windows-encoding.md)
