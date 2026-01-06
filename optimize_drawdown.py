import numpy as np
import pandas as pd
from gcr_model import GCR_ABM_Simulation
import time

def find_soonest_350(results_df):
    target = 350.5
    under_target = results_df[results_df['CO2_ppm'] <= target]
    if not under_target.empty:
        return int(under_target['Year'].min())
    return 1000 # Failed to reach in time

price_floors = [100, 200, 300, 400, 500]
adoption_rates = [3.5, 5.0, 7.5, 10.0]
ramp_up_years = [2, 5, 10]

runs = []
total_scenarios = len(price_floors) * len(adoption_rates) * len(ramp_up_years)
current_scenario = 0

print(f"Starting optimization across {total_scenarios} scenarios...")

for pf in price_floors:
    for ar in adoption_rates:
        for ry in ramp_up_years:
            current_scenario += 1
            # print(f"[{current_scenario}/{total_scenarios}] Testing PF={pf}, AR={ar}, RY={ry}...", end="\r")
            
            sim = GCR_ABM_Simulation(
                years=100,
                price_floor=pf,
                adoption_rate=ar,
                years_to_full_capacity=ry
            )
            results = sim.run_simulation()
            df = pd.DataFrame(results)
            
            year_achieved = find_soonest_350(df)
            final_co2 = df.iloc[-1]['CO2_ppm']
            max_capital = df['Net_Capital_Flow'].max() / 1e9
            
            runs.append({
                'price_floor': pf,
                'adoption_rate': ar,
                'ramp_up_years': ry,
                'year_achieved': year_achieved,
                'final_co2': final_co2,
                'max_capital_b': max_capital
            })

runs_df = pd.DataFrame(runs)
runs_df = runs_df.sort_values(by='year_achieved')

print("\n\n--- OPTIMIZATION RESULTS (Top 10) ---")
print(runs_df.head(10).to_string(index=False))

best = runs_df.iloc[0]
print(f"\nOPTIMAL SETTINGS:")
print(f"- Price Floor: {best['price_floor']}")
print(f"- Adoption Rate: {best['adoption_rate']}")
print(f"- Years to Full Capacity: {best['ramp_up_years']}")
print(f"- Target Reached in Year: {best['year_achieved']}")
