# Climate Target Stabilization Controls

## Purpose

Prevent overshoot below 350 ppm by tapering new project starts before the target and retiring projects faster once the target is exceeded.

## Two-Part Control System (Code-Accurate)

### 1) Climate Urgency Taper (Inflation-Sensitive)

**File**: `gcr_model.py` → `ProjectsBroker._calculate_project_capacity()` (urgency multiplier)

Key ideas:
- Full project capacity when CO2 is well above target (multiplier = 1.0).
- Tapering begins at a **taper_start** that shifts with **realized inflation**.
- Near-target bands (360-350 ppm) taper more aggressively under high inflation.

```python
if current_co2_ppm >= taper_start:
    urgency_factor = 1.0
elif current_co2_ppm > 370.0:
    urgency_factor = 0.6 + 0.4 * (current_co2_ppm - 370.0) / range_size
elif current_co2_ppm > 360.0:
    # Inflation-sensitive mid taper
elif current_co2_ppm > 350.0:
    # Inflation-sensitive final taper
else:
    urgency_factor = 0.02  # minimal maintenance
```

**Interpretation**:
- **Low inflation** → later taper, higher capacity.
- **High inflation** → earlier taper, lower capacity.

### 2) Graduated Retirement (Inflation-Sensitive)

**File**: `gcr_model.py` → `ProjectsBroker.step_projects()`

Retirement scales with overshoot and speeds up under high inflation:

```python
if overshoot_ppm <= 5:
    base_rate = 0.15
elif overshoot_ppm <= 15:
    base_rate = 0.22
elif overshoot_ppm <= 30:
    base_rate = 0.30
else:
    base_rate = 0.40

retirement_probability = min(0.5, base_rate * inflation_multiplier)
```

**Interpretation**:
- Gentle wind-down near target.
- Faster drawdown when overshoot is large or inflation is high.

## Practical Notes

- The urgency factor scales **capital-limited** project counts, not a fixed per-country quota.
- These controls prevent runaway sequestration when the system has many operational projects.
- Inflation enters both initiation and retirement, so monetary pressure can slow deployment even if CO2 remains above target.
- For tighter stabilization around 350 ppm, adjust taper_start ranges, urgency slopes, or retirement multipliers.
