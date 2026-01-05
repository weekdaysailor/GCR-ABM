# Model Assumptions (Plain English)

This model is a simplified, global, yearly simulation. The notes below describe the main assumptions baked into the code.

## Time & Scope
- Time step is one year.
- Everything is global (no regional detail). CO2 is a single global atmosphere number.
- Values are approximate, not predictive; the model is for stress‑testing incentives and feedback loops.

## Carbon Cycle & Temperature
- A four‑reservoir carbon cycle is modeled: atmosphere, surface ocean, deep ocean, and land.
- Ocean and land sinks weaken with warming and higher CO2 (sink saturation is modeled).
- Temperature is based on cumulative emissions (TCRE) with a small lag for ocean heat uptake.
- Permafrost feedback adds emissions when warming exceeds a threshold.

## Emissions Baseline (BAU)
- BAU emissions start at ~40 GtCO2/year.
- Emissions peak around year 6 (roughly “before 2030” in the default setup), plateau, then begin a very gradual late‑century decline as population declines.
- CO2 continues to rise until human emissions fall to effectively zero and removals exceed emissions.
- BAU CO2 uses the same carbon‑cycle sinks as the policy scenario for fair comparison.

## Mitigation Channels
- Physical mitigation channels: CDR, conventional mitigation, and avoided deforestation (land‑use emissions).
- “Co‑benefits” are a reward overlay; they do not add extra tonnes.
- Project rewards are based on cost‑effectiveness (R‑value) relative to marginal CDR cost.
- Policy multipliers do not penalize conventional mitigation; R multipliers are fixed at 1.0.
- Conventional mitigation is structural: projects reduce the human‑emissions baseline; annual conventional mitigation reflects new structural reductions.
- Conventional mitigation is capped by remaining human emissions; once residual emissions are ~0, credits stop and CDR handles drawdown.
- Avoided deforestation reduces land‑use change emissions (LUC) and can continue after net‑zero.
- Learning rates are tunable (defaults: CDR 20%/doubling, conventional 12%/doubling).

## Project Dynamics
- Projects take 1–2 years to develop.
- Operational projects can fail stochastically; failure risk scales with climate conditions.
- Failure reversals return 10% of CDR storage and 50% of mitigation (conventional + avoided deforestation) to the atmosphere.
- Project retirement accelerates when CO2 falls below the target.
- Project initiation is limited by available private capital and physical capacity, not by per‑country caps.
- Project initiation is also throttled by the CEA brake factor when stability or inflation constraints tighten.
- Project scale ramps with cumulative deployment using a normalized sigmoid (starts ~7% of base and reaches full scale around 45 Gt by default; slider range 10–50 Gt).
- Project counts are damped by cumulative deployment (minimum 20% of potential projects early, rising to full scale with experience).
- Conventional capacity tapers down as utilization approaches the hard‑to‑abate limit (no hard cutoff).
- CDR capacity is configurable (1-100 Gt/year via dashboard); conventional mitigation defaults to ~30 Gt/year.

## XCR & Price Floor
- XCR is the reward token. Minting occurs only after verification.
- The price floor is revised periodically, influenced by progress vs roadmap, inflation, and temperature.
- The floor is defended via CQE; if CQE is unwilling or budget‑limited, the market price can slip below the floor.
- Total CQE budget is 5% of annual private capital inflow, capped at 0.5% of active GDP.

## Central Banks (CQE)
- CQE is a backstop, not the whole mitigation budget.
- Total CQE budget is 5% of annual private capital inflow, capped at 0.5% of active GDP.
- CQE purchases are throttled when inflation is high; CPI impacts are bounded.

## Inflation & Macroeconomics
- Global inflation starts at 0 and stays at baseline until the GCR start year.
- After the start year, inflation is corrected toward the target rate.
- Inflation rises when CQE is used but is pulled back toward target each year.
- Private capital demand for XCR increases with inflation (XCR as a hedge).
- A seed capital flow (~$20B/year) is injected early while market cap is small (~$50B) to bootstrap project formation before deep liquidity exists.
- Capital neutrality starts higher for a new market and ramps down over ~10 years after XCR start (more optimistic as liquidity builds).

## Targets
- Default CO2 target is 350 ppm.
- The model reports when/if the target is reached; it is not guaranteed.

## What’s Not Modeled
- Regional climates, extreme events, or sector‑specific constraints.
- Non‑CO2 greenhouse gases.
- Detailed energy system or supply‑chain constraints.
- Sector‑level mitigation pathways (future version should split by sectors).
