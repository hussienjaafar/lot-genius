# Comprehensive LotGenius App Review - ChatGPT Codex Instructions

## Overview

You are tasked with performing a comprehensive end-to-end review of the LotGenius liquidation analysis app to determine if it's ready for real purchasing decisions. Use Playwright for browser automation testing of the deployed application.

## Application Details

**Deployed URL:** https://lot-genius.onrender.com/
**Local Directory:** C:/Users/Husse/lot-genius/
**Technology Stack:** Python FastAPI backend, React frontend, deployed on Render

## Core Business Purpose

LotGenius analyzes liquidation manifests to recommend optimal bid amounts for purchasing liquidation lots. It uses:

- Monte Carlo simulations for risk assessment
- External API data (eBay, Keepa) for pricing
- Two-Source Rule evidence gating for data quality
- CVaR (Conditional Value at Risk) calculations

## Key Files to Examine

### Backend Core Logic

- `backend/lotgenius/roi.py` - ROI optimization and risk calculations
- `backend/lotgenius/evidence.py` - Two-Source Rule evidence gating
- `backend/lotgenius/api/service.py` - Main API service layer
- `backend/lotgenius/config.py` - Configuration management
- `backend/lotgenius/survivorship.py` - Sell-through probability modeling

### Frontend

- `src/` - React application source
- `frontend/` - Additional frontend resources

### Test Data

- `realistic_liquidation_manifest.csv` - Sample liquidation data (20 items)
- `test_manifest.csv` - Test data for validation
- `e2e_test_config.json` - Sample optimization configuration

### API Documentation

- Check `/docs` endpoint on deployed app for OpenAPI documentation
- Key endpoints: `/api/report`, `/api/optimize`, `/api/pipeline`

## Review Objectives

### 1. Functional Testing (Use Playwright)

**Test the deployed app at https://lot-genius.onrender.com/**

Create Playwright tests to verify:

- [ ] App loads and renders properly
- [ ] File upload functionality for CSV manifests
- [ ] Report generation workflow
- [ ] Optimization parameter configuration
- [ ] Results display and interpretation
- [ ] Error handling for invalid inputs
- [ ] API endpoint responses and timing

### 2. Business Logic Analysis

Review code to assess:

- [ ] **Risk Management**: CVaR calculations, Monte Carlo accuracy, constraint handling
- [ ] **Data Quality**: Two-Source Rule implementation, evidence scoring
- [ ] **Pricing Models**: External API integration, price estimation accuracy
- [ ] **Decision Framework**: ROI calculations, bid optimization logic

### 3. Production Readiness

Evaluate:

- [ ] **Error Handling**: Graceful failures, input validation, edge cases
- [ ] **Performance**: Response times, API rate limiting, large file handling
- [ ] **Security**: Input sanitization, API key management, data privacy
- [ ] **Reliability**: Deployment stability, external API failure handling

## Specific Testing Scenarios

### Test Case 1: Basic Upload and Analysis

```javascript
// Playwright test example
test("Upload manifest and generate report", async ({ page }) => {
  await page.goto("https://lot-genius.onrender.com/");

  // Upload test manifest
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles("realistic_liquidation_manifest.csv");

  // Configure optimization parameters
  await page.fill('[data-testid="roi-target"]', "1.5");
  await page.fill('[data-testid="risk-threshold"]', "0.75");
  await page.fill('[data-testid="budget-max"]', "5000");

  // Submit and wait for results
  await page.click('[data-testid="analyze-button"]');
  await page.waitForSelector('[data-testid="results-container"]', {
    timeout: 60000,
  });

  // Verify results structure
  const bidRecommendation = await page.textContent(
    '[data-testid="bid-amount"]',
  );
  const roiEstimate = await page.textContent('[data-testid="roi-estimate"]');

  expect(bidRecommendation).toBeTruthy();
  expect(roiEstimate).toBeTruthy();
});
```

### Test Case 2: API Direct Testing

Test core API endpoints:

- `POST /api/report` - Generate analysis report
- `POST /api/optimize` - Bid optimization
- `GET /api/health` - Health check
- `GET /docs` - API documentation

### Test Case 3: Error Handling

- Invalid CSV format
- Missing required columns
- Network failures
- Large file uploads
- Invalid optimization parameters

## Sample Test Data

Use the realistic liquidation manifest with these items:

- Apple AirPods Pro 2nd Generation ($85 cost)
- Samsung 55" 4K Smart TV ($X cost)
- Nike Air Force 1 Men's Size 10 ($45 cost)
- Instant Pot Duo 7-in-1 ($X cost)
- PlayStation 5 Console ($X cost)

Expected behaviors:

- High-confidence items (ASIN/UPC present) should pass evidence gate
- Electronics should have good Keepa/eBay comparable data
- ROI recommendations should be conservative (1.2-2.0x typical range)
- Risk assessments should show probability distributions

## Critical Success Criteria

### Must Pass (Blocking Issues)

- [ ] App loads without errors
- [ ] Can upload and process CSV files
- [ ] Returns numerical bid recommendations
- [ ] Shows risk assessment metrics
- [ ] Handles basic error cases gracefully

### Should Pass (Important)

- [ ] Response times under 30 seconds for 20-item manifest
- [ ] Evidence gating properly excludes low-confidence items
- [ ] ROI calculations include all business costs
- [ ] Results are interpretable by non-technical users

### Nice to Have

- [ ] Real-time progress updates during processing
- [ ] Export functionality for results
- [ ] Batch processing capabilities
- [ ] Advanced visualization

## Expected Output Format

Provide a comprehensive report with:

1. **Executive Summary** - Overall readiness assessment (Ready/Not Ready/Needs Work)
2. **Test Results** - Detailed Playwright test outcomes with screenshots
3. **Code Review Findings** - Analysis of business logic quality
4. **Performance Metrics** - Response times, error rates, reliability
5. **Risk Assessment** - Potential issues for real-money decisions
6. **Recommendations** - Specific improvements or deployment suggestions

## Environment Setup

The app is already deployed and should be accessible. For local testing, the directory structure is:

```
C:/Users/Husse/lot-genius/
├── backend/          # Python FastAPI backend
├── frontend/         # React frontend
├── src/              # Additional source files
├── *.csv             # Test manifest files
├── *.json            # Configuration files
└── test*.py          # Existing test scripts
```

## Key Questions to Answer

1. **Financial Safety**: Is the risk management sophisticated enough for real money?
2. **Data Reliability**: Does the Two-Source Rule effectively filter bad data?
3. **User Experience**: Can a liquidation buyer easily use this for purchase decisions?
4. **Scalability**: Will it handle larger manifests (100+ items)?
5. **Business Value**: Does it provide actionable insights beyond manual analysis?

Focus on practical usability for liquidation purchasing decisions rather than theoretical code quality. The goal is to determine if this tool is ready to guide real financial transactions.
