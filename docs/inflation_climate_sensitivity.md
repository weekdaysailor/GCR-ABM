# Inflation Sensitivity in Climate Outcomes

## Problem Addressed

**User Feedback**: "It's still too insensitive to inflation"

The system had a 606% effect on XCR issuance but produced **identical CO2 outcomes** (319.4 ppm in both low and high inflation scenarios). The climate urgency factor was purely CO2-based and ignored inflation, causing it to dominate and mask inflation effects.

## Solution: Inflation-Adjusted Climate Urgency

Made the **climate urgency factor itself inflation-sensitive** so inflation affects not just XCR issuance but actual climate outcomes.

### Two-Part Solution

#### 1. Inflation-Adjusted Tapering

**File**: `gcr_model.py` lines 503-565 - `ProjectsBroker._calculate_project_capacity()`

**How It Works**:
```python
# Taper start ranges dramatically based on inflation target
if inflation_target < 1%:
    taper_start = 370 ppm  # Low inflation: very aggressive
elif inflation_target == 2%:
    taper_start = 390 ppm  # Baseline: moderate
elif inflation_target >= 6%:
    taper_start = 420 ppm  # High inflation: very cautious
```

**Effect**:
| Inflation Target | Taper Start | Buffer | Policy Stance |
|-----------------|-------------|--------|---------------|
| 0.5% (low) | 370 ppm | 20 ppm | Aggressive |
| 2% (baseline) | 390 ppm | 40 ppm | Moderate |
| 6% (high) | 420 ppm | 70 ppm | Cautious |

**Range**: 370-425 ppm (55 ppm range)

#### 2. Inflation-Adjusted Retirement

**File**: `gcr_model.py` lines 658-706 - `ProjectsBroker.step_projects()`

**How It Works**:
```python
# Base retirement rates (15-40% based on overshoot)

# Inflation multiplier
if inflation_target > 5%:
    inflation_multiplier = 1.4  # 40% faster (wind down quickly)
elif inflation_target > 3%:
    inflation_multiplier = 1.2  # 20% faster
elif inflation_target < 1%:
    inflation_multiplier = 0.8  # 20% slower (keep projects longer)
else:
    inflation_multiplier = 1.0  # Baseline

retirement_rate = base_rate * inflation_multiplier
```

**Effect**:
| Inflation Target | Multiplier | Example Rate | Interpretation |
|-----------------|------------|--------------|----------------|
| 0.5% (low) | 0.8x | 12% (was 15%) | Keep projects longer |
| 2% (baseline) | 1.0x | 15% | Normal |
| 6% (high) | 1.4x | 21% (was 15%) | Wind down faster |

---

## Results: Inflation Now Affects Real Outcomes

### Before Changes

**Test**: 0.5% vs 6% inflation targets (30-year simulation, same seed)

| Metric | Low Inflation | High Inflation | Difference |
|--------|--------------|----------------|------------|
| **CO2 Outcome** | 319.4 ppm | **319.4 ppm** | **0.0 ppm** ❌ |
| Total Projects | 1,442 | 1,442 | 0% |
| XCR Issuance | 1,107B | 157B | +606% |

**Problem**: Identical climate outcomes despite different inflation policies!

### After Changes

**Test**: Same comparison with inflation-adjusted climate controls

| Metric | Low Inflation | High Inflation | Difference |
|--------|--------------|----------------|------------|
| **CO2 Outcome** | 311.9 ppm | **329.4 ppm** | **-17.4 ppm** ✅ |
| Total Projects | 1,504 | 1,346 | +11.7% |
| Operational (final) | 49 | 10 | +390% |
| XCR Issuance | 1,224B | 139B | +779% |

**Success**: 17.4 ppm difference = 25% of the 70 ppm goal!

### Interpretation

**Low Inflation (0.5% target)**:
- Starts tapering at 370 ppm (very aggressive - confident in ability to manage more issuance)
- Achieves 311.9 ppm (39 ppm below target)
- Keeps 49 operational projects (slower retirement to maintain climate gains)
- Issues 1,224B XCR

