# Climate Equity Analysis in GCR-ABM

## Overview

The GCR system has **built-in wealth transfer mechanisms** that favor the Global South and address historical climate injustice.

## Equity Mechanisms

### 1. R-Value Differential (Cost-Effectiveness Rewards)

**How it works:**
- **1 XCR = 1/R tonnes CO₂e** with 100+ years durability
- Lower R = MORE XCR per tonne sequestered

**Regional Distribution:**

**Global South (Non-OECD):**
- **CDR projects** (afforestation, biochar, soil carbon): **R = 1.0**
- **Co-benefits** (ecosystem restoration, agro-ecology): **R = 0.8 × (marginal_cost / price_floor)**
- Lower marginal costs (~$70-100/tonne)
- **Result: HIGH XCR rewards per tonne**

**Global North (OECD):**
- **Conventional mitigation** (renewables, efficiency, industrial): **R = marginal_cost / price_floor**
- Higher marginal costs ($150+/tonne for many technologies)
- **Result: LOWER XCR rewards per tonne**

### 2. CQE Contribution Differential

**How it works:**
- CQE budgets are GDP-proportional
- Rich countries contribute more to defend the price floor
- When market price < floor, central banks buy XCR with newly created money (CQE)

**Wealth Flow:**
- **North**: Large CQE budgets → buy XCR when price falls → support market
- **South**: Small CQE budgets → sell XCR rewards → earn revenue

### 3. Historical Emissions (Tracked, Optional Adjustment)

The model tracks historical cumulative emissions (1850-2023) for each country:
- **USA**: 420 GtCO₂ (largest historical emitter)
- **China**: 280 GtCO₂
- **Germany**: 95 GtCO₂
- **Kenya**: 0.5 GtCO₂
- **Ethiopia**: 0.4 GtCO₂

**Optional Enhancement**: R-values could be adjusted based on historical responsibility:
```python
adjusted_R = base_R × (1 + historical_emissions_factor)
```
This would further penalize high-historical emitters and reward low-emitters.

## Example Simulation Results

From 50-year simulation with default parameters:

### XCR Earnings
- **OECD (North)**: 1.27e+09 XCR earned
- **Non-OECD (South)**: 1.84e+09 XCR earned
- **Net advantage to South**: +45% more XCR earned

### Wealth Transfer
- South earns **$2.28 trillion USD more** (at $1240/XCR market price)
- This represents North→South financial flow for carbon sequestration services

## Why This Addresses Equity

### 1. Pays South for Climate Solutions
- CDR, nature-based solutions, and co-benefits → predominantly Global South
- These projects earn the MOST XCR per tonne
- Creates direct financial incentive for South to deploy climate solutions

### 2. North Pays for Expensive Mitigation
- Conventional mitigation (renewables, industrial efficiency) → predominantly North
- These projects earn FEWER XCR per tonne
- North bears higher cost burden relative to carbon impact

### 3. Implicit Reparations
- North has larger CQE budgets (GDP-proportional) to defend price floor
- North created most historical emissions but earns fewer XCR
- South created fewer historical emissions but earns more XCR
- **Financial flow matches climate justice principles**

## Measurement

The simulation tracks for each country:
- `xcr_earned`: Total XCR rewards from projects
- `xcr_purchased_equiv`: Total XCR purchased via CQE contributions
- `net_xcr = earned - purchased`: Net position
- `historical_emissions_gtco2`: Cumulative 1850-2023 emissions
- `oecd`: OECD membership status

## Enhancements to Consider

### A. Historical Emissions Adjustment to R-values
Add explicit penalty/bonus based on historical responsibility:
```python
# High historical emitters get penalized R-values (fewer XCR)
# Low historical emitters get bonus R-values (more XCR)
historical_factor = country_emissions / global_avg_emissions
adjusted_R = base_R * historical_factor
```

### B. South-to-South Technology Transfer Fund
Levy small % of Northern CQE spending to fund capacity building in developing countries.

### C. Progressive CQE Contributions
Weight CQE contributions by historical emissions, not just GDP:
```python
cqe_contribution = GDP × (historical_emissions / global_avg)
```

### D. Explicit Climate Justice Metrics
Track in dashboard:
- XCR earned per capita
- XCR earned per historical tonne emitted
- Net wealth transfer as % of GDP

## Dashboard Visualization

The dashboard includes:
- **Equity Tab**: OECD vs non-OECD XCR flows
- **Country-level breakdown**: Top net earners/payers
- **Historical emissions context**: Who's responsible vs who's rewarded
- **Wealth transfer visualization**: North→South financial flows

## Conclusion

The GCR system **already contains powerful equity mechanisms** through:
1. R-value differential (South earns more XCR per tonne)
2. CQE burden sharing (North pays more to defend floor)
3. Project geography (South hosts most CDR/nature-based projects)

This creates a **natural wealth transfer from North to South** that addresses both current climate action AND historical climate injustice.
