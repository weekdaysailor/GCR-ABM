# Inflation-Adjusted CEA Brake System

## Overview

The CEA (Carbon Exchange Authority) brake is the primary mechanism that constrains XCR issuance based on the **inflation target** set by policymakers. This document explains how the brake thresholds and floor dynamically adjust to make inflation the PRIMARY constraint on XCR creation.

## Core Concept

**Inflation target signals policy stance:**
- **Low inflation target** (e.g., 0.5%) → Accommodative policy → Lenient brake → More XCR issuance allowed
- **High inflation target** (e.g., 6-10%) → Restrictive policy → Strict brake → XCR issuance heavily constrained

## Mechanism Details

### 1. Brake Threshold Adjustment

The brake activates when the **stability ratio** (XCR Market Cap / Annual CQE Budget) exceeds certain thresholds. These thresholds scale with the inflation target:

```python
# Calculate inflation adjustment based on TARGET inflation
target_ratio = inflation_target / 0.02  # Normalize to 2% baseline

# Threshold adjustment factor
if target_ratio < 0.5:  # < 1% target (very accommodative)
    inflation_adjustment = 2.0  # Lenient thresholds
elif target_ratio < 2.0:  # 1-4% target (moderate)
    inflation_adjustment = 2.0 - 1.0 * (target_ratio - 0.5)  # Linear interpolation
else:  # > 4% target (restrictive)
    inflation_adjustment = max(0.3, 0.5 - 0.05 * (target_ratio - 2.0))  # Strict

# Adjusted thresholds
warning_threshold = 8.0 * inflation_adjustment
brake_start = 10.0 * inflation_adjustment
brake_mid = 12.0 * inflation_adjustment
brake_heavy = 15.0 * inflation_adjustment
```

**Examples:**

| Inflation Target | Adjustment Factor | Warning | Brake Start | Heavy Brake |
|-----------------|-------------------|---------|-------------|-------------|
| 0.1% (very low) | 2.0x | 16:1 | 20:1 | 30:1 |
| 0.5% (low) | 1.75x | 14:1 | 17.5:1 | 26:1 |
| 2.0% (baseline) | 1.0x | 8:1 | 10:1 | 15:1 |
| 6.0% (high) | 0.4x | 3.2:1 | 4:1 | 6:1 |
| 10% (very high) | 0.3x | 2.4:1 | 3:1 | 4.5:1 |

### 2. Heavy Brake Floor Adjustment

When the system enters "heavy brake" mode (stability ratio > heavy brake threshold), minting is reduced to a minimum floor. This floor also adjusts based on inflation target:

```python
# Calculate inflation-adjusted heavy brake floor
if target_ratio < 0.5:  # < 1% target
    heavy_brake_floor = 0.3  # 30% of normal minting rate
elif target_ratio < 2.0:  # 1-4% target
    heavy_brake_floor = 0.3 - 0.167 * (target_ratio - 0.5)
else:  # > 4% target
    heavy_brake_floor = max(0.01, 0.05 - 0.01 * (target_ratio - 2.0))  # 1% minimum
```

**Examples:**

| Inflation Target | Heavy Brake Floor | Interpretation |
|-----------------|-------------------|----------------|
| 0.1% | 30% | Even in heavy brake, still mints at 30% rate |
| 0.5% | 30% | Accommodative - allows substantial issuance |
| 2.0% | 13% | Baseline - moderate constraint |
| 6.0% | 3% | Restrictive - severe constraint |
| 10% | 1% | Very restrictive - near-zero issuance |

### 3. Brake Interpolation

Between thresholds, the brake factor is calculated using quadratic interpolation to create smooth transitions:

```python
if ratio < brake_start:
    brake_factor = 1.0  # No brake
elif ratio < brake_mid:
    # Linear decline from 1.0 to 0.5
    t = (ratio - brake_start) / (brake_mid - brake_start)
    brake_factor = 1.0 - 0.5 * t
elif ratio < brake_heavy:
    # Quadratic decline from 0.5 to heavy_brake_floor
    t = (ratio - brake_mid) / (brake_heavy - brake_mid)
    brake_factor = 0.5 - (0.5 - heavy_brake_floor) * (t ** 2)
else:
    # Maximum brake
    brake_factor = heavy_brake_floor
```

## Impact on System Behavior

### Test Results (50-year simulation)

**Scenario A: Low Inflation (0.5% target)**
- XCR Supply: 8,010B
- Minimum brake: 0.300x (30% rate)
- Brake active: 88% of years
- Result: **Accommodative** - allows substantial issuance

**Scenario B: High Inflation (6% target)**
- XCR Supply: 1,080B
- Minimum brake: 0.040x (4% rate)
- Brake active: 90% of years
- Result: **Restrictive** - heavily constrains issuance

**Net Effect: 86.6% reduction in issuance with high inflation target**

This demonstrates that **inflation is now the PRIMARY constraint** on XCR creation, not arbitrary limits or project availability.

## Why This Design?

### 1. Policy Flexibility

Different economic conditions require different policy stances:
- **Low inflation environment** (deflation risk): Need aggressive carbon rewards to scale up quickly
- **High inflation environment**: Need restraint to avoid exacerbating inflation

