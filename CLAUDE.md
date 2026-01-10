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
  - Conventional mitigation (Channel 2): R = marginal_cost / marginal_cdr_cost
  - Avoided deforestation (Channel 3): R = marginal_cost / marginal_cdr_cost
- Co-benefits are a reward overlay (no separate tonnes)
- Monitors stability ratio (XCR Market Cap / CQE Budget)
- **Inflation-Adjusted CEA Brake** (PRIMARY CONSTRAINT): Brake thresholds, heavy-brake floor, and inflation penalty scale with realized inflation (normalized to 2% baseline), plus a budget-utilization brake near CQE cap
  - Base thresholds at 2%: warning 8:1, brake tiers 10:1 / 12:1 / 15:1
  - Budget-utilization brake starts at 90% of annual CQE cap (floor 25%)
  - **See**: `docs/inflation_adjusted_brake.md` for formulas and ranges
  - Creates negative feedback: High issuance → High ratio → Brake → Lower issuance
- **Price Floor Adjustments**: Periodic 5-year policy revisions based on roadmap progress
  - Locked-in annual yield between revisions for market predictability
  - Responds to CO2 reduction progress (behind roadmap → higher growth rate)

**2. CentralBankAlliance** - `gcr_model.py:177`
- Defends XCR price floor ($100 RCC default, configurable) using Carbon Quantitative Easing (CQE)
- Sigmoid damping function centered at `1.5 × inflation_target`
  - `k = 12.0` controls brake sharpness
  - Willingness to defend floor decreases as inflation rises
- When market_price < floor: creates new M0 reserves to purchase XCR (budget-capped)
- CQE interventions affect inflation; impacts are bounded and mean‑reverted toward target
- **Budget Model**: Total CQE budget is 5% of annual private capital inflow, capped at 0.5% of active GDP

**3. ProjectsBroker** - `gcr_model.py:222`
- Manages portfolio of mitigation projects across 3 physical channels
- **Project Initiation**: Projects start when `(market_price * brake_factor) >= marginal_cost`
- **Dynamic Channel Distribution** (uses active countries only):
  - Channel 1 (CDR): Prefers tropical/developing countries (South America, Africa, Asia)
  - Channel 2 (Conventional): Prefers Tier 1 developed economies with infrastructure
  - Channel 3 (Avoided Deforestation): Prefers tropical/developing countries (South America, Africa, Asia)
- Co-benefits: reward overlay (no separate projects)
- **Project Lifecycle**:
  - Development phase: 2-4 years randomly assigned
  - Operational phase: Annual sequestration once developed
  - **Channel-specific lifespans**: CDR=100yr, Conventional=25yr, Avoided Deforestation=50yr
  - Stochastic health decay: 2% annual failure rate
- Marginal costs increase with project count (resource depletion curve)
- **Conventional cost penalties**:
  - Budget depletion: 1x → 8x as cumulative deployment reaches 1000 Gt (earlier onset at 60% utilization)
  - Net-zero proximity: 1x → 100x as E:S ratio drops from 6.0 → 1.0 (very steep exponential for shorter credit periods)
- Capacity limits: Conventional 30 Gt/yr, Avoided Deforestation 5 Gt/yr, CDR 20 Gt/yr
- **Net-Zero Transition**: CM credits terminate **permanently** when E:S ratio first reaches ≤ 1.0; AvDef continues

**4. InvestorMarket** - `gcr_model.py:239`
- Represents aggregate market sentiment (0.0 = panic, 1.0 = full trust)
- **Price Discovery**: `Market_Price = Floor + (50 × Sentiment) + Capital_Demand_Premium`
- **Sentiment Decay**: Warnings + inflation thresholds (1.5×, 2×, 3× target)
- **Sentiment Recovery**: +2% of remaining gap when stable; bonus if CO2 is falling

**5. Auditor** - `gcr_model.py:264`
- Validates 100-year durability requirement for projects
- **Annual audits** on all operational projects (controllable via `enable_audits` parameter)
- 1% error rate in detection
- **Audit Pass**: Mints fresh XCR = `tonnes_sequestered * R`
- **Audit Fail**: Burns 50% of project's lifetime XCR rewards, marks project as failed

### Country Adoption Mechanics

The simulation models gradual global adoption of the GCR system over time:

**Country Pool** (50 countries across 3 tiers):
- **Tier 1** (12 countries): High GDP economies (USA, China, Japan, Germany, UK, France, India, etc.)
  - GDP range: $1.6T - $27.0T
- **Tier 2** (22 countries): Medium GDP economies (Mexico, Turkey, Saudi Arabia, Switzerland, etc.)
  - GDP range: $0.4T - $1.5T
- **Tier 3** (16 countries): Developing economies (Vietnam, Bangladesh, Kenya, Ghana, etc.)
  - GDP range: $0.05T - $0.46T

