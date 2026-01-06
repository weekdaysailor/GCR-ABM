import numpy as np
import pandas as pd
from gcr_model import GCR_ABM_Simulation

sim = GCR_ABM_Simulation(years=50, adoption_rate=10.0, price_floor=200)
results = sim.run_simulation()
df = pd.DataFrame(results)

print("--- DIAGNOSTICS ---")
print(f"Max Capital Flow (USD B): {df['Net_Capital_Flow'].max() / 1e9:.2f}")
print(f"Avg Capital Flow (USD B): {df['Net_Capital_Flow'].mean() / 1e9:.2f}")
print(f"Final Count Operational Projects: {df.iloc[-1]['Projects_Operational']}")
print(f"Total Projects Created: {df.iloc[-1]['Projects_Total']}")
print(f"Final Human Emissions (GtCO2): {df.iloc[-1]['Human_Emissions_GtCO2']:.2f}")
print(f"Final CDR Sequestration (GtCO2): {df.iloc[-1]['CDR_Sequestration_Tonnes'] / 1e9:.2f}")

# Check first 10 years of project creation
print("\n--- FIRST 10 YEARS PROJECT CREATION ---")
for i in range(10):
    year_data = df.iloc[i]
    print(f"Year {i}: Capital USD B: {year_data['Net_Capital_Flow']/1e9:.2f}, Projects: {year_data['Projects_Total']}")
