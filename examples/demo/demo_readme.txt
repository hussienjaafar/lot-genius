Lot Genius Demo Bundle
======================

This demo bundle contains sample data to explore Lot Genius capabilities
without requiring API keys or network access.

Contents:
- demo_manifest.csv: 3-item sample manifest with varied data quality
- demo_opt.json: Conservative optimizer configuration
- demo_readme.txt: This instruction file

Quick Start Options:

Option 1: Mock Frontend Demo
---------------------------
1. Extract this bundle to your preferred directory
2. Start the frontend in mock mode:
   cd frontend
   set NEXT_PUBLIC_USE_MOCK=1  (Windows)
   export NEXT_PUBLIC_USE_MOCK=1  (Linux/macOS)
   npm run dev
3. Visit http://localhost:3000
4. Upload demo_manifest.csv and demo_opt.json
5. Watch real-time processing and review results

Option 2: CLI Report Generation
------------------------------
1. Install backend: pip install -e backend
2. Generate report:
   python -m backend.cli.report_lot demo_manifest.csv --opt-json demo_opt.json --out-markdown demo_report.md
3. Review the generated markdown report

Sample Data Explained:
- Item 1: High-quality data (iPhone with UPC + ASIN)
- Item 2: Medium-quality data (Samsung with ASIN only, damaged condition)
- Item 3: Low-quality data (Generic brand, no identifiers)

Expected Behavior:
- Confidence gating will require different evidence levels per item
- Price estimates will vary based on available data quality
- Final recommendation depends on total lot value vs risk tolerance

ASCII Policy:
All output maintains ASCII compatibility for Windows terminals,
documentation systems, and cross-platform compatibility.

For complete documentation: docs/GETTING_STARTED.md
For latest releases: https://github.com/your-org/lot-genius/releases