**Adoption Mechanics** (`adopt_countries()` - gcr_model.py:487):
- Configurable adoption rate (default: 3.5 countries/year)
- Fractional rates handled probabilistically (3.5 = 3-4 countries per year)
- **GDP-weighted selection**: Larger economies more likely to join early
  - Uses square root of GDP to balance large/small economies
  - ±50% random factor ensures diversity
- **Founding members** (5 countries at Year 0): USA, Germany, Brazil, Indonesia, Kenya
**CQE Budget**: Uses annual private capital inflow and GDP cap (not fixed per-country budgets)

**Impact on System**:
- Projects can only be allocated to active countries
- CQE budget is recalculated from annual private inflows and capped by active GDP (adoption can raise the cap)
- Market stability ratio (Market Cap / CQE Budget) moves with private capital inflows and GDP cap changes
- Enables exploration of "early adopter club" vs "rapid global coordination" scenarios

### Execution Flow (per time step)

Each simulation year executes in this order (simplified):
1. Countries adopt the system (if active).
2. Inflation shock/noise is applied, then corrected toward target.
3. Investor sentiment updates when the system is active.
4. Capital flows and price discovery update when the system is active.
5. CEA updates brake factor and price floor (periodic revisions).
6. Projects initiate (if active), then advance and are audited.
7. CQE defends the price floor if needed (annual cap).
8. Carbon cycle updates CO2 and temperature.

**Critical Flow**: Projects sequester CO2 → Auditor verifies → XCR minted × brake_factor × capacity → Market trades XCR → If price < floor → CQE purchases within budget → CEA updates stability and floor.

### Inflation Constraint Feedback Loop (NEW)

Inflation is the PRIMARY constraint on XCR issuance through two parallel mechanisms:

**Mechanism 1: Annual CQE Budget Caps**
```
High XCR issuance
  ↓
More CQE needed to defend floor
  ↓
Annual budget exhausts
  ↓
Cannot defend floor → Price falls below floor
  ↓
Fewer projects profitable → Lower issuance
  ↓
System stabilizes until next year's budget
```

**Mechanism 2: CEA Brake Factor**
```
High XCR issuance
  ↓
Market cap grows relative to CQE budget
  ↓
Stability ratio rises (Market Cap / Annual CQE Budget)
  ↓
Brake activates at 10:1 ratio → Minting rate reduced
  ↓
Lower issuance → Ratio stabilizes
  ↓
Brake releases as ratio falls
```

**Combined Effect**: These mechanisms constrain issuance when inflation pressure builds. The brake provides graduated response, while CQE budgets provide hard limits on floor defense.

**Key Parameters**:
- Brake thresholds: 10:1 light, 12:1 medium, 15:1 heavy (inflation-adjusted)
- CQE budget: 5% of annual private capital inflow, capped at 0.5% of active GDP
- Minting: `XCR = verified_sequestration * R * capacity * brake_factor`

### Net-Zero Transition Mechanics

The model implements a realistic transition where conventional mitigation (CM) and avoided deforestation dominate early (lower costs), then CDR takes over as net-zero approaches:

**Emissions-to-Sinks Ratio**:
```
E:S Ratio = Human_Emissions / (CDR + Ocean_Uptake + Land_Uptake)
```
Note: Avoided deforestation prevents emissions (subtracted from Human_Emissions), not added to sinks (avoids double-counting)

**Transition Logic**:
1. **Ratio > 2.0**: Full CM project initiation and crediting; AvDef/CDR continue normally
2. **Ratio 1.0-2.0**: CM project initiation ramps down linearly (factor = ratio - 1.0)
3. **Ratio ≤ 1.0 (Net-Zero - First Time)**:
   - **Conventional Mitigation**: XCR crediting STOPS **PERMANENTLY** (job done - emissions balanced)
   - System sets `net_zero_ever_reached = True` flag
   - Even if ratio later rises above 1.0, CM credits never resume
   - **Avoided Deforestation**: Continues being credited (stores carbon in biomass like CDR)
   - **CDR**: Continues being credited (active carbon removal)
   - Operational CM infrastructure CONTINUES reducing emissions (no XCR, but still working)

**Project Lifespans** (per Chen spec):
- **CDR**: 100 years (long-term carbon storage)
- **Conventional Mitigation**: 25 years (infrastructure turnover)
- **Avoided Deforestation**: 50 years (forest maturation cycle)

**Net-Zero Proximity Cost Penalty**:

CM projects face economic pressure as net-zero approaches because:
- **Truncated crediting period**: A CM project with 25yr lifespan starting at year 25 (operational ~year 27) would normally earn XCR for 25 years, but if net-zero hits at year 30, it only earns for ~3 years
- **Uncertain ROI**: Investors can't predict exactly when net-zero will hit, making late-stage CM projects risky
- **Cost multiplier** (very steep exponential, starts at E:S ratio 6.0):
  - E:S ratio 6.0+: 1.0x (no penalty)
  - E:S ratio 5.0: 2.5x cost (early concern)
  - E:S ratio 4.0: 6.3x cost (serious concern)
  - E:S ratio 3.0: 15.9x cost (very expensive, new projects stop here)
  - E:S ratio 2.0: 39.8x cost (prohibitive)
  - E:S ratio 1.0: 100x cost (impossible)

This naturally shifts capital from CM → CDR as net-zero approaches.

**Key Insight**:
- **Conventional Mitigation** avoids emissions → stops crediting **permanently** once net-zero first achieved (further crediting would be double-counting)
- **Avoided Deforestation** stores carbon in biomass → continues crediting like CDR throughout
- CM infrastructure continues operating and reducing emissions, just without XCR rewards
- **Permanent Termination**: If E:S ratio temporarily rises above 1.0 later (e.g., project failures), CM credits do NOT resume
- **Economic Decline**: CM costs rise exponentially (up to 10x) as E:S ratio drops from 2.0 → 1.0, making projects unprofitable before net-zero is reached

## Key Technical Concepts

### Carbon Cycle Modeling (Stocks vs Flows)

The model properly separates **stocks** (atmospheric CO2 concentration) from **flows** (emissions and sequestration rates):

**Stocks (measured in ppm or GtCO2):**
- Atmospheric CO2: Current concentration (starts at 420 ppm = ~3,200 GtCO2)
- This is the "bathtub water level" we're trying to reduce to 350 ppm

**Flows (measured in GtCO2/year):**
- BAU emissions: 40 GtCO2/year, peak around year 6, plateau, then very gradual late‑century decline (~0.2%/yr)
- GCR sequestration: Variable based on project deployment (0 → 100+ Gt/year)
- Net flow = Emissions + feedbacks - sinks - removals

**Critical Physics:**
- BAU emissions are determined by human activity (burning fossil fuels), NOT by atmospheric concentration
- Burning 100M barrels/day emits ~40 GtCO2/year regardless of whether CO2 is 420 ppm or 400 ppm
- **Atmospheric CO2 only declines when: Sinks + removals exceed emissions** (net-negative flow)

**Expected Timeline:**
- **Years 0-15:** CO2 RISES (emissions > sequestration) despite GCR system operating
- **Years 15-20:** CO2 stabilizes as system approaches net-zero
- **Years 20+:** CO2 DECLINES once net-negative flows dominate, toward 350 ppm target

This ensures the model respects the fundamental constraint that atmospheric CO2 cannot decline until global emissions reach net-zero.

### R-Value (Reward Multiplier)

From Chen paper (Definition Box 9):
- **1 XCR = 1/R tonnes of mitigated CO₂e with 100+ years durability**
- R enables adjustable rewards while maintaining single instrument
- **Purpose**: R is ONLY used to increase the reward for difficult mitigation (cost-effectiveness)
- XCR minting formula: `XCR = tonnes_mitigated * R`
- Example (price floor = $100):
  - CDR project at $100/tonne: R=1, receives 1 XCR per tonne
  - Solar project at $150/tonne: R=1.5, receives 1.5 XCR per tonne (0.67 tonnes per XCR)
  - Reforestation at $75/tonne: R=0.75, receives 0.75 XCR per tonne (1.33 tonnes per XCR)

**Project R-values** are set at project initiation based on marginal cost relative to marginal CDR cost and determine the XCR/tonne ratio. This ensures cost-effective allocation of rewards across different mitigation technologies.

### Technology Learning Curves & Policy Prioritization

The model implements **dynamic technology costs** and fixed (non‑penalizing) policy multipliers to capture realistic technology evolution:

#### Learning Curves (Cost Reduction with Deployment)

As technologies deploy at scale, costs decrease following experience curve dynamics:

- **Formula**: `Cost = Base_Cost × (Cumulative_Capacity / Reference_Capacity)^(-b)`
  where `b = log(1 - LR) / log(2)`

- **Learning Rates**:
  - **CDR**: 20% per doubling (aggressive improvement for early-stage tech)
  - **Conventional**: 12% per doubling (moderate, already mature technologies)
  - **Co-benefits**: 8% per doubling (defined, but co-benefits are a reward overlay)

#### Policy R-Multipliers (Channel Prioritization)

Policy multipliers are **fixed at 1.0** for CDR and conventional mitigation (no penalties or time shifts).

**Rationale**: R-values are purely cost-effectiveness based per Chen; any prioritization is handled by costs, capital availability, and capacity limits.

#### Conventional Capacity Limits

Conventional mitigation (solar, wind, efficiency) faces physical limits:

