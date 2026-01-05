# Agent: Investors
**Role:** Market Liquidity and Sentiment Providers

## Objective
To trade XCR as a financial asset, providing the secondary market liquidity required for the policy to function.

## Key Logic (Code-Accurate)
1. **Sentiment Index:** Ranges from 0.1 (minimum) to 1.0 (full trust).
2. **Warning Decay:** CEA warnings reduce sentiment (larger drop on new warnings).
3. **Inflation Decay:** Sentiment falls when inflation exceeds 1.5×, 2×, or 3× the target.
4. **Recovery:** Sentiment recovers slowly when inflation is near target and there are no warnings.
5. **CO2 Progress Bonus:** If CO2 falls vs baseline, sentiment gains a small bonus.
6. **Forward Guidance & Floor Revisions:** Stronger guidance and upward floor revisions boost sentiment.
7. **Price Formula:** `Market_Price = Price_Floor + 50 × Sentiment + Capital_Demand_Premium`.
