# Inflation Sensitivity in Climate Outcomes

## Problem Addressed

Earlier versions constrained XCR issuance but produced nearly identical CO2 paths under different inflation conditions. The climate urgency logic was CO2-only, so inflation did not materially affect sequestration.

## Current Behavior (Code-Accurate)

Inflation now affects **project initiation** and **retirement** using **realized inflation** (CPI), not the policy target. The initiation logic returns an **urgency multiplier** applied to capital-limited project counts.

### 1) Inflation-Adjusted Tapering

**File**: `gcr_model.py` → `ProjectsBroker._calculate_project_capacity()` (urgency multiplier)

```python
inflation_ratio = max(current_inflation, 0.0) / 0.02  # 2% baseline

if inflation_ratio < 0.5:
    taper_start = 370.0  # low inflation: later taper (more aggressive)
elif inflation_ratio < 1.5:
    taper_start = 370.0 + 20.0 * (inflation_ratio - 0.5)  # 370-390
else:
    taper_start = min(425.0, 390.0 + 15.0 * (inflation_ratio - 1.5))  # 390-425
```

**Interpretation**:
- **Low inflation** → later tapering (more aggressive scale-up).
- **High inflation** → earlier tapering (more cautious scale-up).

Urgency slopes also steepen under high inflation in the mid/final approach bands (360-350 ppm), reducing new project counts faster.

### 2) Inflation-Adjusted Retirement

**File**: `gcr_model.py` → `ProjectsBroker.step_projects()`

```python
inflation_ratio = max(current_inflation, 0.0) / 0.02

if inflation_ratio > 2.5:      # >5% inflation
    inflation_multiplier = 1.4
elif inflation_ratio > 1.5:    # 3-5%
    inflation_multiplier = 1.2
elif inflation_ratio < 0.5:    # <1%
    inflation_multiplier = 0.8
else:
    inflation_multiplier = 1.0

retirement_probability = min(0.5, base_rate * inflation_multiplier)
```

**Interpretation**:
- **High inflation** → faster retirement (reduces minting pressure).
- **Low inflation** → slower retirement (keeps capacity online).

## Net Effect

Inflation now **changes real climate outcomes** by directly throttling or extending deployment, not just by changing token issuance.

## Notes for Calibration

- If inflation appears to have little climate impact, check that realized CPI is moving (not pinned) and that the urgency taper ranges are still active (CO2 above 350 ppm).
- If inflation is too dominant, reduce the inflation multipliers or narrow the taper-start range.
