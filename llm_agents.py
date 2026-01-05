"""
LLM-Powered Agents for GCR-ABM Simulation

Provides LLM-enhanced versions of simulation agents that use local Ollama
models for decision-making while retaining rule-based fallbacks.

Agents:
- InvestorMarketLLM: Sentiment reasoning based on market conditions
- CapitalMarketLLM: Capital flow reasoning based on investor behavior
- CEA_LLM: Policy decisions under complex conditions
- CentralBankAllianceLLM: Intervention strategy reasoning
"""

import logging
from typing import Dict, Any, Optional

from llm_engine import LLMEngine, CacheMode

logger = logging.getLogger(__name__)


class LLMAgentMixin:
    """Mixin providing common LLM functionality for agents"""

    PROMPT_TEMPLATE: str = ""  # Override in subclasses

    def __init__(self, llm_engine: Optional[LLMEngine] = None, **kwargs):
        self.llm_engine = llm_engine
        self.llm_enabled = llm_engine is not None and llm_engine.is_available
        self._current_year = 0

    def _llm_decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Make decision using LLM"""
        if not self.llm_enabled:
            raise RuntimeError("LLM not enabled")

        return self.llm_engine.decide(
            agent_name=self.__class__.__name__,
            prompt_template=self.PROMPT_TEMPLATE,
            state=state,
            year=self._current_year
        )


# =============================================================================
# InvestorMarketLLM - Sentiment reasoning
# =============================================================================

class InvestorMarketLLM(LLMAgentMixin):
    """LLM-powered investor sentiment agent

    Replaces mechanical decay/recovery formulas with LLM reasoning about
    how investors would respond to market conditions.
    """

    PROMPT_TEMPLATE = """You model aggregate investor sentiment for a carbon reward market (XCR).

Current Market State:
- CO2 Level: {co2:.1f} ppm (target: 350 ppm, started: 420 ppm)
- CO2 Change from Last Year: {co2_change:+.2f} ppm (negative = improvement)
- Inflation: {inflation:.1f}% (target: {inflation_target:.1f}%)
- CEA Warning Active: {warning} (stability ratio concern if True)
- Previous Sentiment: {prev_sentiment:.2f} (0.0=panic, 1.0=full trust)
- Market Price: ${price:.2f} (floor: ${floor:.2f})
- Year: {year} of {total_years}

Investor Psychology:
1. Progress toward 350 ppm target builds confidence
2. High inflation erodes trust in system stability
3. CEA warnings signal regulatory concern
4. Price above floor indicates healthy demand
5. Sentiment is sticky - doesn't change drastically without major events

Determine new sentiment (0.1 to 1.0) based on rational investor response.
Changes should typically be small (±0.02 to ±0.05) unless major event.

