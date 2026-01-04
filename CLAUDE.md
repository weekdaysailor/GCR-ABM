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
- Monitors stability ratio (XCR Market Cap / Annual CQE Budget)
- **Inflation-Adjusted CEA Brake** (PRIMARY CONSTRAINT): Brake thresholds and floor dynamically adjust based on inflation target
  - **Low inflation target** (e.g., 0.5%): Lenient thresholds, higher brake floor (30%)
    - Brake starts at 17.5:1 ratio
    - Heavy brake floor: 30% of normal minting rate
    - Accommodative: Allows substantial issuance for rapid climate action
  - **Baseline** (2% target): Moderate thresholds, 13% brake floor
    - Warning: 8:1, Brake start: 10:1, Heavy: 15:1
    - Standard constraint level
  - **High inflation target** (e.g., 6%): Strict thresholds, low brake floor (3%)
    - Brake starts at 4:1 ratio
    - Heavy brake floor: 3% of normal minting rate
    - Restrictive: Prioritizes price stability over rapid scaling
  - **Impact**: Changing inflation target from 0.5% → 6% reduces issuance by ~86%
  - **See**: `docs/inflation_adjusted_brake.md` for detailed mechanics
  - Creates negative feedback: High issuance → High ratio → Brake → Lower issuance
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
- **Annual CQE Budget Caps**:
  - Each country has annual CQE budget (e.g., USA: $50B/year = 10% of QE capacity)
  - Total starting budget (5 countries): ~$68B/year
  - Total budget at full adoption (50 countries): ~$196B/year
  - Budget resets each year (tracked in `annual_cqe_spent`)
  - **Hard cap**: Cannot defend floor when annual budget exhausted
  - Price can fall below floor until next year
  - **Realistic levels**: Designed to be binding constraint at gigatonne scale
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
4. `cea.update_policy()` - Monitor stability ratio, calculate brake factor, adjust price floor (periodic 5-year revisions)
5. `projects_broker.initiate_projects()` - Start new projects where economics favor it
6. `projects_broker.step_projects()` - Advance all projects (development progress, stochastic decay)
7. `auditor.verify_and_mint_xcr()` - Audit operational projects, mint/burn XCR **with brake factor applied**
8. `central_bank.defend_floor()` - CQE intervention if price < floor (subject to annual budget cap)
9. Update CO2 levels based on verified sequestration

**Critical Flow**: Projects sequester CO2 → Auditor verifies → XCR minted fresh (increases supply) × **brake_factor** × capacity → Market trades XCR → If price < floor → Central banks buy with CQE (annual budget cap) → CEA monitors stability → Calculates brake factor → Adjusts price floor periodically

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

**Combined Effect**: These mechanisms create negative feedback loops that automatically constrain issuance when inflation pressure builds. The brake provides graduated response (50% → 25% → 10% minting reduction), while budget caps provide hard limits (cannot defend floor when exhausted).

**Key Parameters**:
- Brake thresholds: 10:1 light, 12:1 medium, 15:1 heavy
- Annual CQE budgets: GDP-proportional, reset yearly
- Brake calculation: `XCR_minted = base_minting × capacity × brake_factor`

## Key Technical Concepts

### Carbon Cycle Modeling (Stocks vs Flows)

The model properly separates **stocks** (atmospheric CO2 concentration) from **flows** (emissions and sequestration rates):

**Stocks (measured in ppm or GtCO2):**
- Atmospheric CO2: Current concentration (starts at 420 ppm = ~3,200 GtCO2)
- This is the "bathtub water level" we're trying to reduce to 350 ppm

**Flows (measured in GtCO2/year):**
- BAU emissions: Constant 40 GtCO2/year growing at 1% (fossil fuels + land use)
- GCR sequestration: Variable based on project deployment (0 → 100+ Gt/year)
- Net flow = Emissions - Sequestration

**Critical Physics:**
- BAU emissions are determined by human activity (burning fossil fuels), NOT by atmospheric concentration
- Burning 100M barrels/day emits ~40 GtCO2/year regardless of whether CO2 is 420 ppm or 400 ppm
- **Atmospheric CO2 only declines when: Sequestration > Emissions** (net-zero achieved)