- **Capacity constraint**: Conventional availability tapers toward an 80% hard‑to‑abate frontier by year 60 using a sigmoid curve, then floors at a 10% residual tail
- **Effect**: Conventional project initiation tapers down as utilization approaches the frontier (no hard cutoff)
- **Implication**: Encourages transition to CDR as conventional opportunities saturate

**Combined Effect**: Conventional mitigation dominates early due to lower costs. As conventional capacity tightens and CDR costs fall, CDR takes a larger share.

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
    price_floor=100.0,                     # Initial XCR price floor (USD)
    inflation_target=0.02,                 # 2% baseline (0.001-0.10 range)
    adoption_rate=3.5,                     # Countries joining per year
    bau_peak_year=6,                       # BAU emissions peak year (default 6 = 2030)
    one_time_seed_capital_usd=20e9,        # One-time seed capital at market launch ($20B)
    cdr_material_budget_gt=500.0,          # CDR material budget before scarcity (500 Gt)
    cdr_material_cost_multiplier=4.0,      # Max cost increase when materials exhausted (4x)
    cdr_material_capacity_floor=0.25,      # Min capacity when materials exhausted (25%)
    cdr_buildout_stop_year=25,             # Stop NEW CDR projects after year 25
    cdr_buildout_stop_on_co2_peak=True     # Also stop buildout when CO2 peaks
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

**7 Main Tabs:**

1. **Climate & CO2** - Atmospheric CO2 concentration over time, GCR vs BAU trajectories, sequestration rates, operational projects
2. **XCR Economics** - Total supply, minting/burning dynamics, cumulative statistics
3. **Market Dynamics** - Market price vs floor, investor sentiment, inflation tracking, stability ratio, CEA warnings
4. **Projects** - Portfolio analysis by country and channel, project status over time, failure rates, country adoption & CQE budget growth
5. **Technology Economics** - **NEW!** Learning curves, policy R-multipliers, channel profitability, conventional capacity limits
   - Technology cost evolution (experience curves showing cost reduction over time)
   - Policy multipliers are fixed at 1.0 per Chen (no time-shifted priorities)
   - Channel profitability comparison (shows when each technology becomes economically viable)
   - Conventional capacity availability (taper to residual floor)
6. **Climate Equity** - OECD vs non-OECD XCR flows, wealth transfer analysis, country-level net positions
7. **Data Table** - Full simulation data with sorting, filtering, and CSV export (includes all new transparency columns)

**Interactive Controls (Sidebar):**
- Simulation years: 10-200 (default 100)
- XCR price floor (initial): $0-$999
- GCR adoption rate: 0-10 countries/year
- Enable/disable audits
- Random seed for reproducibility
- **BAU Emissions Peak Year**: Calendar year when BAU emissions peak (2024-2044, default 2030)
- **One-Time Seed Capital**: Initial capital deployed at XCR market launch ($0-$200B, default $20B)
- **CDR Material Budget**: Total CDR before material scarcity increases costs (100-2000 Gt, default 500 Gt)
- **CDR Material Cost Multiplier**: Maximum cost increase when materials exhausted (1.0-10.0x, default 4.0x)
- **CDR Material Capacity Floor**: Minimum project initiation rate when materials exhausted (10-50%, default 25%)
- **CDR Buildout Stop Year**: Year when NEW CDR project construction stops (10-100, default 25)
- **Stop CDR Buildout at CO2 Peak**: Also stop NEW CDR projects when atmospheric CO2 peaks and starts declining (checkbox, default True)
- CDR learning rate (per doubling)
- Conventional learning rate (per doubling)
- Scale damping full‑scale deployment (Gt)
- Sigmoid damping slope
- Monte Carlo runs (ensemble count)
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
- **Inflation Target**: 2% guidance; inflation stays at 0 pre‑start, then is corrected toward target
- **CEA Brake**: Thresholds 8:1 / 10:1 / 12:1 / 15:1 (inflation‑adjusted)
- **CQE Budget**: 5% of annual private capital inflow, capped at 0.5% of active GDP
- **Price Floor Revisions**: Every 5 years based on roadmap progress, inflation, and temperature
- **BAU Emissions Flow**: 40 GtCO2/year at year 0, grows 1%/year until peak (configurable via `bau_peak_year` parameter, default year 6), plateau to year 60, then slow late‑century decline (~0.2%/yr)
- **One-Time Seed Capital**: `one_time_seed_capital_usd` (default $20B, configurable $0-$200B) - deployed ONCE at XCR market launch to bootstrap initial supply
- **CDR Material Budget**: `cdr_material_budget_gt` (default 500 Gt, configurable 100-2000 Gt) - total CDR before material scarcity increases costs
- **CDR Material Cost Multiplier**: `cdr_material_cost_multiplier` (default 4.0x, configurable 1.0-10.0x) - maximum cost increase when materials exhausted
- **CDR Material Capacity Floor**: `cdr_material_capacity_floor` (default 0.25, configurable 0.10-0.50) - minimum project initiation rate when materials exhausted
- **CDR Buildout Stop Year**: `cdr_buildout_stop_year` (default 25, configurable 10-100) - stop NEW CDR project initiation after this year
- **CDR Buildout Stop on CO2 Peak**: `cdr_buildout_stop_on_co2_peak` (default True) - also stop NEW CDR projects when atmospheric CO2 peaks and starts declining
- **Capacity Limits**: Conventional 30 Gt/yr, Avoided Deforestation 5 Gt/yr; CDR 20 Gt/yr (material-constrained)
- **Auditor Error Rate**: 1% (Class 3 operational risk)
- **Chaos Monkey**: 5% chance per year of 0.5-1.5% inflation shock (only after GCR start)