Respond with JSON only:
{{"sentiment": 0.XX, "reasoning": "brief explanation"}}"""

    def __init__(self,
                 llm_engine: Optional[LLMEngine] = None,
                 price_floor: float = 100.0):
        LLMAgentMixin.__init__(self, llm_engine)
        # Core state from base InvestorMarket
        self.sentiment = 1.0
        self.price_floor = price_floor
        self.market_price_xcr = price_floor + 50.0
        self.last_warning = False
        self._prev_co2 = 420.0

    def update_sentiment(self,
                        cea_warning: bool,
                        global_inflation: float,
                        inflation_target: float = 0.02,
                        co2_level: float = None,
                        initial_co2: float = None,
                        year: int = 0,
                        total_years: int = 50) -> float:
        """Update sentiment using LLM or rule-based fallback"""
        self._current_year = year

        if self.llm_enabled:
            try:
                co2_change = co2_level - self._prev_co2 if co2_level else 0
                state = {
                    "co2": co2_level or 420.0,
                    "co2_change": co2_change,
                    "inflation": global_inflation * 100,
                    "inflation_target": inflation_target * 100,
                    "warning": cea_warning,
                    "prev_sentiment": self.sentiment,
                    "price": self.market_price_xcr,
                    "floor": self.price_floor,
                    "year": year,
                    "total_years": total_years
                }

                decision = self._llm_decide(state)
                new_sentiment = float(decision.get("sentiment", self.sentiment))

                # Clamp to valid range
                new_sentiment = max(0.1, min(1.0, new_sentiment))

                self.sentiment = new_sentiment
                self._prev_co2 = co2_level or self._prev_co2
                self.last_warning = cea_warning

                logger.debug(f"InvestorMarketLLM sentiment: {self.sentiment:.3f}")
                return self.sentiment

            except Exception as e:
                logger.warning(f"LLM failed, using rule-based fallback: {e}")

        # Rule-based fallback (from base InvestorMarket logic)
        return self._rule_based_sentiment(
            cea_warning, global_inflation, inflation_target,
            co2_level, initial_co2
        )

    def _rule_based_sentiment(self,
                             cea_warning: bool,
                             global_inflation: float,
                             inflation_target: float,
                             co2_level: float,
                             initial_co2: float) -> float:
        """Original rule-based sentiment logic as fallback"""
        inflation_ratio = global_inflation / inflation_target if inflation_target > 0 else 1.0

        # Decay on warning
        if cea_warning:
            if not self.last_warning:
                self.sentiment *= 0.97  # New warning: 3% decay
            else:
                self.sentiment *= 0.995  # Persistent warning: 0.5% decay

        # Decay on high inflation
        if inflation_ratio > 3.0:
            self.sentiment *= 0.94
        elif inflation_ratio > 2.0:
            self.sentiment *= 0.97
        elif inflation_ratio > 1.5:
            self.sentiment *= 0.995

        # Recovery when stable
        if not cea_warning and inflation_ratio <= 1.25:
            recovery = 0.02
            self.sentiment = min(1.0, self.sentiment + (1.0 - self.sentiment) * recovery)

        # CO2 progress bonus
        if co2_level is not None and initial_co2 is not None:
            co2_reduction = initial_co2 - co2_level
            if co2_reduction > 0.5:
                self.sentiment = min(1.0, self.sentiment + 0.015)
            elif co2_reduction > 0.1:
                self.sentiment = min(1.0, self.sentiment + 0.005)

        # Floor
        self.sentiment = max(0.1, self.sentiment)
        self.last_warning = cea_warning

        return self.sentiment

    def calculate_price(self, capital_demand_premium: float = 0.0) -> float:
        """Calculate market price from sentiment"""
        sentiment_premium = 50 * self.sentiment
        self.market_price_xcr = self.price_floor + sentiment_premium + capital_demand_premium
        return self.market_price_xcr


# =============================================================================
# CapitalMarketLLM - Capital flow reasoning
# =============================================================================

class CapitalMarketLLM(LLMAgentMixin):
    """LLM-powered capital market agent

    Replaces formula-based capital flows with LLM reasoning about
    realistic investor behavior and capital allocation.
    """

    PROMPT_TEMPLATE = """You model private capital flows into a carbon reward market (XCR).

Current Market State:
- XCR Market Cap: ${market_cap:.1f}B
- XCR Supply: {supply:.2e} units
- Price Floor: ${floor:.2f} (guaranteed by central banks)
- Market Price: ${price:.2f} (current trading price)
- Inflation: {inflation:.1f}% (target: {target:.1f}%)
- CO2 Level: {co2:.1f} ppm (target: 350 ppm)
- CO2 Progress: {progress:.1f}% toward target
- Roadmap Gap: {roadmap_gap:+.1f} ppm (positive = behind schedule)
- Investor Sentiment: {sentiment:.2f} (0-1 scale)
- Year: {year} of {total_years}

Capital Flow Drivers:
1. Forward-looking investors care about climate trajectory
2. High inflation increases demand for real assets (XCR as hedge)
3. Low sentiment may trigger outflows (selling pressure)
4. Strong CO2 progress attracts ESG/climate-focused capital
5. Price above floor indicates healthy market demand
6. Being behind roadmap may concern long-term investors

Estimate net capital flow as percentage of market cap.
Typical range: -5% to +5% per year. Extreme: -10% to +10%.