**High Inflation (6% target)**:
- Starts tapering at 420 ppm (very cautious - avoids inflationary pressure)
- Achieves 329.4 ppm (21 ppm below target)
- Only 10 operational projects (faster wind-down to limit minting)
- Issues 139B XCR (88% less)

**Trade-off**: High inflation policy achieves less aggressive climate mitigation (329 vs 312 ppm) in exchange for price stability.

---

## Policy Implications

### Inflation as Policy Tool

Inflation target now controls the **aggressiveness of climate action**:

- **Low inflation target** (0-1%): System pursues very aggressive climate mitigation
  - Earlier tapering (starts at 370 ppm)
  - More projects kept operational longer
  - Willing to accept more XCR issuance
  - Better climate outcome (311 ppm)

- **High inflation target** (5-10%): System prioritizes price stability
  - Later tapering (starts at 420 ppm)
  - Projects retired faster once target achieved
  - Limited XCR issuance
  - Less aggressive climate outcome (329 ppm)

### Real-World Analogy

Like central bank policy:
- **Dovish** (low inflation target): Accept higher inflation risk to maximize employment/growth → In GCR: maximize climate mitigation
- **Hawkish** (high inflation target): Prioritize price stability over growth → In GCR: limit climate action to control inflation

---

## Technical Details

### Modified Code Sections

1. **`_calculate_project_capacity()`** - Lines 503-565
   - Added `inflation_target` parameter
   - Taper start ranges from 370-425 ppm based on inflation
   - Urgency factors differ by inflation tier

2. **`step_projects()`** - Lines 658-706
   - Added `inflation_target` parameter
   - Retirement rates multiplied by inflation factor (0.8x-1.4x)

3. **Call Sites**
   - Line 627: Pass `cea.inflation_target` to `_calculate_project_capacity()`
   - Line 1259: Pass `self.inflation_target` to `step_projects()`

### Urgency Factor Comparison

**At 365 ppm (15 ppm above target)**:
- Low inflation: urgency = 0.45 → ~45 projects/year
- Baseline: urgency = 0.30 → ~30 projects/year
- High inflation: urgency = 0.18 → ~18 projects/year

**At 352 ppm (2 ppm above target)**:
- Low inflation: urgency = 0.10 → ~10 projects/year
- Baseline: urgency = 0.07 → ~7 projects/year
- High inflation: urgency = 0.03 → ~3 projects/year

**Below 350 ppm**:
- All scenarios: urgency = 0.02 → ~2 projects/year
- But retirement differs: low inflation keeps more projects operational

---

## Testing

### Verification Command

```bash
venv/bin/python -c "
import numpy as np
from gcr_model import GCR_ABM_Simulation

# Low inflation
np.random.seed(42)
sim_low = GCR_ABM_Simulation(years=30, inflation_target=0.005)
df_low = sim_low.run_simulation()

# High inflation
np.random.seed(42)
sim_high = GCR_ABM_Simulation(years=30, inflation_target=0.06)
df_high = sim_high.run_simulation()

co2_diff = df_low.iloc[-1]['CO2_ppm'] - df_high.iloc[-1]['CO2_ppm']
print(f'CO2 Difference: {co2_diff:.1f} ppm')
print('Expected: ~15-20 ppm difference')
"
```

### Expected Behavior

- CO2 difference: **15-20 ppm** (25-30% of 70 ppm goal)
- XCR difference: **600-800%** (low inflation issues 7-8x more)
- Project difference: **10-15%** more projects with low inflation
- Inflation constraint test: **PASS** (all 5 criteria)

---

## Summary

Inflation is now a **PRIMARY constraint** affecting:
1. ✅ XCR issuance (779% difference)
2. ✅ Climate outcomes (17.4 ppm difference)
3. ✅ Project dynamics (11.7% difference, 390% more operational)

The system demonstrates realistic policy trade-offs between price stability and climate ambition.
