# Agent: Central Bank Alliance
**Role:** Price floor backstop via CQE

## Objective
Defend the XCR price floor when market price dips, while limiting inflation impacts.

## Key Logic (Code-Accurate)
1. **Floor Defense:** If `Market_Price < Price_Floor`, CQE buys XCR using newly created reserves.
2. **Willingness (Inflation Brake):** Defense willingness is a sigmoid function of inflation with center at `1.5 × inflation_target`. If `inflation_target` is 0, CQE defense is disabled.
3. **Annual Budget Cap:** CQE spending is capped each year; once exhausted, the floor can slip.
4. **Budget Size:** Total CQE budget is `5%` of annual private capital inflow (flow‑based backstop), capped at `0.5%` of active GDP.
5. **Intervention Size:** Purchases are limited to a fraction of supply per step to avoid overshoot.
6. **Inflation Impact:** CQE spending increases inflation, but impacts are bounded and mean‑reverted toward target.