Respond with JSON only:
{{"flow_percent": X.X, "reasoning": "brief explanation"}}"""

    def __init__(self, llm_engine: Optional[LLMEngine] = None):
        LLMAgentMixin.__init__(self, llm_engine)
        # Core state
        self.cumulative_capital_inflow = 0.0
        self.cumulative_capital_outflow = 0.0
        self.last_forward_guidance = 0.5

    def update_capital_flows(self,
                            current_co2: float,
                            year: int,
                            total_years: int,
                            roadmap_gap: float,
                            global_inflation: float,
                            inflation_target: float,
                            sentiment: float,
                            xcr_supply: float,
                            price_floor: float,
                            market_price: float = None,
                            market_age_years: float = 0.0) -> tuple:
        """Update capital flows using LLM or rule-based fallback

        Returns: (net_capital_flow, capital_demand_premium, forward_guidance)
        """
        self._current_year = year
        market_price = market_price or price_floor + 50 * sentiment
        market_cap = xcr_supply * market_price / 1e9 if xcr_supply > 0 else 1.0

        # Calculate progress
        initial_co2 = 420.0
        target_co2 = 350.0
        progress = (initial_co2 - current_co2) / (initial_co2 - target_co2) * 100

        if self.llm_enabled:
            try:
                state = {
                    "market_cap": market_cap,
                    "supply": xcr_supply,
                    "floor": price_floor,
                    "price": market_price,
                    "inflation": global_inflation * 100,
                    "target": inflation_target * 100,
                    "co2": current_co2,
                    "progress": max(0, progress),
                    "roadmap_gap": roadmap_gap,
                    "sentiment": sentiment,
                    "year": year,
                    "total_years": total_years
                }

                decision = self._llm_decide(state)
                flow_percent = float(decision.get("flow_percent", 0.0))

                # Clamp to reasonable range
                flow_percent = max(-10.0, min(10.0, flow_percent))

                # Convert to USD
                net_capital_flow = market_cap * 1e9 * (flow_percent / 100)

                # Track flows
                if net_capital_flow > 0:
                    self.cumulative_capital_inflow += net_capital_flow
                else:
                    self.cumulative_capital_outflow += abs(net_capital_flow)

                # Calculate price premium
                capital_intensity = flow_percent / 100
                capital_demand_premium = price_floor * max(-0.5, min(0.5, capital_intensity))

                # Forward guidance based on progress
                self.last_forward_guidance = min(1.0, max(0.0, progress / 100))

                logger.debug(f"CapitalMarketLLM flow: {flow_percent:.1f}%")
                return net_capital_flow, capital_demand_premium, self.last_forward_guidance

            except Exception as e:
                logger.warning(f"LLM failed, using rule-based fallback: {e}")

        # Rule-based fallback
        return self._rule_based_flows(
            current_co2, year, total_years, roadmap_gap,
            global_inflation, inflation_target, sentiment,
            xcr_supply, price_floor, market_age_years
        )

    def _rule_based_flows(self, current_co2, year, total_years, roadmap_gap,
                         global_inflation, inflation_target, sentiment,
                         xcr_supply, price_floor, market_age_years: float = 0.0) -> tuple:
        """Original rule-based capital flow logic as fallback"""
        # Forward guidance
        initial_co2 = 420.0
        target_co2 = 350.0
        co2_gap = current_co2 - target_co2
        co2_factor = 1.0 - min(1.0, max(0.0, co2_gap / (initial_co2 - target_co2)))

        time_urgency = (year / total_years) ** 2
        progress_factor = 1.0 - min(1.0, max(0.0, roadmap_gap / 20.0))

        forward_guidance = 0.4 * co2_factor + 0.3 * time_urgency + 0.3 * progress_factor
        forward_guidance = max(0.0, min(1.0, forward_guidance))

        # Inflation hedge demand
        if global_inflation <= inflation_target:
            inflation_hedge = 0.5 + 0.5 * (inflation_target - global_inflation) / inflation_target
        else:
            excess = global_inflation - inflation_target
            inflation_hedge = 1.0 + min(1.5, excess / 0.04)

        # Capital demand
        market_cap = max(xcr_supply * price_floor, 1e9)
        combined_attractiveness = forward_guidance * inflation_hedge * sentiment
        neutrality_start = 0.6
        neutrality_end = 0.3
        neutrality_ramp_years = 10
        if market_age_years <= 0:
            neutrality = neutrality_start
        elif market_age_years >= neutrality_ramp_years:
            neutrality = neutrality_end
        else:
            progress = market_age_years / neutrality_ramp_years
            neutrality = neutrality_start + (neutrality_end - neutrality_start) * progress

        net_capital_flow = market_cap * 0.10 * 2 * (combined_attractiveness - neutrality)

        # Track
        if net_capital_flow > 0:
            self.cumulative_capital_inflow += net_capital_flow
        else:
            self.cumulative_capital_outflow += abs(net_capital_flow)

        # Premium
        capital_intensity = net_capital_flow / market_cap if market_cap > 0 else 0
        capital_demand_premium = price_floor * max(-0.5, min(0.5, capital_intensity))

        self.last_forward_guidance = forward_guidance
        return net_capital_flow, capital_demand_premium, forward_guidance


# =============================================================================
# CEA_LLM - Policy reasoning
# =============================================================================

class CEA_LLM(LLMAgentMixin):
    """LLM-powered Carbon Exchange Authority

    Uses LLM for periodic policy reviews while maintaining rule-based
    logic for routine operations between reviews.
    """

    PROMPT_TEMPLATE = """You are the Carbon Exchange Authority (CEA) governing XCR policy.

