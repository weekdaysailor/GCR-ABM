# LLM-Powered Projects Broker Design

## Overview

This document designs **ProjectsBrokerLLM**, an LLM-powered variant of the ProjectsBroker agent that uses local language models to make strategic decisions about project portfolio allocation.

Unlike the simpler LLM agents (InvestorMarket, CapitalMarket, CEA, CentralBank) which make scalar decisions (sentiment, flow %, brake factor), ProjectsBroker makes **complex multi-dimensional portfolio allocation decisions** involving:
- Capital allocation across CDR vs Conventional channels
- Geographic distribution across 50 countries
- Project scale and development timeline decisions
- Capacity constraint management

---

## Design Challenges

### Challenge 1: Context Window Constraints

**Problem**: Full portfolio state exceeds context limits for local models.

- **Current portfolio**: 100-1000+ projects in later years
- **Country pool**: 50 countries with individual attributes (GDP, tier, active status, preferences)
- **Technology state**: Learning curves, costs per channel, cumulative deployment
- **Llama 3.1 8B context**: ~8K tokens
- **Llama 3.1 70B context**: ~128K tokens (extended)

**Solution**: Use **aggregated state representation** instead of per-project detail.

### Challenge 2: Decision Granularity

**Problem**: Should LLM decide per-project or in aggregate?

**Options**:
- **Option A (Aggregate)**: "Initiate X CDR projects in Africa, Y Conventional in North America"
- **Option B (Per-Project)**: "For this specific 47 MT CDR project in Brazil, decide yes/no"
- **Option C (Capital Allocation)**: "Allocate $5B to CDR, $3B to Conventional"

**Recommendation**: **Option C (Capital Allocation)** - Aligns with how real investors/policymakers think, fits context window, allows rule-based execution.

### Challenge 3: Integration with Existing Logic

**Problem**: ProjectsBroker has well-tested logic for:
- Country preferences by channel (CDR prefers tropical, Conventional prefers Tier 1)
- Project scale damping (learning curves)
- Profitability calculations
- Stochastic failures

**Solution**: **Hybrid approach** - LLM decides strategic allocation, rule-based logic executes tactical details.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ProjectsBrokerLLM                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Strategic Layer (LLM)                      │  │
│  │  - Allocate capital across channels                  │  │
│  │  - Set regional priorities                           │  │
│  │  - Adjust risk appetite                              │  │
│  │  - Respond to climate urgency                        │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│                   ▼                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Tactical Layer (Rule-Based)                │  │
│  │  - Execute project initiations per LLM allocation    │  │
│  │  - Apply country preferences                         │  │
│  │  - Calculate project scale (damping)                 │  │
│  │  - Handle stochastic failures                        │  │
│  │  - Enforce capacity constraints                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Division of Labor**:
- **LLM (Strategic)**: "Allocate 60% of capital to CDR, 40% to Conventional; prioritize Asia/Africa"
- **Rule-based (Tactical)**: "Create 12 CDR projects in Indonesia, India, Kenya per profitability and preferences"

---

## LLM Decision Structure

### Input State (Aggregated)

```python
{
    # Economic state
    "available_capital_usd": 5.2e9,
    "market_price_xcr": 142.5,
    "price_floor_xcr": 130.0,
    "sentiment": 0.82,

    # Climate urgency
    "current_co2_ppm": 408.3,
    "target_co2_ppm": 350.0,
    "years_remaining": 42,
    "roadmap_gap_ppm": 3.2,  # Behind or ahead
    "temperature_anomaly_c": 1.18,

    # Portfolio state (aggregated)
    "projects_operational_cdr": 234,
    "projects_operational_conventional": 178,
    "projects_development_cdr": 45,
    "projects_development_conventional": 32,
    "annual_sequestration_cdr_gt": 8.3,
    "annual_sequestration_conventional_gt": 12.1,

    # Technology economics
    "cdr_cost_per_tonne": 78.50,
    "conventional_cost_per_tonne": 62.30,
    "cdr_profitability": 0.81,  # (price/R) / cost
    "conventional_profitability": 0.94,
    "cdr_capacity_utilization": 0.83,
    "conventional_capacity_utilization": 0.61,

    # Regional opportunity (top regions by available capacity)
    "top_regions": [
        {"region": "Asia", "active_countries": 8, "available_capacity_gt": 3.2},
        {"region": "North America", "active_countries": 2, "available_capacity_gt": 2.1},
        {"region": "Africa", "active_countries": 6, "available_capacity_gt": 1.8},
        {"region": "South America", "active_countries": 3, "available_capacity_gt": 1.1}
    ],

    # Constraints
    "cea_brake_factor": 0.85,
    "inflation": 0.027,
    "cqe_budget_utilization": 0.42,

    # Year context
    "year": 8,
    "total_years": 50
}
```

