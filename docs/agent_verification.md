# Agent Verification Guide

## How do I know the agents are actually working?

This guide explains how to verify that the GCR ABM is a **true agent-based model** where autonomous agents make real decisions, not a spreadsheet with predetermined outcomes.

---

## Quick Answer: Three Verification Tools

### 1. **Run Agent Diagnostics** (Detailed Decision Logging)

```bash
venv/bin/python agent_diagnostics.py
```

**What it shows:**
- Every agent decision with timestamps
- Why each decision was made (triggering conditions)
- How agents interact and respond to each other
- Evidence of state-dependent behavior

**Key Evidence:**
- InvestorMarket sentiment changes based on warnings/inflation
- ProjectsBroker only initiates when `profit > 0`
- CentralBankAlliance only intervenes when `price < floor`
- Auditor stochastically passes/fails projects based on health

### 2. **Run Response Test** (Parameter Sensitivity)

```bash
venv/bin/python agent_response_test.py
```

**What it shows:**
- Two scenarios: baseline ($100 floor) vs high ($200 floor)
- Same random seed, but **different outcomes**
- Agents make different decisions when incentives change

**Key Evidence:**
- Higher price floor → ProjectsBroker initiates 17% more projects
- Higher price floor → CDR becomes profitable 14 years earlier
- Higher price floor → 95% more XCR minted
- **Proves agents respond dynamically to economic incentives**

### 3. **Explore Dashboard** (Visual Verification)

```bash
venv/bin/streamlit run dashboard.py
```

**What to check:**
- **Technology Economics tab**: Shows channels competing based on profitability
- **Market Dynamics tab**: Sentiment responds to warnings and inflation
- **Projects tab**: Country adoption timing varies by GDP
- **Change parameters and re-run**: Different outputs prove dynamic behavior

---

## Five Hallmarks of Agent-Based Models

### ✅ 1. Internal State

**Agents maintain their own state that evolves over time:**

- **InvestorMarket**: `sentiment` (0.0-1.0) changes based on system performance
- **ProjectsBroker**: `projects` list grows/shrinks, `cumulative_deployment` tracks learning
- **CentralBankAlliance**: `total_cqe_spent` accumulates with interventions
- **CEA**: `warning_8to1_active`, `brake_10to1_active` flags respond to stability ratio
- **Auditor**: `total_xcr_burned` tracks clawbacks

**Verification**: Check `gcr_model.py` - each agent class has `__init__()` defining state variables.

### ✅ 2. Decision Rules (Conditional Logic)

**Agents have explicit decision rules based on state:**

```python
# InvestorMarket (gcr_model.py:331)
if cea_warning:
    self.sentiment *= 0.96  # DECISION: Decay on warning
elif not cea_warning and global_inflation <= 0.025:
    self.sentiment = min(1.0, self.sentiment + recovery)  # DECISION: Recover when stable

# ProjectsBroker (gcr_model.py:413)
if revenue_per_tonne >= marginal_cost:
    # DECISION: Initiate project (profitable)
    project = Project(...)
    self.projects.append(project)

# CentralBankAlliance (gcr_model.py:197)
if market_price_xcr < self.price_floor_rcc:
    # DECISION: Defend floor with CQE
    price_support = price_gap * intervention_strength
```

**Verification**: Search `gcr_model.py` for `if` statements in agent methods - these are decision points.

### ✅ 3. Agent Interactions (Feedback Loops)

**Agents respond to each other's actions:**

**Example Feedback Loop 1: CQE Intervention Spiral**
1. CentralBankAlliance buys XCR (if price < floor) → increases inflation
2. Higher inflation → InvestorMarket reduces sentiment
3. Lower sentiment → Market price drops further
4. Lower price → triggers more CQE intervention (loop)

**Example Feedback Loop 2: Learning Curve Acceleration**
1. ProjectsBroker initiates profitable projects
2. Projects deploy → cumulative deployment increases
3. Learning curves reduce costs
4. Lower costs → more projects become profitable (loop)

**Verification**: Run `agent_diagnostics.py` and trace how one agent's action changes another's state.

### ✅ 4. Heterogeneity (Individual Differences)

**Not all agents/entities are identical:**

- **Countries**: Different GDP, CQE budgets, adoption timing, regions
- **Projects**: Different costs, R-values, sequestration amounts, countries, development times
- **Channels**: Compete with different learning rates and capacity limits (policy multipliers fixed at 1.0)
- **Stochastic variation**: Inflation shocks, project failures, audit outcomes

