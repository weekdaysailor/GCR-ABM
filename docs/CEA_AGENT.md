# Agent: Carbon Exchange Authority (CEA)
**Role:** The Central System Governor / Controller

## Objective
To manage the "Carrot" (XCR) supply to ensure the atmospheric CO2 concentration returns to the target roadmap (e.g., 350 ppm) while maintaining system stability.

## Key Logic
1. **Roadmap Tracking:** Monitors the "Sequestration Gap" between current sensors and the target roadmap.
2. **Reward Multiplier (R):** Adjusts the R-value to increase or decrease the reward for mitigation. R is a PID-controlled actuator.
3. **Stability Ratio:** Monitors (Total XCR Market Cap) / (Total Alliance CQE Budget).
   - **8:1 Ratio:** Trigger "Warning" status to Investors.
   - **10:1 Ratio:** Trigger "System Brake" status.
4. **Braking Logic (Inertia):** Implements a 2-year lag (2 time-steps) for policy changes to reflect institutional and social inertia.
