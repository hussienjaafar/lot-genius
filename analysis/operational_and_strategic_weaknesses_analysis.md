# Analysis of Operational & Strategic Weaknesses for Purchasing Decisions

This analysis covers critical gaps in the system beyond data sufficiency and statistical model implementation that impact the quality of real-world purchasing decisions.

### 1. Operational Cost Blind Spots

The current ROI model appears to omit two of the largest and most variable real-world costs, causing it to systematically overestimate profitability.

- **Labor & Throughput Costs:** The model does not seem to account for the human time required to sort, test, clean, photograph, list, and ship each item. It cannot distinguish between a low-effort lot and a high-effort lot, even if their resale values are identical.
- **Storage & Holding Costs:** The model does not appear to factor in the cost of warehousing inventory over time. A lot of large items that take months to sell is more expensive than a lot of small items that sell quickly.

### 2. Lack of Dynamic Market and Pricing Strategy

The model produces a single price estimate, ignoring the strategic elements of pricing in a dynamic market.

- **Seasonality:** The system is blind to seasonal demand shifts (e.g., winter coats in summer vs. fall). It will incorrectly value seasonal goods depending on when the analysis is run.
- **Velocity vs. Margin Trade-off:** The model cannot answer strategic pricing questions like, "What is the best price to maximize profit within 30 days?" vs. "What is the best price to maximize profit within 90 days?" It lacks the concept of a pricing ladder or time-based discounting.

### 3. No Feedback Loop (The "Fire-and-Forget" Problem)

This is a critical strategic weakness. The system is designed to make a **pre-purchase prediction** but has no mechanism to learn from **post-purchase reality**.

To improve, the system must track its own performance on purchased lots:

- What was the actual final sale price?
- How long did the item actually take to sell?
- What was the true defect and return rate?

Without this feedback loop, the model's assumptions can never be validated, and its parameters can never be truly calibrated. It is doomed to repeat its mistakes and cannot systematically improve its own accuracy over time.