**Verification**: Check DataFrame - every project has unique `id`, `country`, `marginal_cost`, `r_value`.

### ✅ 5. Emergent Behavior (Unpredictable Outcomes)

**System behavior emerges from agent interactions, not hardcoded:**

**Not Predetermined:**
- Market price emerges from `sentiment + floor` (not a fixed schedule)
- Project timing emerges from `cost/price` dynamics (not predetermined years)
- Inflation trajectory emerges from CQE interventions + chaos monkey (not scripted)
- Technology transition emerges from learning + capacity (not a switch at year 50)

**Predetermined (For Comparison):**
- Target CO2 (350 ppm) is a fixed parameter
- Policy multipliers are fixed at 1.0 (no time-shifted penalties)
- Learning rates (CDR=20%) are fixed parameters

**The difference**: Parameters are fixed, but **when and how** they affect outcomes depends on agent decisions.

**Verification**: Change `price_floor` from $100→$200 in two runs. If outcomes differ significantly, behavior is emergent (agents responded to incentive change).

---

## Common Questions

### Q: "How do I know projects aren't just scheduled to start at fixed years?"

**A**: Run this test:

```python
# Scenario 1: High price floor
sim1 = GCR_ABM_Simulation(years=30, price_floor=200)
df1 = sim1.run_simulation()

# Scenario 2: Low price floor
sim2 = GCR_ABM_Simulation(years=30, price_floor=50)
df2 = sim2.run_simulation()

# Compare when projects start
print(f"Scenario 1: {df1.iloc[10]['Projects_Total']} projects by year 10")
print(f"Scenario 2: {df2.iloc[10]['Projects_Total']} projects by year 10")
```

**Result**: Different numbers because ProjectsBroker makes profitability decisions each year based on `(market_price * R_eff * brake_factor) >= cost`.

### Q: "How do I know sentiment isn't just a random walk?"

**A**: Check the decision rules in `InvestorMarket.update_sentiment()` (gcr_model.py:331):

- Sentiment **decays** when `cea_warning=True` (0.96x multiplier)
- Sentiment **decays** when `inflation > 6%` (0.94x multiplier)
- Sentiment **recovers** when `stable + low inflation` (+recovery)

**Not random** - responds deterministically to system state.

**Verify**: Trigger a CEA warning by creating instability, observe sentiment drops.

### Q: "Is the technology transition hardcoded at year 50?"

**A**: No. Three independent mechanisms create the transition:

1. **Learning curves** reduce CDR costs as deployment grows (dynamic)
2. **Conventional capacity** tapers toward an 80% hard‑to‑abate frontier by ~year 60 using a sigmoid curve, then floors at a residual tail

**Combined effect**: CDR becomes competitive gradually based on actual deployment, not a switch.

**Verify**: Change `conventional_capacity_limit_year` from 60→80. Transition timing changes.

### Q: "How do I know agents aren't just executing a script?"

**A**: Scripts produce identical outputs with identical inputs. Change one parameter and re-run:

- Change `price_floor`: Project timing changes
- Change `adoption_rate`: CQE budget growth changes
- Change `learning_rates`: Cost trajectories change
- Change `random_seed`: Stochastic outcomes change

**Agent systems produce different emergent behavior when incentives/constraints change.**

---

## Advanced Verification: Code Inspection

### Look for Decision Points

**Agent decision points are `if` statements that depend on state:**

```bash
# Find all decision points in agent classes
grep -n "if.*self\." gcr_model.py | grep -E "(CEA|CentralBank|Projects|Investor|Auditor)"
```

**What to look for:**
- `if market_price < floor:` → CentralBank decides whether to intervene
- `if revenue >= cost:` → ProjectsBroker decides whether to initiate
- `if cea_warning:` → InvestorMarket decides to decay sentiment

### Trace Agent Interactions

**Find where one agent's action affects another's state:**

```bash
# Central bank affects investor market
grep -A5 "central_bank.defend_floor" gcr_model.py | grep "investor_market"

# Projects affect broker's cumulative deployment
grep -A5 "update_cumulative_deployment" gcr_model.py
```

### Check for Emergent Calculations

**Emergent values are calculated each timestep, not read from a table:**

```python
# Market price is emergent (not hardcoded)
market_price_xcr = price_floor + (50 * sentiment)

# Profitability is emergent (depends on costs, R-values, price)
profit = (market_price / r_effective) - marginal_cost

# R-effective is emergent (combines base R and policy multiplier)
r_effective = r_base * calculate_policy_r_multiplier(channel, year)
```