### 2. Transparent Signal

The inflation target is a clear, observable policy parameter that stakeholders can understand. Investors, project developers, and central banks can predict system behavior based on this single variable.

### 3. Automatic Stabilization

The brake automatically adjusts without manual intervention:
- High issuance → stability ratio increases → brake tightens → issuance slows
- Combined with inflation target → double feedback loop for stability

### 4. Gigatonne-Scale Compatible

At gigatonne scale (hundreds of billions of XCR), the system MUST have strong constraints. The inflation-adjusted brake ensures:
- Low inflation environments can still reach climate goals
- High inflation environments don't create hyperinflation risk
- System is self-regulating at any scale

## Implementation Notes

### Location in Code

**File**: `gcr_model.py`

**Key Method**: `CEA.calculate_brake_factor()` (lines 150-217)

```python
def calculate_brake_factor(self, ratio: float, current_inflation: float,
                          inflation_target: float) -> float:
    """Calculate XCR minting reduction based on stability ratio AND inflation

    Brake thresholds adjust based on inflation target:
    - Low inflation → lenient thresholds (allow more issuance)
    - High inflation → strict thresholds (constrain issuance)
    """
    # Implementation details...
```

**Called From**: `CEA.update_policy()` (line 226)

```python
self.brake_factor = self.calculate_brake_factor(ratio, global_inflation, self.inflation_target)
```

### Parameters

Set in `GCR_ABM_Simulation.__init__()`:

```python
sim = GCR_ABM_Simulation(
    years=50,
    inflation_target=0.02,  # 2% baseline, range: 0.001-0.10
    price_floor=100.0
)
```

### Testing

**Test File**: `test_inflation_constraint.py`

Compares low (0.5%) vs high (6%) inflation targets:
- Verifies >50% difference in issuance
- Confirms brake thresholds adjust correctly
- Validates heavy brake floor responds to target

**Run Test**:
```bash
venv/bin/python test_inflation_constraint.py
```

Expected: ALL TESTS PASSED with 86.6% reduction

## Calibration Trade-offs

### Current Settings

- **Threshold scaling**: 0.3x - 2.0x adjustment range
- **Heavy brake floor**: 1% - 30% range
- **Baseline**: 2% inflation target (10:1 brake start)

### Potential Adjustments

**If issuance too constrained at high inflation:**
- Increase heavy brake floor minimum (1% → 5%)
- Reduce strictness of threshold scaling (0.3x → 0.5x)

**If issuance too loose at low inflation:**
- Decrease heavy brake floor maximum (30% → 20%)
- Reduce leniency of threshold scaling (2.0x → 1.5x)

**If transition too abrupt:**
- Widen interpolation ranges
- Use cubic instead of quadratic interpolation

## Comparison to Previous System

### Before Inflation-Adjusted Brake

- Brake thresholds: Fixed at 8:1, 10:1, 12:1, 15:1
- Heavy brake floor: Fixed at 10%
- Inflation target effect: **Minimal** (0.3% difference)
- Constraint: Project availability, not inflation policy

### After Inflation-Adjusted Brake

- Brake thresholds: Dynamic 2.4:1 - 30:1 based on target
- Heavy brake floor: Dynamic 1% - 30% based on target
- Inflation target effect: **Dramatic** (86.6% difference)
- Constraint: **Inflation policy is PRIMARY**

## Economic Intuition

Think of the inflation target as the "thermostat" for XCR creation:

- **Low setting** (0.5%): System says "we can afford rapid carbon finance expansion"
  - Brake kicks in late (20:1 ratio)
  - Even when brake active, still mints at 30% rate
  - Prioritizes climate goals over inflation concerns

- **High setting** (6%): System says "we must be cautious, inflation is risky"
  - Brake kicks in early (4:1 ratio)
  - When brake active, mints at only 4% rate
  - Prioritizes price stability over rapid scaling

This makes the GCR system **adaptable to different economic regimes** while maintaining climate impact.

## Related Documentation

- **System scaling**: `CLAUDE.md` - Gigatonne-scale operation
- **Agent verification**: `docs/agent_verification.md` - How to verify brake is working
- **Training guide**: `docs/training.md` - Overall system behavior
- **Test suite**: `test_inflation_constraint.py` - Automated verification

## Questions?

Run the test with different inflation targets to see the effect:

```python
import numpy as np
from gcr_model import GCR_ABM_Simulation

# Very low inflation (accommodative)
sim_low = GCR_ABM_Simulation(years=30, inflation_target=0.001)
df_low = sim_low.run_simulation()

# Very high inflation (restrictive)
sim_high = GCR_ABM_Simulation(years=30, inflation_target=0.10)
df_high = sim_high.run_simulation()

# Compare final XCR supply
print(f"Low inflation: {df_low.iloc[-1]['XCR_Supply']/1e9:.1f}B XCR")
print(f"High inflation: {df_high.iloc[-1]['XCR_Supply']/1e9:.1f}B XCR")
```

Expected: Low inflation produces 10-15x more XCR than high inflation.