**Size**: ~400-600 tokens (well within llama 3.1 8B context)

### Output Decision

```json
{
    "capital_allocation": {
        "cdr_fraction": 0.62,
        "conventional_fraction": 0.38
    },
    "regional_priorities": {
        "Asia": 0.35,
        "North America": 0.25,
        "Africa": 0.20,
        "South America": 0.12,
        "Europe": 0.08
    },
    "risk_appetite": 0.75,
    "reasoning": "Climate urgency high (3.2 ppm behind roadmap). CDR profitability improved (0.81), prioritize scale-up. Asia has largest available capacity (3.2 Gt). Conservative risk appetite (0.75) due to inflation at 2.7% and brake factor engaged."
}
```

**Validation**:
- `cdr_fraction + conventional_fraction == 1.0`
- `sum(regional_priorities.values()) == 1.0`
- `0.0 <= risk_appetite <= 1.0` (affects project scale variance)

---

## Prompt Template

```python
PROJECTS_BROKER_PROMPT = """
You are managing a global portfolio of carbon mitigation projects for the GCR system.

## Current State (Year {year} of {total_years})

### Climate Urgency
- Current CO2: {current_co2_ppm} ppm (target: {target_co2_ppm} ppm)
- Roadmap Status: {roadmap_status} ({roadmap_gap_ppm:+.1f} ppm)
- Temperature: {temperature_anomaly_c:.2f}°C above pre-industrial
- Years Remaining: {years_remaining}

### Available Resources
- Available Capital: ${available_capital_usd/1e9:.2f}B
- Market Sentiment: {sentiment:.2f} (0=panic, 1=full trust)
- XCR Price: ${market_price_xcr:.2f} (floor: ${price_floor_xcr:.2f})

### Current Portfolio
- **CDR Projects**: {projects_operational_cdr} operational ({annual_sequestration_cdr_gt:.1f} Gt/yr), {projects_development_cdr} developing
- **Conventional Projects**: {projects_operational_conventional} operational ({annual_sequestration_conventional_gt:.1f} Gt/yr), {projects_development_conventional} developing

### Technology Economics
- **CDR**: ${cdr_cost_per_tonne:.2f}/tonne, profitability {cdr_profitability:.2f}, capacity {cdr_capacity_utilization:.0%} used
- **Conventional**: ${conventional_cost_per_tonne:.2f}/tonne, profitability {conventional_profitability:.2f}, capacity {conventional_capacity_utilization:.0%} used

### Regional Opportunities
{regional_summary}

### Economic Constraints
- CEA Brake Factor: {cea_brake_factor:.2f} (1.0 = no constraint)
- Inflation: {inflation:.1%} (target: 2.0%)
- CQE Budget Used: {cqe_budget_utilization:.0%}

## Your Task

Allocate the available capital across CDR and Conventional channels, and set regional priorities.

**Strategic Considerations**:
1. **Climate Urgency**: How far behind/ahead of roadmap? Temperature risk?
2. **Economic Viability**: Which channel offers better profitability?
3. **Capacity Constraints**: Which channel has room to grow?
4. **Geographic Opportunity**: Where are the best project sites available?
5. **System Stability**: How tight are economic constraints (brake, inflation)?
6. **Portfolio Balance**: Avoid over-concentration in one channel/region

**Capital Allocation Rules**:
- Must sum to 1.0 (100% of capital allocated)
- CDR: High permanence, higher cost, limited capacity (10 Gt/yr)
- Conventional: Lower cost, larger capacity (30 Gt/yr), mature tech

**Regional Priority Rules**:
- Must sum to 1.0
- Regions: Asia, North America, Africa, South America, Europe, Oceania
- Consider active countries and available capacity per region

**Risk Appetite** (0.0-1.0):
- High (0.9-1.0): Aggressive project initiation, larger scale variance
- Medium (0.5-0.8): Balanced approach
- Low (0.0-0.4): Conservative, smaller projects, high certainty

Respond with JSON only:
{{
    "capital_allocation": {{
        "cdr_fraction": 0.XX,
        "conventional_fraction": 0.XX
    }},
    "regional_priorities": {{
        "Asia": 0.XX,
        "North America": 0.XX,
        "Africa": 0.XX,
        "South America": 0.XX,
        "Europe": 0.XX,
        "Oceania": 0.XX
    }},
    "risk_appetite": 0.XX,
    "reasoning": "brief explanation (2-3 sentences)"
}}
"""
```

