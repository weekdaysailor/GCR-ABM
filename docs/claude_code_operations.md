# Code Changes & Learnings (Recent)

## Simulation Engine
- Set CDR annual capacity cap default to 10 Gt/yr (slider 1–100 Gt/yr) and scale-damping full-scale threshold to 45 Gt with a ~7% minimum scale (slider 10–50 Gt).
- Inflation clamp on CQE interventions: capped CPI bump at +2pp per intervention and added mean-reversion toward target to prevent runaway inflation.
- CQE budget ties to annual private capital inflow (5% of annual flow) with GDP cap; price-floor adjustments now consider inflation and temperature.
- Carbon cycle integrated BAU trajectory uses the same sink model to avoid BAU vs GCR divergence when minting is zero.
- Project initiation is now capital-limited (no per-country caps) with a $20B seed inflow until market cap reaches ~$50B to bootstrap early market formation.
- Capital demand neutrality now ramps down from ~0.6 to ~0.3 over the first ~10 years after XCR start to reflect growing market confidence.
- Learning rates for CDR and conventional mitigation are now exposed as dashboard sliders.
- Scale damping full-scale deployment (Gt) is now adjustable in the dashboard, with normalized sigmoid scaling at low deployment.
- CDR capacity cap is now adjustable in the dashboard (1-100 Gt/yr).
- Conventional mitigation no longer faces R‑value penalties; capacity tapers down as utilization approaches the limit (no hard cutoff).

## Dashboard
- Monte Carlo support with run selector; aggregates climate metrics (mean, 10-90% bands) and shows CO2 ribbon when multiple runs are used.
- CO2 chart y-axis starts at 200 ppm for better visibility; sequestration stacked bars split CDR vs Conventional vs Avoided Deforestation; summary metrics include per-channel delivery.

## Testing
- `./venv/bin/pytest -q` passing (one known warning: test returns bool instead of assert).

## Notes
- Branch previously ahead; recent changes not pushed until user requests.
