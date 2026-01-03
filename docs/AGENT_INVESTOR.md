# Agent: Investors
**Role:** Market Liquidity and Sentiment Providers

## Objective
To trade XCR as a financial asset, providing the secondary market liquidity required for the policy to function.

## Key Logic
1. **Sentiment Index:** Ranges from 0.0 (Panic) to 1.0 (Full Trust).
2. **Safe-Haven Logic:** XCR is treated as a "limited-risk financial asset" when the floor is stable and inflation is low.
3. **Flight to Safety:** - If CEA issues an 8:1 Warning, sentiment decays linearly.
   - If Inflation > 3% for 2 units, sentiment decays exponentially as investors anticipate the "Central Bank Brake."
4. **Demand Function:** $Market\_Price = Floor + (50 \times Sentiment)$.