---

## Tactical Execution (Rule-Based)

After LLM provides strategic allocation, rule-based logic executes:

```python
def execute_llm_allocation(self, llm_decision, state):
    """
    Execute LLM strategic decision using rule-based tactical logic.
    """
    # Parse LLM decision
    cdr_capital = state["available_capital"] * llm_decision["cdr_fraction"]
    conv_capital = state["available_capital"] * llm_decision["conventional_fraction"]

    # CDR projects
    cdr_projects = self._initiate_channel_projects(
        channel="CDR",
        budget=cdr_capital,
        regional_priorities=llm_decision["regional_priorities"],
        risk_appetite=llm_decision["risk_appetite"],
        state=state
    )

    # Conventional projects
    conv_projects = self._initiate_channel_projects(
        channel="CONVENTIONAL",
        budget=conv_capital,
        regional_priorities=llm_decision["regional_priorities"],
        risk_appetite=llm_decision["risk_appetite"],
        state=state
    )

    return cdr_projects + conv_projects

def _initiate_channel_projects(self, channel, budget, regional_priorities, risk_appetite, state):
    """
    Tactical project initiation per LLM allocation.
    """
    projects = []
    remaining_budget = budget

    # Get active countries sorted by regional priority
    countries = self._get_countries_by_priority(regional_priorities, channel)

    while remaining_budget > 0:
        # Select country (weighted by regional priority)
        country = self._select_country(countries, regional_priorities)

        # Calculate project scale (base scale × damping × risk appetite variance)
        base_scale = np.random.uniform(10e6, 100e6)  # 10-100 MT
        damped_scale = base_scale * self._get_scale_damper(state["cumulative_deployment"])

        # Risk appetite affects scale variance
        if risk_appetite > 0.8:
            scale = damped_scale * np.random.uniform(0.8, 1.2)  # High variance
        elif risk_appetite > 0.5:
            scale = damped_scale * np.random.uniform(0.9, 1.1)  # Medium variance
        else:
            scale = damped_scale * np.random.uniform(0.95, 1.05)  # Low variance

        # Check profitability
        cost = self._get_technology_cost(channel, state["cumulative_deployment"])
        if (state["market_price"] / self._get_r_value(channel)) < cost:
            break  # Not profitable, stop initiating

        # Check capacity constraints
        if not self._check_capacity_available(channel, scale, state):
            break

        # Calculate project cost
        project_cost = scale * cost * 2.5  # Development years

        if project_cost > remaining_budget:
            break

        # Create project
        project = Project(
            channel=channel,
            country=country,
            annual_sequestration_tonnes=scale,
            marginal_cost_per_tonne=cost,
            # ... other fields
        )
        projects.append(project)
        remaining_budget -= project_cost

    return projects
```

---

## Integration with GCR_ABM_Simulation