### Gigatonne-Scale Operation

The model uses **deployment-based scale damping** where project size grows with cumulative industry experience, not calendar time.

**Learning-by-Doing Curve (Project Scale Damping)**:
- Sigmoid from **15% to 100%** scale across **0 → 25 Gt** cumulative deployment (industry-wide).
- Midpoint at ~**7.5 Gt** (30% of full scale) for a smooth transition.

**Scaling Mechanics**:
- Base project scale: **10-100 MT/year** (random uniform).
- Actual scale: `base_scale × damper(cumulative_gt)`.
- Project initiation: **Capital- and capacity-limited**, scaled by climate urgency, with sequential capital allocation (avoided deforestation → conventional → CDR; no per‑country caps).
- Development lag: **1-2 years** before becoming operational.
- CEA brake and CQE budget caps constrain aggressive growth.

**Interaction with Learning Curves**:
- Cost learning curves: **CDR 20%** and **Conventional 12%** cost reduction per doubling.
- Scale learning curves: Industry-wide; experience in one channel supports scale in the other.
- Co-benefit overlay: **15% of minted XCR** redistributed by project co-benefit scores (no extra tonnes).

**Realistic Constraints**:
- Stochastic failure: **2% annual decay rate**.
- Economic limits: CEA brake + CQE budget caps.
- Physical limits: **Conventional 30 Gt/yr**, **Avoided Deforestation 5 Gt/yr**, **CDR 20 Gt/yr**.

Located in `ProjectsBroker.__init__()` (gcr_model.py:419):
- **Base Costs**: CDR=$100/tonne, Conventional=$80/tonne, Avoided Deforestation=$60/tonne
- **Project Scale**: 10M-100M tonnes/year base (damped by cumulative deployment)
- **Scale Damping**: Enabled by default, full scale at 25 Gt cumulative deployment (min scale ~15%)
- **Count Damping**: Project counts ramp with cumulative deployment (min 40% early, rising to full scale)
- **Sigmoid Slope**: Controls the ramp speed for scale/count damping and the CDR learning-rate taper
- **CDR Capacity Limit**: 20 Gt/yr (energy, storage, materials constraints)
- **Project Initiation Rate**: Capital‑limited (no per‑country caps), scaled by urgency
- **Development Time**: 2-4 years randomly assigned
- **Project Lifespans**: CDR=100yr, Conventional=25yr, Avoided Deforestation=50yr
- **Project Failure**: 2% annual stochastic decay rate
- **Resource Depletion**: Logarithmic scaling (15% per order-of-magnitude project count)

## Data Structures

### Project Object (gcr_model.py:26)
```python
@dataclass
class Project:
    id: str
    channel: ChannelType  # CDR, CONVENTIONAL, AVOIDED_DEFORESTATION
    country: str
    start_year: int
    development_years: int  # 2-4 years randomly assigned
    annual_sequestration_tonnes: float
    marginal_cost_per_tonne: float
    r_base: float  # Base R-value from cost-effectiveness
    r_effective: float  # Effective R-value (r_base × policy_multiplier) - used for XCR minting
    status: ProjectStatus  # DEVELOPMENT, OPERATIONAL, FAILED
    health: float  # 1.0 = healthy, decays stochastically
    total_xcr_minted: float
    years_operational: int  # Track operational lifespan (increments annually)
    max_operational_years: int  # Channel-specific: CDR=100, CM=25, AvDef=50
```

Note: Projects store both `r_base` (cost-effectiveness) and `r_effective` (with policy multiplier applied). XCR minting uses `r_effective` which is locked in at project creation. Projects retire when `years_operational >= max_operational_years`. CDR, Conventional, and Avoided Deforestation projects are initiated; co-benefits are handled as an overlay.

### Simulation Output DataFrame