Current System State:
- CO2 Level: {co2:.1f} ppm (target: 350 ppm)
- Roadmap Target: {roadmap:.1f} ppm (for this year)
- Roadmap Gap: {gap:+.1f} ppm (positive = behind schedule)
- Stability Ratio: {ratio:.1f}:1 (Market Cap / CQE Budget)
- Current Inflation: {inflation:.1f}% (target: {target:.1f}%)
- Current Brake Factor: {brake:.2f} (1.0 = no brake, lower = minting reduced)
- Current Price Floor: ${floor:.2f}
- CQE Budget Utilization: {utilization:.1f}%
- Year: {year} of {total_years}

Policy Tools Available:
1. Warning Flag (bool): Signal concern to markets when ratio > 8:1
2. Brake Factor (0.1-1.0): Reduce XCR minting when ratio > 10:1
   - 10:1 ratio → ~0.5x brake
   - 15:1 ratio → ~0.1x brake (heavy)
3. Policy guidance: Recommend floor adjustment direction

Per Chen (2025) GCR specification, you must:
- Monitor stability (ratio should stay < 15:1)
- Balance climate urgency vs economic stability
- Avoid pro-cyclical policy that amplifies volatility

Determine appropriate policy response:

Respond with JSON only:
{{"warning": true/false, "brake_factor": 0.XX, "floor_direction": "up"/"stable"/"down", "reasoning": "brief explanation"}}"""

    def __init__(self,
                 llm_engine: Optional[LLMEngine] = None,
                 target_co2_ppm: float = 350.0,
                 initial_co2_ppm: float = 420.0,
                 inflation_target: float = 0.02):
        LLMAgentMixin.__init__(self, llm_engine)
        # Core state
        self.target_co2_ppm = target_co2_ppm
        self.initial_co2_ppm = initial_co2_ppm
        self.roadmap_co2 = initial_co2_ppm
        self.inflation_target = inflation_target

        self.warning_8to1_active = False
        self.brake_10to1_active = False
        self.brake_factor = 1.0

        self.revision_interval = 5
        self.locked_annual_yield = 0.02
        self.last_revision_year = 0

    def update_policy(self,
                     current_co2_ppm: float,
                     market_cap_xcr: float,
                     total_cqe_budget: float,
                     global_inflation: float,
                     budget_utilization: float,
                     year: int = 0,
                     total_years: int = 50) -> None:
        """Update policy using LLM for periodic reviews"""
        self._current_year = year
        ratio = market_cap_xcr / total_cqe_budget if total_cqe_budget > 0 else 0
        roadmap_target = self.calculate_roadmap_target(year, total_years)
        gap = current_co2_ppm - roadmap_target

        # Use LLM for policy review years
        is_review_year = (year % self.revision_interval == 0 and year > 0)

        if self.llm_enabled and is_review_year:
            try:
                state = {
                    "co2": current_co2_ppm,
                    "roadmap": roadmap_target,
                    "gap": gap,
                    "ratio": ratio,
                    "inflation": global_inflation * 100,
                    "target": self.inflation_target * 100,
                    "brake": self.brake_factor,
                    "floor": 100.0,  # Placeholder
                    "utilization": budget_utilization * 100,
                    "year": year,
                    "total_years": total_years
                }

                decision = self._llm_decide(state)

                self.warning_8to1_active = decision.get("warning", ratio > 8)
                self.brake_factor = float(decision.get("brake_factor", self.brake_factor))
                self.brake_factor = max(0.1, min(1.0, self.brake_factor))

                logger.debug(f"CEA_LLM policy: warning={self.warning_8to1_active}, brake={self.brake_factor}")
                return

            except Exception as e:
                logger.warning(f"LLM failed, using rule-based fallback: {e}")

        # Rule-based for non-review years or fallback
        self._rule_based_policy(ratio, global_inflation, budget_utilization)

    def _rule_based_policy(self, ratio: float, inflation: float, utilization: float):
        """Rule-based policy logic"""
        inflation_ratio = inflation / self.inflation_target if self.inflation_target > 0 else 1.0

        # Warning threshold
        warning_threshold = 8.0 * (1.0 / max(0.5, min(2.0, inflation_ratio)))
        self.warning_8to1_active = ratio > warning_threshold

        # Brake calculation
        brake_start = 10.0 * (1.0 / max(0.5, min(2.0, inflation_ratio)))
        brake_heavy = 15.0 * (1.0 / max(0.5, min(2.0, inflation_ratio)))

        if ratio < brake_start:
            self.brake_factor = 1.0
        elif ratio < brake_heavy:
            self.brake_factor = 1.0 - 0.5 * (ratio - brake_start) / (brake_heavy - brake_start)
        else:
            self.brake_factor = 0.1

        # Budget brake
        if utilization > 0.9:
            budget_brake = max(0.25, 1.0 - (utilization - 0.9) / 0.1)
            self.brake_factor = min(self.brake_factor, budget_brake)

        self.brake_10to1_active = self.brake_factor < 1.0

    def calculate_roadmap_target(self, year: int, total_years: int) -> float:
        """Linear roadmap from initial to target CO2"""
        progress = year / total_years if total_years > 0 else 0
        return self.initial_co2_ppm - (self.initial_co2_ppm - self.target_co2_ppm) * progress

    def adjust_price_floor(self, current_co2_ppm: float, current_floor: float,
                          year: int, total_years: int) -> tuple:
        """Adjust price floor based on roadmap progress"""
        revision_occurred = False

        if year % self.revision_interval == 0 and year > 0:
            revision_occurred = True
            roadmap_target = self.calculate_roadmap_target(year, total_years)
            roadmap_gap = current_co2_ppm - roadmap_target

            base_yield = 0.02
            max_gap = self.initial_co2_ppm - self.target_co2_ppm
            adjustment = (roadmap_gap / max_gap) * 0.05 if max_gap > 0 else 0

            new_yield = max(-0.03, min(0.07, base_yield + adjustment))
            self.locked_annual_yield = new_yield
            self.last_revision_year = year

        new_floor = current_floor * (1 + self.locked_annual_yield)
        new_floor = max(new_floor, current_floor * 0.95)

        return new_floor, revision_occurred

    def calculate_project_r_value(self, channel, marginal_cost: float,
                                  benchmark_cdr_cost: float, current_year: int = 0) -> tuple:
        """Calculate R value for project cost-effectiveness"""
        from gcr_model import ChannelType

        if channel == ChannelType.CDR:
            r_base = 1.0
        elif channel == ChannelType.CONVENTIONAL:
            r_base = marginal_cost / benchmark_cdr_cost if benchmark_cdr_cost > 0 else 1.0
            r_base = max(0.1, r_base)
        else:
            r_base = (marginal_cost * 0.8) / benchmark_cdr_cost if benchmark_cdr_cost > 0 else 1.0
            r_base = max(0.1, r_base)

        policy_mult = self.calculate_policy_r_multiplier(channel, current_year)

        if channel == ChannelType.CDR:
            r_effective = r_base
        else:
            r_effective = r_base * policy_mult

        return r_base, r_effective

    def calculate_policy_r_multiplier(self, channel, current_year: int) -> float:
        """Time-dependent policy multiplier for channel prioritization"""
        from gcr_model import ChannelType
        import numpy as np

        transition_midpoint = 50
        transition_width = 10
        k = 0.8

        transition = 1 / (1 + np.exp(-k * (current_year - transition_midpoint) / transition_width))

        if channel == ChannelType.CDR:
            return 1.0
        elif channel == ChannelType.CONVENTIONAL:
            pre = 0.7
            post = 1.2
        else:
            pre = 0.8
            post = 1.0

        return pre + (post - pre) * transition


# =============================================================================
# CentralBankAllianceLLM - Intervention reasoning
# =============================================================================

class CentralBankAllianceLLM(LLMAgentMixin):
    """LLM-powered Central Bank Alliance

    Uses LLM to reason about intervention strategy when defending
    the XCR price floor via CQE.
    """

    PROMPT_TEMPLATE = """You represent central banks defending the XCR price floor via CQE.