```python
# Modified __init__ in gcr_model.py
def __init__(self,
             years=50,
             llm_enabled=False,
             llm_model="llama3.1:8b",
             llm_agents=None):

    # Initialize LLM engine
    if llm_enabled:
        self.llm_engine = LLMEngine(model=llm_model)

    # Create ProjectsBroker (LLM or rule-based)
    if llm_enabled and "projects_broker" in llm_agents:
        from llm_agents import ProjectsBrokerLLM
        self.projects_broker = ProjectsBrokerLLM(
            llm_engine=self.llm_engine,
            countries=self.countries,
            # ... other params
        )
    else:
        self.projects_broker = ProjectsBroker(
            countries=self.countries,
            # ... other params
        )
```

---

## State Aggregation Functions

```python
def _aggregate_state_for_llm(self, year):
    """
    Create compact state representation for LLM (< 1000 tokens).
    """
    # Regional aggregation
    regions = {
        "Asia": ["China", "India", "Indonesia", "Japan", "South Korea", ...],
        "North America": ["USA", "Canada", "Mexico"],
        "Africa": ["Kenya", "Nigeria", "South Africa", ...],
        "South America": ["Brazil", "Argentina", "Colombia", ...],
        "Europe": ["Germany", "UK", "France", ...],
        "Oceania": ["Australia", "New Zealand"]
    }

    regional_summary = []
    for region, country_list in regions.items():
        active = sum(1 for c in country_list if c in self.active_countries)
        capacity = self._calculate_available_capacity(country_list, region)
        regional_summary.append({
            "region": region,
            "active_countries": active,
            "available_capacity_gt": capacity
        })

    # Portfolio aggregation
    cdr_projects = [p for p in self.projects if p.channel == "CDR" and p.status == "OPERATIONAL"]
    conv_projects = [p for p in self.projects if p.channel == "CONVENTIONAL" and p.status == "OPERATIONAL"]

    return {
        "available_capital_usd": self._calculate_available_capital(year),
        "market_price_xcr": self.market_price,
        "current_co2_ppm": self.current_co2,
        "roadmap_gap_ppm": self._calculate_roadmap_gap(year),
        "projects_operational_cdr": len(cdr_projects),
        "annual_sequestration_cdr_gt": sum(p.annual_sequestration_tonnes for p in cdr_projects) / 1e9,
        # ... other aggregated state
        "top_regions": sorted(regional_summary, key=lambda x: x["available_capacity_gt"], reverse=True)[:4],
        "year": year,
        "total_years": self.years
    }
```

---

## Fallback Behavior

If LLM fails (Ollama down, timeout, invalid JSON):

```python
def _llm_decide_allocation(self, state):
    """
    Strategic allocation decision via LLM with rule-based fallback.
    """
    try:
        response = self.llm_engine.decide(
            agent_name="projects_broker",
            prompt_template=self.PROMPT_TEMPLATE,
            state=state,
            year=state["year"]
        )

        # Validate response
        self._validate_allocation(response)
        return response

    except (ConnectionError, TimeoutError, JSONDecodeError, ValidationError) as e:
        logger.warning(f"ProjectsBrokerLLM failed, using rule-based fallback: {e}")
        return self._rule_based_allocation(state)

def _rule_based_allocation(self, state):
    """
    Default allocation strategy when LLM unavailable.
    """
    # Simple heuristic: allocate based on profitability
    cdr_prof = state["cdr_profitability"]
    conv_prof = state["conventional_profitability"]
    total_prof = cdr_prof + conv_prof

    # Capacity-constrained adjustment
    cdr_capacity_available = 1.0 - state["cdr_capacity_utilization"]
    conv_capacity_available = 1.0 - state["conventional_capacity_utilization"]

    return {
        "capital_allocation": {
            "cdr_fraction": (cdr_prof / total_prof) * cdr_capacity_available,
            "conventional_fraction": (conv_prof / total_prof) * conv_capacity_available
        },
        "regional_priorities": self._default_regional_priorities(),
        "risk_appetite": 0.6,  # Medium risk default
        "reasoning": "Rule-based fallback allocation"
    }
```

---

