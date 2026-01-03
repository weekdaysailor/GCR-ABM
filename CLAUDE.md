# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Global Carbon Reward (GCR) Agent-Based Model (ABM) simulation that models a carbon sequestration economy using XCR (carbon reward tokens) backed by Carbon Quantitative Easing (CQE). The system simulates interactions between five agent types to model how a global carbon market could achieve atmospheric CO2 reduction from 420 ppm to 350 ppm.

**Authoritative Source**: `docs/chen_chap5.md` contains the definitive specification for GCR logic, R-values, and agent behaviors based on Chen's 2025 research.

## Core Architecture

The simulation implements a true multi-agent system with five distinct agent classes that interact each time step:

### Agent Classes

**1. CEA (Carbon Exchange Authority)** - `gcr_model.py:56`
- Central system governor managing XCR supply and policy
- Calculates project-specific R-values based on cost-effectiveness:
  - CDR projects (Channel 1): R = 1 (fixed)
  - Conventional mitigation (Channel 2): R = marginal_cost / price_floor
  - Co-benefits (Channel 3): R adjusted by co-benefit value (0.8x cost)
- Monitors stability ratio (XCR Market Cap / CQE Budget):
  - 8:1 triggers warning to investors
  - 10:1 triggers system brake
- **Price Floor Adjustments**: Periodic 5-year policy revisions based on roadmap progress
  - Locked-in annual yield between revisions for market predictability
  - Responds to CO2 reduction progress (behind roadmap → higher growth rate)

**2. CentralBankAlliance** - `gcr_model.py:177`
- Defends XCR price floor ($100 RCC default, configurable) using Carbon Quantitative Easing (CQE)
- Sigmoid damping function: `W = 1/(1 + e^(k*(π - 0.03)))`
  - `k = 12.0` controls brake sharpness
  - Willingness to defend floor decreases as inflation rises
- When market_price < floor: creates new M0 reserves to purchase XCR
- CQE interventions increase XCR supply and cause inflation
- Represents global climate alliance with GDP-proportional CQE budgets
- **Dynamic Budget**: Total CQE budget grows as new countries join GCR system

**3. ProjectsBroker** - `gcr_model.py:222`
- Manages portfolio of mitigation projects across 3 channels
- **Project Initiation**: Projects start when `(market_price / R) >= marginal_cost`
- **Dynamic Channel Distribution** (uses active countries only):
  - Channel 1 (CDR): Prefers tropical/developing countries (South America, Africa, Asia)
  - Channel 2 (Conventional): Prefers Tier 1 developed economies with infrastructure
  - Channel 3 (Co-benefits): Prefers Tier 2/3 developing countries (ecosystem restoration)
- **Project Lifecycle**:
  - Development phase: 2-4 years randomly assigned
  - Operational phase: Annual sequestration once developed
  - Stochastic health decay: 2% annual failure rate
- Marginal costs increase with project count (resource depletion curve)

**4. InvestorMarket** - `gcr_model.py:239`
- Represents aggregate market sentiment (0.0 = panic, 1.0 = full trust)
- **Price Discovery**: `Market_Price = Floor + (50 × Sentiment)`
- **Sentiment Decay**:
  - CEA 8:1 warning: 0.9x multiplier (linear)
  - Inflation > 4%: 0.85x multiplier (exponential)
- **Sentiment Recovery**: +0.05 when stable (no warning, inflation ≤ 3%)

**5. Auditor** - `gcr_model.py:264`
- Validates 100-year durability requirement for projects
- **Annual audits** on all operational projects (controllable via `enable_audits` parameter)
- 2% error rate in detection
- **Audit Pass**: Mints fresh XCR = `tonnes_sequestered / R`
- **Audit Fail**: Burns 50% of project's lifetime XCR rewards, marks project as failed

### Country Adoption Mechanics

The simulation models gradual global adoption of the GCR system over time:

**Country Pool** (50 countries across 3 tiers):
- **Tier 1** (12 countries): High GDP economies (USA, China, Japan, Germany, UK, France, India, etc.)
  - GDP range: $1.6T - $27.0T
  - CQE capacity: $0.035T - $0.5T
- **Tier 2** (22 countries): Medium GDP economies (Mexico, Turkey, Saudi Arabia, Switzerland, etc.)
  - GDP range: $0.4T - $1.5T
  - CQE capacity: $0.009T - $0.03T
