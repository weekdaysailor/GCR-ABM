# Climate Model Design: Carbon Cycle with Ocean and Terrestrial Sinks

## Executive Summary

This document specifies a redesigned climate model for the GCR-ABM simulation that replaces the current simplified "bathtub" model with a physically-based carbon cycle including ocean and terrestrial sinks, temperature feedbacks, and climate-dependent project risks.

**Current State**: Atmospheric-only model with fixed airborne fraction (0.47 ppm/GtC)

**Target State**: Four-reservoir carbon cycle with dynamic sink behavior, temperature calculation, and feedback loops

---

## 1. Current Model Limitations

### 1.1 What Exists Today

```
Current Carbon Flow (gcr_model.py lines 1525-1550):

    BAU Emissions (40 GtCO2/yr)
           │
           ▼
    ┌─────────────────┐
    │   ATMOSPHERE    │  ← Only reservoir modeled
    │   (420 ppm)     │
    └─────────────────┘
           ▲
           │
    CDR Sequestration
```

**Fixed Conversion**: `1 GtC ≈ 0.47 ppm` (no sink dynamics)

### 1.2 What's Missing

| Component | Real World | Current Model | Impact |
|-----------|-----------|---------------|--------|
| Ocean sink | 25% of emissions | Not modeled | Overestimates atmospheric accumulation |
| Terrestrial sink | 30% of emissions | Not modeled | Overestimates atmospheric accumulation |
| Temperature | Drives feedbacks | Not calculated | Cannot assess physical climate risk |
| Sink saturation | Weakens with warming | Fixed conversion | Underestimates late-stage difficulty |
| Permafrost | Amplifying feedback | Not modeled | Missing ~100 GtC risk |
| Project risk | Climate-dependent | Fixed 2% failure | Understates CDR reversal risk |

### 1.3 Implications for BoE Audit

Without proper carbon cycle modeling, the simulation cannot answer:
- "What happens to XCR value if ocean sink saturates?"
- "What's the stranded asset risk if warming exceeds 2°C?"
- "How does project durability change with climate?"
- "What are the tail risks from climate feedbacks?"

---

## 2. Proposed Architecture

### 2.1 Four-Reservoir Carbon Cycle

```
                    EMISSIONS (Fossil + Land Use)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ATMOSPHERE                                │
│                     (Currently: 870 GtC)                        │
│                     (Target: 735 GtC = 350 ppm)                 │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    ▲
         │ Ocean              │ Land               │ Feedbacks
         │ Uptake             │ Uptake             │ (Permafrost,
         ▼                    ▼                    │  Fire, etc.)
┌─────────────────┐   ┌─────────────────┐         │
│  SURFACE OCEAN  │   │   TERRESTRIAL   │         │
│   (~1000 GtC)   │   │   BIOSPHERE     │─────────┘
│                 │   │   (~2000 GtC)   │
└────────┬────────┘   └─────────────────┘
         │
         │ Deep mixing
         ▼
┌─────────────────┐
│   DEEP OCEAN    │
│  (~37,000 GtC)  │
└─────────────────┘
```

### 2.2 Key State Variables

| Variable | Symbol | Units | Initial Value | Description |
|----------|--------|-------|---------------|-------------|
| Atmospheric CO2 | C_atm | GtC | 870 (420 ppm) | Primary state variable |
| Surface ocean carbon | C_ocean_s | GtC | 1,000 | Mixed layer (0-100m) |
| Deep ocean carbon | C_ocean_d | GtC | 37,000 | Below mixed layer |
| Terrestrial carbon | C_land | GtC | 2,000 | Vegetation + soils |
| Global mean temperature | T | °C | +1.2 | Anomaly vs pre-industrial |
| Cumulative emissions | E_cum | GtC | 650 | Since 1750 |

### 2.3 Conversion Constants

| Constant | Value | Source |
|----------|-------|--------|
| ppm per GtC | 0.47 | IPCC AR6 |
| GtCO2 per GtC | 3.67 | Molecular weight ratio |
| Pre-industrial CO2 | 280 ppm (590 GtC) | IPCC |
| Current CO2 | 420 ppm (870 GtC) | 2024 observation |
| Target CO2 | 350 ppm (735 GtC) | GCR target |

---

## 3. Ocean Sink Model

### 3.1 Physical Basis

