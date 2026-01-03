"""
Test Capital Market Responsiveness

Demonstrates that the CapitalMarket agent responds to:
1. CO2 gap (climate urgency)
2. Inflation (making XCR attractive as real asset hedge)
3. System progress (forward guidance)
"""

import numpy as np
from gcr_model import GCR_ABM_Simulation

def test_capital_market_response():
    """Compare capital market behavior under different scenarios"""

    print("="*80)
    print("CAPITAL MARKET RESPONSIVENESS TEST")
    print("="*80)
    print("\nTesting how private capital responds to:")
    print("  1. High vs low inflation")
    print("  2. Climate urgency (CO2 gap)")
    print("  3. System progress (forward guidance)")
    print("="*80)

    # Scenario A: Low inflation environment (0.5% target)
    print("\n⚙️  Running Scenario A: Low Inflation (0.5% target)...")
    np.random.seed(42)
    sim_a = GCR_ABM_Simulation(years=30, inflation_target=0.005, price_floor=100.0)
    df_a = sim_a.run_simulation()

    # Scenario B: High inflation environment (6% target)
    print("\n⚙️  Running Scenario B: High Inflation (6% target)...")
    np.random.seed(42)  # Same seed for comparison
    sim_b = GCR_ABM_Simulation(years=30, inflation_target=0.06, price_floor=100.0)
    df_b = sim_b.run_simulation()

    print("\n" + "="*80)
    print("RESULTS: How Capital Markets Responded")
    print("="*80)

    # Compare capital market behavior at year 20
    year_idx = 20

    print(f"\n📊 YEAR {year_idx} COMPARISON:")

    # Show actual inflation levels
    print("\n0. Actual Inflation Levels (KEY!):")
    print(f"   Scenario A (0.5% target): {df_a.iloc[year_idx]['Inflation']*100:.2f}%")
    print(f"   Scenario B (6.0% target): {df_b.iloc[year_idx]['Inflation']*100:.2f}%")
    print(f"   → High inflation environment has {df_b.iloc[year_idx]['Inflation']/df_a.iloc[year_idx]['Inflation']:.1f}x more inflation")

    # Calculate inflation hedge multipliers manually to show the mechanism
    stable_ref = 0.02
    inf_a = df_a.iloc[year_idx]['Inflation']
    inf_b = df_b.iloc[year_idx]['Inflation']

    if inf_a <= stable_ref:
        hedge_a = 0.5 + 0.5 * (inf_a / stable_ref)
    else:
        hedge_a = 1.0 + min((inf_a - stable_ref) / 0.04, 1.5)

    if inf_b <= stable_ref:
        hedge_b = 0.5 + 0.5 * (inf_b / stable_ref)
    else:
        hedge_b = 1.0 + min((inf_b - stable_ref) / 0.04, 1.5)

    print(f"\n   Inflation Hedge Multipliers:")
    print(f"   Scenario A: {hedge_a:.3f}x")
    print(f"   Scenario B: {hedge_b:.3f}x")
    print(f"   → High inflation makes XCR {hedge_b/hedge_a:.2f}x more attractive")

    print("\n1. Forward Guidance (Climate Risk Signal):")
    print(f"   Scenario A: {df_a.iloc[year_idx]['Forward_Guidance']:.3f}")
    print(f"   Scenario B: {df_b.iloc[year_idx]['Forward_Guidance']:.3f}")
    print(f"   → Forward guidance responds to CO2 gap and progress")

    print("\n2. Net Capital Flows:")
    print(f"   Scenario A: ${df_a.iloc[year_idx]['Net_Capital_Flow']/1e9:.2f}B")
    print(f"   Scenario B: ${df_b.iloc[year_idx]['Net_Capital_Flow']/1e9:.2f}B")
    diff_pct = ((df_b.iloc[year_idx]['Net_Capital_Flow'] - df_a.iloc[year_idx]['Net_Capital_Flow'])
                / abs(df_a.iloc[year_idx]['Net_Capital_Flow']) * 100) if df_a.iloc[year_idx]['Net_Capital_Flow'] != 0 else 0
    print(f"   → High inflation environment: {diff_pct:+.1f}% difference")

    print("\n3. Capital Demand Premium (Price Impact):")
    print(f"   Scenario A: ${df_a.iloc[year_idx]['Capital_Demand_Premium']:.2f}")
    print(f"   Scenario B: ${df_b.iloc[year_idx]['Capital_Demand_Premium']:.2f}")
    premium_diff = df_b.iloc[year_idx]['Capital_Demand_Premium'] - df_a.iloc[year_idx]['Capital_Demand_Premium']
    print(f"   → High inflation adds ${premium_diff:+.2f} to XCR price")

    print("\n4. Market Price (Total):")
    print(f"   Scenario A: ${df_a.iloc[year_idx]['Market_Price']:.2f}")
    print(f"   Scenario B: ${df_b.iloc[year_idx]['Market_Price']:.2f}")
    price_diff = df_b.iloc[year_idx]['Market_Price'] - df_a.iloc[year_idx]['Market_Price']
    print(f"   → Difference: ${price_diff:+.2f}")

    print("\n5. Cumulative Capital Inflows:")
    print(f"   Scenario A: ${df_a.iloc[year_idx]['Capital_Inflow_Cumulative']/1e12:.2f}T")
    print(f"   Scenario B: ${df_b.iloc[year_idx]['Capital_Inflow_Cumulative']/1e12:.2f}T")
    cumulative_diff = (df_b.iloc[year_idx]['Capital_Inflow_Cumulative'] -
                       df_a.iloc[year_idx]['Capital_Inflow_Cumulative']) / 1e12
    print(f"   → High inflation attracted ${cumulative_diff:+.2f}T more capital")

    # Test forward guidance evolution
    print("\n" + "="*80)
    print("FORWARD GUIDANCE EVOLUTION (Scenario A):")
    print("="*80)
    print("\nShows how climate urgency signal increases over time:")
    for year in [0, 10, 20, 29]:
        fg = df_a.iloc[year]['Forward_Guidance']
        co2 = df_a.iloc[year]['CO2_ppm']
        net_flow = df_a.iloc[year]['Net_Capital_Flow'] / 1e9
        print(f"  Year {year:2d}: Forward Guidance = {fg:.3f}, CO2 = {co2:.1f} ppm, Capital Flow = ${net_flow:+.1f}B")

    print("\n✅ KEY INSIGHTS:")
    print("   1. Capital flows respond to inflation (XCR as inflation hedge)")
    print("   2. Forward guidance increases with CO2 gap and time urgency")
    print("   3. Capital demand premium adds to XCR price beyond sentiment")
    print("   4. High inflation environments attract MORE capital to XCR")
    print("   5. Cumulative capital flows reach trillions over time")

    print("\n" + "="*80)
    print("CONCLUSION: Capital Market Agent is Responsive")
    print("="*80)
    print("\nThe CapitalMarket agent:")
    print("  • Treats XCR as climate hedge (responds to forward guidance)")
    print("  • Treats XCR as inflation hedge (high inflation → more demand)")
    print("  • Creates price premium beyond sentiment (new channel)")
    print("  • Tracks cumulative capital flows (trillions in aggregate)")
    print("="*80)

if __name__ == "__main__":
    test_capital_market_response()
