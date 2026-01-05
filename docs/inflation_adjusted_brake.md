# Inflation-Adjusted CEA Brake System

## Overview

The CEA brake throttles XCR minting based on:
- **Stability ratio** (XCR market cap / CQE budget)
- **Realized inflation** (CPI), normalized to a 2% baseline
- **CQE budget utilization** (annual cap pressure)

The inflation target influences macro correction, but the **brake itself uses realized inflation** to tighten or loosen thresholds.

## Core Mechanics (Code-Accurate)

### 1. Threshold Scaling by Realized Inflation

```python
inflation_ratio = max(current_inflation, 0.0) / 0.02  # 2% baseline

if inflation_ratio < 0.5:        # <1% inflation
    inflation_adjustment = 2.0   # lenient thresholds
elif inflation_ratio < 2.0:      # 1-4% inflation
    inflation_adjustment = 2.0 - 1.0 * (inflation_ratio - 0.5)
else:                             # >4% inflation
    inflation_adjustment = max(0.3, 0.5 - 0.05 * (inflation_ratio - 2.0))

warning_threshold = 8.0 * inflation_adjustment
brake_start = 10.0 * inflation_adjustment
brake_mid = 12.0 * inflation_adjustment
brake_heavy = 15.0 * inflation_adjustment
```

**Baseline (2% inflation)**: thresholds at 8:1, 10:1, 12:1, 15:1.  
Lower inflation raises thresholds (more issuance). Higher inflation lowers thresholds (tighter brake).

### 2. Heavy-Brake Floor (Inflation-Sensitive)

```python
if inflation_ratio < 0.5:
    heavy_brake_floor = 0.30   # 30% minting
elif inflation_ratio < 2.0:
    heavy_brake_floor = 0.30 - 0.167 * (inflation_ratio - 0.5)
else:
    heavy_brake_floor = max(0.01, 0.05 - 0.01 * (inflation_ratio - 2.0))
```

Range:
- **Low inflation**: floor ~30%
- **High inflation**: floor falls toward 1%

### 3. Budget Utilization Brake

```python
if utilization < 0.90:
    budget_brake = 1.0
else:
    budget_brake = max(0.25, 1.0 - (utilization - 0.90) / 0.10)
```

Starts braking at **90%** of the annual CQE cap and bottoms out at **25%**.

### 4. Inflation Penalty

```python
if inflation_ratio > 1.0:
    inflation_penalty = max(0.2, 1.0 - 0.4 * (inflation_ratio - 1.0))
else:
    inflation_penalty = 1.0
```

Directly reduces minting when CPI runs above the 2% baseline.

### 5. Combined Brake

```python
brake_factor = ratio_brake * budget_brake * inflation_penalty
```

## Implementation Notes

- **Method**: `CEA.calculate_brake_factor(ratio, current_inflation, budget_utilization)`
- **Caller**: `CEA.update_policy(...)` in `gcr_model.py`
- **Defaults**: 2% baseline for inflation normalization; CQE budget utilization brake starts at 90%.

## Practical Interpretation

- Low inflation + low utilization → high issuance capacity (lenient thresholds).
- High inflation or near-exhausted CQE budgets → tight brake and low minting.
- The brake is **automatic** and responds to realized CPI, not policy intent alone.