**Expected Timeline:**
- **Years 0-15:** CO2 RISES (emissions > sequestration) despite GCR system operating
- **Years 15-20:** CO2 stabilizes as system approaches net-zero
- **Years 20+:** CO2 DECLINES (sequestration > emissions) toward 350 ppm target

This ensures the model respects the fundamental constraint that atmospheric CO2 cannot decline until global emissions reach net-zero.

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

### Technology Learning Curves & Policy Prioritization

The model implements **dynamic technology costs** and **time-dependent policy prioritization** to capture realistic technology evolution and strategic climate policy goals:

#### Learning Curves (Cost Reduction with Deployment)

As technologies deploy at scale, costs decrease following experience curve dynamics:

- **Formula**: `Cost = Base_Cost × (Cumulative_Capacity / Reference_Capacity)^(-b)`
  where `b = log(1 - LR) / log(2)`

- **Learning Rates**:
  - **CDR**: 20% per doubling (aggressive improvement for early-stage tech)
  - **Conventional**: 12% per doubling (moderate, already mature technologies)
  - **Co-benefits**: 8% per doubling (nature-based, limited technological gains)

- **Result**: CDR starts expensive ($100+/tonne) but becomes cost-competitive ($50-70/tonne) by 2060-2080 as deployment scales

#### Policy R-Multipliers (Channel Prioritization)

Policy applies time-dependent multipliers to R-values to prioritize conventional mitigation early and shift to CDR post-2050:

**Pre-2050 (Conventional First Era)**:
- CDR: `R_effective = R_base × 2.0` → Penalized (fewer XCR/tonne, less attractive)
- Conventional: `R_effective = R_base × 0.7` → Subsidized (more XCR/tonne, more attractive)
- Co-benefits: `R_effective = R_base × 0.8` → Slight subsidy

**Post-2050 (CDR Ramp-Up Era)**:
- CDR: `R_effective = R_base × 1.0` → Normalized (full market access)
- Conventional: `R_effective = R_base × 1.2` → Slight penalty (peak deployment past)
- Co-benefits: `R_effective = R_base × 1.0` → Normalized

**Transition**: Smooth sigmoid curve 2045-2055 avoids cliff effects

**Rationale**: Aligns with Paris Agreement strategies—maximize near-term emissions reductions (conventional mitigation) while CDR technologies mature, then transition to CDR for net-negative emissions post-2050.

#### Conventional Capacity Limits

Conventional mitigation (solar, wind, efficiency) faces physical limits:

- **Capacity constraint**: 80% of emissions potential by year 60 (2060)
- **Effect**: After ~80% utilization, no new conventional projects can initiate
- **Implication**: Forces economic transition to CDR as conventional opportunities saturate

**Combined Effect**: Early years dominated by conventional mitigation (double advantage: lower costs + policy subsidy). Mid-century transition as CDR costs fall and policy shifts. Late simulation dominated by CDR as conventional capacity exhausted.

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
    inflation_target=0.02,  # 2% baseline (0.001-0.10 range)
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

**7 Main Tabs:**

1. **Climate & CO2** - Atmospheric CO2 concentration over time, GCR vs BAU trajectories, sequestration rates, operational projects
2. **XCR Economics** - Total supply, minting/burning dynamics, cumulative statistics
3. **Market Dynamics** - Market price vs floor, investor sentiment, inflation tracking, stability ratio, CEA warnings
4. **Projects** - Portfolio analysis by country and channel, project status over time, failure rates, country adoption & CQE budget growth
5. **Technology Economics** - **NEW!** Learning curves, policy R-multipliers, channel profitability, conventional capacity limits
   - Technology cost evolution (experience curves showing cost reduction over time)
   - Policy multiplier transitions (conventional priority → CDR priority post-2050)
   - Channel profitability comparison (shows when each technology becomes economically viable)
   - Conventional capacity utilization (80% limit visualized)
