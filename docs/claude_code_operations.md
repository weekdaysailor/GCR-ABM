# Code Changes & Learnings (Recent)

## Simulation Engine
- Removed the hard CDR capacity cap (CDR now scales with capital, learning, and damping rather than a fixed annual limit).
- Set scale-damping full-scale threshold to 45 Gt with a ~7% minimum scale (slider 10–50 Gt) and added a sigmoid slope slider to tune ramp speed.
- Project capital allocation uses sequential channel order (avoided deforestation → conventional → CDR), and the initiation gate compares price to each channel’s own marginal cost (not the CDR gate).
- Inflation clamp on CQE interventions: capped CPI bump at +2pp per intervention and added mean-reversion toward target to prevent runaway inflation.
- CQE budget ties to annual private capital inflow (5% of annual flow) with GDP cap; price-floor adjustments now consider inflation and temperature.
- Carbon cycle integrated BAU trajectory uses the same sink model to avoid BAU vs GCR divergence when minting is zero.
- Project initiation is now capital-limited (no per-country caps) with a $20B seed inflow until market cap reaches ~$50B to bootstrap early market formation.
- Capital demand neutrality now ramps down from ~0.6 to ~0.3 over the first ~10 years after XCR start to reflect growing market confidence.
- Learning rates for CDR and conventional mitigation are now exposed as dashboard sliders.
- Scale damping full-scale deployment (Gt) is now adjustable in the dashboard, with normalized sigmoid scaling at low deployment.
- Sigmoid slope is now adjustable in the dashboard to control scale/count damping and CDR learning-rate taper.
- Conventional mitigation no longer faces R‑value penalties; capacity tapers down as utilization approaches the limit (no hard cutoff).

## Dashboard
- Monte Carlo support with run selector; aggregates climate metrics (mean, 10-90% bands) and shows CO2 ribbon when multiple runs are used.
- CO2 chart y-axis starts at 200 ppm for better visibility; sequestration stacked bars split CDR vs Conventional vs Avoided Deforestation; summary metrics include per-channel delivery.

## Testing
- `./venv/bin/pytest -q` passing (one known warning: test returns bool instead of assert).

## Notes
- Branch previously ahead; recent changes not pushed until user requests.
