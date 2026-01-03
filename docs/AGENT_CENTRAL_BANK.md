# Agent: Central Bank Alliance
**Role:** The Guarantors of the Price Floor

## Objective
To defend the XCR Price Floor ($RCC$) using Carbon Quantitative Easing (CQE) without destabilizing national fiat currencies.

## Key Logic
1. **Floor Defense:** If $MarketPrice_{XCR} < RCC$, the banks create new reserves ($M0$) to purchase XCR.
2. **Sigmoid Damping (The Brake):** Willingness to defend the floor ($W$) is a function of the global inflation rate ($\pi$):
   $$W = \frac{1}{1 + e^{k(\pi - 0.03)}}$$
   Where $k$ is the sharpness of the brake. This ensures that if inflation exceeds 3%, the "Carbon Mandate" is throttled to protect price stability.
3. **5-Nation Club:** Logic is applied across USA, Germany, Brazil, Indonesia, and Kenya with GDP-proportional budgets.