- **Tier 3** (16 countries): Developing economies (Vietnam, Bangladesh, Kenya, Ghana, etc.)
  - GDP range: $0.05T - $0.46T
  - CQE capacity: $0.001T - $0.009T

**Adoption Mechanics** (`adopt_countries()` - gcr_model.py:487):
- Configurable adoption rate (default: 3.5 countries/year)
- Fractional rates handled probabilistically (3.5 = 3-4 countries per year)
- **GDP-weighted selection**: Larger economies more likely to join early
  - Uses square root of GDP to balance large/small economies
  - ±50% random factor ensures diversity
- **Founding members** (5 countries at Year 0): USA, Germany, Brazil, Indonesia, Kenya
- **CQE Budget**: Automatically recalculates as countries join

**Impact on System**:
- Projects can only be allocated to active countries
- CQE budget grows with each new member
- Market stability ratio (Market Cap / CQE Budget) affected by budget growth
- Enables exploration of "early adopter club" vs "rapid global coordination" scenarios

### Execution Flow (per time step)

Each simulation year executes in this order:
0. `adopt_countries()` - New countries join GCR system based on adoption rate
1. `chaos_monkey()` - 5% chance of inflation shock (+0.5-1.5%)
2. Inflation correction toward 2% target (25-40% correction rate)
3. `investor_market.update_sentiment()` - Adjust based on warnings and inflation
4. `cea.update_policy()` - Monitor stability ratio, adjust price floor (periodic 5-year revisions)
5. `projects_broker.initiate_projects()` - Start new projects where economics favor it
6. `projects_broker.step_projects()` - Advance all projects (development progress, stochastic decay)
7. `auditor.verify_and_mint_xcr()` - Audit operational projects, mint/burn XCR
8. `central_bank.defend_floor()` - CQE intervention if price < floor
9. Update CO2 levels based on verified sequestration

**Critical Flow**: Projects sequester CO2 → Auditor verifies → XCR minted fresh (increases supply) → Market trades XCR → If price < floor → Central banks buy with CQE → CEA monitors stability → Adjusts price floor periodically

## Key Technical Concepts

### R-Value (Reward Multiplier)

From Chen paper (Definition Box 9):
- **1 XCR = 1/R tonnes of mitigated CO₂e with 100+ years durability**
- R enables adjustable rewards while maintaining single instrument
- **Purpose**: R is ONLY used to increase the reward for difficult mitigation (cost-effectiveness)
- XCR minting formula: `XCR = tonnes_mitigated / R`
- Example (price floor = $100):
  - CDR project at $100/tonne: R=1, receives 1 XCR per tonne
  - Solar project at $150/tonne: R=1.5, receives 0.67 XCR per tonne
  - Reforestation at $75/tonne: R=0.75, receives 1.33 XCR per tonne

**Project R-values** are set at project initiation based on marginal cost and determine the XCR/tonne ratio. This ensures cost-effective allocation of rewards across different mitigation technologies.

## Running the Simulation

```bash
# Setup (first time only)
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Run simulation (50-year default, audits enabled)
venv/bin/python gcr_model.py

# Run with custom parameters (in Python)
sim = GCR_ABM_Simulation(
    years=100,
    enable_audits=True,
    price_floor=100.0,      # Initial XCR price floor (USD)
    adoption_rate=3.5       # Countries joining per year
)
df = sim.run_simulation()
```

## Interactive Dashboard

An interactive Streamlit dashboard is available for visualizing simulation results with rich charts and real-time exploration.

### Running the Dashboard

```bash
# Make sure dependencies are installed
venv/bin/pip install -r requirements.txt

# Launch dashboard (opens in browser at http://localhost:8501)
venv/bin/streamlit run dashboard.py
```

### Dashboard Features

**5 Main Tabs:**

1. **Climate & CO2** - Atmospheric CO2 concentration over time, GCR vs BAU trajectories, sequestration rates, operational projects
2. **XCR Economics** - Total supply, minting/burning dynamics, cumulative statistics
3. **Market Dynamics** - Market price vs floor, investor sentiment, inflation tracking, stability ratio, CEA warnings
4. **Projects** - Portfolio analysis by country and channel, project status over time, failure rates, country adoption & CQE budget growth
5. **Data Table** - Full simulation data with sorting, filtering, and CSV export

**Interactive Controls (Sidebar):**
- Simulation years: 10-100
- XCR price floor (initial): $0-$999
- GCR adoption rate: 0-10 countries/year
- Enable/disable audits
- Random seed for reproducibility
- Run button to execute simulation

