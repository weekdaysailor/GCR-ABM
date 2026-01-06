# Channel Capacity Constraints

## Purpose

Prevent unrealistic deployment rates by enforcing channel-specific physical limits.

## Current Limits (Code-Accurate)

**File**: `gcr_model.py` → `ProjectsBroker.__init__()`

```python
self.max_capacity_gt_per_year = {
    ChannelType.CDR: None,           # No hard cap for CDR/DAC scaling
    ChannelType.CONVENTIONAL: 30.0,  # Earlier taper to force CDR reliance
    ChannelType.COBENEFITS: 50.0,    # Nature-based potential (overlay exists separately)
    ChannelType.AVOIDED_DEFORESTATION: 5.0  # Land-use emissions ceiling
}
```

Notes:
- **CDR**, **Conventional**, and **Avoided Deforestation** are initiated as physical channels.
- Co-benefits are a **reward overlay**; the COBENEFITS limit is retained for completeness.

## Capacity Enforcement

**File**: `gcr_model.py` → `ProjectsBroker.initiate_projects()`

```python
planned_rate_gt = self.get_planned_sequestration_rate(channel)
max_capacity_gt = self.max_capacity_gt_per_year[channel]

if max_capacity_gt is not None and planned_rate_gt >= max_capacity_gt:
    continue  # channel at capacity
```

This check uses **planned capacity** (operational + in-development) to prevent exceeding limits.

Conventional capacity availability **tapers down** as utilization approaches the limit using a sigmoid curve; there is no hard cutoff. A small residual floor remains for hard‑to‑abate sectors.

## Related Fix: CDR R-Value

CDR uses a **fixed R = 1.0** (per Chen). This avoids accidental policy penalties that would otherwise suppress CDR deployment.

**File**: `gcr_model.py` → `CEA.calculate_policy_r_multiplier()`

```python
if channel == ChannelType.CDR:
    return 1.0
```

## Calibration Notes

- If conventional mitigation crowds out CDR, lower the conventional cap or accelerate the conventional capacity limit timeline.