6. **Climate Equity** - OECD vs non-OECD XCR flows, wealth transfer analysis, country-level net positions
7. **Data Table** - Full simulation data with sorting, filtering, and CSV export (includes all new transparency columns)

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
- **Inflation Target**: 2% baseline (configurable 0.1%-10%, PRIMARY constraint on issuance)
- **Inflation Correction**: 25-40% correction rate toward target
- **Inflation-Adjusted CEA Brake**: Thresholds and floor scale with inflation target
  - Low target (0.5%): Brake starts 17.5:1, floor 30% (lenient)
  - Baseline (2%): Brake starts 10:1, floor 13% (moderate)
  - High target (6%): Brake starts 4:1, floor 3% (strict)
  - **Impact**: Changing target from 0.5%→6% reduces issuance by ~86%
- **Annual CQE Budgets**: GDP-proportional, reset yearly, hard spending cap
- **Price Floor Revisions**: Every 5 years based on roadmap progress
- **BAU Emissions Flow**: 40 GtCO2/year constant emission rate (fossil fuels + land use)
  - Grows at 1% annually (economic growth increases fossil fuel use)
  - ~5.1 ppm/year initially, growing to ~6.8 ppm/year by year 50
  - **Critical**: Emissions are a FLOW determined by human activity, not % of atmospheric stock
  - CO2 only declines when sequestration exceeds emissions (net-zero achieved)
- **CQE Budgets**: GDP-proportional across 50 countries - USA: $50B/year (10% QE capacity)
  - Total starting (5 founding): ~$68B/year
  - Total all 50 countries: ~$196B/year
  - **Realistic levels** designed to be binding constraint at gigatonne scale
- **Auditor Error Rate**: 2% (Class 3 operational risk)
- **Chaos Monkey**: 5% chance per year of 0.5-1.5% inflation shock

### Gigatonne-Scale Operation

The model implements **deployment-based learning curves** where project scale grows with cumulative industry experience, not calendar time:

**Learning-by-Doing Curve (Project Scale Damping)**:

Project sizes scale with cumulative deployment across all channels:
- **0-10 Gt deployed**: 15-20% scale → 1.5-20 MT/project (pilot scale)
- **10-100 Gt deployed**: 20-40% scale → 2-40 MT/project (early commercial)
- **100-300 Gt deployed**: 40-90% scale → 4-90 MT/project (commercial scale)
- **300-500 Gt deployed**: 90-100% scale → 9-100 MT/project (industrial scale)
- **500+ Gt deployed**: 100% scale → 10-100 MT/project (full industrial scale)

**Key Insight**: As the industry deploys more total capacity, engineers learn to build bigger facilities. A world that has deployed 300 Gt cumulatively has the experience to build 90 MT plants; a world with only 10 Gt deployed is still at pilot scale.

**Expected Aggregate Sequestration Timeline**:
- **Year 5**: ~1-2 Gt/year (early deployments, ~15% scale)
- **Year 10**: ~5-10 Gt/year (~20% scale, 20-30 Gt cumulative)
- **Year 20**: ~20-30 Gt/year (~60% scale, 150-200 Gt cumulative)
- **Year 25-30**: ~40-60 Gt/year (~95-100% scale, 300-600 Gt cumulative, net-zero achieved)
- **Year 35-50**: ~80-110 Gt/year (full scale, 1000+ Gt cumulative, net-negative emissions)

**Scaling Mechanics**:
- Base project scale: 10-100 MT/year (random uniform distribution)
- Scale damper applied at project creation: `actual_scale = base_scale × damper(cumulative_gt)`
- Damper uses sigmoid curve: 15% → 100% from 0 Gt → 500 Gt cumulative
- Inflection point: 150 Gt cumulative (mid-commercial transition)
- 300 projects/year initiation rate (with 50 active countries)
- Development lag (2-4 years) delays operational capacity
- CEA brake and CQE budget caps constrain aggressive growth

**Interaction with Learning Curves**:
- **Cost learning curves** (already present): Make projects **economically viable** over time
  - CDR: 20% cost reduction per doubling (expensive → cheap)
  - Conventional: 12% cost reduction per doubling
  - Co-benefits: 8% cost reduction per doubling
