# Code Changes & Learnings (Recent)

## Simulation Engine
- Increased CDR annual capacity cap to 100 Gt/yr (was 12) and lowered learning full-scale threshold to 250 Gt to avoid artificial throttling of DAC/CDR.
- Inflation clamp on CQE interventions: capped CPI bump at +2pp per intervention and added mean-reversion toward target to prevent runaway inflation.
- CQE budget ties to cumulative private capital (15% mid-band) with GDP cap; price-floor adjustments now consider inflation and temperature.
- Carbon cycle integrated BAU trajectory uses the same sink model to avoid BAU vs GCR divergence when minting is zero.

## Dashboard
- Monte Carlo support with run selector; aggregates climate metrics (mean, 10-90% bands) and shows CO2 ribbon when multiple runs are used.
- CO2 chart y-axis starts at 200 ppm for better visibility; sequestration stacked bars split CDR vs Conventional; summary metrics include per-channel delivery.

## Testing
- `./venv/bin/pytest -q` passing (one known warning: test returns bool instead of assert).

## Notes
- Branch previously ahead; recent changes not pushed until user requests.
