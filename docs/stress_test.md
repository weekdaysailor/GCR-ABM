# Stress Test Harness

This harness runs multi-scenario Monte Carlo sweeps to build central-bank confidence in GCR stability, inflation control, and climate outcomes under stress.

## Usage

```bash
./venv/bin/python stress_harness.py --runs 30 --years 100 --seed 42
```

Optional filters:

```bash
./venv/bin/python stress_harness.py --scenario baseline --scenario high_shock_inflation
```

Outputs:
- Console summary table (mean/p10/p90 per scenario)
- `stress_results.csv` with run-level metrics

## Scenarios (default)

- **baseline**: Current default model.
- **delayed_start**: XCR starts after 10 years.
- **high_shock_inflation**: Elevated shock frequency and volatility.
- **low_private_capital**: Private capital demand throttled (30%).
- **high_bau_emissions**: Higher BAU emissions and slower decline.
- **tight_cqe**: CQE ratio reduced to 5% (weaker floor defense).

## Metrics Tracked

- Inflation: peak, mean, share of years above target
- Temperature: peak, share of years above 2C
- CO2: final and minimum, year reaching 350 ppm
- Market stability: minimum market price vs floor ratio
- CQE: peak utilization, total spend, share of years intervening
- XCR: total minted, final supply

## Interpretation Hints

- **Inflation control**: Peak and persistence above target should remain bounded in most scenarios.
- **Floor defense**: Low price-to-floor ratios or high CQE utilization indicate stress on the backstop.
- **Paris alignment**: Watch peak temperature and time above 2C for regime risk.

