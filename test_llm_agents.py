"""
Test suite for LLM-powered agents in GCR-ABM simulation

Tests:
1. LLM engine initialization and caching
2. Each LLM agent produces valid outputs
3. Fallback to rule-based when LLM unavailable
4. Comparison of LLM vs rule-based trajectories
5. Cache reproducibility
"""

import os
import tempfile
import logging
from pathlib import Path

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_llm_engine_cache():
    """Test LLM engine caching functionality"""
    from llm_engine import LLMEngine, DecisionCache, CacheMode, LLMDecision

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")

        # Test cache operations
        cache = DecisionCache(db_path)

        # Store a decision
        decision = LLMDecision(
            agent="test_agent",
            year=5,
            state_hash="abc123",
            decision={"sentiment": 0.85},
            reasoning="Test reasoning",
            model="llama3.2",
            timestamp="2024-01-01T00:00:00",
            run_id="test_run"
        )
        cache.store(decision)

        # Retrieve it
        retrieved = cache.retrieve("abc123", "test_agent")
        assert retrieved is not None
        assert retrieved.decision["sentiment"] == 0.85
        assert retrieved.reasoning == "Test reasoning"

        # Check stats
        stats = cache.get_stats()
        assert stats["total_decisions"] == 1
        assert stats["by_agent"]["test_agent"] == 1

        # Export
        export_path = os.path.join(tmpdir, "export.json")
        count = cache.export_decisions(export_path)
        assert count == 1
        assert os.path.exists(export_path)

        print("✓ LLM engine cache test passed")
        return True


def test_investor_market_llm_fallback():
    """Test InvestorMarketLLM falls back to rule-based when LLM unavailable"""
    from llm_agents import InvestorMarketLLM

    # Create agent without LLM engine (should use fallback)
    investor = InvestorMarketLLM(llm_engine=None, price_floor=100.0)

    assert not investor.llm_enabled

    # Should use rule-based fallback
    sentiment = investor.update_sentiment(
        cea_warning=False,
        global_inflation=0.025,
        inflation_target=0.02,
        co2_level=415.0,
        initial_co2=420.0,
        year=5,
        total_years=50
    )

    assert 0.1 <= sentiment <= 1.0
    print(f"✓ InvestorMarketLLM fallback test passed (sentiment={sentiment:.3f})")
    return True


def test_capital_market_llm_fallback():
    """Test CapitalMarketLLM falls back to rule-based when LLM unavailable"""
    from llm_agents import CapitalMarketLLM

    capital = CapitalMarketLLM(llm_engine=None)

    assert not capital.llm_enabled

    flow, premium, guidance = capital.update_capital_flows(
        current_co2=415.0,
        year=5,
        total_years=50,
        roadmap_gap=2.0,
        global_inflation=0.025,
        inflation_target=0.02,
        sentiment=0.8,
        xcr_supply=1e8,
        price_floor=100.0
    )

    # Should return reasonable values
    assert isinstance(flow, float)
    assert isinstance(premium, float)
    assert 0.0 <= guidance <= 1.0

    print(f"✓ CapitalMarketLLM fallback test passed (flow=${flow/1e9:.2f}B)")
    return True


def test_cea_llm_fallback():
    """Test CEA_LLM falls back to rule-based when LLM unavailable"""
    from llm_agents import CEA_LLM

    cea = CEA_LLM(
        llm_engine=None,
        target_co2_ppm=350.0,
        initial_co2_ppm=420.0,
        inflation_target=0.02
    )

    assert not cea.llm_enabled

    # Test policy update
    cea.update_policy(
        current_co2_ppm=415.0,
        market_cap_xcr=1e10,
        total_cqe_budget=1e9,
        global_inflation=0.025,
        budget_utilization=0.3,
        year=5,
        total_years=50
    )

    assert 0.1 <= cea.brake_factor <= 1.0
    assert isinstance(cea.warning_8to1_active, bool)

    print(f"✓ CEA_LLM fallback test passed (brake={cea.brake_factor:.2f})")
    return True


def test_central_bank_llm_fallback():
    """Test CentralBankAllianceLLM falls back to rule-based when LLM unavailable"""
    from llm_agents import CentralBankAllianceLLM

    countries = {"USA": {"gdp_tril": 27.0}}
    cb = CentralBankAllianceLLM(
        llm_engine=None,
        countries=countries,
        price_floor=100.0
    )

    assert not cb.llm_enabled

    # Set budget
    cb.update_cqe_budget(1e10)

    # Test floor defense
    price_support, inflation_impact, xcr_purchased = cb.defend_floor(
        market_price_xcr=95.0,  # Below floor
        total_xcr_supply=1e8,
        global_inflation=0.025,
        inflation_target=0.02,
        current_year=5
    )

    assert price_support >= 0
    assert inflation_impact >= 0
    assert xcr_purchased >= 0

    print(f"✓ CentralBankAllianceLLM fallback test passed (support=${price_support:.2f})")
    return True


