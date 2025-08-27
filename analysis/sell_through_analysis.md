# Analysis of Sell-Through Rate Calculation and Demand Scoring

This analysis audits the current sell-through rate calculation and demand scoring within the Lot Genius project, assessing its robustness and sufficiency for determining sales velocity.

## Current Approach

The project uses a "proxy survival model" to estimate `sell_p60` (the probability an item sells within 60 days). This model considers:

- Keepa sales rank (mapped to daily sales).
- Keepa offers count (as a proxy for saturation/competition).
- Price-to-market z-score (how competitively priced the item is).

## Significant Gaps in Sell-Through Rate Calculation

1.  **Lack of Calibration (Critical Gap):** The `README` explicitly states that the "coefficients are tunable" and "Later steps will calibrate from backtests." This is the most crucial weakness. An **uncalibrated model** means that the `sell_p60` values are essentially unverified estimates. Without empirical proof of their accuracy, the model's output is not trustworthy for financial decisions.

2.  **"Proxy" Limitations (Simplified Model):** The model is described as a "proxy" and a "scaffold," with a "full survival model" planned for v0.2 in the PRD. A proxy is a simplification that may miss complex, non-linear relationships or different hazard rates over time that a more sophisticated survival model could capture.

3.  **Missing Key Features (as per PRD):** The PRD lists several crucial features for `p60` that do not appear to be explicitly integrated into the current proxy model:
    - **Seasonality:** Ignoring seasonality will lead to inaccurate velocity estimates for seasonal items.
    - **Condition:** The model does not explicitly factor in the item's exact condition (e.g., "Used - Like New" vs. "Used - For Parts") into its velocity estimate.
    - **Brand/Category Specificity:** Explicit modeling of brand and category effects could improve accuracy, as different brands/categories have different demand curves.

4.  **Data Input Dependency (Weak for Non-Amazon Items):** The model heavily relies on Keepa data. For items without a strong Amazon presence or clear Keepa data, the velocity estimate is very weak and likely unreliable, as it falls back to a generic baseline.

## Is This Analysis "Good Enough" for Sales Velocity?

**No, not yet.**

While the conceptual framework is sound and the chosen inputs are relevant, the current implementation is a **rough estimate** at best. The lack of calibration, its "proxy" nature, and the absence of critical features mean that the `sell_p60` values cannot be confidently used to determine the sales velocity of items for real purchasing decisions.

## Recommendations for Improvement

To make the sell-through analysis reliable, the following work should be prioritized:

1.  **Prioritize Calibration:** Tune and validate the model parameters using historical data.
2.  **Implement Full Survival Model:** As per PRD v0.2, move beyond the proxy to a more sophisticated survival analysis.
3.  **Integrate Missing Features:** Incorporate Seasonality, Condition, and Brand/Category as direct inputs.
4.  **Expand Data Sources:** Improve data inputs for non-Amazon items to provide better velocity estimates.