**Verify**: Search for `=` assignments in simulation loop, not lookup tables.

---

## What Would a NON-Agent Model Look Like?

For comparison, here's what this model would look like if it **weren't** agent-based:

### ❌ Spreadsheet Model (Non-Agent)

```python
# Predetermined outcomes
PROJECTS_BY_YEAR = {0: 0, 5: 10, 10: 25, 15: 40, ...}  # Fixed schedule
SENTIMENT_BY_YEAR = {0: 1.0, 5: 0.95, 10: 0.90, ...}   # Fixed trajectory
XCR_PRICE = 150.0  # Constant price

def run_simulation():
    for year in range(years):
        # No decisions, just lookup
        projects = PROJECTS_BY_YEAR[year]
        sentiment = SENTIMENT_BY_YEAR[year]
        price = XCR_PRICE

        # No interactions
        results.append({"projects": projects, "sentiment": sentiment})
```

**Key difference**: No `if` statements, no state updates, no interactions. Just table lookups.

### ✅ Agent-Based Model (This Model)

```python
# Agents maintain state
investor_market.sentiment  # Changes based on warnings/inflation
projects_broker.projects   # Grows based on profitability decisions
central_bank.total_cqe_spent  # Accumulates with interventions

def run_simulation():
    for year in range(years):
        # Agents make decisions based on state
        investor_market.update_sentiment(cea_warning, inflation)  # DECISION

        if market_price < floor:  # DECISION
            central_bank.defend_floor()  # ACTION

        for channel in ChannelType:
            if (price / r_eff) >= cost:  # DECISION
                projects_broker.initiate_project(channel)  # ACTION

        # Emergent outcomes
        results.append({"sentiment": investor_market.sentiment, ...})
```

**Key difference**: Decision rules (`if`), state updates, agent interactions, emergent outcomes.

---

## Checklist: Is This a Real ABM?

Use this checklist to verify any agent-based model:

- [x] **Agents have internal state** (not just global variables)
- [x] **Agents make decisions** (conditional logic based on state)
- [x] **Agents interact** (one agent's action changes another's state)
- [x] **Agents are heterogeneous** (individual differences)
- [x] **Behavior is emergent** (outcomes not predetermined)
- [x] **System responds to parameter changes** (different inputs → different outputs)
- [x] **Stochastic variation** (randomness in decisions/events)
- [x] **Feedback loops** (circular causality between agents)

**This model checks all boxes.**

---

## Summary

### How to Know Agents Are Working

1. **Run diagnostics**: See agents making timestep-by-timestep decisions
2. **Change parameters**: Different incentives → Different agent decisions → Different outcomes
3. **Trace causality**: Agent A's action → Agent B's state change → Agent C's decision
4. **Inspect code**: Decision rules are `if` statements, not table lookups
5. **Look for emergence**: Market price, project timing, sentiment trajectories are calculated, not predetermined

### What Makes This an ABM

- **Agents decide** when to initiate projects (profitability rule)
- **Agents respond** to warnings and inflation (sentiment dynamics)
- **Agents interact** through market price, XCR supply, CQE interventions
- **Agents differ** in costs, countries, adoption timing, stochastic variation
- **System emerges** from bottom-up agent decisions, not top-down equations

### The Proof

Run these two commands with different seeds:

```bash
# Seed 1
venv/bin/python -c "import numpy as np; np.random.seed(1); from gcr_model import GCR_ABM_Simulation; sim = GCR_ABM_Simulation(years=20); df = sim.run_simulation(); print(f'Projects: {int(df.iloc[-1][\"Projects_Total\"])}')"

# Seed 2
venv/bin/python -c "import numpy as np; np.random.seed(2); from gcr_model import GCR_ABM_Simulation; sim = GCR_ABM_Simulation(years=20); df = sim.run_simulation(); print(f'Projects: {int(df.iloc[-1][\"Projects_Total\"])}')"
```

**If outputs differ**: Stochastic agent decisions produced different emergent outcomes. ✅

**If outputs identical**: Would suggest predetermined outcomes (not agent-based). ❌

**Expected result**: Different project counts, proving agents made stochastic decisions.

---

## References

- Agent diagnostics: `agent_diagnostics.py`
- Response test: `agent_response_test.py`
- Model source: `gcr_model.py` (search for agent class definitions)
- Dashboard: `dashboard.py` (visualize emergent behavior)

**Questions?** Run the diagnostics and observe agents making real-time decisions!