**Summary Metrics (8 cards):**
- CO2 reduction (absolute from 420 ppm)
- CO2 avoided vs BAU (counterfactual)
- Final XCR supply and last-year minting
- Active countries (final vs starting)
- Operational projects (vs total initiated)
- Market price (vs floor)
- Final inflation (vs 2% target)
- CQE budget total (final vs starting)

The dashboard uses Plotly for interactive charts with hover details, zooming, and panning. All visualizations update dynamically when you run a new simulation.

## Key System Parameters

Located in `GCR_ABM_Simulation.__init__()` (gcr_model.py:380):
- **Initial CO2**: 420 ppm
- **Target CO2**: 350 ppm
- **Price Floor (RCC)**: $100 USD per XCR (default, configurable $0-$999)
- **Adoption Rate**: 3.5 countries/year (default, configurable 0-10)
- **Global Inflation**: 2% baseline target
- **Inflation Correction**: 25-40% correction rate toward target
- **Stability Ratios**: 8:1 warning, 10:1 system brake
- **Price Floor Revisions**: Every 5 years based on roadmap progress
- **BAU CO2 Growth**: 0.5% annual (Business As Usual baseline)
- **CQE Budgets**: GDP-proportional across 50 countries (starts with 5 founding members)
- **Auditor Error Rate**: 2% (Class 3 operational risk)
- **Chaos Monkey**: 5% chance per year of 0.5-1.5% inflation shock

Located in `ProjectsBroker.__init__()` (gcr_model.py:231):
- **Base Costs**: CDR=$100/tonne, Conventional=$80/tonne, Co-benefits=$70/tonne
- **Project Scale**: 100k-1M tonnes/year sequestration
- **Development Time**: 2-4 years randomly assigned
- **Project Failure**: 2% annual stochastic decay rate

## Data Structures

### Project Object (gcr_model.py:26)
```python
@dataclass
class Project:
    id: str
    channel: ChannelType  # CDR, CONVENTIONAL, COBENEFITS
    country: str
    start_year: int
    development_years: int
    annual_sequestration_tonnes: float
    marginal_cost_per_tonne: float
    r_value: float  # Set at creation based on cost-effectiveness
    status: ProjectStatus  # DEVELOPMENT, OPERATIONAL, FAILED
    health: float  # 1.0 = healthy, decays stochastically
    total_xcr_minted: float
```

### Simulation Output DataFrame
Columns: Year, CO2_ppm, BAU_CO2_ppm, CO2_Avoided, Inflation, XCR_Supply, XCR_Minted, XCR_Burned, Market_Price, Price_Floor, Sentiment, Projects_Total, Projects_Operational, Sequestration_Tonnes, CEA_Warning, CQE_Spent, Active_Countries, CQE_Budget_Total

## Development Notes

### Adding New Agent Behavior
- Each agent class is self-contained with clear responsibilities
- Agent state should remain internal; interactions happen through method calls
- Maintain execution order in `run_simulation()` to preserve causal relationships

### Modifying Economic Parameters
- **Sigmoid damping sharpness** (k=12.0 in CentralBankAlliance): Controls how aggressively banks brake during inflation
- **Sentiment rates** (InvestorMarket): Decay (0.9, 0.85) vs recovery (0.05)
- **Inflation correction**: 25-40% rate toward 2% target each year
- **Project failure rates**: 2% annual stochastic decay
- **Clawback severity**: Currently 50% of lifetime XCR burned on audit failure
- **Price floor adjustments**: 5-year revision cycle with locked yields between revisions
- **Adoption rate**: Controls how quickly countries join (affects CQE budget growth)

### Understanding R-Value Mechanics
- When modifying project economics, remember: Higher R = fewer XCR per tonne
- Projects are profitable when: `(market_price / R) >= marginal_cost`
- R adjusts to ensure cost-effective projects receive adequate finance
- **Important**: R is ONLY for cost-effectiveness, not macro stability control

### Common Calibration Points
- If CO2 isn't reducing fast enough: Increase project sequestration scale, decrease base costs, or increase adoption rate
- If inflation spirals: Reduce CQE intervention volume, increase sigmoid damping, or adjust inflation correction rate
- If too many projects fail: Decrease stochastic failure rate or audit strictness
- If market price crashes: Check sentiment decay rates and stability ratio thresholds
- If country adoption too slow/fast: Adjust adoption_rate parameter (default 3.5/year)