The ocean absorbs CO2 through:
1. **Solubility pump**: CO2 dissolves in cold surface water, sinks to depth
2. **Biological pump**: Phytoplankton fix CO2, organic matter sinks
3. **Carbonate chemistry**: CO2 + H2O ↔ H2CO3 ↔ HCO3⁻ + H⁺ ↔ CO3²⁻ + 2H⁺

### 3.2 Uptake Formulation

**Base Ocean Uptake** (Revelle factor approach):

```
F_ocean = k_ocean × (C_atm - C_atm_eq) × β(T) × γ(ΔpCO2)

Where:
- k_ocean = 0.25 (baseline: 25% of emissions absorbed)
- C_atm_eq = pre-industrial equilibrium (590 GtC)
- β(T) = temperature sensitivity (reduces uptake as ocean warms)
- γ(ΔpCO2) = Revelle factor (reduces uptake as ocean acidifies)
```

### 3.3 Temperature Sensitivity (β)

Warmer oceans hold less dissolved CO2:

```
β(T) = 1 - 0.03 × (T - T_ref)

Where:
- T = current temperature anomaly (°C)
- T_ref = 1.0°C (reference warming)
- Coefficient: 3% reduction per °C warming
```

| Temperature Anomaly | β(T) | Effect |
|--------------------|------|--------|
| +1.0°C | 1.00 | Baseline |
| +1.5°C | 0.985 | 1.5% reduction |
| +2.0°C | 0.97 | 3% reduction |
| +3.0°C | 0.94 | 6% reduction |
| +4.0°C | 0.91 | 9% reduction |

### 3.4 Revelle Factor Sensitivity (γ)

As CO2 increases, ocean chemistry becomes less favorable for absorption:

```
γ(ΔpCO2) = 1 / (1 + 0.0015 × (C_atm - 590))

Where:
- 590 GtC = pre-industrial baseline
- Coefficient calibrated to IPCC projections
```

| CO2 Level | ΔC from PI | γ factor | Effect |
|-----------|-----------|----------|--------|
| 280 ppm (590 GtC) | 0 | 1.00 | Baseline |
| 350 ppm (735 GtC) | 145 | 0.82 | 18% reduction |
| 420 ppm (870 GtC) | 280 | 0.70 | 30% reduction |
| 500 ppm (1050 GtC) | 460 | 0.59 | 41% reduction |
| 560 ppm (1175 GtC) | 585 | 0.53 | 47% reduction |

### 3.5 Ocean-Atmosphere Exchange

```
Annual flux (GtC/year):

F_ocean_uptake = k_ocean × E_annual × β(T) × γ(ΔpCO2)

Where:
- E_annual = annual emissions (GtC/year)
- Result: fraction of emissions absorbed by ocean
```

### 3.6 Deep Ocean Mixing

Surface-to-deep transfer (slow, multi-century timescale):

```
F_mixing = k_mix × (C_ocean_s - C_ocean_s_eq)

Where:
- k_mix = 0.01 (1% per year turnover)
- Represents thermohaline circulation
- Creates long-term carbon storage
```

---

## 4. Terrestrial Sink Model

### 4.1 Physical Basis

Land absorbs CO2 through:
1. **Photosynthesis**: CO2 + H2O + light → organic carbon
2. **Soil sequestration**: Organic matter accumulates in soils
3. **Forest growth**: Biomass accumulation in expanding forests

Land releases CO2 through:
1. **Respiration**: Temperature-dependent decomposition
2. **Fire**: Climate-dependent wildfire emissions
3. **Land use change**: Deforestation, agriculture

### 4.2 Uptake Formulation

**Net Terrestrial Flux**:

```
F_land = F_uptake - F_respiration - F_fire - F_luc

Where:
- F_uptake = CO2 fertilization + regrowth
- F_respiration = temperature-dependent decomposition
- F_fire = climate-driven wildfire emissions
- F_luc = land use change emissions (exogenous)
```

### 4.3 CO2 Fertilization Effect

Higher CO2 increases photosynthesis (logarithmic saturation):

```
F_uptake_base = k_land × ln(C_atm / C_atm_pi) × A_forest

Where:
- k_land = 3.0 GtC/year (baseline uptake rate)
- C_atm_pi = 590 GtC (pre-industrial)
- A_forest = forest area factor (0-1, decreases with deforestation)
```