**Core Columns**:
Year, CO2_ppm, BAU_CO2_ppm, CO2_Avoided, Inflation, Market_Price, Price_Floor, Sentiment,
XCR_Supply, XCR_Minted, XCR_Burned_Annual, XCR_Burned_Cumulative, Cobenefit_Bonus_XCR,
Projects_Total, Projects_Operational, Projects_Development, Projects_Failed,
Sequestration_Tonnes, CDR_Sequestration_Tonnes, Conventional_Mitigation_Tonnes, Avoided_Deforestation_Tonnes,
Reversal_Tonnes, Human_Emissions_GtCO2, Conventional_Installed_GtCO2, CEA_Warning, CQE_Spent, XCR_Purchased,
Active_Countries, CQE_Budget_Total, Capacity

**CQE & Inflation Columns**:
- **CEA_Brake_Factor**: Minting rate multiplier (1.0 = no brake)
- **Annual_CQE_Spent**: CQE spending this year (resets annually)
- **Annual_CQE_Budget**: Total annual CQE cap (global, GDP-capped)
- **CQE_Budget_Utilization**: Percentage of annual budget used (0.0-1.0)

**Capital Market Columns**:
- `Net_Capital_Flow`, `Capital_Demand_Premium`, `Forward_Guidance`
- `Capital_Inflow_Cumulative`, `Capital_Outflow_Cumulative`

**Climate Physics Columns**:
- `Temperature_Anomaly`, `Ocean_Uptake_GtC`, `Land_Uptake_GtC`, `Airborne_Fraction`
- `Ocean_Sink_Capacity`, `Land_Sink_Capacity`, `Permafrost_Emissions_GtC`, `Fire_Emissions_GtC`
- `Cumulative_Emissions_GtC`, `Climate_Risk_Multiplier`, `C_Ocean_Surface_GtC`, `C_Land_GtC`

**Technology & Policy Columns**:
- `CDR_Cost_Per_Tonne`, `Conventional_Cost_Per_Tonne`
- `CDR_Cumulative_GtCO2`, `Conventional_Cumulative_GtCO2`
- `CDR_Policy_Multiplier`, `Conventional_Policy_Multiplier`
- `CDR_R_Base`, `CDR_R_Effective`, `Conventional_R_Base`, `Conventional_R_Effective`
- `CDR_Profitability`, `Conventional_Profitability`
- `Conventional_Capacity_Utilization`, `Conventional_Capacity_Available`, `Conventional_Capacity_Factor`
- `CDR_Material_Utilization`, `CDR_Material_Cost_Factor`, `CDR_Material_Capacity_Factor` (Feature 3: material constraints)
- `CDR_Buildout_Stopped`, `CDR_Buildout_Stop_Year` (Feature 4: buildout stop)

All transparency columns are exported to CSV and visible in the dashboard tabs.

## Development Notes

### Adding New Agent Behavior
- Each agent class is self-contained with clear responsibilities
- Agent state should remain internal; interactions happen through method calls
- Maintain execution order in `run_simulation()` to preserve causal relationships

### Modifying Economic Parameters

**Core Economic Parameters**:
- **Sigmoid damping sharpness** (k=12.0 in CentralBankAlliance): Controls how aggressively banks brake during inflation
- **Sentiment dynamics** (InvestorMarket): 3% decay on new warnings, 0.5% on persistent warnings; inflation decay 6%/3%/0.5% at 3x/2x/1.5x target; recovery is 2% of gap plus CO2/forward-guidance bonuses
- **Inflation correction**: 25-40% rate toward 2% target each year
- **One-time seed capital** (CapitalMarket): `one_time_seed_capital` ($20B default, configurable $0-$200B) deploys ONCE at XCR market launch (year 3) to bootstrap initial XCR supply. After seed deployment, private capital flows sustain the market based on sentiment.
- **Capital demand neutrality**: Starts around ~0.6 and ramps down to ~0.3 over ~10 years after XCR start (net inflows once `combined_attractiveness` exceeds the current threshold)
- **Project failure rates**: 2% annual stochastic decay
- **Clawback severity**: Currently 50% of lifetime XCR burned on audit failure
- **Price floor adjustments**: 5-year revision cycle with locked yields between revisions
- **Adoption rate**: Controls how quickly countries join (affects GDP cap and project allocation)

**Inflation Constraint Parameters**:
- **CEA brake thresholds** (`CEA.calculate_brake_factor()` - gcr_model.py:150):
  - Base thresholds at 2% inflation: warning 8:1, brake 10:1 / 12:1 / 15:1
  - Thresholds scale with **realized inflation** (lower inflation → lenient, higher inflation → strict)
  - Heavy brake floor ranges from ~30% (low inflation) to ~1% (very high inflation)
- **Budget utilization brake**:
  - Starts at 90% of annual CQE cap, floors at 25%