Current Market State:
- Market Price: ${price:.2f}
- Price Floor: ${floor:.2f}
- Price Gap: ${gap:.2f} below floor (0 if above)
- Global Inflation: {inflation:.1f}% (target: {target:.1f}%)
- Annual CQE Budget: ${budget:.1f}B
- Budget Spent This Year: ${spent:.1f}B ({utilization:.1f}%)
- Remaining Budget: ${remaining:.1f}B
- Year: {year}

Intervention Considerations:
1. Defending floor creates new M0 reserves (inflationary)
2. Annual budget is limited - cannot exceed it
3. Over-intervention may signal desperation to markets
4. Under-intervention risks floor credibility
5. High inflation should reduce willingness to intervene
6. Preserve budget for later in year if uncertainty high

Decide what percentage of the price gap to close (0-100%):
- 0% = No intervention (let market find level)
- 50% = Moderate support (balance credibility vs inflation)
- 100% = Full defense (close entire gap)

Respond with JSON only:
{{"intervention_pct": XX, "reasoning": "brief explanation"}}"""

    def __init__(self,
                 llm_engine: Optional[LLMEngine] = None,
                 countries: dict = None,
                 price_floor: float = 100.0):
        LLMAgentMixin.__init__(self, llm_engine)
        self.countries = countries or {}
        self.price_floor_rcc = price_floor
        self.total_cqe_budget = 0.0
        self.cqe_ratio = 0.05
        self.gdp_cap_ratio = 0.005
        self.total_cqe_spent = 0.0
        self.annual_cqe_spent = 0.0
        self.current_budget_year = 0

    def update_cqe_budget(self, annual_private_capital_inflow: float):
        """Recalculate CQE budget"""
        market_cap_budget = annual_private_capital_inflow * self.cqe_ratio
        active_gdp_tril = sum(c.get("gdp_tril", 0) for c in self.countries.values())
        gdp_cap_budget = active_gdp_tril * 1e12 * self.gdp_cap_ratio
        self.total_cqe_budget = min(market_cap_budget, gdp_cap_budget)

    def defend_floor(self,
                    market_price_xcr: float,
                    total_xcr_supply: float,
                    global_inflation: float,
                    inflation_target: float = 0.02,
                    current_year: int = 0) -> tuple:
        """Defend price floor using LLM or rule-based logic

        Returns: (price_support, inflation_impact, xcr_purchased)
        """
        self._current_year = current_year

        # Reset annual budget at year start
        if current_year != self.current_budget_year:
            self.annual_cqe_spent = 0.0
            self.current_budget_year = current_year

        # Check if budget exhausted
        if self.annual_cqe_spent >= self.total_cqe_budget:
            return 0.0, 0.0, 0.0

        if inflation_target <= 0:
            return 0.0, 0.0, 0.0

        # Calculate gap
        gap = max(0, self.price_floor_rcc - market_price_xcr)
        if gap == 0:
            return 0.0, 0.0, 0.0

        remaining_budget = self.total_cqe_budget - self.annual_cqe_spent

        if self.llm_enabled:
            try:
                state = {
                    "price": market_price_xcr,
                    "floor": self.price_floor_rcc,
                    "gap": gap,
                    "inflation": global_inflation * 100,
                    "target": inflation_target * 100,
                    "budget": self.total_cqe_budget / 1e9,
                    "spent": self.annual_cqe_spent / 1e9,
                    "utilization": (self.annual_cqe_spent / self.total_cqe_budget * 100
                                   if self.total_cqe_budget > 0 else 0),
                    "remaining": remaining_budget / 1e9,
                    "year": current_year
                }

                decision = self._llm_decide(state)
                intervention_pct = float(decision.get("intervention_pct", 50))
                intervention_pct = max(0, min(100, intervention_pct))

                # Calculate intervention
                intervention_strength = intervention_pct / 100
                price_support = gap * intervention_strength

                xcr_purchased = total_xcr_supply * intervention_strength * 0.01
                fiat_created = xcr_purchased * self.price_floor_rcc

                # Check budget constraint
                if self.annual_cqe_spent + fiat_created > self.total_cqe_budget:
                    fiat_created = remaining_budget
                    xcr_purchased = fiat_created / self.price_floor_rcc if self.price_floor_rcc > 0 else 0
                    price_support = gap * (fiat_created / (total_xcr_supply * 0.01 * self.price_floor_rcc)) if total_xcr_supply > 0 else 0

                self.annual_cqe_spent += fiat_created
                self.total_cqe_spent += fiat_created

                inflation_impact = (fiat_created / 1e12) * 0.001

                logger.debug(f"CentralBankLLM intervention: {intervention_pct}%")
                return price_support, inflation_impact, xcr_purchased

            except Exception as e:
                logger.warning(f"LLM failed, using rule-based fallback: {e}")

        # Rule-based fallback
        return self._rule_based_defend(
            market_price_xcr, total_xcr_supply,
            global_inflation, inflation_target, gap
        )

    def _rule_based_defend(self, market_price, supply, inflation, target, gap) -> tuple:
        """Rule-based floor defense logic"""
        import numpy as np

        # Sigmoid damping
        k = 12.0
        sigmoid_center = target * 1.5
        willingness = 1 / (1 + np.exp(k * (inflation - sigmoid_center)))

        # Intervention strength
        intervention_strength = min(gap / self.price_floor_rcc, 0.5) * willingness
        price_support = gap * intervention_strength

        xcr_purchased = supply * intervention_strength * 0.01
        fiat_created = xcr_purchased * self.price_floor_rcc

        # Budget check
        remaining = self.total_cqe_budget - self.annual_cqe_spent
        if fiat_created > remaining:
            fiat_created = remaining
            xcr_purchased = fiat_created / self.price_floor_rcc if self.price_floor_rcc > 0 else 0

        self.annual_cqe_spent += fiat_created
        self.total_cqe_spent += fiat_created

        inflation_impact = (fiat_created / 1e12) * 0.001

        return price_support, inflation_impact, xcr_purchased


# =============================================================================
# Factory function for creating agents
# =============================================================================

def create_llm_agents(llm_engine: Optional[LLMEngine],
                     agent_types: list,
                     countries: dict = None,
                     price_floor: float = 100.0,
                     inflation_target: float = 0.02) -> dict:
    """
    Factory function to create LLM-powered agents

    Args:
        llm_engine: LLMEngine instance (or None for rule-based)
        agent_types: List of agent types to create ['investor', 'capital', 'cea', 'central_bank']
        countries: Country dict for CentralBankAlliance
        price_floor: Initial price floor
        inflation_target: Inflation target for CEA

    Returns:
        Dict of agent instances
    """
    agents = {}

    if 'investor' in agent_types:
        agents['investor_market'] = InvestorMarketLLM(
            llm_engine=llm_engine,
            price_floor=price_floor
        )

    if 'capital' in agent_types:
        agents['capital_market'] = CapitalMarketLLM(
            llm_engine=llm_engine
        )

    if 'cea' in agent_types:
        agents['cea'] = CEA_LLM(
            llm_engine=llm_engine,
            inflation_target=inflation_target
        )

    if 'central_bank' in agent_types:
        agents['central_bank'] = CentralBankAllianceLLM(
            llm_engine=llm_engine,
            countries=countries,
            price_floor=price_floor
        )

    return agents


# Test function
def test_llm_agents():
    """Test LLM agents with mock data"""
    print("Testing LLM agents...")

    # Create engine (will use fallback if Ollama unavailable)
    engine = LLMEngine(model="llama3.2", cache_mode=CacheMode.DISABLED)

    # Test InvestorMarket
    investor = InvestorMarketLLM(llm_engine=engine)
    sentiment = investor.update_sentiment(
        cea_warning=False,
        global_inflation=0.025,
        inflation_target=0.02,
        co2_level=415.0,
        initial_co2=420.0,
        year=5,
        total_years=50
    )
    print(f"InvestorMarket sentiment: {sentiment:.3f}")

    # Test CapitalMarket
    capital = CapitalMarketLLM(llm_engine=engine)
    flow, premium, guidance = capital.update_capital_flows(
        current_co2=415.0,
        year=5,
        total_years=50,
        roadmap_gap=2.0,
        global_inflation=0.025,
        inflation_target=0.02,
        sentiment=sentiment,
        xcr_supply=1e8,
        price_floor=100.0,
        market_age_years=5
    )
    print(f"CapitalMarket flow: ${flow/1e9:.2f}B, premium: ${premium:.2f}")

    print("LLM agent tests complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_llm_agents()