| CO2 Level | ln(C/C_pi) | Fertilization Factor |
|-----------|------------|---------------------|
| 280 ppm | 0.00 | 1.00 (baseline) |
| 350 ppm | 0.22 | 1.22 |
| 420 ppm | 0.39 | 1.39 |
| 500 ppm | 0.58 | 1.58 |
| 560 ppm | 0.69 | 1.69 |

### 4.4 Temperature-Dependent Respiration

Warmer soils release more CO2 (Q10 relationship):

```
F_respiration = F_resp_base × Q10^((T - T_ref) / 10)

Where:
- F_resp_base = 2.0 GtC/year
- Q10 = 2.0 (respiration doubles per 10°C warming)
- T_ref = 1.0°C
```

| Temperature | Q10 Factor | Respiration (GtC/yr) |
|-------------|-----------|---------------------|
| +1.0°C | 1.00 | 2.0 (baseline) |
| +1.5°C | 1.04 | 2.1 |
| +2.0°C | 1.07 | 2.1 |
| +3.0°C | 1.15 | 2.3 |
| +4.0°C | 1.23 | 2.5 |

### 4.5 Climate-Driven Fire Emissions

Fire risk increases non-linearly with warming:

```
F_fire = F_fire_base × (1 + α_fire × max(0, T - 1.5)^2)

Where:
- F_fire_base = 0.5 GtC/year (current)
- α_fire = 0.3 (fire sensitivity to warming)
- Threshold: 1.5°C (fires increase above this)
```

| Temperature | Fire Factor | Fire Emissions (GtC/yr) |
|-------------|------------|------------------------|
| +1.0°C | 1.00 | 0.5 |
| +1.5°C | 1.00 | 0.5 |
| +2.0°C | 1.08 | 0.54 |
| +3.0°C | 1.68 | 0.84 |
| +4.0°C | 2.88 | 1.44 |

### 4.6 Net Terrestrial Flux

Combining all terms:

```
F_land_net = F_uptake - F_respiration - F_fire - F_luc

Typical values (current climate):
- F_uptake ≈ 3.5 GtC/year
- F_respiration ≈ 2.0 GtC/year
- F_fire ≈ 0.5 GtC/year
- F_luc ≈ 1.0 GtC/year (exogenous, declining over time)
- Net ≈ 0 GtC/year (roughly balanced currently)
```

---

## 5. Temperature Model

### 5.1 Approach: Transient Climate Response

Use simple climate model relating cumulative emissions to temperature:

```
T = TCRE × E_cum + T_committed

Where:
- TCRE = 0.45°C per 1000 GtC (Transient Climate Response to Emissions)
- E_cum = cumulative emissions since 1750 (GtC)
- T_committed = delayed warming from ocean heat uptake
```

### 5.2 TCRE Calibration

From IPCC AR6 (central estimate):

| Cumulative Emissions | Temperature Anomaly |
|---------------------|-------------------|
| 0 GtC (1750) | 0.0°C |
| 650 GtC (2024) | +1.2°C |
| 1000 GtC | +1.8°C |
| 1500 GtC | +2.7°C |
| 2000 GtC | +3.6°C |

### 5.3 Committed Warming

Ocean thermal inertia means temperature lags CO2:

```
T_committed = 0.5°C × (1 - exp(-t_since_stabilization / τ_ocean))

Where:
- τ_ocean = 30 years (ocean response timescale)
- Represents "warming in the pipeline"
```

### 5.4 Climate Sensitivity Uncertainty

Model should support sensitivity analysis:

| Parameter | Low | Central | High |
|-----------|-----|---------|------|
| TCRE (°C/1000 GtC) | 0.27 | 0.45 | 0.63 |
| ECS (°C per 2×CO2) | 2.5 | 3.0 | 4.5 |
| Ocean thermal lag (years) | 20 | 30 | 50 |

---

## 6. Feedback Mechanisms

### 6.1 Permafrost Carbon Feedback

Thawing permafrost releases stored carbon:

```
F_permafrost = 0 if T < 1.5°C
             = k_pf × (T - 1.5) × C_permafrost_remaining if T ≥ 1.5°C

Where:
- k_pf = 0.005 (0.5% of remaining per °C per year)
- C_permafrost_initial = 100 GtC (vulnerable fraction)
- C_permafrost_remaining decreases as carbon is released
```

### 6.2 Amazon Dieback Risk

Tipping point behavior above threshold:

```
P_amazon_dieback = 0 if T < 2.5°C
                 = sigmoid((T - 3.0) / 0.5) if T ≥ 2.5°C

If dieback triggers:
- F_amazon_release = 50 GtC over 50 years (1 GtC/year)
- Reduces future terrestrial sink capacity by 20%
```

### 6.3 Ocean Circulation Weakening

AMOC slowdown reduces ocean uptake:

```
AMOC_strength = 1 - 0.1 × max(0, T - 2.0)

Effect:
- Reduces k_ocean proportionally
- At +4°C: 20% reduction in ocean uptake capacity
```

### 6.4 Feedback Summary Table

| Feedback | Threshold | Magnitude | Timescale |
|----------|-----------|-----------|-----------|
| Permafrost | +1.5°C | 100 GtC | 50-200 years |
| Amazon dieback | +2.5-3.5°C | 50 GtC | 50 years |
| Boreal forest | +3.0°C | 30 GtC | 100 years |
| AMOC weakening | +2.0°C | -20% ocean sink | Gradual |
| Methane hydrates | +4.0°C | 50-500 GtC | 100+ years |

---

## 7. Airborne Fraction Dynamics

### 7.1 Definition

```
AF = ΔC_atm / E_annual

Where:
- AF = airborne fraction (fraction of emissions staying in atmosphere)
- Current value: ~45% (0.45)
- Historical range: 40-50%
```

### 7.2 Dynamic Calculation

Replace fixed 0.47 ppm/GtC with:

```
AF(t) = 1 - f_ocean(t) - f_land(t) + f_feedback(t)

Where:
- f_ocean = F_ocean_uptake / E_annual
- f_land = F_land_net / E_annual
- f_feedback = (F_permafrost + F_fire_excess) / E_annual
```

### 7.3 Projected Airborne Fraction

| Scenario | 2024 | 2050 | 2100 |
|----------|------|------|------|
| Low warming (+1.5°C) | 0.45 | 0.47 | 0.50 |
| Medium (+2.0°C) | 0.45 | 0.50 | 0.55 |
| High (+3.0°C) | 0.45 | 0.55 | 0.65 |
| Very high (+4.0°C) | 0.45 | 0.60 | 0.75 |

**Key Insight**: Airborne fraction INCREASES with warming, making late-stage mitigation harder.

---

## 8. Integration with GCR Model

### 8.1 New CarbonCycle Class

```
class CarbonCycle:
    """Four-reservoir carbon cycle with feedbacks"""

    State variables:
    - c_atm: float          # Atmospheric carbon (GtC)
    - c_ocean_surface: float # Surface ocean carbon (GtC)
    - c_ocean_deep: float   # Deep ocean carbon (GtC)
    - c_land: float         # Terrestrial carbon (GtC)
    - temperature: float    # Global mean temperature anomaly (°C)
    - cumulative_emissions: float  # Since pre-industrial (GtC)

    Key methods:
    - step(emissions, sequestration, year) → updates all reservoirs
    - get_airborne_fraction() → current AF
    - get_sink_capacities() → ocean and land uptake rates
    - get_feedback_emissions() → permafrost, fire, etc.
    - get_project_risk_multiplier(temp) → climate risk to projects
```

### 8.2 Modified Simulation Flow

```
Current flow (simplified):
  emissions → atmosphere → sequestration

Proposed flow:
  emissions
      │
      ├── atmosphere (airborne fraction)
      ├── ocean sink (temperature, chemistry dependent)
      └── land sink (CO2 fertilization, respiration balance)

  feedbacks
      │
      ├── permafrost → atmosphere
      ├── fire → atmosphere
      └── sink weakening → higher airborne fraction

  temperature
      │
      ├── TCRE formula from cumulative emissions
      └── affects all sink rates and feedbacks
```

### 8.3 Project Risk Integration

Climate affects GCR project durability:

```
project_failure_rate = base_rate × climate_risk_multiplier(T)

climate_risk_multiplier(T):
    if T < 1.5: return 1.0
    elif T < 2.0: return 1.0 + 0.2 × (T - 1.5)  # 1.0-1.1
    elif T < 3.0: return 1.1 + 0.3 × (T - 2.0)  # 1.1-1.4
    else: return 1.4 + 0.5 × (T - 3.0)          # 1.4+
```

