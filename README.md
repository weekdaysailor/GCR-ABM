# GCR Agent-Based Model

Agent-Based Model (ABM) simulation of a Global Carbon Reward (GCR) economy using XCR tokens and Carbon Quantitative Easing (CQE).

## Overview

This simulation models a carbon sequestration economy with five interacting agent types:
- **CEA** (Carbon Exchange Authority) - System governor
- **Central Bank Alliance** - Price floor defenders via CQE
- **Projects Broker** - Carbon mitigation project portfolio
- **Investor Market** - Market sentiment and price discovery
- **Auditor** - Verification and risk management

The model simulates how XCR (carbon reward) tokens incentivize carbon sequestration to reduce atmospheric CO2 from 420 ppm to 350 ppm.

**Based on**: Chen (2025) carbon reward policy framework (see `docs/chen_chap5.md`)

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python3 -m venv venv

# Install dependencies
venv/bin/pip install -r requirements.txt
```

### 2. Run Simulation (CLI)

```bash
# Run 50-year simulation with default parameters
venv/bin/python gcr_model.py
```

**Output**: Console display of first 10 years, last 10 years, and final summary statistics.

### 3. Launch Interactive Dashboard

```bash
# Start Streamlit dashboard (opens in browser)
venv/bin/streamlit run dashboard.py
```

**Dashboard URL**: http://localhost:8501

## Dashboard Features

Interactive web interface with:
- **Climate & CO2**: Atmospheric concentration, GCR vs BAU comparison, sequestration rates
- **XCR Economics**: Supply, minting, burning dynamics
- **Market Dynamics**: Price vs floor, sentiment, inflation, stability ratio
- **Projects**: Portfolio by country/channel, country adoption over time, failure rates
- **Data Export**: CSV download of full simulation results

**Controls**:
- Simulation years (10-200, default 100)
- XCR price floor ($0-$999)
- GCR adoption rate (0-10 countries/year)
- Enable/disable audits
- Random seed for reproducibility
- Monte Carlo runs (ensemble count)

## Project Structure

```
.
├── gcr_model.py          # Core ABM simulation with agent classes
├── dashboard.py          # Streamlit visualization dashboard
├── requirements.txt      # Python dependencies
├── CLAUDE.md            # Technical documentation for Claude Code
├── docs/
│   ├── chen_chap5.md    # Authoritative GCR policy specification
│   ├── CEA_AGENT.md     # CEA agent documentation
│   ├── AGENT_CENTRAL_BANK.md
│   ├── AGENT_PROJECTS_BROKER.md
│   ├── AGENT_INVESTOR.md
│   └── AGENT_AUDITOR.md
└── venv/                # Virtual environment (created by setup)
```

## Key Concepts

### R-Value (Reward Multiplier)

**1 XCR = 1/R tonnes of CO₂e** with 100+ years durability

- **CDR projects**: R = 1 (fixed)
- **Conventional mitigation**: R = marginal_cost / marginal_cdr_cost
- **Avoided deforestation**: R = marginal_cost / marginal_cdr_cost

**XCR Minting**: `XCR = tonnes_sequestered * R`

### Reward Channels

1. **CDR** (Carbon Dioxide Removal) - Direct carbon capture (physical tonnes)
2. **Conventional Mitigation** - Renewables, efficiency (structural reductions)
3. **Avoided Deforestation** - Land‑use emissions avoidance (physical tonnes)
4. **Co-benefits** - Reward overlay (no additional tonnes)

### Economic Flow

```
Countries join GCR system (adoption rate: 3.5/year default)
  → Projects sequester CO2
  → Auditor verifies (1% error rate)
  → XCR minted fresh (increases supply)
  → Market trades XCR
  → If price < floor → Central banks buy via CQE (budget‑capped, inflation‑aware)
  → CEA monitors stability → Adjusts price floor (5-year cycles)
```

## Simulation Parameters

Default values in `GCR_ABM_Simulation.__init__()`:
- **Initial CO2**: 420 ppm
- **Target CO2**: 350 ppm
- **Price Floor**: $100 USD per XCR (configurable $0-$999)
- **Adoption Rate**: 3.5 countries/year (configurable 0-10)
- **Inflation Target**: 2% guidance with 25-40% correction rate; inflation starts at 0
- **Stability Ratios**: 8:1 warning, 10:1 system brake
- **CQE Budgets**: 15% of cumulative private capital inflow, capped at 2% of active GDP
- **BAU Emissions**: 40 GtCO2/yr, peak around year 6, plateau, then slow late‑century decline (~0.2%/yr)
- **Project Development**: 2-4 years
- **Audit Failure Penalty**: 50% of lifetime XCR burned

## Customization

### Python API

```python
from gcr_model import GCR_ABM_Simulation

# Custom simulation
sim = GCR_ABM_Simulation(
    years=100,                 # Simulation length
    enable_audits=True,        # Enable/disable verification
    price_floor=150.0,         # Initial XCR price floor (USD)
    adoption_rate=5.0          # Countries joining per year
)

# Run and get results as DataFrame
df = sim.run_simulation()

# Access agent states
print(f"Active countries: {len(sim.countries)}")
print(f"CQE budget: ${sim.central_bank.total_cqe_budget/1e12:.2f}T")
print(f"Investor sentiment: {sim.investor_market.sentiment}")
print(f"Total projects: {len(sim.projects_broker.projects)}")
```

### Modifying Parameters

Edit `gcr_model.py` to adjust:
- **Economic**: Price floor, inflation targets, CQE ratio and GDP cap
- **Projects**: Base costs, sequestration rates, failure rates
- **Learning**: CDR/conventional learning rates, scale damping behavior
- **Policy**: Sigmoid damping sharpness, price floor revision cycles, adoption rate
- **Market**: Sentiment decay/recovery rates
- **Countries**: GDP, CQE capacity, tier/region assignments in country pool

See `CLAUDE.md` for detailed guidance on extending the model.

## Output Data

Simulation returns pandas DataFrame with columns:
- `Year`, `CO2_ppm`, `BAU_CO2_ppm`, `CO2_Avoided`, `Temperature_Anomaly`
- `Inflation`, `Market_Price`, `Price_Floor`, `Sentiment`, `CEA_Brake_Factor`
- `XCR_Supply`, `XCR_Minted`, `XCR_Burned_Annual`, `XCR_Burned_Cumulative`, `Cobenefit_Bonus_XCR`
- `Projects_Total`, `Projects_Operational`, `Projects_Development`, `Projects_Failed`
- `Sequestration_Tonnes`, `CDR_Sequestration_Tonnes`, `Conventional_Mitigation_Tonnes`, `Avoided_Deforestation_Tonnes`, `Reversal_Tonnes`
- `CQE_Spent`, `Annual_CQE_Spent`, `Annual_CQE_Budget`, `CQE_Budget_Utilization`, `XCR_Purchased`, `CQE_Budget_Total`

See `CLAUDE.md` for the full column list (capital flows, climate physics, and learning curves).

## Documentation

- **CLAUDE.md** - Technical architecture, agent details, development guide
- **docs/chen_chap5.md** - Authoritative GCR policy specification
- **docs/AGENT_*.md** - Individual agent role documentation

## Requirements

- Python 3.12+
- numpy >= 1.24.0
- pandas >= 2.0.0
- streamlit >= 1.28.0 (for dashboard)
- plotly >= 5.17.0 (for dashboard)

## License

See project documentation for licensing information.

## Acknowledgments

Based on the carbon reward policy framework by Chen (2025). See `docs/chen_chap5.md` for full specification.
