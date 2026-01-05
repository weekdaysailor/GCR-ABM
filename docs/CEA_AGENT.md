# Agent: Carbon Exchange Authority (CEA)
**Role:** The Central System Governor / Controller

## Objective
To manage the XCR supply to return atmospheric CO2 to the target roadmap (e.g., 350 ppm) while maintaining system stability.

## Key Logic (Code-Accurate)
1. **Roadmap Tracking:** Uses a linear CO2 roadmap from current to target.
2. **Stability Ratio:** Monitors `Market_Cap / CQE_Budget`.
   - **8:1** triggers warning.
   - **10:1** activates braking.
3. **Braking:** Brake factor reduces XCR minting when ratios are high, inflation is high, or CQE budgets are near exhaustion.
4. **Price Floor Revisions:** Updated every 5 years, adjusted by roadmap performance, inflation, and temperature.
5. **Policy Multipliers:** Channel‑specific R‑multipliers are fixed at 1.0 (no penalties or time shifts).
6. **R‑Value Basis:** Conventional R is set by marginal cost relative to marginal CDR cost (CDR R = 1 fixed).