def test_simulation_rule_based():
    """Test simulation runs with rule-based agents"""
    from gcr_model import GCR_ABM_Simulation

    sim = GCR_ABM_Simulation(
        years=10,
        enable_audits=True,
        price_floor=100.0,
        llm_enabled=False
    )

    df = sim.run_simulation()

    assert len(df) == 10
    assert "CO2_ppm" in df.columns
    assert "Sentiment" in df.columns
    assert df["CO2_ppm"].iloc[0] > 0

    print(f"✓ Rule-based simulation test passed (final CO2={df['CO2_ppm'].iloc[-1]:.1f} ppm)")
    return True


def test_simulation_llm_fallback():
    """Test simulation gracefully falls back when LLM unavailable"""
    from gcr_model import GCR_ABM_Simulation

    # Enable LLM but it will fall back if Ollama not available
    sim = GCR_ABM_Simulation(
        years=5,
        enable_audits=True,
        price_floor=100.0,
        llm_enabled=True,
        llm_model="llama3.2",
        llm_cache_mode="disabled"
    )

    # Should run regardless of LLM availability
    df = sim.run_simulation()

    assert len(df) == 5
    assert df["CO2_ppm"].iloc[0] > 0

    llm_status = "enabled" if sim.llm_enabled else "fallback"
    print(f"✓ LLM simulation fallback test passed (mode={llm_status})")
    return True


def test_compare_llm_vs_rules():
    """Compare LLM and rule-based simulation trajectories (if LLM available)"""
    from gcr_model import GCR_ABM_Simulation

    np.random.seed(42)

    # Rule-based
    sim_rules = GCR_ABM_Simulation(
        years=10,
        enable_audits=True,
        price_floor=100.0,
        llm_enabled=False
    )
    np.random.seed(42)
    df_rules = sim_rules.run_simulation()

    # LLM (will fallback if unavailable)
    np.random.seed(42)
    sim_llm = GCR_ABM_Simulation(
        years=10,
        enable_audits=True,
        price_floor=100.0,
        llm_enabled=True,
        llm_cache_mode="disabled"
    )
    np.random.seed(42)
    df_llm = sim_llm.run_simulation()

    # Compare key metrics
    co2_diff = abs(df_rules["CO2_ppm"].iloc[-1] - df_llm["CO2_ppm"].iloc[-1])
    sentiment_diff = abs(df_rules["Sentiment"].iloc[-1] - df_llm["Sentiment"].iloc[-1])

    print(f"\nTrajectory Comparison (10 years):")
    print(f"  Rule-based final CO2: {df_rules['CO2_ppm'].iloc[-1]:.1f} ppm")
    print(f"  LLM final CO2:        {df_llm['CO2_ppm'].iloc[-1]:.1f} ppm")
    print(f"  Difference:           {co2_diff:.1f} ppm")
    print(f"  Rule-based sentiment: {df_rules['Sentiment'].iloc[-1]:.3f}")
    print(f"  LLM sentiment:        {df_llm['Sentiment'].iloc[-1]:.3f}")

    # If LLM fell back to rules, results should be identical
    if not sim_llm.llm_enabled:
        assert co2_diff < 0.1, "Fallback should produce identical results"
        print("✓ LLM fell back to rule-based (identical results)")
    else:
        print("✓ LLM active (results may differ due to LLM reasoning)")

    return True


def run_all_tests():
    """Run all LLM agent tests"""
    print("\n" + "="*60)
    print("LLM AGENT TEST SUITE")
    print("="*60 + "\n")

    tests = [
        ("Cache Operations", test_llm_engine_cache),
        ("InvestorMarket Fallback", test_investor_market_llm_fallback),
        ("CapitalMarket Fallback", test_capital_market_llm_fallback),
        ("CEA Fallback", test_cea_llm_fallback),
        ("CentralBank Fallback", test_central_bank_llm_fallback),
        ("Rule-Based Simulation", test_simulation_rule_based),
        ("LLM Simulation Fallback", test_simulation_llm_fallback),
        ("LLM vs Rules Comparison", test_compare_llm_vs_rules),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n--- {name} ---")
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