- **CQE budget** (`CentralBankAlliance.update_cqe_budget()` - gcr_model.py:374):
  - 5% of annual private capital inflow, capped at 0.5% of active GDP
  - Global annual cap (not per-country budgets)

**Learning Curve Parameters** (`ProjectsBroker.__init__()` - gcr_model.py:238):
- **Learning rates**: CDR=20%, Conventional=12% (dashboard sliders can override)
  - Modify to explore optimistic/pessimistic technology scenarios
  - Higher learning rate = faster cost reduction
- **Reference capacity**: Set on first deployment (used as baseline for learning calculations)
- **Resource depletion**: Logarithmic cost lift (1 + 0.15 × log10(project_count + 1))
  - Balances learning curve gains with resource scarcity
- **Co-benefit pool**: `cobenefit_pool_fraction` (0.15) holds back XCR for redistribution based on project co-benefit scores

**Policy Prioritization Parameters** (`CEA.calculate_policy_r_multiplier()` - gcr_model.py:157):
- **Multipliers**: Fixed at 1.0 for CDR and conventional mitigation (no penalties)
- **Co-benefits**: Overlay only; no time‑varying multipliers

**Capacity Constraint Parameters** (`ProjectsBroker.__init__()` - gcr_model.py:260):
- **Conventional capacity frontier**: 80% by year 60 (default) with a 10% residual floor
- **Limit reach year**: 60 (year when limit is hit)
- **Taper**: Conventional initiation tapers as utilization approaches the limit (no hard cutoff)
- Adjust these to model different mitigation potential assumptions

**Conventional Budget Depletion** ("easy stuff first" mechanics):
- **Budget**: 1000 Gt total "easy" conventional mitigation potential
- **Cost multiplier**: 4.0x maximum when budget exhausted (hard-to-abate transition)
- **Capacity floor**: 10% minimum project initiation when budget exhausted
- **Sigmoid transition**: Centered at 70% utilization, costs/capacity degrade sharply 70-100%
- **Effect**: Early conventional is cheap ($18-25/tonne), rises to $50+/tonne as budget depletes
- **Crossover**: CDR becomes cost-competitive when conventional budget ~80-100% utilized

**CDR Material Constraints** ("material scarcity" mechanics):
- **Budget**: `cdr_material_budget_gt` (default 500 Gt, configurable 100-2000 Gt) - total "easy" CDR before material scarcity (limestone, energy, water, steel) increases costs
- **Cost multiplier**: `cdr_material_cost_multiplier` (default 4.0x, configurable 1.0-10.0x) - maximum cost increase when materials exhausted
- **Capacity floor**: `cdr_material_capacity_floor` (default 25%, configurable 10-50%) - minimum project initiation rate when materials exhausted
- **Sigmoid transition**: Centered at 60% utilization, costs/capacity degrade sharply 60-100%
- **Effect**: Early CDR benefits from learning curves (costs fall), but material scarcity eventually dominates (costs rise)
- **Buildout phase only**: Material inflation applies during NEW project construction. Once operational, projects only face opex costs (energy)
- **Interaction with learning**: At low deployment (0-300 Gt), learning dominates. At high deployment (300-500 Gt), material scarcity dominates.

**CDR Buildout Stop** ("prevent overshoot" mechanics):
- **Time-based stop**: `cdr_buildout_stop_year` (default 25 years, configurable 10-100) - stop NEW CDR project initiation after this year
- **CO2 peak-based stop**: `cdr_buildout_stop_on_co2_peak` (default True) - also stop NEW CDR projects when atmospheric CO2 concentration peaks and starts declining (2-3 consecutive years of decline)
- **Whichever comes first**: If CO2 peaks at year 20 and buildout stop at year 25, buildout stops at year 20
- **Existing projects continue**: Operational CDR projects keep running (opex only - energy costs), maintaining current removal capacity
- **Effect**: Prevents CO2 overshoot below 350 ppm target by freezing CDR capacity once measurable drawdown is achieved
- **Rationale**: Net-zero is when CDR really gets started (emissions balanced). CO2 peak proves we have enough CDR capacity for measurable atmospheric drawdown. Continued expansion would cause excessive removal below target.

### Understanding R-Value Mechanics
- When modifying project economics, remember: Higher R_effective = more XCR per tonne
- Project initiation gate uses: `(market_price * brake_factor) >= marginal_cost`
- **R_base** captures cost-effectiveness, **R_effective** = R_base × policy_multiplier (currently fixed at 1.0)
- XCR minting always uses R_effective (locked in at project creation)
- **Important**: R is for cost-effectiveness and policy prioritization, not macro stability control

### Common Calibration Points

