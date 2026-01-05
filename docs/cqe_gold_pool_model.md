# CQE Budget: Flow-Based Backstop Implementation

## Problem Addressed

**User Requirement**: CQE budgets should be a **small fraction of annual private capital flow**, not a large cumulative stock. The earlier cumulative model overshot by orders of magnitude at scale.

The original implementation had **fixed CQE budgets per country** (USA: $50B, China: $35B, etc.) that summed to ~$196B regardless of private capital levels. This didn't scale with market dynamics or follow historical precedent.

## Solution: Flow-Based Backstop (Option 2)

Implemented CQE as **5% of annual private capital inflow** to XCR, with a **GDP cap** to prevent outsized interventions.

### Historical Precedent: XAU (Gold) Markets

From Chen paper reference to "Gold Pool - 1961-68":

**Gold Pool Structure:**
- 8 central banks pooled gold reserves to defend $35/oz floor
- Pool size: ~$270M initially (~$2-3B in 2024 dollars)
- Private gold market: ~$40B at the time
- **Ratio: Central bank intervention capacity was ~5-10% of total market**

**Modern Gold Markets:**
- Central banks hold ~35,000 tonnes (~17-20% of all above-ground gold)
- Private holdings: ~165,000 tonnes (~80-83%)
- **Backstop range**: Public backstop is a minority share of total market depth

### Implementation Details

**File**: `gcr_model.py` (`CentralBankAlliance`)

```python
class CentralBankAlliance:
    """Central Bank Alliance - Price floor defenders via CQE

    CQE Budget Model (Option 2 - Flow-Based Backstop):
    - Total CQE budget = 5% of annual private capital inflow to XCR
    - Capped at 0.5% of active GDP
    - Private capital leads; CQE remains a minority backstop
    """

    def __init__(self, countries: Dict[str, Dict], price_floor: float = 100.0):
        self.countries = countries
        self.price_floor_rcc = price_floor
        self.total_cqe_budget = 0.0  # Calculated dynamically from private capital
        self.cqe_ratio = 0.05  # CQE = 5% of annual private capital inflow
        self.gdp_cap_ratio = 0.005  # CQE cap as share of active GDP
        self.total_cqe_spent = 0.0  # Track total M0 created (cumulative)
        self.annual_cqe_spent = 0.0  # Track spending this year (resets annually)
        self.current_budget_year = 0  # Track year for annual reset

    def update_cqe_budget(self, annual_private_capital_inflow: float):
        """Recalculate CQE budget as 5% of annual private capital inflow

        Flow-Based Backstop:
        - Private capital leads each year; CQE follows as a minority backstop
        - Uses a conservative 5% ratio to avoid overshoot
        - Budget is capped by active GDP (0.5% cap).
        """
        active_gdp_tril = sum(country["gdp_tril"] for country in self.countries.values())
        active_gdp_usd = active_gdp_tril * 1e12
        market_cap_budget = annual_private_capital_inflow * self.cqe_ratio
        gdp_cap_budget = active_gdp_usd * self.gdp_cap_ratio
        self.total_cqe_budget = min(market_cap_budget, gdp_cap_budget)
```

### Simulation Loop Integration

**File**: `gcr_model.py` (main loop)

```python
# 2b. Update capital market (private investors)
net_capital_flow, capital_demand_premium, forward_guidance = self.capital_market.update_capital_flows(
    self.co2_level, year, self.years, roadmap_gap,
    self.global_inflation, self.inflation_target,
    self.investor_market.sentiment, self.total_xcr_supply,
    self.price_floor
)

# 2b2. Update CQE budget (5% of annual private capital inflow)
self.central_bank.update_cqe_budget(max(net_capital_flow, 0.0))
```

**Execution Order**:
1. Private capital flows calculated for the year
2. Annual private capital inflow computed
3. CQE budget recalculated as 5% of annual inflow (GDP-capped)
4. CEA uses updated budget for stability ratio calculations

---

## Three Options Considered

### Option 1: CQE = 20% of XCR Market Cap
- **Pro**: Scales with market size naturally
- **Con**: Very large budgets when market cap is high (could be trillions)
- **Example**: $1T market cap → $200B CQE budget

### Option 2: CQE = 5% of Annual Private Capital Flow ✓ **Selected**
- **Pro**: Keeps CQE budgets modest relative to yearly market activity
- **Pro**: Avoids cumulative overshoot as the system matures
- **Con**: Smaller buffers during large, sudden drawdowns
- **Example**: $1T annual inflow → $50B CQE budget (before GDP cap)