| Temperature | Risk Multiplier | Effective Failure Rate |
|-------------|-----------------|----------------------|
| +1.5°C | 1.0× | 2.0% (baseline) |
| +2.0°C | 1.1× | 2.2% |
| +2.5°C | 1.25× | 2.5% |
| +3.0°C | 1.4× | 2.8% |
| +4.0°C | 1.9× | 3.8% |

### 8.4 Channel-Specific Climate Risks

| Channel | Climate Sensitivity | Rationale |
|---------|-------------------|-----------|
| CDR (engineered) | Low (1.0×) | Less climate-dependent |
| Conventional | Medium (1.2×) | Some infrastructure risk |
| Co-benefits (nature) | High (1.5×) | Forest fire, drought, pest |

---

## 9. Output Variables

### 9.1 New DataFrame Columns

| Column | Units | Description |
|--------|-------|-------------|
| `Temperature_Anomaly` | °C | Global mean temperature vs pre-industrial |
| `Ocean_Uptake_GtC` | GtC/year | Annual ocean carbon absorption |
| `Land_Uptake_GtC` | GtC/year | Annual terrestrial carbon absorption |
| `Airborne_Fraction` | ratio | Fraction of emissions staying in atmosphere |
| `Ocean_Sink_Capacity` | ratio | Current vs baseline ocean uptake (0-1) |
| `Land_Sink_Capacity` | ratio | Current vs baseline land uptake (0-1) |
| `Permafrost_Emissions_GtC` | GtC/year | Feedback emissions from permafrost |
| `Fire_Emissions_GtC` | GtC/year | Climate-driven fire emissions |
| `Cumulative_Emissions_GtC` | GtC | Total since simulation start |
| `Climate_Risk_Multiplier` | ratio | Project failure rate multiplier |
| `C_Ocean_Surface_GtC` | GtC | Surface ocean carbon stock |
| `C_Land_GtC` | GtC | Terrestrial carbon stock |

### 9.2 Dashboard Additions

New "Climate Physics" tab showing:
1. Four-reservoir carbon stocks over time
2. Ocean and land uptake rates
3. Temperature trajectory vs Paris targets
4. Airborne fraction evolution
5. Feedback emissions breakdown
6. Sink capacity degradation
7. Project risk multiplier

---

## 10. Validation Requirements

### 10.1 Historical Calibration

Model must reproduce observed data:

| Metric | Observed | Model Target |
|--------|----------|--------------|
| Current CO2 | 420 ppm | 420 ± 5 ppm |
| Current temperature | +1.2°C | +1.2 ± 0.1°C |
| Ocean uptake (2010-2020) | 2.5 GtC/year | 2.5 ± 0.5 |
| Land uptake (2010-2020) | 3.1 GtC/year | 3.1 ± 0.8 |
| Airborne fraction | 44% | 44 ± 5% |

### 10.2 Scenario Consistency

Compare projections against:
- IPCC AR6 SSP scenarios
- MAGICC/FaIR reduced-complexity models
- CMIP6 Earth System Model ensemble

### 10.3 Sensitivity Tests

| Parameter | Test Range | Expected Behavior |
|-----------|-----------|-------------------|
| TCRE | 0.27-0.63 | Temperature scales linearly |
| Ocean uptake rate | ±30% | Airborne fraction changes inversely |
| Land uptake rate | ±50% | High uncertainty, large impact |
| Permafrost threshold | 1.0-2.0°C | Earlier/later feedback onset |
| Fire sensitivity | ±50% | Non-linear amplification at high T |

---

## 11. Implementation Phases

### Phase 1: Core Carbon Cycle (Priority: CRITICAL)

**Scope**: Replace fixed airborne fraction with dynamic ocean + land sinks

**Deliverables**:
- CarbonCycle class with 4 reservoirs
- Temperature calculation (TCRE)
- Basic sink dynamics (no feedbacks)
- Validation against historical data

**Acceptance Criteria**:
- Reproduces 420 ppm, +1.2°C current state
- Airborne fraction within 40-50%
- Ocean/land uptake within IPCC ranges

### Phase 2: Feedback Mechanisms (Priority: HIGH)

**Scope**: Add climate feedbacks that amplify warming

**Deliverables**:
- Permafrost carbon release
- Temperature-dependent fire emissions
- Sink saturation effects
- AMOC weakening impact

**Acceptance Criteria**:
- Feedbacks activate at documented thresholds
- Total feedback potential matches IPCC estimates
- Non-linear behavior at high temperatures