**General Issues**:
- If CO2 isn't reducing fast enough: Increase project sequestration scale, decrease base costs, or increase adoption rate
- If inflation spirals: Reduce CQE intervention volume, increase sigmoid damping, or adjust inflation correction rate
- If too many projects fail: Decrease stochastic failure rate or audit strictness
- If market price crashes: Check sentiment decay rates and stability ratio thresholds
- If country adoption too slow/fast: Adjust adoption_rate parameter (default 3.5/year)

**Inflation Constraint Issues** (NEW):
- If brake never activates: Reduce CQE budgets (smaller denominator → higher ratio), increase price floor (higher market cap), or lower brake threshold (<10:1)
- If brake activates too aggressively: Increase CQE budgets, lower price floor, or raise brake thresholds (>10:1)
- If annual budgets never exhaust: Reduce budget sizes significantly (try 50% of default), or increase floor defense intensity
- If budgets exhaust too quickly: Increase annual budgets, reduce price floor (less CQE needed), or increase sigmoid damping (less aggressive defense)
- If issuance not inflation-constrained: Check brake_factor column (should be <1.0 in some years), check CQE_Budget_Utilization (should reach >50% in some years)
- To test constraint mechanisms: Run `venv/bin/python test_inflation_constraint.py` to verify brake and budget dynamics

**Technology Transition Issues**:
- If CDR never becomes competitive: Increase CDR learning rate (>20%), reduce CDR base costs, or reduce conventional budget (faster depletion)
- If conventional dominates too long: Reduce `conventional_budget_gt` (default 1000 Gt), increase `conventional_budget_cost_multiplier` (default 4.0x)
- If transition happens too early: Increase `conventional_budget_gt` to delay hard-to-abate phase
- If the transition feels too abrupt: Lower `conventional_budget_cost_multiplier` or raise capacity floor
- If costs drop unrealistically fast: Reduce learning rates or increase the depletion coefficient (0.15 in the log scaling)
- If costs don't drop enough: Increase learning rates, ensure projects are deploying (check profitability), reduce resource depletion

**CDR Material Constraint Issues** (NEW - Feature 3):
- If CDR costs rise too quickly: Increase `cdr_material_budget_gt` (default 500 Gt), reduce `cdr_material_cost_multiplier` (default 4.0x)
- If CDR costs never rise: Check `CDR_Material_Utilization` column - ensure cumulative deployment exceeds 60% of budget
- If material constraints too restrictive: Increase `cdr_material_capacity_floor` (default 25%), or increase budget
- If material constraints too lenient: Decrease budget or increase cost multiplier to force earlier constraint binding
- To test material inflation: Run scenarios with tight budget (250 Gt) vs generous (1000 Gt) and compare CDR deployment curves

**CDR Buildout Stop Issues** (NEW - Feature 4):
- If CO2 overshoots below 350 ppm: Reduce `cdr_buildout_stop_year` (default 25) to stop buildout earlier, or ensure `cdr_buildout_stop_on_co2_peak` is enabled (default True)
- If CO2 never reaches 350 ppm: Increase buildout stop year (50-100) to allow more CDR capacity, or disable CO2 peak-based stop
- If buildout stops too early: Check `CDR_Buildout_Stop_Year` column to see when stop triggered, adjust year or disable CO2 peak trigger
- If existing CDR projects insufficient: Buildout stop only prevents NEW projects - existing projects continue. May need to increase project scale or reduce costs to deploy more capacity before stop triggers
- To test overshoot prevention: Run 100-year scenario with default settings, verify CO2 peaks (starts declining), buildout stops, and CO2 stabilizes near 350 ppm without excessive overshoot
- **Important**: CO2 peak detection requires 2 consecutive years of decline to avoid false peaks from noise

**BAU Emissions Trajectory Issues** (NEW - Feature 2):
- If emissions peak too early/late: Adjust `bau_peak_year` parameter (default 6 = 2030)
- Early peak (year 3-5): Models aggressive near-term climate action, higher initial emissions baseline
- Late peak (year 10-15): Models delayed action, continued emissions growth
- Peak timing affects forward guidance and project urgency in early years

**Debugging Technology Dynamics**:
- Check Technology Economics dashboard tab to visualize cost curves, capacity taper, and profitability
- Export DataFrame and examine transparency columns (costs, cumulative deployment, R-values, profitability)
- Verify conventional capacity reaches the intended frontier year (check `Conventional_Capacity_Utilization` and `Conventional_Capacity_Factor`)

## Future Roadmap

- **Detailed Mitigation Breakout**: Split physical mitigation channels into specific technology types (e.g., DAC vs. BECCS, Wind vs. Solar) to better account for resource utilization, land-use competition, and energy system constraints.
- **Regional Climate Impacts**: Incorporate regional climate vulnerabilities into project failure rates and country participation incentives.
- **Non-CO2 Greenhouse Gases**: Expand the model to include Methane (CH4) and Nitrous Oxide (N2O) with appropriate GWP-100 characterization.