- **Scale learning curves** (NEW): Make projects **physically buildable** at larger scale
  - All channels: Scale increases with total cumulative deployment
  - Industry-wide learning: CDR experience helps conventional scaling and vice versa

**Realistic Constraints**:
- Learning-by-doing: Projects start small, scale as industry gains experience
- Development time: 2-4 years from initiation to operational
- Stochastic failure: 2% annual decay rate
- Economic limits: CEA brake (stability ratio) + CQE budget caps (inflation control)
- Physical limits: Channel-specific capacity caps (Gt/year)

Located in `ProjectsBroker.__init__()` (gcr_model.py:419):
- **Base Costs**: CDR=$100/tonne, Conventional=$80/tonne, Co-benefits=$70/tonne
- **Project Scale**: 10M-100M tonnes/year base (damped by cumulative deployment)
- **Scale Damping**: Enabled by default, full scale at 500 Gt cumulative deployment
- **Project Initiation Rate**: 2 projects per active country per channel per year (scales with adoption)
- **Maximum Rate**: 50 projects per channel per year (safety cap = 150 total/year)
- **Development Time**: 2-4 years randomly assigned
- **Project Failure**: 2% annual stochastic decay rate
- **Resource Depletion**: Logarithmic scaling (1.6x at 10,000 projects vs 151x with linear)

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
    r_base: float  # Base R-value from cost-effectiveness
    r_effective: float  # Effective R-value (r_base × policy_multiplier) - used for XCR minting
    status: ProjectStatus  # DEVELOPMENT, OPERATIONAL, FAILED
    health: float  # 1.0 = healthy, decays stochastically
    total_xcr_minted: float
