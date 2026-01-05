# Agent: Projects & Broker
**Role:** The Mitigators (Carbon Producers)

## Objective
To supply sequestration (Gt/yr) by responding to the XCR reward price.

## Key Logic (Code-Accurate)
1. **Channels:**
   - **CDR**, **Conventional**, and **Avoided Deforestation** create physical mitigation.
   - **Co-benefits** are a reward overlay only (no extra tonnes).
2. **Initiation Rule:** Projects start when `Market_Price * R_effective * Brake_Factor ≥ Marginal_Cost`, subject to available capital.
   - **R‑Value Basis:** Conventional R is marginal cost relative to marginal CDR cost (CDR R = 1).
3. **Capacity Limits:** Annual caps are applied (CDR slider 1–100 Gt/yr, Conventional 30 Gt/yr, Avoided Deforestation 5 Gt/yr) with no per‑country project caps.
4. **Conventional Taper:** Conventional capacity availability tapers down as utilization approaches the hard‑to‑abate limit.
5. **Co-benefit Pool:** 15% of minted XCR is redistributed by project co-benefit scores.
6. **Learning Curves:** Costs fall with cumulative deployment.
7. **Scale Damping:** Project size ramps with cumulative deployment (pilot → industrial), with a dashboard slider for the full‑scale threshold.
8. **Retirement:** Projects retire faster when CO2 drops below target.
9. **Allocation:** Country selection is weighted by tier/region preferences (not fixed country lists).
10. **Milestones:** Rewards are issued after audits of annual sequestration.
