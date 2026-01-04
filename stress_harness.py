import argparse
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from gcr_model import GCR_ABM_Simulation


@dataclass
class Scenario:
    name: str
    description: str
    kwargs: Dict[str, float] = field(default_factory=dict)
    mutate: Optional[Callable[[GCR_ABM_Simulation], None]] = None


def _scale_capital_flow(sim: GCR_ABM_Simulation, multiplier: float) -> None:
    original = sim.capital_market.calculate_capital_demand

    def wrapped(*args, **kwargs):
        return original(*args, **kwargs) * multiplier

    sim.capital_market.calculate_capital_demand = wrapped


def _override_chaos(sim: GCR_ABM_Simulation, shock_prob: float, shock_low: float,
                    shock_high: float, noise_std: float) -> None:
    def chaos_monkey():
        if np.random.rand() < shock_prob:
            shock = np.random.uniform(shock_low, shock_high)
            sim.global_inflation += shock
        sim.global_inflation += np.random.normal(0, noise_std)

    sim.chaos_monkey = chaos_monkey


def _metrics(df: pd.DataFrame, sim: GCR_ABM_Simulation) -> Dict[str, float]:
    inflation_target = sim.inflation_target
    price_floor_ratio = (df["Market_Price"] / df["Price_Floor"]).min() if (df["Price_Floor"] > 0).all() else 0.0
    co2_target_year = float((df["CO2_ppm"] < 350.0).idxmax()) if (df["CO2_ppm"] < 350.0).any() else -1.0

    return {
        "peak_inflation": df["Inflation"].max(),
        "mean_inflation": df["Inflation"].mean(),
        "inflation_years_above_target": float((df["Inflation"] > inflation_target).mean()),
        "peak_temperature": df["Temperature_Anomaly"].max(),
        "years_above_2c": float((df["Temperature_Anomaly"] > 2.0).mean()),
        "final_co2": df["CO2_ppm"].iloc[-1],
        "min_co2": df["CO2_ppm"].min(),
        "year_reach_350ppm": co2_target_year,
        "total_xcr_minted": df["XCR_Minted"].sum(),
        "final_xcr_supply": df["XCR_Supply"].iloc[-1],
        "price_floor_ratio_min": price_floor_ratio,
        "cqe_utilization_peak": df["CQE_Budget_Utilization"].max(),
        "cqe_spend_total": df["CQE_Spent"].iloc[-1],
        "cqe_spend_years": float((df["XCR_Purchased"] > 0).mean())
    }


def _summarize(results: pd.DataFrame) -> pd.DataFrame:
    def p10(x):
        return x.quantile(0.1)

    def p90(x):
        return x.quantile(0.9)

    metrics = [
        "peak_inflation", "mean_inflation", "inflation_years_above_target",
        "peak_temperature", "years_above_2c", "final_co2", "min_co2",
        "year_reach_350ppm", "total_xcr_minted", "final_xcr_supply",
        "price_floor_ratio_min", "cqe_utilization_peak", "cqe_spend_total",
        "cqe_spend_years"
    ]

    agg = results.groupby("scenario")[metrics].agg(["mean", p10, p90])
    agg.columns = [f"{metric}_{stat}" for metric, stat in agg.columns]
    return agg.reset_index()


def _build_scenarios() -> List[Scenario]:
    return [
        Scenario(
            name="baseline",
            description="Default parameters"
        ),
        Scenario(
            name="delayed_start",
            description="XCR starts after 10 years",
            kwargs={"xcr_start_year": 10}
        ),
        Scenario(
            name="high_shock_inflation",
            description="More frequent inflation shocks",
            mutate=lambda sim: _override_chaos(sim, shock_prob=0.15, shock_low=0.01, shock_high=0.03, noise_std=0.004)
        ),
        Scenario(
            name="low_private_capital",
            description="Private capital demand throttled",
            mutate=lambda sim: _scale_capital_flow(sim, multiplier=0.3)
        ),
        Scenario(
            name="high_bau_emissions",
            description="Higher BAU emissions with slower decline",
            mutate=lambda sim: (
                setattr(sim, "bau_emissions_gt_per_year", 50.0),
                setattr(sim, "bau_decline_rate_post_peak", -0.005)
            )
        ),
        Scenario(
            name="tight_cqe",
            description="Lower CQE ratio reduces floor defense",
            mutate=lambda sim: setattr(sim.central_bank, "cqe_ratio", 0.05)
        ),
    ]


def run_stress_suite(runs: int, years: int, seed: Optional[int], scenario_filter: Optional[List[str]]) -> pd.DataFrame:
    scenarios = _build_scenarios()
    if scenario_filter:
        scenario_filter = {name.strip() for name in scenario_filter}
        scenarios = [s for s in scenarios if s.name in scenario_filter]

    results = []

    for scenario in scenarios:
        for run in range(runs):
            if seed is not None:
                np.random.seed(seed + run)
            sim = GCR_ABM_Simulation(years=years, **scenario.kwargs)
            if scenario.mutate:
                scenario.mutate(sim)
            df = sim.run_simulation()
            metrics = _metrics(df, sim)
            metrics.update({
                "scenario": scenario.name,
                "run": run,
                "description": scenario.description
            })
            results.append(metrics)

    return pd.DataFrame(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="GCR ABM stress test harness")
    parser.add_argument("--runs", type=int, default=30, help="Monte Carlo runs per scenario")
    parser.add_argument("--years", type=int, default=100, help="Simulation years")
    parser.add_argument("--seed", type=int, default=42, help="Base RNG seed")
    parser.add_argument("--scenario", action="append", help="Scenario name (can be repeated)")
    parser.add_argument("--csv", type=str, default="stress_results.csv", help="Output CSV path")

    args = parser.parse_args()

    results = run_stress_suite(args.runs, args.years, args.seed, args.scenario)
    summary = _summarize(results)

    pd.set_option("display.max_columns", None)
    print("\nSTRESS TEST SUMMARY (mean/p10/p90)")
    print(summary.to_string(index=False))

    if args.csv:
        results.to_csv(args.csv, index=False)
        print(f"\nSaved raw results: {args.csv}")


if __name__ == "__main__":
    main()