### Phase 3: Project Risk Integration (Priority: HIGH)

**Scope**: Connect climate state to GCR project durability

**Deliverables**:
- Climate risk multiplier for project failure
- Channel-specific risk factors
- Reversal rate increases with temperature
- Stranded asset risk quantification

**Acceptance Criteria**:
- Co-benefits (nature) most climate-sensitive
- CDR (engineered) least sensitive
- Risk increases non-linearly above +2°C

### Phase 4: Uncertainty Quantification (Priority: MEDIUM)

**Scope**: Enable Monte Carlo analysis of climate uncertainty

**Deliverables**:
- Parameter distributions for all climate parameters
- Ensemble run capability
- Confidence intervals on all outputs
- Tail risk quantification

**Acceptance Criteria**:
- 5th-95th percentile ranges match IPCC
- Tail risks (>+3°C) properly captured
- Sensitivity rankings documented

---

## 12. Data Sources and References

### 12.1 Primary Sources

| Source | Used For | Citation |
|--------|----------|----------|
| IPCC AR6 WG1 | TCRE, carbon budgets, feedback magnitudes | Masson-Delmotte et al. 2021 |
| Global Carbon Budget | Current fluxes, historical trends | Friedlingstein et al. 2023 |
| NOAA ESRL | CO2 observations, trends | Keeling & Keeling |
| HadCRUT5 | Temperature observations | Morice et al. 2021 |

### 12.2 Model Intercomparison

| Model | Type | Use |
|-------|------|-----|
| MAGICC | Reduced complexity | Validation benchmark |
| FaIR | Simple climate model | Parameter calibration |
| CMIP6 ensemble | Earth System Models | Uncertainty bounds |
| Hector | Open source SCM | Implementation reference |

### 12.3 Key Parameters with Sources

| Parameter | Value | Source |
|-----------|-------|--------|
| TCRE | 0.45 ± 0.18 °C/1000 GtC | IPCC AR6 WG1 Ch5 |
| Ocean uptake | 2.5 ± 0.6 GtC/year | Global Carbon Budget 2023 |
| Land uptake | 3.1 ± 0.8 GtC/year | Global Carbon Budget 2023 |
| Permafrost C | 1400-1600 GtC total | IPCC AR6 WG1 Ch5 |
| Vulnerable permafrost | 100-200 GtC | Schuur et al. 2022 |
| Amazon tipping point | 2-4°C local | Armstrong McKay et al. 2022 |

---

## 13. Risk Assessment for BoE

### 13.1 Model Risk Categories

| Risk | Current Model | Proposed Model |
|------|---------------|----------------|
| Physical accuracy | LOW (bathtub only) | HIGH (4-reservoir) |
| Sink dynamics | NONE | Full representation |
| Feedback risks | NONE | Permafrost, fire, AMOC |
| Temperature projection | NONE | TCRE-based |
| Project durability | Fixed rate | Climate-dependent |
| Tail risks | Not captured | Explicit modeling |

### 13.2 Remaining Limitations

Even with proposed changes, model will NOT include:
- Regional climate patterns
- Extreme event statistics
- Ecosystem-specific responses
- Ice sheet dynamics
- Sea level rise
- Non-CO2 greenhouse gases

### 13.3 Recommended Caveats

Model outputs should include:
1. "Climate projections are illustrative, not predictive"
2. "Feedback magnitudes have high uncertainty (±50%)"
3. "Tail risks may be underestimated"
4. "Regional impacts not captured"

---

## 14. Summary

### 14.1 Key Changes from Current Model

| Aspect | Current | Proposed |
|--------|---------|----------|
| Reservoirs | 1 (atmosphere) | 4 (atm, ocean surface, ocean deep, land) |
| Airborne fraction | Fixed (0.47 ppm/GtC) | Dynamic (depends on T, CO2) |
| Temperature | Not modeled | TCRE-based calculation |
| Ocean sink | Not modeled | Chemistry + temperature dependent |
| Land sink | Not modeled | CO2 fertilization + respiration |
| Feedbacks | None | Permafrost, fire, sink saturation |
| Project risk | Fixed 2% | Climate-dependent (2-4%+) |

### 14.2 Expected Impact on Simulation Results