```

Note: Projects store both `r_base` (cost-effectiveness) and `r_effective` (with policy multiplier applied). XCR minting uses `r_effective` which is locked in at project creation.

### Simulation Output DataFrame

**Core Columns** (original):
Year, CO2_ppm, BAU_CO2_ppm, CO2_Avoided, Inflation, XCR_Supply, XCR_Minted, XCR_Burned, Market_Price, Price_Floor, Sentiment, Projects_Total, Projects_Operational, Sequestration_Tonnes, CEA_Warning, CQE_Spent, Active_Countries, CQE_Budget_Total, Capacity

**Inflation Constraint Columns** (NEW):
- **CEA_Brake_Factor**: Minting rate multiplier (1.0 = no brake, 0.1 = heavy brake at 15:1 ratio)
- **Annual_CQE_Spent**: CQE spending this year (resets annually)
- **Annual_CQE_Budget**: Total annual CQE budget (sum of all active countries)
- **CQE_Budget_Utilization**: Percentage of annual budget used (0.0-1.0, 1.0 = exhausted)

**Transparency Columns** (for learning curves & policy):
- **Technology Costs** (learning-adjusted): `CDR_Cost_Per_Tonne`, `Conventional_Cost_Per_Tonne`
- **Cumulative Deployment** (learning progress): `CDR_Cumulative_GtCO2`, `Conventional_Cumulative_GtCO2`
- **Policy Multipliers**: `CDR_Policy_Multiplier`, `Conventional_Policy_Multiplier`
- **R-Values**: `CDR_R_Base`, `CDR_R_Effective`, `Conventional_R_Base`, `Conventional_R_Effective`
- **Profitability**: `CDR_Profitability`, `Conventional_Profitability`
- **Co-benefit Bonus**: `Cobenefit_Bonus_XCR` (Robin Hood redistribution overlay, no additional tonnes)
- **Capacity Constraints**: `Conventional_Capacity_Utilization`, `Conventional_Capacity_Available`

All transparency columns are exported to CSV and visible in the dashboard tabs.

## Development Notes

### Adding New Agent Behavior
- Each agent class is self-contained with clear responsibilities
- Agent state should remain internal; interactions happen through method calls
- Maintain execution order in `run_simulation()` to preserve causal relationships

### Modifying Economic Parameters

**Core Economic Parameters**:
- **Sigmoid damping sharpness** (k=12.0 in CentralBankAlliance): Controls how aggressively banks brake during inflation
- **Sentiment rates** (InvestorMarket): Decay (0.9, 0.85) vs recovery (0.05)
- **Inflation correction**: 25-40% rate toward 2% target each year
- **Project failure rates**: 2% annual stochastic decay
- **Clawback severity**: Currently 50% of lifetime XCR burned on audit failure
- **Price floor adjustments**: 5-year revision cycle with locked yields between revisions
- **Adoption rate**: Controls how quickly countries join (affects CQE budget growth)

**Inflation Constraint Parameters** (NEW):
- **CEA brake thresholds** (`CEA.calculate_brake_factor()` - gcr_model.py:150):
  - 10:1 ratio → Start brake (1.0x → 0.5x reduction)
  - 12:1 ratio → Medium brake (0.5x → 0.25x reduction)
  - 15:1 ratio → Heavy brake (0.1x, 90% reduction)
  - Adjust thresholds to make constraint tighter (lower ratios) or looser (higher ratios)
- **Annual CQE budgets** (`CentralBankAlliance.__init__()` - gcr_model.py:243):
  - Default: Sum of GDP-proportional country budgets (~$2.7T starting)
  - Hard cap enforced in `defend_floor()`
  - Reduce budgets to make constraint bite harder (exhaustion more likely)
  - Increase to allow more price floor defense before constraint activates

**Learning Curve Parameters** (`ProjectsBroker.__init__()` - gcr_model.py:238):
- **Learning rates**: CDR=20%, Conventional=12%
  - Modify to explore optimistic/pessimistic technology scenarios
  - Higher learning rate = faster cost reduction
- **Reference capacity**: Set on first deployment (used as baseline for learning calculations)
- **Resource depletion rate**: Currently 1.5% cost increase per project
  - Balances learning curve gains with resource scarcity
- **Co-benefit pool**: `cobenefit_pool_fraction` (0.15) holds back XCR for redistribution based on project co-benefit scores

**Policy Prioritization Parameters** (`CEA.calculate_policy_r_multiplier()` - gcr_model.py:157):
- **Transition timing**: Midpoint year 50, width 10 years (currently 2045-2055)
- **Pre-2050 multipliers**: CDR=2.0x penalty, Conventional=0.7x subsidy
- **Post-2050 multipliers**: CDR=1.0x neutral, Conventional=1.2x penalty
- **Sigmoid steepness**: k=0.8 controls smoothness of transition

**Capacity Constraint Parameters** (`ProjectsBroker.__init__()` - gcr_model.py:260):
- **Conventional capacity limit**: 80% (default)
- **Limit reach year**: 60 (year when limit is hit)
- Adjust these to model different mitigation potential assumptions

### Understanding R-Value Mechanics
- When modifying project economics, remember: Higher R_effective = fewer XCR per tonne
- Projects are profitable when: `(market_price / R_effective) >= marginal_cost`
- **R_base** captures cost-effectiveness, **R_effective** = R_base × policy_multiplier
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
- If CDR never becomes competitive: Increase CDR learning rate (>20%), reduce policy penalty multiplier (<2.0x), or delay conventional capacity limit
- If conventional dominates too long: Increase policy subsidy exit speed (higher k in sigmoid), advance transition midpoint (<50), or lower capacity limit year
- If technology transition too abrupt: Widen transition window (>10 years), reduce sigmoid steepness (k<0.8)
- If costs drop unrealistically fast: Reduce learning rates, increase resource depletion rate (>1.5% per project)
- If costs don't drop enough: Increase learning rates, ensure projects are actually deploying (check profitability), reduce resource depletion

**Debugging Technology Dynamics**:
- Check Technology Economics dashboard tab to visualize cost curves, policy transitions, and profitability
- Export DataFrame and examine transparency columns (costs, cumulative deployment, R-values, profitability)
- Verify conventional capacity hits limit around intended year (check `Conventional_Capacity_Utilization` column)
- Confirm policy multipliers transition smoothly (should see sigmoid curve, not step function)