## Caching Considerations

**Challenge**: Portfolio state changes every year, so state hashes rarely match.

**Solutions**:

1. **Coarse-grained state hashing**: Round values to reduce hash diversity
   ```python
   def _hash_state(self, state):
       # Round to reduce cache misses
       rounded = {
           "co2": round(state["current_co2_ppm"], 1),  # 408.3 → 408.3
           "capital": round(state["available_capital_usd"] / 1e9, 1),  # Billions
           "cdr_prof": round(state["cdr_profitability"], 2),
           "year_bin": state["year"] // 5  # Cache per 5-year period
       }
       return hashlib.sha256(json.dumps(rounded, sort_keys=True).encode()).hexdigest()
   ```

2. **Periodic caching**: Only cache every N years
   ```python
   def decide_allocation(self, state):
       if state["year"] % 5 == 0:  # Cache every 5 years
           return self._llm_decide_allocation(state)
       else:
           return self._rule_based_allocation(state)  # Rule-based between
   ```

3. **Disable caching for ProjectsBroker**: Use LLM variation every year
   ```python
   sim = GCR_ABM_Simulation(
       llm_enabled=True,
       llm_cache_mode="disabled",  # Fresh LLM calls
       llm_agents=["projects_broker"]
   )
   ```

**Recommendation**: Use **periodic caching** (every 5 years) to balance computational cost with strategic variety.

---

## Performance Considerations

| Configuration | LLM Calls/Run | Time per Run | Strategy |
|---------------|---------------|--------------|----------|
| **Every year** | 50 calls (50 years) | ~200-500 seconds | Maximum variation |
| **Every 5 years** | 10 calls | ~40-100 seconds | Balanced |
| **Every 10 years** | 5 calls | ~20-50 seconds | Fast, strategic shifts |
| **Cached (read_write)** | ~5 unique (first run) | ~20-50 seconds (first), ~10s (cached) | Reproducible |

**Recommendation**: Start with **every 5 years** for development/testing.

---

## Testing Strategy

```python
# test_llm_agents.py additions

def test_projects_broker_llm_allocation():
    """Test ProjectsBrokerLLM produces valid allocation decisions"""
    from llm_agents import ProjectsBrokerLLM

    broker = ProjectsBrokerLLM(llm_engine=None, countries=test_countries)

    # Test with mock state
    state = {
        "available_capital_usd": 5e9,
        "current_co2_ppm": 410.0,
        "cdr_profitability": 0.85,
        "conventional_profitability": 0.92,
        # ... full state
    }

    allocation = broker.decide_allocation(state)

    # Validate structure
    assert "capital_allocation" in allocation
    assert abs(allocation["capital_allocation"]["cdr_fraction"] +
               allocation["capital_allocation"]["conventional_fraction"] - 1.0) < 0.01

    assert "regional_priorities" in allocation
    assert abs(sum(allocation["regional_priorities"].values()) - 1.0) < 0.01

    assert 0.0 <= allocation["risk_appetite"] <= 1.0

    print(f"✓ ProjectsBrokerLLM allocation test passed")
    print(f"  CDR: {allocation['capital_allocation']['cdr_fraction']:.1%}")
    print(f"  Conventional: {allocation['capital_allocation']['conventional_fraction']:.1%}")
    print(f"  Risk appetite: {allocation['risk_appetite']:.2f}")

def test_projects_broker_llm_fallback():
    """Test graceful fallback when LLM unavailable"""
    from llm_agents import ProjectsBrokerLLM

    broker = ProjectsBrokerLLM(llm_engine=None, countries=test_countries)

    state = {...}  # Mock state

    # Should use rule-based fallback
    allocation = broker.decide_allocation(state)

    assert allocation is not None
    assert "reasoning" in allocation
    assert "fallback" in allocation["reasoning"].lower()

    print(f"✓ ProjectsBrokerLLM fallback test passed")
```

---

## Model Recommendations