With proper carbon cycle:
1. **Early years**: Similar to current (sinks absorb ~55% of emissions)
2. **Mid-century**: Harder to reduce CO2 (sinks weakening)
3. **Late century**: Much harder if T > 2°C (feedbacks activate)
4. **Project failures**: Higher in warming scenarios
5. **XCR economics**: More conservative projections

### 14.3 BoE Audit Readiness

Proposed model addresses:
- ✅ Physical basis for carbon projections
- ✅ Temperature calculation for risk assessment
- ✅ Sink dynamics for late-stage scenarios
- ✅ Feedback risks for tail events
- ✅ Climate-dependent project durability
- ✅ Uncertainty quantification capability

Remaining gaps (out of scope):
- ⚠️ Regional climate modeling
- ⚠️ Non-CO2 gases
- ⚠️ Extreme events
- ⚠️ Ice sheet dynamics

---

## 15. Review Notes (Implementation Improvements)

1. **Fix temperature units in §5.1**: Use a single formulation that matches Appendix A: `T = (TCRE/1000) × E_cum + T_committed`, with `E_cum` defined as GtC from 1850 onward, to avoid a silent 1000× scaling error.
2. **Pick one ocean uptake driver**: §3.2 uses atmospheric disequilibrium `(C_atm - C_atm_eq)` while §3.5/§7.2 use a fixed fraction of annual emissions. Choose the disequilibrium + mixing formulation, and calibrate `k_ocean`, `β`, and `γ` to the Global Carbon Budget targets so airborne fraction and sink saturation behavior are consistent.
3. **Clarify timestep and guards in Appendix A**: State the 1-year step order, require reservoir stocks `≥ 0`, and guard that `F_ocean + F_land ≤ E + feedbacks + sequestration`. Add a small hindcast test harness (1850→2024) that asserts ppm, °C, and airborne fraction hit the targets to catch implementation drift.

## Appendix A: Mathematical Summary

### A.1 State Update Equations

```
Per time step (1 year):

1. Emissions flux:
   E = E_bau - E_conventional_mitigation

2. Ocean uptake:
   F_ocean = k_o × E × β(T) × γ(C_atm)
   C_ocean_s += F_ocean - F_mixing
   C_ocean_d += F_mixing

3. Land flux:
   F_land = k_l × ln(C_atm/C_pi) - F_resp(T) - F_fire(T) - F_luc
   C_land += F_land

4. Feedbacks:
   F_fb = F_permafrost(T) + F_fire_excess(T)

5. Atmospheric update:
   C_atm += E - F_ocean - F_land + F_fb - Sequestration_CDR

6. Temperature update:
   E_cum += E
   T = TCRE × E_cum / 1000
```

### A.2 Parameter Table

| Symbol | Parameter | Value | Units |
|--------|-----------|-------|-------|
| k_o | Ocean uptake coefficient | 0.25 | - |
| k_l | Land uptake coefficient | 3.0 | GtC/year |
| k_mix | Ocean mixing rate | 0.01 | year⁻¹ |
| TCRE | Climate response | 0.45 | °C/1000 GtC |
| Q10 | Respiration sensitivity | 2.0 | - |
| α_fire | Fire sensitivity | 0.3 | °C⁻² |
| k_pf | Permafrost release rate | 0.005 | year⁻¹ °C⁻¹ |

---

## Appendix B: Validation Test Cases

### B.1 Historical Reproduction (1850-2024)

| Year | Observed CO2 | Model CO2 | Observed T | Model T |
|------|--------------|-----------|------------|---------|
| 1850 | 285 ppm | 285 ppm | 0.0°C | 0.0°C |
| 1950 | 310 ppm | 310 ± 5 | +0.2°C | +0.2°C |
| 2000 | 370 ppm | 370 ± 5 | +0.6°C | +0.6°C |
| 2024 | 420 ppm | 420 ± 5 | +1.2°C | +1.2°C |

### B.2 SSP Scenario Comparison

| Scenario | 2100 CO2 (IPCC) | 2100 CO2 (Model) | 2100 T (IPCC) | 2100 T (Model) |
|----------|-----------------|------------------|---------------|----------------|
| SSP1-1.9 | 350-400 ppm | Within range | +1.4°C | Within range |
| SSP2-4.5 | 500-600 ppm | Within range | +2.7°C | Within range |
| SSP5-8.5 | 800-1000 ppm | Within range | +4.4°C | Within range |

---

*Document Version: 1.0*
*Created: 2026-01-03*
*Status: Design Specification (Not Implemented)*