### Option 3: CQE = 15% of Cumulative Private Capital
- **Pro**: Private capital leads, public follows conservatively
- **Con**: Budgets compound over time and can overshoot by orders of magnitude
- **Example**: $1B cumulative inflow → $150M CQE budget (before GDP cap)

---

## Verification Notes

- CQE budget scales with **annual private capital inflow** at a 5% ratio.
- A GDP cap (0.5% of active GDP) prevents CQE from exceeding realistic macro bounds.
- CQE is a backstop; it can remain unused for long periods when market price stays above the floor.

### Budget Utilization

In the test simulation:
- CQE budget present but never spent
- Price remained above floor throughout simulation
- This is correct behavior (CQE is backstop, only used when needed)

---

## Design Philosophy

### Private Capital Leads, CQE Follows

**Private Capital Leads**:
- **Private Capital**: Market-driven price discovery, climate urgency signals
- **CQE Backstop**: Minority share for floor defense when private demand is insufficient

**Why This Ratio?**
1. **Market discipline**: Private capital majority ensures genuine price signals
2. **Credible backstop**: 5% of annual flow is large enough to defend the floor but not dominate
3. **Overshoot control**: Annual-flow sizing avoids cumulative budget inflation
4. **Bootstrapping**: CQE grows naturally as private capital commits

### Lessons from Gold Pool Failure (1968)

The Gold Pool collapsed when private demand overwhelmed central bank capacity. This is **intentional design**:

- If private capital wants to buy more XCR than CQE can supply → price rises above floor (good signal!)
- CQE defends the floor, not the ceiling
- Market-determined price appreciation signals climate urgency

### Economic Interpretation

**Year 1-5 (Bootstrapping)**:
- Private capital explores new asset class
- Small initial commitments
- CQE budget small but present
- Floor credible even with small budget (XCR supply also small)

**Year 10-20 (Growth)**:
- Private capital inflows rise as climate urgency increases
- CQE budget scales with annual inflows (GDP-capped)

**Year 20+ (Maturity)**:
- Larger annual inflows during climate stress periods
- CQE budget remains bounded by annual flow and GDP cap
- Backstop remains credible at scale

---

## Comparison to Previous System

### Before (Fixed Budgets)

```python
# Fixed per-country budgets
"USA": {"base_cqe": 0.05, ...},  # $50B/year
"China": {"base_cqe": 0.035, ...},  # $35B/year
...
total_cqe_budget = sum(base_cqe) * 1e12  # ~$196B fixed
```

**Problems**:
- No relationship to private capital
- Fixed regardless of market size
- Arbitrary country allocations
- Didn't scale with system dynamics

### After (Flow-Based Backstop)

```python
# Dynamic, market-driven
total_cqe_budget = annual_private_capital_inflow * 0.05  # 5% ratio
total_cqe_budget = min(total_cqe_budget, gdp_cap_budget)  # 0.5% of active GDP

# Country attribution uses base_cqe weights for reporting (not budget allocation)
```

**Benefits**:
- ✅ Scales with private capital commitment
- ✅ Ensures private capital leads (minority public backstop)
- ✅ Historical precedent (Gold Pool, gold reserves)
- ✅ Self-adjusting to market conditions
- ✅ Credible at any scale

---

## Country Attribution (Current Behavior)

CQE budgeting is **global** (5% of annual private inflow, GDP-capped). The model does **not** allocate budgets per country. Instead, country `base_cqe` weights are used to **attribute CQE purchases** for reporting.

---

## Related Documentation

- **Chen paper**: `docs/chen_chap5.md` - Gold Pool historical precedent (line 285)
- **Central Bank Agent**: `docs/AGENT_CENTRAL_BANK.md` - CQE mechanics
- **Main documentation**: `CLAUDE.md` - System overview

---

## Summary

The flow-based backstop implements CQE as a **5% annual inflow backstop** to private capital (GDP-capped), ensuring:

1. ✅ Private capital leads
2. ✅ Public backstop follows as a minority share
3. ✅ Historical precedent (gold market intervention ratios)
4. ✅ Scales naturally with market dynamics
5. ✅ Self-adjusting and credible at any scale

The 5% ratio applies before the GDP cap and is recalculated annually from private inflows.