| Model | Size | Context | Quality | Recommendation |
|-------|------|---------|---------|----------------|
| **llama3.1:8b** | 8B | 8K | Good | ✅ Default - fast, adequate reasoning |
| **llama3.1:70b** | 70B | 128K | Better | ✅ Best balance (higher quality, extended context) |
| **llama3.1:405b** | 405B | 128K | Best | ⚠️ Slow, requires high-end GPU |
| **llama3.2** | 3B | 4K | Fair | ❌ Too small for portfolio reasoning |
| **mistral** | 7B | 8K | Good | ✅ Alternative to llama3.1:8b |
| **deepseek-r1:8b** | 8B | 8K | Best reasoning | ✅ Best for complex allocation logic |

**Recommendation**: Start with **llama3.1:8b** or **deepseek-r1:8b** for initial testing. Upgrade to **llama3.1:70b** if reasoning quality insufficient.

---

## Comparison: LLM vs Rule-Based

| Aspect | Rule-Based | LLM-Powered |
|--------|------------|-------------|
| **Decision basis** | Fixed formulas (profitability, capacity) | Contextual reasoning (urgency, risk, balance) |
| **Adaptability** | Deterministic, predictable | Responsive to complex conditions |
| **Computational cost** | ~0.01 seconds/year | ~4-10 seconds/year |
| **Reproducibility** | Perfect (same inputs → same outputs) | Requires caching for reproducibility |
| **Transparency** | Formulas visible in code | Reasoning in LLM response text |
| **Failure mode** | N/A (always works) | Fallback to rule-based |

**When to use LLM**:
- Exploring adaptive strategies under uncertainty
- Testing climate urgency response
- Modeling investor/policymaker psychology
- Research scenarios (not operational deployment)

**When to use rule-based**:
- Production systems requiring determinism
- Fast Monte Carlo runs (1000+ iterations)
- Regulatory audits requiring explainability
- Baseline comparisons

---

## Implementation Checklist

When implementing ProjectsBrokerLLM:

- [ ] Create `ProjectsBrokerLLM` class in `llm_agents.py`
- [ ] Implement `_aggregate_state_for_llm()` for compact state
- [ ] Write `PROJECTS_BROKER_PROMPT` template
- [ ] Implement `_validate_allocation()` for JSON validation
- [ ] Implement `execute_llm_allocation()` for tactical execution
- [ ] Add `_rule_based_allocation()` fallback
- [ ] Integrate with `GCR_ABM_Simulation.__init__()`
- [ ] Add tests to `test_llm_agents.py`
- [ ] Document in `docs/llm_agents.md`
- [ ] Add dashboard toggle (if applicable)

**Estimated Effort**: 6-8 hours (design already complete in this document)

---

## Future Enhancements

1. **Multi-agent Coordination**: ProjectsBroker consults CEA and CentralBank before allocation
   ```python
   cea_guidance = self.cea.get_strategic_guidance()
   allocation = self.llm_decide_with_guidance(state, cea_guidance)
   ```

2. **Hierarchical Decisions**: Strategic allocation (yearly) + Tactical adjustments (quarterly)

3. **Ensemble Reasoning**: Query multiple models, aggregate decisions
   ```python
   llm_decisions = [
       self.llm_engine.decide(model="llama3.1:8b", ...),
       self.llm_engine.decide(model="deepseek-r1:8b", ...),
   ]
   final_allocation = self._ensemble_aggregate(llm_decisions)
   ```

4. **Fine-tuning**: Train model on historical GCR simulation data for domain-specific reasoning

5. **Explainability Dashboard**: Show LLM reasoning alongside allocation charts in Streamlit

---

## Conclusion

**ProjectsBrokerLLM** is feasible with llama 3.1 using:
- **Aggregated state** to fit context window (< 1000 tokens)
- **Strategic/tactical split**: LLM decides allocation, rule-based executes
- **Hybrid caching**: Periodic LLM calls (every 5 years) to balance cost/variation
- **Robust fallback**: Rule-based allocation if LLM unavailable

This design preserves the strengths of the existing ProjectsBroker logic while adding adaptive, context-aware strategic decision-making via local LLMs.

**Ready for implementation** when needed.
