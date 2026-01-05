import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from climate import CarbonCycle
from country_equity_data import COUNTRY_EQUITY_DATA

# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

class ProjectStatus(Enum):
    DEVELOPMENT = "development"
    OPERATIONAL = "operational"
    FAILED = "failed"

class ChannelType(Enum):
    CDR = 1          # Carbon Dioxide Removal (R=1 fixed)
    CONVENTIONAL = 2  # Conventional mitigation (R adjustable)
    COBENEFITS = 3   # Co-benefits (R adjustable)
    AVOIDED_DEFORESTATION = 4  # Avoided deforestation (LUC mitigation)

CDR_FAILURE_REVERSAL_FRACTION = 0.10
CONVENTIONAL_FAILURE_REVERSAL_FRACTION = 0.50

def get_failure_reversal_fraction(channel: ChannelType) -> float:
    """Return the fraction of stored/avoided emissions that reverses on failure."""
    if channel in (ChannelType.CONVENTIONAL, ChannelType.AVOIDED_DEFORESTATION):
        return CONVENTIONAL_FAILURE_REVERSAL_FRACTION
    return CDR_FAILURE_REVERSAL_FRACTION

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Project:
    """Represents a carbon mitigation/sequestration project"""
    id: str
    channel: ChannelType
    country: str
    start_year: int
    development_years: int
    annual_sequestration_tonnes: float  # Once operational
    marginal_cost_per_tonne: float
    r_base: float  # Base R-value from cost-effectiveness
    r_effective: float  # Effective R-value (r_base × policy_multiplier) - used for XCR minting
    status: ProjectStatus = ProjectStatus.DEVELOPMENT
    years_in_development: int = 0
    total_xcr_minted: float = 0.0
    health: float = 1.0  # 1.0 = healthy, decays over time with stochastic events
    durability_years: int = 100  # Minimum durability
    total_sequestered_tonnes: float = 0.0  # Physical carbon delivered (for reversals)
    structural_credited_tonnes: float = 0.0  # Structural mitigation credited once (conventional)
    co_benefit_score: float = 0.0  # Robin Hood overlay (0-1)

    # Backward compatibility property
    @property
    def r_value(self) -> float:
        """Alias for r_effective (backward compatibility)"""
        return self.r_effective

    def step(self, failure_multiplier: float = 1.0):
        """Advance project by one year"""
        if self.status == ProjectStatus.DEVELOPMENT:
            self.years_in_development += 1
            if self.years_in_development >= self.development_years:
                self.status = ProjectStatus.OPERATIONAL
        elif self.status == ProjectStatus.OPERATIONAL:
            # Stochastic decay: natural failures (fires, leaks, tech failure)
            annual_failure_rate = np.clip(0.02 * failure_multiplier, 0.0, 0.5)
            if np.random.rand() < annual_failure_rate:  # Climate-adjusted failure rate
                self.health *= np.random.uniform(0.8, 0.95)

# ============================================================================
# AGENT CLASSES
# ============================================================================

class CEA:
    """Carbon Exchange Authority - The central governor"""

    def __init__(self, target_co2_ppm: float = 350.0, initial_co2_ppm: float = 420.0,
                 inflation_target: float = 0.02):
        self.target_co2_ppm = target_co2_ppm
        self.initial_co2_ppm = initial_co2_ppm
        self.roadmap_co2 = initial_co2_ppm  # Updated each year based on roadmap
        self.inflation_target = inflation_target  # Target inflation for brake adjustment

        # Stability monitoring
        self.warning_8to1_active = False
        self.brake_10to1_active = False
        self.brake_factor = 1.0  # Minting rate multiplier (1.0 = no brake)
        self.budget_brake_start = 0.90  # Start braking at 90% of annual CQE cap
        self.budget_brake_floor = 0.25  # Minimum brake factor once cap is hit

        # Price floor guidance (revised periodically)
        self.revision_interval = 5  # Revise policy every 5 years
        self.locked_annual_yield = 0.02  # Current locked-in growth rate
        self.years_until_revision = 5  # Countdown to next policy revision
        self.last_revision_year = 0

    def calculate_roadmap_target(self, year: int, total_years: int) -> float:
        """Linear roadmap from initial to target CO2"""
        progress = year / total_years
        return self.initial_co2_ppm - (self.initial_co2_ppm - self.target_co2_ppm) * progress

    def adjust_price_floor(self, current_co2_ppm: float, current_floor: float,
                          year: int, total_years: int, current_inflation: float = 0.02,
                          temperature_anomaly: float = 1.2) -> tuple[float, bool]:
        """Adjust price floor based on roadmap progress per Chen paper

        From Chen (2025):
        - Price floor REVISED PERIODICALLY (not annually) based on:
          * New climate science
          * GHG trends and roadmap progress
          * Technological advances
        - ~10 years of guaranteed prices (rolling forward)
        - Peaks potentially mid-century

        Returns: (new_floor, revision_occurred)
        """
        revision_occurred = False

        # Check if it's time for a policy revision
        if year % self.revision_interval == 0 and year > 0:
            revision_occurred = True
            print(f"[Year {year}] CEA POLICY REVISION")

            # Calculate roadmap target
            roadmap_target = self.calculate_roadmap_target(year, total_years)

            # Gap between actual and roadmap (positive = behind, negative = ahead)
            roadmap_gap_ppm = current_co2_ppm - roadmap_target

            # Base annual yield (typical 2-5% increase per year)
            base_yield = 0.02  # 2% baseline

            # Adjustment based on roadmap performance
            # Behind roadmap: increase floor faster (up to +5% additional)
            # Ahead of roadmap: slow increase or decrease (down to -3%)
            max_gap = (self.initial_co2_ppm - self.target_co2_ppm)
            performance_adjustment = (roadmap_gap_ppm / max_gap) * 0.05

            # Mid-century peak effect (increase more aggressively early/mid, taper later)
            # Peaks around year 25-30 in a 50-year simulation
            mid_point = total_years / 2
            peak_factor = 1.0 + 0.5 * np.exp(-((year - mid_point) ** 2) / (total_years / 4) ** 2)

            # Calculate new locked-in yield for next 10 years
            new_yield = (base_yield + performance_adjustment) * peak_factor

            # Inflation guard: damp yield if CPI is above target to reduce added pressure
            if self.inflation_target > 0:
                inflation_gap_ratio = max(0.0, current_inflation - self.inflation_target) / self.inflation_target
                inflation_guard = max(0.25, 1.0 - 0.6 * inflation_gap_ratio)
                new_yield *= inflation_guard

            # Climate guard: if warming exceeds Paris guardrail, slow floor growth
            if temperature_anomaly > 2.0:
                new_yield *= 0.5
            elif temperature_anomaly > 1.75:
                new_yield *= 0.7

            # Limit yield to reasonable range (-3% to +10% per year)
            new_yield = np.clip(new_yield, -0.03, 0.10)

            # Lock in this yield for the next period
            self.locked_annual_yield = new_yield
            self.last_revision_year = year

            print(f"  Roadmap gap: {roadmap_gap_ppm:.2f} ppm")
            print(f"  New annual yield: {new_yield*100:.2f}% (locked for next {self.revision_interval} years)")

        # Apply locked-in annual yield (whether revised or not)
        new_floor = current_floor * (1 + self.locked_annual_yield)

        # Floor cannot decrease too fast (prevents perverse incentives)
        new_floor = max(new_floor, current_floor * 0.95)  # Max 5% decrease per year

        return new_floor, revision_occurred

    def calculate_brake_factor(self, ratio: float, current_inflation: float,
                               budget_utilization: float) -> float:
        """Calculate XCR minting reduction based on stability ratio AND realized inflation

        Brake thresholds adjust based on realized inflation:
        - Low inflation → lenient thresholds (allow more issuance)
        - High inflation → strict thresholds (constrain issuance)

        Base thresholds (at 2% inflation baseline):
        - ratio < 8.0: 1.0 (no brake)
        - ratio 8.0-10.0: 1.0 (warning zone)
        - ratio 10.0-12.0: Light brake (1.0 → 0.5)
        - ratio 12.0-15.0: Medium brake (0.5 → 0.25)
        - ratio > 15.0: Heavy brake (0.1)

        Inflation adjustment:
        - At 0.5x baseline inflation: thresholds × 2.0 (more lenient)
        - At 1.0x baseline inflation: thresholds × 1.0 (baseline)
        - At 3.0x baseline inflation: thresholds × 0.5 (more strict)
        """
        if self.inflation_target <= 0:
            return 0.0

        # Normalize realized inflation to 2% baseline
        inflation_ratio = max(current_inflation, 0.0) / 0.02  # 2% is baseline

        # Threshold adjustment factor
        # Low inflation (0.5%): 4x lenient → thresholds × 2.0
        # Medium inflation (2%): 1x baseline → thresholds × 1.0
        # High inflation (10%): 5x high → thresholds × 0.4
        if inflation_ratio < 0.5:  # < 1% inflation
            inflation_adjustment = 2.0
        elif inflation_ratio < 2.0:  # 1-4% inflation
            # Linear: 0.5 → 2.0, 2.0 → 0.5
            inflation_adjustment = 2.0 - 1.0 * (inflation_ratio - 0.5)
        else:  # > 4% target
            inflation_adjustment = max(0.3, 0.5 - 0.05 * (inflation_ratio - 2.0))

        # Adjust thresholds based on inflation target
        warning_threshold = 8.0 * inflation_adjustment
        brake_start = 10.0 * inflation_adjustment
        brake_mid = 12.0 * inflation_adjustment
        brake_heavy = 15.0 * inflation_adjustment

        # Calculate inflation-adjusted heavy brake floor
        # Low target → more lenient floor (30% rate)
        # High target → stricter floor (1% rate)
        if inflation_ratio < 0.5:  # < 1% inflation
            heavy_brake_floor = 0.3  # 30% rate (lenient)
        elif inflation_ratio < 2.0:  # 1-4% inflation
            # Linear: 0.5 → 0.3, 2.0 → 0.05
            heavy_brake_floor = 0.3 - 0.167 * (inflation_ratio - 0.5)
        else:  # > 4% target
            heavy_brake_floor = max(0.01, 0.05 - 0.01 * (inflation_ratio - 2.0))

        # Apply brake based on adjusted thresholds
        if ratio < warning_threshold:
            ratio_brake = 1.0  # No brake
        elif ratio < brake_start:
            ratio_brake = 1.0  # Warning zone - no minting reduction yet
        elif ratio < brake_mid:
            # Linear interpolation: brake_start → 1.0x, brake_mid → 0.5x
            ratio_brake = 1.0 - 0.5 * (ratio - brake_start) / (brake_mid - brake_start)
        elif ratio < brake_heavy:
            # Linear interpolation: brake_mid → 0.5x, brake_heavy → 0.25x
            ratio_brake = 0.5 - 0.25 * (ratio - brake_mid) / (brake_heavy - brake_mid)
        else:
            ratio_brake = heavy_brake_floor  # Inflation-adjusted heavy brake

        # Budget utilization brake (start at 90% of cap)
        utilization = min(max(budget_utilization, 0.0), 1.0)
        if utilization < self.budget_brake_start:
            budget_brake = 1.0
        else:
            span = max(1.0 - self.budget_brake_start, 1e-6)
            budget_brake = 1.0 - (utilization - self.budget_brake_start) / span
            budget_brake = max(self.budget_brake_floor, budget_brake)

        # Inflation penalty directly slows minting when CPI exceeds target
        inflation_penalty = 1.0
        if inflation_ratio > 1.0:
            inflation_penalty = max(0.2, 1.0 - 0.4 * (inflation_ratio - 1.0))

        return min(ratio_brake, budget_brake) * inflation_penalty

    def update_policy(self, current_co2_ppm: float, market_cap_xcr: float,
                     total_cqe_budget: float, global_inflation: float,
                     budget_utilization: float):
        """Update CEA policy based on system state

        Monitors stability ratio and issues warnings to investors.
        Calculates brake factor to reduce XCR minting when ratio exceeds thresholds.

        Actual control mechanisms:
        - Price floor adjustments (based on roadmap progress)
        - CQE sigmoid damping (central bank willingness to defend floor)
        - Investor sentiment response to warnings
        - Brake factor (reduces XCR minting rate when ratio > 10:1)
        """
        # Stability Ratio monitoring
        ratio = market_cap_xcr / total_cqe_budget if total_cqe_budget > 0 else 0
        self.warning_8to1_active = ratio >= 8.0
        self.brake_10to1_active = ratio >= 10.0

        # Calculate brake factor (proportional minting reduction, inflation-adjusted)
        self.brake_factor = self.calculate_brake_factor(ratio, global_inflation, budget_utilization)

    def calculate_policy_r_multiplier(self, channel: ChannelType, current_year: int) -> float:
        """Calculate policy R-multiplier for channel prioritization

        Per Chen, multipliers are fixed at 1.0 (no penalties or time shifts).
        """
        return 1.0

    def calculate_project_r_value(self, channel: ChannelType,
                                  marginal_cost: float, benchmark_cdr_cost: float,
                                  current_year: int = 0) -> tuple[float, float]:
        """Calculate R value for a project based on cost-effectiveness

        From Chen paper:
        - CDR (Channel 1): R = 1 (fixed)
        - Conventional (Channel 2): R = marginal_cost / marginal_cdr_cost
        - Co-benefits (Channel 3): R adjusted by co-benefit value

        Returns: (r_base, r_effective)
        - r_base: Cost-effectiveness R-value
        - r_effective: r_base × policy_multiplier
        """
        # Calculate base R-value from cost-effectiveness
        if channel == ChannelType.CDR:
            r_base = 1.0
        elif channel in (ChannelType.CONVENTIONAL, ChannelType.AVOIDED_DEFORESTATION):
            # R represents cost-effectiveness relative to CDR baseline
            r_base = marginal_cost / benchmark_cdr_cost if benchmark_cdr_cost > 0 else 1.0
            r_base = max(0.1, r_base)  # Minimum R to prevent division issues
        else:  # COBENEFITS
            # Simplified: assume co-benefits reduce effective cost by 20%
            r_base = (marginal_cost * 0.8) / benchmark_cdr_cost if benchmark_cdr_cost > 0 else 1.0
            r_base = max(0.1, r_base)

        # Apply policy multiplier for channel prioritization
        # Exception: CDR R-value is FIXED at 1.0 (no policy adjustment)
        if channel == ChannelType.CDR:
            r_effective = r_base  # CDR: R = 1 (fixed, per Chen paper)
        else:
            policy_multiplier = self.calculate_policy_r_multiplier(channel, current_year)
            r_effective = r_base * policy_multiplier

        return r_base, r_effective


class CentralBankAlliance:
    """Central Bank Alliance - Price floor defenders via CQE

    CQE Budget Model (Flow-Based Backstop):
    - Total CQE budget = 5% of annual private capital inflow, capped by GDP share
    - Apportioned among countries by GDP share
    - Ensures private capital leads; public backstop remains a minority share
    """

    def __init__(self, countries: Dict[str, Dict], price_floor: float = 100.0):
        self.countries = countries
        self.price_floor_rcc = price_floor
        self.total_cqe_budget = 0.0  # Calculated dynamically from private capital
        self.cqe_ratio = 0.05  # CQE = 5% of annual private capital inflow before GDP cap
        self.gdp_cap_ratio = 0.005  # CQE cap as share of active-country GDP
        self.total_cqe_spent = 0.0  # Track total M0 created (cumulative)
        self.annual_cqe_spent = 0.0  # Track spending this year (resets annually)
        self.current_budget_year = 0  # Track year for annual reset

    def update_cqe_budget(self, annual_private_capital_inflow: float):
        """Recalculate CQE budget as 5% of annual private capital inflow, capped by GDP

        Flow-Based Backstop:
        - Private capital leads; CQE follows as a minority backstop
        - Annual inflow sizing avoids cumulative overshoot

        Budget is capped by active GDP (0.5% of active GDP).
        """
        market_cap_budget = annual_private_capital_inflow * self.cqe_ratio
        active_gdp_tril = sum(country["gdp_tril"] for country in self.countries.values())
        gdp_cap_budget = active_gdp_tril * 1e12 * self.gdp_cap_ratio
        self.total_cqe_budget = min(market_cap_budget, gdp_cap_budget)

    def defend_floor(self, market_price_xcr: float, total_xcr_supply: float,
                    global_inflation: float, inflation_target: float = 0.02,
                    current_year: int = 0) -> tuple[float, float, float]:
        """Defend price floor using sigmoid-damped CQE with annual budget cap

        Returns: (price_support, inflation_impact, xcr_purchased)

        Sigmoid damping: willingness decreases as inflation rises above target.
        - Center: 1.5x inflation target (willingness = 0.5)
        - Full willingness when inflation ≤ target
        - Zero willingness when inflation >> 1.5x target

        Annual Budget Cap:
        - Cannot spend more than total_cqe_budget per year
        - When exhausted, price can fall below floor until next year
        """
        # Check if annual budget already exhausted
        if self.annual_cqe_spent >= self.total_cqe_budget:
            # Budget exhausted - cannot defend floor this year
            return 0.0, 0.0, 0.0

        if inflation_target <= 0:
            return 0.0, 0.0, 0.0

        # Sigmoid damping: willingness decreases as inflation rises
        k = 12.0  # Sharpness of brake
        sigmoid_center = inflation_target * 1.5  # Center sigmoid at 1.5x target
        willingness = 1 / (1 + np.exp(k * (global_inflation - sigmoid_center)))

        if market_price_xcr < self.price_floor_rcc:
            # Calculate price gap
            price_gap = self.price_floor_rcc - market_price_xcr

            # Intervention strength based on gap and willingness
            # Close gap proportionally (don't overshoot)
            intervention_strength = min(price_gap / self.price_floor_rcc, 0.5) * willingness

            # Price support (pushes price toward floor)
            price_support = price_gap * intervention_strength

            # M0 creation for buying XCR
            # Amount of fiat created = XCR bought × price
            xcr_purchased = total_xcr_supply * intervention_strength * 0.05  # Buy up to 5% of supply
            fiat_created = xcr_purchased * self.price_floor_rcc

            # Check if this intervention would exceed annual budget
            if self.annual_cqe_spent + fiat_created > self.total_cqe_budget:
                # Partial intervention - only spend remaining budget
                remaining_budget = self.total_cqe_budget - self.annual_cqe_spent
                fiat_created = remaining_budget
                xcr_purchased = fiat_created / self.price_floor_rcc if self.price_floor_rcc > 0 else 0
                # Recalculate price support based on actual spending
                price_support = price_support * (remaining_budget / (xcr_purchased * self.price_floor_rcc)) if xcr_purchased * self.price_floor_rcc > 0 else 0

            # Track spending
            self.annual_cqe_spent += fiat_created
            self.total_cqe_spent += fiat_created

            # Inflation impact: proportional to money creation relative to real economy
            # Uses active GDP as the scale for CPI impact.
            active_gdp_tril = sum(country["gdp_tril"] for country in self.countries.values())
            active_gdp_usd = active_gdp_tril * 1e12
            inflation_impact = (fiat_created / active_gdp_usd) * 5 if active_gdp_usd > 0 else 0.0
            # Ensure material signal when spending is non-trivial
            if active_gdp_usd > 0 and (fiat_created / active_gdp_usd) > 0.001:
                inflation_impact = max(inflation_impact, 0.0025)
            inflation_impact = float(np.clip(inflation_impact, 0.0, 0.02))  # Cap at +2pp

            return price_support, inflation_impact, xcr_purchased

        return 0.0, 0.0, 0.0


class ProjectsBroker:
    """Projects & Broker - Manages portfolio of mitigation projects"""

    def __init__(self, countries: Dict[str, Dict]):
        self.countries = countries
        self.projects: List[Project] = []
        self.next_project_id = 1

        # Project scale damping (learning-by-doing curve)
        # Project size scales with cumulative deployment experience
        self.scale_damping_enabled = True
        self.full_scale_deployment_gt = 45.0  # Default full-scale threshold (Gt)

        # Co-benefits pool: fraction of XCR held back for redistribution
        self.cobenefit_pool_fraction = 0.15  # 15% of minted XCR is reallocated via co-benefit scores

        # Marginal cost curves by channel (simplified)
        self.base_costs = {
            ChannelType.CDR: 100.0,  # Starts at price floor
            ChannelType.CONVENTIONAL: 80.0,  # Initially cheaper
            ChannelType.COBENEFITS: 70.0,  # Co-benefits reduce costs
            ChannelType.AVOIDED_DEFORESTATION: 60.0  # Low-cost land-use mitigation
        }

        # Learning curve parameters (cost reduction with cumulative deployment)
        self.learning_rates = {
            ChannelType.CDR: 0.20,  # 20% cost reduction per doubling
            ChannelType.CONVENTIONAL: 0.12,  # 12% (already mature)
            ChannelType.COBENEFITS: 0.08,  # 8% (nature-based, limited tech gains)
            ChannelType.AVOIDED_DEFORESTATION: 0.08  # Similar to nature-based
        }

        # Track cumulative deployment by channel (in tonnes CO2)
        self.cumulative_deployment = {
            ChannelType.CDR: 0.0,
            ChannelType.CONVENTIONAL: 0.0,
            ChannelType.COBENEFITS: 0.0,
            ChannelType.AVOIDED_DEFORESTATION: 0.0
        }

        # Reference capacity for learning curves (first year deployment)
        self.reference_capacity = {
            ChannelType.CDR: None,  # Will be set on first project
            ChannelType.CONVENTIONAL: None,
            ChannelType.COBENEFITS: None,
            ChannelType.AVOIDED_DEFORESTATION: None
        }

        # Conventional capacity limit parameters
        self.conventional_capacity_limit = 0.80  # 80% of potential emissions
        self.conventional_capacity_limit_year = 60  # Reach limit by year 60 (2060 if start=2000)
        self.conventional_capacity_min_factor = 0.10  # Residual hard-to-abate tail

        # Maximum annual sequestration capacity by channel (Gt/year)
        # Represents physical/technological limits on deployment scale
        self.max_capacity_gt_per_year = {
            ChannelType.CDR: 10.0,  # DAC/NCC upper bound
            ChannelType.CONVENTIONAL: 30.0,  # Earlier taper to force CDR reliance
            ChannelType.COBENEFITS: 50.0,  # Nature-based solutions - large potential
            ChannelType.AVOIDED_DEFORESTATION: 5.0  # Land-use emissions ceiling
        }

    def calculate_project_scale_damper(self, cumulative_deployment_gt: float = 0.0) -> float:
        """Calculate project scale damping factor based on cumulative deployment experience

        As the industry deploys more total capacity, they learn to build bigger facilities.
        This links scale growth to actual learning-by-doing, not just calendar time.

        Project size scales with cumulative deployment:
        - Early deployments: Pilot scale (0.7-7 MT/year)
        - Mid deployments: Commercial scale (5-30 MT/year)
        - Late deployments: Industrial scale (30-100 MT/year)

        Returns multiplier from 0.07 (7% scale) to 1.0 (full scale)

        Deployment milestones (approx, default 45 Gt full-scale):
        - 0-4.5 Gt: 7-20% scale (pilot projects)
        - 4.5-18 Gt: 20-60% scale (early commercial)
        - 18-36 Gt: 60-90% scale (commercial)
        - 36-45 Gt: 90-100% scale (industrial)
        - 45+ Gt: 100% scale (full industrial)
        """
        if not self.scale_damping_enabled:
            return 1.0

        # Total cumulative deployment across all channels (industry-wide learning)
        total_deployment_gt = sum(self.cumulative_deployment.values()) / 1e9

        min_scale = 0.07
        if total_deployment_gt <= 0:
            return min_scale
        if total_deployment_gt >= self.full_scale_deployment_gt:
            return 1.0  # Full scale

        # Sigmoid curve for smooth scaling (normalized to hit min/max at endpoints)
        # Maps 0 Gt → min_scale, full_scale → 1.0
        midpoint = self.full_scale_deployment_gt * 0.3  # Mid-commercial
        steepness = 8.0 / max(self.full_scale_deployment_gt, 1e-6)

        s0 = 1.0 / (1.0 + np.exp(-steepness * (0.0 - midpoint)))
        s1 = 1.0 / (1.0 + np.exp(-steepness * (self.full_scale_deployment_gt - midpoint)))
        s = 1.0 / (1.0 + np.exp(-steepness * (total_deployment_gt - midpoint)))
        normalized = (s - s0) / max(s1 - s0, 1e-6)
        normalized = np.clip(normalized, 0.0, 1.0)

        return min_scale + (1.0 - min_scale) * normalized

    def calculate_marginal_cost(self, channel: ChannelType) -> float:
        """Calculate current marginal cost using learning curves

        Cost = Base_Cost × (Cumulative_Deployment / Reference_Capacity)^(-b)
        where b = log(1 - LR) / log(2)

        Learning reduces costs as deployment grows, but resource depletion
        (from project count) provides upward pressure.
        """
        base = self.base_costs[channel]
        cumulative = self.cumulative_deployment[channel]
        reference = self.reference_capacity[channel]

        # If no deployment yet, return base cost
        if reference is None or reference == 0 or cumulative == 0:
            return base

        # Learning curve exponent: b = log(1 - LR) / log(2)
        lr = self.learning_rates[channel]
        b = np.log(1 - lr) / np.log(2)

        # Learning curve effect (cost reduction)
        learning_factor = (cumulative / reference) ** b

        # Resource depletion effect (cost increase from scarcity)
        # Count projects to model diminishing easy opportunities
        # Logarithmic scaling: costs increase slowly with project count
        # At 100 projects: log10(100) = 2.0 → 1.3x cost
        # At 10,000 projects: log10(10000) = 4.0 → 1.6x cost
        channel_projects = [p for p in self.projects if p.channel == channel]
        count = len(channel_projects)
        if count > 0:
            depletion_factor = 1.0 + (0.15 * np.log10(count + 1))
        else:
            depletion_factor = 1.0

        # Combined effect
        marginal_cost = base * learning_factor * depletion_factor

        return marginal_cost

    def get_conventional_capacity_utilization(self, current_year: int) -> float:
        """Calculate how much of conventional mitigation capacity has been utilized

        Returns value from 0.0 to 1.0 representing capacity utilization.
        Reaches capacity_limit (0.8) by conventional_capacity_limit_year via sigmoid taper.
        """
        if current_year <= 0:
            return 0.0
        if current_year >= self.conventional_capacity_limit_year:
            return self.conventional_capacity_limit

        # Sigmoid progression to limit (normalized to hit 0->1 across the window)
        progress = current_year / self.conventional_capacity_limit_year
        k = 8.0  # Steepness of the taper curve
        s0 = 1.0 / (1.0 + np.exp(-k * (0.0 - 0.5)))
        s1 = 1.0 / (1.0 + np.exp(-k * (1.0 - 0.5)))
        s = 1.0 / (1.0 + np.exp(-k * (progress - 0.5)))
        normalized = (s - s0) / max(s1 - s0, 1e-6)
        utilization = np.clip(normalized, 0.0, 1.0) * self.conventional_capacity_limit

        return utilization

    def is_conventional_capacity_available(self, current_year: int) -> bool:
        """Check if conventional mitigation capacity is still available"""
        return self.get_conventional_capacity_factor(current_year) > self.conventional_capacity_min_factor

    def get_conventional_capacity_factor(self, current_year: int) -> float:
        """Return taper factor for conventional project initiation (0.0-1.0)."""
        utilization = self.get_conventional_capacity_utilization(current_year)
        if self.conventional_capacity_limit <= 0:
            return 1.0
        utilization_ratio = min(utilization / self.conventional_capacity_limit, 1.0)
        factor = 1.0 - utilization_ratio
        return max(self.conventional_capacity_min_factor, factor)

    def update_cumulative_deployment(self, channel: ChannelType, tonnes: float):
        """Update cumulative deployment for learning curve tracking

        Call this when a project becomes operational or produces verified sequestration.
        """
        self.cumulative_deployment[channel] += tonnes

        # Set reference capacity on first deployment
        if self.reference_capacity[channel] is None:
            self.reference_capacity[channel] = tonnes

    def get_current_sequestration_rate(self, channel: ChannelType) -> float:
        """Get current annual sequestration rate for a channel in Gt/year

        Returns the sum of annual sequestration from all operational projects in this channel.
        """
        total_tonnes = sum(
            p.annual_sequestration_tonnes
            for p in self.projects
            if p.channel == channel and p.status == ProjectStatus.OPERATIONAL
        )
        return total_tonnes / 1e9  # Convert tonnes to Gt

    def get_planned_sequestration_rate(self, channel: ChannelType) -> float:
        """Get planned annual sequestration rate (operational + development) in Gt/year"""
        total_tonnes = sum(
            p.annual_sequestration_tonnes
            for p in self.projects
            if p.channel == channel and p.status != ProjectStatus.FAILED
        )
        return total_tonnes / 1e9  # Convert tonnes to Gt

    def _calculate_project_capacity(self, channel: ChannelType, current_co2_ppm: float, current_inflation: float = 0.02) -> float:
        """Calculate climate urgency multiplier for project initiation

        Returns a 0.0-1.0 factor applied to capital-limited project counts.

        Scales with:
        1. Climate urgency (reduces as we approach 350 ppm target)
        2. Realized inflation (high inflation → taper earlier & more aggressively)
        """

        # Apply inflation-adjusted climate urgency factor
        # High inflation → Start tapering earlier and more aggressively
        target_co2 = 350.0

        # Adjust taper start based on realized inflation
        # Low inflation (0.5%): Start at 370 ppm (20 ppm buffer) - VERY aggressive
        # Baseline (2%): Start at 390 ppm (40 ppm buffer) - moderate
        # High inflation (6%): Start at 420 ppm (70 ppm buffer) - VERY cautious
        inflation_ratio = max(current_inflation, 0.0) / 0.02  # Normalize to 2% baseline

        if inflation_ratio < 0.5:
            taper_start = 370.0  # Low inflation: very aggressive, start early
        elif inflation_ratio < 1.5:
            taper_start = 370.0 + 20.0 * (inflation_ratio - 0.5)  # 370-390 ppm
        else:
            taper_start = min(425.0, 390.0 + 15.0 * (inflation_ratio - 1.5))  # 390-425 ppm max

        if current_co2_ppm >= taper_start:
            # High urgency: Above taper start - full capacity
            urgency_factor = 1.0
        elif current_co2_ppm > 370.0:
            # Early approach: Gentle taper
            range_size = taper_start - 370.0
            urgency_factor = 0.6 + 0.4 * (current_co2_ppm - 370.0) / range_size
        elif current_co2_ppm > 360.0:
            # Mid approach: Moderate taper
            # Inflation-sensitive: High inflation tapers much more steeply
            if inflation_ratio > 2.5:  # High inflation (>5%)
                urgency_factor = 0.15 + 0.45 * (current_co2_ppm - 360.0) / 10.0
            elif inflation_ratio > 1.5:  # Medium inflation (3-5%)
                urgency_factor = 0.2 + 0.4 * (current_co2_ppm - 360.0) / 10.0
            else:  # Low inflation
                urgency_factor = 0.3 + 0.3 * (current_co2_ppm - 360.0) / 10.0
        elif current_co2_ppm > target_co2:
            # Final approach: Steep taper
            # Inflation-sensitive: High inflation drops to near-zero capacity
            if inflation_ratio > 2.5:  # High inflation (>5%)
                urgency_factor = 0.01 + 0.14 * (current_co2_ppm - target_co2) / 10.0
            elif inflation_ratio > 1.5:  # Medium inflation (3-5%)
                urgency_factor = 0.02 + 0.18 * (current_co2_ppm - target_co2) / 10.0
            else:  # Low inflation
                urgency_factor = 0.05 + 0.25 * (current_co2_ppm - target_co2) / 10.0
        else:
            # Below target: minimal maintenance only
            urgency_factor = 0.02

        return max(urgency_factor, 0.0)

    def _select_country(self, channel: ChannelType) -> str:
        """Select country for project based on channel preferences

        CDR: Prefers tropical/developing countries (land availability)
        Conventional: Prefers developed economies (infrastructure)
        Co-benefits: Prefers developing countries (ecosystem restoration)
        """
        active_countries = list(self.countries.keys())

        if not active_countries:
            raise ValueError("No active countries available for project allocation")

        # Channel-specific country preferences
        if channel in (ChannelType.CDR, ChannelType.AVOIDED_DEFORESTATION):
            # Prefer tropical/developing regions with land
            preferred = [c for c in active_countries
                        if self.countries[c].get('region') in
                        ['South America', 'Africa', 'Asia']]
        elif channel == ChannelType.CONVENTIONAL:
            # Prefer developed economies with infrastructure
            preferred = [c for c in active_countries
                        if self.countries[c].get('tier') == 1]
        else:  # COBENEFITS
            # Prefer developing countries (ecosystem restoration)
            preferred = [c for c in active_countries
                        if self.countries[c].get('tier') in [2, 3]]

        country_pool = preferred if preferred else active_countries
        return np.random.choice(country_pool)

    def initiate_projects(self, market_price_xcr: float, price_floor: float, cea: CEA, current_year: int,
                          current_co2_ppm: float, current_inflation: float,
                          available_capital_usd: float = 0.0, brake_factor: float = 1.0,
                          residual_emissions_gt: Optional[float] = None,
                          residual_luc_emissions_gt: Optional[float] = None):
        """Initiate new projects where economics are favorable

        Project starts when: (market_price * R_effective * brake_factor) >= marginal_cost
        Project capacity scales with climate urgency (reduces as CO2 approaches 350 ppm)
        Which means: market_price * R_effective * brake_factor >= marginal_cost
        Or equivalently: XCR revenue covers costs

        Uses learning-adjusted costs and policy R-multipliers.
        Respects conventional capacity limits.
        Enforces physical capacity caps and available capital constraints.
        """
        remaining_capital = max(available_capital_usd, 0.0)

        benchmark_cdr_cost = self.calculate_marginal_cost(ChannelType.CDR)

        # Only initiate physical mitigation channels; co-benefits are handled as reward overlay
        for channel in (ChannelType.CDR, ChannelType.CONVENTIONAL, ChannelType.AVOIDED_DEFORESTATION):
            if remaining_capital <= 0:
                break

            # Check channel capacity limits (Gt/year)
            planned_rate_gt = self.get_planned_sequestration_rate(channel)
            max_capacity_gt = self.max_capacity_gt_per_year[channel]

            if planned_rate_gt >= max_capacity_gt:
                # Channel at or above maximum planned capacity
                continue
            remaining_capacity_gt = max_capacity_gt - planned_rate_gt

            if channel == ChannelType.CONVENTIONAL and residual_emissions_gt is not None:
                remaining_capacity_gt = min(remaining_capacity_gt, max(residual_emissions_gt, 0.0))
                if remaining_capacity_gt <= 0:
                    continue
            if channel == ChannelType.AVOIDED_DEFORESTATION and residual_luc_emissions_gt is not None:
                remaining_capacity_gt = min(remaining_capacity_gt, max(residual_luc_emissions_gt, 0.0))
                if remaining_capacity_gt <= 0:
                    continue

            # Calculate learning-adjusted marginal cost
            marginal_cost = self.calculate_marginal_cost(channel)

            # Get R-values (base and policy-adjusted effective)
            r_base, r_effective = cea.calculate_project_r_value(
                channel, marginal_cost, benchmark_cdr_cost, current_year
            )

            # Economics check: revenue per tonne = price * R_effective * brake
            revenue_per_tonne = market_price_xcr * r_effective * brake_factor

            if revenue_per_tonne >= marginal_cost:
                # Profitable - initiate multiple projects
                # Climate urgency factor (0-1) scales capital-limited capacity
                urgency_factor = self._calculate_project_capacity(channel, current_co2_ppm, current_inflation)
                capacity_factor = 1.0
                if channel == ChannelType.CONVENTIONAL:
                    capacity_factor = self.get_conventional_capacity_factor(current_year)

                # Estimate how many projects available capital and capacity can support
                scale_damper = self.calculate_project_scale_damper()
                expected_base_seq = 5.5e7  # Expected base scale (10-100M tonnes avg)
                min_base_seq = 1e7  # Minimum base scale
                expected_seq = expected_base_seq * scale_damper
                min_seq = min_base_seq * scale_damper

                max_by_capital = int(remaining_capital / max(marginal_cost * expected_seq, 1.0))
                max_by_capacity = int((remaining_capacity_gt * 1e9) / max(min_seq, 1.0))
                max_projects = max(min(max_by_capital, max_by_capacity), 0)
                num_projects = int(max_projects * urgency_factor * capacity_factor)

                # Inner loop: create multiple projects for this channel
                for _ in range(num_projects):
                    if remaining_capacity_gt <= 0 or remaining_capital <= 0:
                        break

                    # Select country based on channel preferences
                    country = self._select_country(channel)

                    # Project parameters
                    dev_years = np.random.randint(1, 3)  # 1-2 years development

                    # Base project scale: 10M-100M tonnes/year
                    base_annual_seq = np.random.uniform(1e7, 1e8)

                    # Apply scale damping (learning-by-doing curve)
                    # Scale increases as industry gains deployment experience
                    # Early deployments: pilot scale (7% → 0.7-7 MT/year)
                    # Late deployments: industrial scale (100% → 10-100 MT/year)
                    annual_seq = base_annual_seq * scale_damper
                    annual_seq = min(annual_seq, remaining_capacity_gt * 1e9)

                    # Cap by available capital (simple affordability constraint)
                    max_affordable = (remaining_capital / marginal_cost) if marginal_cost > 0 else 0.0
                    annual_seq = min(annual_seq, max_affordable)
                    if annual_seq <= 0:
                        break

                    co_benefit_score = float(np.clip(np.random.normal(0.6, 0.2), 0.0, 1.0))

                    project = Project(
                        id=f"P{self.next_project_id:04d}",
                        channel=channel,
                        country=country,
                        start_year=current_year,
                        development_years=dev_years,
                        annual_sequestration_tonnes=annual_seq,
                        marginal_cost_per_tonne=marginal_cost,
                        r_base=r_base,
                        r_effective=r_effective,
                        co_benefit_score=co_benefit_score
                    )

                    self.projects.append(project)
                    self.countries[country]['projects'].append(project.id)
                    self.next_project_id += 1
                    remaining_capital -= annual_seq * marginal_cost
                    remaining_capacity_gt -= annual_seq / 1e9

    def step_projects(
        self,
        current_co2_ppm: float = 420.0,
        current_inflation: float = 0.02,
        climate_risk_multiplier: float = 1.0,
        channel_risk_fn=None
    ) -> float:
        """Advance all projects by one year and return reversal_tonnes

        When CO2 < 350 ppm (target achieved), projects have increased retirement rate
        to gradually wind down operations as climate goal is achieved.

        High inflation environments retire projects more aggressively to reduce
        ongoing minting pressure.
        """
        target_co2 = 350.0

        reversal_tonnes = 0.0

        for project in self.projects:
            if project.status != ProjectStatus.FAILED:
                # Check for climate-target-achieved retirement
                if current_co2_ppm < target_co2 and project.status == ProjectStatus.OPERATIONAL:
                    # Retirement rate scales with how far below target
                    # AND with realized inflation (high inflation = faster retirement)
                    overshoot_ppm = target_co2 - current_co2_ppm
                    inflation_ratio = max(current_inflation, 0.0) / 0.02  # Normalize to 2%

                    # Base retirement rates
                    if overshoot_ppm <= 5:
                        base_rate = 0.15  # Minimal overshoot
                    elif overshoot_ppm <= 15:
                        base_rate = 0.22  # Moderate overshoot
                    elif overshoot_ppm <= 30:
                        base_rate = 0.30  # Significant overshoot
                    else:
                        base_rate = 0.40  # Severe overshoot

                    # Inflation adjustment: High inflation → faster retirement
                    if inflation_ratio > 2.5:  # High inflation (>5%)
                        inflation_multiplier = 1.4  # 40% faster retirement
                    elif inflation_ratio > 1.5:  # Medium inflation (3-5%)
                        inflation_multiplier = 1.2  # 20% faster
                    elif inflation_ratio < 0.5:  # Low inflation (<1%)
                        inflation_multiplier = 0.8  # 20% slower (keep projects longer)
                    else:
                        inflation_multiplier = 1.0  # Baseline

                    retirement_probability = min(0.5, base_rate * inflation_multiplier)

                    if np.random.random() < retirement_probability:
                        project.status = ProjectStatus.FAILED
                        reversal_fraction = get_failure_reversal_fraction(project.channel)
                        reversal_tonnes += project.total_sequestered_tonnes * reversal_fraction
                        project.total_sequestered_tonnes = 0.0
                        # Note: This is retirement, not failure, but uses same status
                        continue

                # Normal project step (development progress, stochastic decay)
                channel_factor = channel_risk_fn(project.channel.name.lower()) if channel_risk_fn else 1.0
                project.step(failure_multiplier=climate_risk_multiplier * channel_factor)

        return reversal_tonnes

    def get_operational_projects(self) -> List[Project]:
        """Return list of operational projects ready for verification"""
        return [p for p in self.projects if p.status == ProjectStatus.OPERATIONAL]


class InvestorMarket:
    """Investor Market - Aggregate sentiment and price discovery"""

    def __init__(self, price_floor: float = 100.0):
        self.sentiment = 1.0  # 0.0 (panic) to 1.0 (full trust)
        self.price_floor = price_floor
        self.market_price_xcr = price_floor + (50 * self.sentiment)
        self.last_warning = False

    def calculate_price(self, capital_demand_premium: float = 0.0) -> float:
        """Calculate market price from sentiment and capital demand

        Price = Floor + Sentiment Premium + Capital Demand Premium

        - Floor: Defended by CQE (baseline)
        - Sentiment Premium: System credibility (0 to $50)
        - Capital Demand Premium: Private investor demand (can be ± based on flows)
        """
        sentiment_premium = 50 * self.sentiment  # Max $50 at full trust
        self.market_price_xcr = self.price_floor + sentiment_premium + capital_demand_premium
        return self.market_price_xcr

    def update_sentiment(self, cea_warning: bool, global_inflation: float,
                        inflation_target: float = 0.02,
                        co2_level: float = None, initial_co2: float = None,
                        forward_guidance: float = None,
                        price_floor_delta: float = 0.0):
        """Update investor sentiment based on system state

        Sentiment ranges from 0.0 (panic) to 1.0 (full trust).
        Responds to both problems (warnings, inflation) AND success (CO2 reduction).

        Inflation thresholds are RELATIVE to target:
        - Very high: 3x target
        - High: 2x target
        - Moderate: 1.5x target
        - Acceptable: ≤ 1.25x target
        """
        # NEGATIVE DRIVERS: Decay when there are problems
        if cea_warning:
            # Apply larger decay on warning onset, smaller decay if warning persists.
            if not self.last_warning:
                self.sentiment *= 0.97  # 3% decay on new warning
            else:
                self.sentiment *= 0.995  # 0.5% decay if warning persists

        # Inflation decay - relative to target
        very_high_threshold = inflation_target * 3.0
        high_threshold = inflation_target * 2.0
        moderate_threshold = inflation_target * 1.5

        if global_inflation > very_high_threshold:  # Very high (3x target)
            self.sentiment *= 0.94  # 6% decay
        elif global_inflation > high_threshold:  # High (2x target)
            self.sentiment *= 0.97  # 3% decay
        elif global_inflation > moderate_threshold:  # Moderate (1.5x target)
            self.sentiment *= 0.995  # 0.5% decay (above comfort zone)

        # POSITIVE DRIVERS: Recovery based on system performance
        # Base recovery: System functioning, no major problems
        acceptable_threshold = inflation_target * 1.25  # 25% above target is acceptable
        if not cea_warning and global_inflation <= acceptable_threshold:
            # Recover when inflation under control (≤ 1.25x target)
            base_recovery = 0.02  # 2% of gap to 1.0
            self.sentiment = min(1.0, self.sentiment + (1.0 - self.sentiment) * base_recovery)

        # Bonus recovery: System is delivering meaningful CO2 reductions
        if co2_level is not None and initial_co2 is not None:
            co2_reduction = initial_co2 - co2_level
            # Scaled bonus: more reduction = more confidence boost
            if co2_reduction > 0.5:  # Significant progress (>0.5 ppm)
                bonus_recovery = 0.015  # 1.5% bonus
                self.sentiment = min(1.0, self.sentiment + (1.0 - self.sentiment) * bonus_recovery)
            elif co2_reduction > 0.1:  # Moderate progress (>0.1 ppm)
                bonus_recovery = 0.005  # 0.5% bonus
                self.sentiment = min(1.0, self.sentiment + (1.0 - self.sentiment) * bonus_recovery)

        # Positive signal: stronger forward guidance on climate damages
        if forward_guidance is not None:
            fg_boost = min(0.2, max(0.0, forward_guidance) * 0.2)  # up to +20% of remaining gap
            self.sentiment = min(1.0, self.sentiment + (1.0 - self.sentiment) * fg_boost)

        # Positive signal: price floor revised upward (policy confidence)
        if price_floor_delta and price_floor_delta > 0:
            # Normalize delta to percentage change
            floor_boost = min(0.25, 5.0 * (price_floor_delta / max(self.price_floor, 1e-6)))
            self.sentiment = min(1.0, self.sentiment + (1.0 - self.sentiment) * floor_boost)

        # Ensure minimum sentiment (prevent total collapse)
        self.sentiment = max(0.1, self.sentiment)
        self.last_warning = cea_warning


class CapitalMarket:
    """Private capital investors buying/selling XCR as climate hedge

    XCR attracts private capital as:
    1. Climate hedge (forward guidance on climate damages)
    2. Inflation hedge (real asset in high-inflation environments)
    3. Return potential (price appreciation)
    """

    def __init__(self, initial_co2: float = 420.0, target_co2: float = 350.0):
        self.initial_co2 = initial_co2
        self.target_co2 = target_co2
        self.cumulative_capital_inflow = 0.0  # Total capital deployed (USD)
        self.cumulative_capital_outflow = 0.0  # Total capital withdrawn (USD)
        self.seed_capital_usd = 2e10  # Bootstrap inflow for early-stage market formation
        self.seed_market_cap_usd = 5e10  # Seed applies while market cap is small
        self.neutrality_start = 0.6  # Higher hurdle for new markets
        self.neutrality_end = 0.3  # More optimistic after market matures
        self.neutrality_ramp_years = 10  # Years to reach optimistic neutrality

    def _neutrality_threshold(self, market_age_years: float) -> float:
        """Return capital neutrality threshold based on market age."""
        if self.neutrality_ramp_years <= 0:
            return self.neutrality_end
        if market_age_years <= 0:
            return self.neutrality_start
        if market_age_years >= self.neutrality_ramp_years:
            return self.neutrality_end
        progress = market_age_years / self.neutrality_ramp_years
        return self.neutrality_start + (self.neutrality_end - self.neutrality_start) * progress

    def calculate_forward_guidance(self, current_co2: float, year: int,
                                   total_years: int, roadmap_gap: float) -> float:
        """Calculate forward guidance signal for climate damages

        Higher CO2 + running out of time + falling behind = stronger signal
        Returns: 0.0 (no urgency) to 1.0 (extreme urgency)
        """
        # Component 1: CO2 gap (how far from target)
        co2_gap = current_co2 - self.target_co2
        max_gap = self.initial_co2 - self.target_co2
        co2_urgency = min(co2_gap / max_gap, 1.0)  # 0.0 to 1.0

        # Component 2: Time urgency (running out of time)
        time_progress = year / total_years
        time_urgency = time_progress ** 2  # Accelerates: 0.25 at year 50%, 1.0 at year 100%

        # Component 3: Progress gap (falling behind roadmap)
        # Positive roadmap_gap = behind schedule = bad
        progress_urgency = min(max(roadmap_gap / max_gap, 0.0), 1.0)

        # Combined forward guidance (weighted average)
        forward_guidance = (
            0.4 * co2_urgency +      # 40% weight: current state
            0.3 * time_urgency +     # 30% weight: deadline pressure
            0.3 * progress_urgency   # 30% weight: falling behind
        )

        return forward_guidance

    def calculate_inflation_hedge_demand(self, global_inflation: float,
                                         inflation_target: float) -> float:
        """Calculate inflation hedge demand for XCR

        High ABSOLUTE inflation → MORE demand for XCR (real asset hedge)
        XCR is attractive in high-inflation environments regardless of target.

        In countries with 5% inflation, XCR is MORE attractive than in 2% countries,
        because it's a real asset backed by physical carbon removal.

        Returns: hedge demand multiplier (0.5 to 2.5)
        """
        # Use absolute inflation level with 2% as stable reference
        # (NOT relative to target - high inflation environments attract more capital)
        stable_reference = 0.02

        if global_inflation <= stable_reference:
            # Low inflation (0-2%): weak hedge demand (0.5-1.0)
            hedge_demand = 0.5 + 0.5 * (global_inflation / stable_reference)
        else:
            # High inflation (>2%): strong hedge demand (1.0-2.5)
            # Each 2% above 2% adds 0.5 to multiplier
            # Examples: 4% → 1.5x, 6% → 2.0x, 8%+ → 2.5x (capped)
            excess_inflation = global_inflation - stable_reference
            hedge_demand = 1.0 + min(excess_inflation / 0.04, 1.5)

        return hedge_demand

    def calculate_capital_demand(self, forward_guidance: float, inflation_hedge: float,
                                sentiment: float, xcr_supply: float, price_floor: float,
                                market_age_years: float = 0.0) -> float:
        """Calculate private capital demand for XCR

        Returns: USD amount of capital inflow/outflow this period
        """
        # Base demand: fraction of XCR market cap per year
        # Typical: 5-20% of market cap turns over annually in emerging assets
        base_turnover_rate = 0.10  # 10% of market cap per year

        # Market cap estimate (using floor as conservative price)
        # Floor a minimum to allow early-stage capital flows before supply exists.
        observed_market_cap = xcr_supply * price_floor
        market_cap = max(observed_market_cap, 1e9)

        # Demand drivers (all 0-1 or multiplicative)
        combined_attractiveness = forward_guidance * inflation_hedge * sentiment

        # Net capital flow
        # - combined_attractiveness > neutrality → inflow
        # - combined_attractiveness < neutrality → outflow
        # - Scale by market cap and turnover rate
        neutrality = self._neutrality_threshold(market_age_years)
        net_capital_flow = market_cap * base_turnover_rate * (combined_attractiveness - neutrality) * 2

        # Seed capital for early market formation (pre-liquidity bootstrap)
        seed_inflow = 0.0
        if observed_market_cap < self.seed_market_cap_usd:
            seed_inflow = self.seed_capital_usd * max(0.2, forward_guidance)
            net_capital_flow = max(net_capital_flow, seed_inflow)

        return net_capital_flow

    def update_capital_flows(self, current_co2: float, year: int, total_years: int,
                            roadmap_gap: float, global_inflation: float,
                            inflation_target: float, sentiment: float,
                            xcr_supply: float, price_floor: float,
                            market_age_years: float = 0.0) -> tuple[float, float, float]:
        """Update capital flows and return capital demand premium

        Returns: (net_capital_flow, capital_demand_premium, forward_guidance)
        """
        # Calculate forward guidance
        forward_guidance = self.calculate_forward_guidance(
            current_co2, year, total_years, roadmap_gap
        )

        # Calculate inflation hedge demand
        inflation_hedge = self.calculate_inflation_hedge_demand(
            global_inflation, inflation_target
        )

        # Calculate net capital flow (USD)
        net_capital_flow = self.calculate_capital_demand(
            forward_guidance, inflation_hedge, sentiment, xcr_supply, price_floor,
            market_age_years
        )

        # Track cumulative flows
        if net_capital_flow > 0:
            self.cumulative_capital_inflow += net_capital_flow
        else:
            self.cumulative_capital_outflow += abs(net_capital_flow)

        # Convert capital flow to price premium
        # More capital → higher price premium
        # Scale: $1B inflow on $10B market cap → ~10% price premium
        market_cap = xcr_supply * price_floor if xcr_supply > 0 else 1e9
        capital_intensity = net_capital_flow / market_cap if market_cap > 0 else 0

        # Price premium from capital (can be positive or negative)
        # Cap at ±50% to prevent extreme swings
        capital_demand_premium = price_floor * np.clip(capital_intensity, -0.5, 0.5)

        return net_capital_flow, capital_demand_premium, forward_guidance


class Auditor:
    """Auditor (MRV) - Verification and risk management"""

    def __init__(self, error_rate: float = 0.01):
        self.error_rate = error_rate
        self.total_xcr_burned = 0.0

    def audit_project(self, project: Project) -> str:
        """Stochastic verification with error rate

        Returns: "PASS" or "FAIL"
        """
        health_gap = max(0.0, 0.9 - project.health) / 0.9
        failure_probability = min(0.3, self.error_rate + (health_gap * 0.25))
        if np.random.rand() < failure_probability:
            return "FAIL"
        return "PASS"

    def verify_and_mint_xcr(self, project: Project) -> tuple[float, float]:
        """Verify project and return (XCR to mint, reversal_tonnes)"""
        audit_result = self.audit_project(project)

        if audit_result == "PASS":
            # Mint XCR: tonnes sequestered * R
            xcr_minted = project.annual_sequestration_tonnes * project.r_value
            return xcr_minted, 0.0
        else:
            # FAIL - clawback (burn previously minted XCR)
            clawback_amount = project.total_xcr_minted * 0.5  # Burn 50% of lifetime rewards
            self.total_xcr_burned += clawback_amount
            reversal_fraction = get_failure_reversal_fraction(project.channel)
            reversal_tonnes = project.total_sequestered_tonnes * reversal_fraction
            project.total_sequestered_tonnes = 0.0
            project.status = ProjectStatus.FAILED
            return -clawback_amount, reversal_tonnes  # Negative = burn


# ============================================================================
# MAIN SIMULATION
# ============================================================================

class GCR_ABM_Simulation:
    """Main simulation coordinating all agents

    Supports both rule-based and LLM-powered agents for realistic behavior modeling.
    """

    def __init__(self, years: int = 50, enable_audits: bool = True, price_floor: float = 100.0,
                 adoption_rate: float = 3.5, inflation_target: float = 0.02,
                 xcr_start_year: int = 0, years_to_full_capacity: int = 5,
                 cdr_learning_rate: float = 0.20, conventional_learning_rate: float = 0.12,
                 scale_full_deployment_gt: float = 45.0,
                 cdr_capacity_gt: float = 10.0,
                 # LLM agent parameters
                 llm_enabled: bool = False,
                 llm_model: str = "llama3.2",
                 llm_cache_mode: str = "read_write",
                 llm_agents: list = None):
        """
        Initialize GCR ABM simulation.

        Args:
            years: Simulation duration
            enable_audits: Enable project auditing
            price_floor: Initial XCR price floor (USD)
            adoption_rate: Countries joining per year
            inflation_target: Target inflation rate
            xcr_start_year: Year when XCR system starts
            years_to_full_capacity: Institutional ramp-up period
            cdr_learning_rate: CDR technology learning rate
            conventional_learning_rate: Conventional tech learning rate
            scale_full_deployment_gt: Full-scale deployment threshold for scale damping (Gt)
            cdr_capacity_gt: Annual CDR capacity cap (Gt/year)
            llm_enabled: Use LLM-powered agents (requires Ollama)
            llm_model: Ollama model name (llama3.2, mistral, etc.)
            llm_cache_mode: Cache mode (disabled, read_write, read_only, write_only)
            llm_agents: List of agents to use LLM for ['investor', 'capital', 'cea', 'central_bank']
        """
        self.years = years
        self.enable_audits = enable_audits
        self.price_floor = price_floor
        self.adoption_rate = adoption_rate  # Countries joining per year
        self.inflation_target = inflation_target  # Target inflation rate (default 2%)
        self.xcr_start_year = xcr_start_year  # Year when XCR system starts
        self.years_to_full_capacity = years_to_full_capacity  # Ramp-up period
        self.step = 0

        # LLM configuration
        self.llm_enabled = llm_enabled
        self.llm_model = llm_model
        self.llm_cache_mode = llm_cache_mode
        self.llm_agents = llm_agents or ['investor', 'capital', 'cea', 'central_bank']
        self.llm_engine = None

        # Global state
        self.co2_level = 420.0  # ppm
        self.global_inflation = 0.0  # Start at baseline; target guides corrections
        self.total_xcr_supply = 0.0
        self.carbon_cycle = CarbonCycle(initial_co2_ppm=self.co2_level)
        self.co2_level = self.carbon_cycle.co2_ppm  # Keep ppm aligned with carbon cycle state
        self.land_use_change_gtc = self.carbon_cycle.params.land_use_change_gtc  # Exogenous LUC emissions
        self.bau_carbon_cycle = CarbonCycle(initial_co2_ppm=self.co2_level, params=self.carbon_cycle.params)

        # BAU (Business As Usual) emissions - flow rate that peaks then declines
        # Real-world emissions: ~40 GtCO2/year (36 fossil + 4 land use) today
        # Convert to ppm change: 1 GtC ≈ 0.47 ppm, 1 GtCO2 = 1/3.67 GtC
        # So 40 GtCO2/year = (40/3.67) GtC/year × 0.47 ppm/GtC ≈ 5.12 ppm/year
        self.bau_emissions_gt_per_year = 40.0  # GtCO2/year constant emission flow
        self.bau_peak_year = 6  # Years to peak (~2030 if start ~2024)
        self.bau_growth_rate_pre_peak = 0.01  # 1% annual growth until peak
        self.bau_decline_start_year = 60  # Late-century population decline begins
        self.bau_post_peak_plateau_rate = 0.0  # Flat emissions until population decline
        self.bau_decline_rate_post_peak = -0.002  # 0.2% annual decline after population decline begins
        self.structural_conventional_capacity_tonnes = 0.0  # Installed structural mitigation (tonnes/year)

        # Expanded country pool (50 countries with varied characteristics)
        # Format: gdp_tril, base_cqe (as fraction of trillion), tier, region, active, adoption_year
        self.all_countries = {
            # Tier 1: High GDP economies
            "USA": {"gdp_tril": 27.0, "base_cqe": 0.05, "tier": 1, "region": "North America", "active": True, "adoption_year": 0, "projects": []},
            "China": {"gdp_tril": 18.0, "base_cqe": 0.034999999999999996, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Japan": {"gdp_tril": 4.2, "base_cqe": 0.009, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Germany": {"gdp_tril": 4.5, "base_cqe": 0.01, "tier": 1, "region": "Europe", "active": True, "adoption_year": 0, "projects": []},
            "UK": {"gdp_tril": 3.5, "base_cqe": 0.008, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "France": {"gdp_tril": 3.0, "base_cqe": 0.007000000000000001, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "India": {"gdp_tril": 3.7, "base_cqe": 0.006, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Italy": {"gdp_tril": 2.2, "base_cqe": 0.005, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Canada": {"gdp_tril": 2.1, "base_cqe": 0.005, "tier": 1, "region": "North America", "active": False, "adoption_year": None, "projects": []},
            "South Korea": {"gdp_tril": 1.7, "base_cqe": 0.004, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Australia": {"gdp_tril": 1.7, "base_cqe": 0.004, "tier": 1, "region": "Oceania", "active": False, "adoption_year": None, "projects": []},
            "Spain": {"gdp_tril": 1.6, "base_cqe": 0.0035000000000000005, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},

            # Tier 2: Medium GDP economies
            "Brazil": {"gdp_tril": 2.1, "base_cqe": 0.005, "tier": 2, "region": "South America", "active": True, "adoption_year": 0, "projects": []},
            "Mexico": {"gdp_tril": 1.5, "base_cqe": 0.003, "tier": 2, "region": "North America", "active": False, "adoption_year": None, "projects": []},
            "Indonesia": {"gdp_tril": 1.4, "base_cqe": 0.003, "tier": 2, "region": "Asia", "active": True, "adoption_year": 0, "projects": []},
            "Netherlands": {"gdp_tril": 1.1, "base_cqe": 0.0025, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Saudi Arabia": {"gdp_tril": 1.1, "base_cqe": 0.0025, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Turkey": {"gdp_tril": 1.0, "base_cqe": 0.002, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Switzerland": {"gdp_tril": 0.9, "base_cqe": 0.002, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Poland": {"gdp_tril": 0.8, "base_cqe": 0.0018, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Argentina": {"gdp_tril": 0.6, "base_cqe": 0.0015, "tier": 2, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Sweden": {"gdp_tril": 0.6, "base_cqe": 0.0015, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Belgium": {"gdp_tril": 0.6, "base_cqe": 0.0014, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Thailand": {"gdp_tril": 0.5, "base_cqe": 0.0012000000000000001, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Nigeria": {"gdp_tril": 0.5, "base_cqe": 0.001, "tier": 2, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Austria": {"gdp_tril": 0.5, "base_cqe": 0.0012000000000000001, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Norway": {"gdp_tril": 0.5, "base_cqe": 0.0012000000000000001, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "UAE": {"gdp_tril": 0.5, "base_cqe": 0.0012000000000000001, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Israel": {"gdp_tril": 0.5, "base_cqe": 0.0012000000000000001, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Singapore": {"gdp_tril": 0.5, "base_cqe": 0.0012000000000000001, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Malaysia": {"gdp_tril": 0.4, "base_cqe": 0.001, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Philippines": {"gdp_tril": 0.4, "base_cqe": 0.001, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "South Africa": {"gdp_tril": 0.4, "base_cqe": 0.001, "tier": 2, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Colombia": {"gdp_tril": 0.4, "base_cqe": 0.0009, "tier": 2, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Denmark": {"gdp_tril": 0.4, "base_cqe": 0.001, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},

            # Tier 3: Lower GDP / Developing economies
            "Kenya": {"gdp_tril": 0.13, "base_cqe": 0.00030000000000000003, "tier": 3, "region": "Africa", "active": True, "adoption_year": 0, "projects": []},
            "Vietnam": {"gdp_tril": 0.43, "base_cqe": 0.0009, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Bangladesh": {"gdp_tril": 0.46, "base_cqe": 0.0008, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Egypt": {"gdp_tril": 0.4, "base_cqe": 0.0008, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Pakistan": {"gdp_tril": 0.34, "base_cqe": 0.0007, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Chile": {"gdp_tril": 0.32, "base_cqe": 0.0007, "tier": 3, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Peru": {"gdp_tril": 0.26, "base_cqe": 0.0006000000000000001, "tier": 3, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Czech Republic": {"gdp_tril": 0.33, "base_cqe": 0.0007, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Romania": {"gdp_tril": 0.3, "base_cqe": 0.0006000000000000001, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "New Zealand": {"gdp_tril": 0.25, "base_cqe": 0.0006000000000000001, "tier": 3, "region": "Oceania", "active": False, "adoption_year": None, "projects": []},
            "Portugal": {"gdp_tril": 0.28, "base_cqe": 0.0006000000000000001, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Greece": {"gdp_tril": 0.24, "base_cqe": 0.0005, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Iraq": {"gdp_tril": 0.26, "base_cqe": 0.0005, "tier": 3, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Kazakhstan": {"gdp_tril": 0.22, "base_cqe": 0.0005, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Morocco": {"gdp_tril": 0.14, "base_cqe": 0.00030000000000000003, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Ethiopia": {"gdp_tril": 0.16, "base_cqe": 0.00030000000000000003, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Ghana": {"gdp_tril": 0.08, "base_cqe": 0.0002, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Tanzania": {"gdp_tril": 0.08, "base_cqe": 0.0002, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Uganda": {"gdp_tril": 0.05, "base_cqe": 0.0001, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
        }

        # Enhance countries with equity data (OECD status, historical emissions, XCR tracking)
        for country_name, country_data in self.all_countries.items():
            equity_data = COUNTRY_EQUITY_DATA.get(country_name, {})
            country_data["oecd"] = equity_data.get("oecd", False)
            country_data["historical_emissions_gtco2"] = equity_data.get("historical_emissions_gtco2", 0.0)
            country_data["xcr_earned"] = 0.0  # Track XCR earned from projects
            country_data["xcr_purchased_equiv"] = 0.0  # Track XCR equivalent purchased via CQE

        # Start with 5 founding countries active (USA, Germany, Brazil, Indonesia, Kenya)
        self.countries = {k: v for k, v in self.all_countries.items() if v["active"]}

        # Initialize LLM engine if enabled
        if self.llm_enabled:
            try:
                from llm_engine import LLMEngine, CacheMode
                cache_mode_map = {
                    'disabled': CacheMode.DISABLED,
                    'read_write': CacheMode.READ_WRITE,
                    'read_only': CacheMode.READ_ONLY,
                    'write_only': CacheMode.WRITE_ONLY
                }
                self.llm_engine = LLMEngine(
                    model=self.llm_model,
                    cache_mode=cache_mode_map.get(self.llm_cache_mode, CacheMode.READ_WRITE)
                )
                if not self.llm_engine.is_available:
                    print(f"Warning: Ollama not available. LLM agents will use rule-based fallback.")
            except ImportError as e:
                print(f"Warning: LLM engine not available ({e}). Using rule-based agents.")
                self.llm_engine = None
                self.llm_enabled = False

        # Initialize agents (LLM or rule-based)
        if self.llm_enabled and self.llm_engine:
            from llm_agents import (
                CEA_LLM, CentralBankAllianceLLM,
                InvestorMarketLLM, CapitalMarketLLM
            )

            # CEA agent
            if 'cea' in self.llm_agents:
                self.cea = CEA_LLM(
                    llm_engine=self.llm_engine,
                    target_co2_ppm=350.0,
                    initial_co2_ppm=420.0,
                    inflation_target=self.inflation_target
                )
            else:
                self.cea = CEA(target_co2_ppm=350.0, initial_co2_ppm=420.0, inflation_target=self.inflation_target)

            # Central Bank agent
            if 'central_bank' in self.llm_agents:
                self.central_bank = CentralBankAllianceLLM(
                    llm_engine=self.llm_engine,
                    countries=self.countries,
                    price_floor=price_floor
                )
            else:
                self.central_bank = CentralBankAlliance(self.countries, price_floor=price_floor)

            # Investor Market agent
            if 'investor' in self.llm_agents:
                self.investor_market = InvestorMarketLLM(
                    llm_engine=self.llm_engine,
                    price_floor=price_floor
                )
            else:
                self.investor_market = InvestorMarket(price_floor=price_floor)

            # Capital Market agent
            if 'capital' in self.llm_agents:
                self.capital_market = CapitalMarketLLM(
                    llm_engine=self.llm_engine
                )
            else:
                self.capital_market = CapitalMarket(initial_co2=420.0, target_co2=350.0)
        else:
            # Rule-based agents (default)
            self.cea = CEA(target_co2_ppm=350.0, initial_co2_ppm=420.0, inflation_target=self.inflation_target)
            self.central_bank = CentralBankAlliance(self.countries, price_floor=price_floor)
            self.investor_market = InvestorMarket(price_floor=price_floor)
            self.capital_market = CapitalMarket(initial_co2=420.0, target_co2=350.0)

        # ProjectsBroker and Auditor always rule-based
        self.projects_broker = ProjectsBroker(self.countries)
        # Allow learning-rate overrides for scenario tuning
        self.projects_broker.learning_rates[ChannelType.CDR] = cdr_learning_rate
        self.projects_broker.learning_rates[ChannelType.CONVENTIONAL] = conventional_learning_rate
        self.projects_broker.full_scale_deployment_gt = scale_full_deployment_gt
        self.projects_broker.max_capacity_gt_per_year[ChannelType.CDR] = cdr_capacity_gt
        self.auditor = Auditor(error_rate=0.01)

    def chaos_monkey(self):
        """Inject stochastic economic shocks

        Models external economic events (oil shocks, supply chain disruptions, etc.)
        that cause temporary inflation spikes.
        """
        # Large shocks are rare (major economic disruptions)
        if np.random.rand() < 0.05:  # 5% chance per year (was 10%)
            shock = np.random.uniform(0.005, 0.015)  # 0.5-1.5% (was 1-4%)
            self.global_inflation += shock
            print(f"[Year {self.step}] SHOCK: Inflation +{shock*100:.1f}%")

        # Normal economic noise around baseline (small variations)
        noise = np.random.normal(0, 0.002)  # ±0.2% typical variation
        self.global_inflation += noise

    def adopt_countries(self, current_year: int) -> List[str]:
        """Add new countries to GCR system based on adoption rate

        Returns list of newly adopted country names
        """
        # Get list of inactive countries
        inactive = {k: v for k, v in self.all_countries.items() if not v["active"]}

        if not inactive:
            return []  # All countries already adopted

        # Determine number to adopt this year (fractional adoption_rate handled probabilistically)
        num_to_adopt = int(self.adoption_rate)
        fractional = self.adoption_rate - num_to_adopt
        if np.random.rand() < fractional:
            num_to_adopt += 1

        num_to_adopt = min(num_to_adopt, len(inactive))

        if num_to_adopt == 0:
            return []

        # Weight adoption probability by GDP (larger economies more likely to join early)
        # But include randomness for diversity
        weights = []
        country_names = list(inactive.keys())
        for name in country_names:
            gdp_weight = inactive[name]["gdp_tril"] ** 0.5  # Square root to reduce dominance
            random_factor = np.random.uniform(0.5, 1.5)  # ±50% randomness
            weights.append(gdp_weight * random_factor)

        # Normalize weights
        weights = np.array(weights)
        weights = weights / weights.sum()

        # Select countries to adopt
        adopted_names = np.random.choice(country_names, size=num_to_adopt, replace=False, p=weights)

        # Mark as active and add to countries dict
        newly_adopted = []
        for name in adopted_names:
            self.all_countries[name]["active"] = True
            self.all_countries[name]["adoption_year"] = current_year
            self.countries[name] = self.all_countries[name]
            newly_adopted.append(name)
            # Note: CQE budget now calculated dynamically from private capital (15% ratio)
            print(f"[Year {current_year}] {name} joined GCR (GDP: ${self.all_countries[name]['gdp_tril']}T)")

        # CQE budget now updated in main simulation loop based on cumulative private capital

        return newly_adopted

    def get_capacity_multiplier(self, current_year: int) -> float:
        """Calculate system capacity based on institutional learning curve

        Returns value from 0.0 to 1.0 representing system capacity.
        Before XCR start year: 0.0 (system not active)
        During ramp-up: Linear progression from 0.0 to 1.0
        After ramp-up: 1.0 (full capacity)

        Args:
            current_year: Current simulation year

        Returns:
            Capacity multiplier (0.0 to 1.0)
        """
        if current_year < self.xcr_start_year:
            return 0.0  # System hasn't started yet

        years_since_start = current_year - self.xcr_start_year

        if years_since_start >= self.years_to_full_capacity:
            return 1.0  # Full capacity reached

        # Linear ramp from 0.0 to 1.0
        progress = years_since_start / self.years_to_full_capacity
        return progress

    def run_simulation(self):
        """Execute multi-agent simulation"""
        results = []
        bau_co2 = self.bau_carbon_cycle.co2_ppm  # BAU trajectory via carbon cycle

        for year in range(self.years):
            self.step = year

            # Capture prior-year CQE utilization before reset
            budget_utilization = (
                self.central_bank.annual_cqe_spent / self.central_bank.total_cqe_budget
                if self.central_bank.total_cqe_budget > 0 else 0.0
            )
            system_active = year >= self.xcr_start_year

            # Annual CQE budget reset
            if year != self.central_bank.current_budget_year:
                self.central_bank.annual_cqe_spent = 0.0
                self.central_bank.current_budget_year = year

            # 0. Get capacity multiplier for this year (institutional learning)
            capacity = self.get_capacity_multiplier(year)

            # 0a. Country adoption - new countries join GCR system
            # Apply capacity multiplier to adoption rate
            if capacity > 0:
                newly_adopted = self.adopt_countries(year)
            else:
                newly_adopted = []  # No adoption before XCR starts

            # 1. Inflation dynamics (only after GCR starts)
            if system_active:
                # Chaos monkey - stochastic shocks
                self.chaos_monkey()

                # Inflation correction toward target
                # Central banks actively manage inflation with interest rates
                inflation_gap = self.global_inflation - self.inflation_target
                correction_rate = 0.25  # 25% correction per year (was 10%)
                # Stronger correction when far from target
                if abs(inflation_gap) > 0.02:  # More than 2pp away
                    correction_rate = 0.4  # 40% when inflation problematic
                self.global_inflation -= inflation_gap * correction_rate
            else:
                # No GCR policy effects before the start year
                self.global_inflation = 0.0

            # 2. Update investor sentiment
            price_floor_prev = self.price_floor

            if system_active:
                self.investor_market.update_sentiment(
                    self.cea.warning_8to1_active,
                    self.global_inflation,
                    self.inflation_target,
                    self.co2_level,
                    self.cea.initial_co2_ppm
                )

            # 2b. Update capital market (private investors)
            # Calculate roadmap gap for forward guidance
            roadmap_target = self.cea.calculate_roadmap_target(year, self.years)
            roadmap_gap = self.co2_level - roadmap_target

            if system_active:
                market_age_years = year - self.xcr_start_year
                net_capital_flow, capital_demand_premium, forward_guidance = self.capital_market.update_capital_flows(
                    self.co2_level, year, self.years, roadmap_gap,
                    self.global_inflation, self.inflation_target,
                    self.investor_market.sentiment, self.total_xcr_supply,
                    self.price_floor, market_age_years
                )
            else:
                net_capital_flow, capital_demand_premium, forward_guidance = (0.0, 0.0, 0.0)

            # 2c. Calculate market price (sentiment + capital demand)
            if system_active:
                self.investor_market.calculate_price(capital_demand_premium)
            market_cap = self.total_xcr_supply * self.investor_market.market_price_xcr if system_active else 0.0

            # 2c2. Update CQE budget (5% of annual private capital inflow)
            if system_active:
                annual_private_inflow = max(net_capital_flow, 0.0)
                self.central_bank.update_cqe_budget(annual_private_inflow)

            # 3. CEA updates policy
            if system_active:
                self.cea.update_policy(
                    self.co2_level,
                    market_cap,
                    self.central_bank.total_cqe_budget,
                    self.global_inflation,
                    budget_utilization
                )

            # 3b. CEA adjusts price floor based on roadmap progress (only after start)
            if system_active:
                self.price_floor, revision_occurred = self.cea.adjust_price_floor(
                    self.co2_level,
                    self.price_floor,
                    year,
                    self.years,
                    current_inflation=self.global_inflation,
                    temperature_anomaly=self.carbon_cycle.temperature
                )
            else:
                revision_occurred = False
            price_floor_delta = self.price_floor - price_floor_prev
            # Update price floor in agents
            self.central_bank.price_floor_rcc = self.price_floor
            self.investor_market.price_floor = self.price_floor

            # 4. Projects broker initiates new projects
            # Only initiate projects if capacity > 0 (system active)
            if capacity > 0 and system_active:
                available_capital_usd = max(net_capital_flow, 0.0)
                structural_conventional_gt = self.structural_conventional_capacity_tonnes / 1e9
                remaining_conventional_need_gt = max(
                    0.0, self.bau_emissions_gt_per_year - structural_conventional_gt
                )
                land_use_change_gtco2 = (
                    self.land_use_change_gtc * self.carbon_cycle.params.gtco2_per_gtc
                )
                planned_avoided_deforestation_gt = self.projects_broker.get_planned_sequestration_rate(
                    ChannelType.AVOIDED_DEFORESTATION
                )
                remaining_luc_emissions_gt = max(
                    0.0, land_use_change_gtco2 - planned_avoided_deforestation_gt
                )
                self.projects_broker.initiate_projects(
                    self.investor_market.market_price_xcr,
                    self.price_floor,
                    self.cea,
                    year,
                    self.co2_level,  # Pass current CO2 for urgency calculation
                    self.global_inflation,
                    available_capital_usd,
                    self.cea.brake_factor,
                    residual_emissions_gt=remaining_conventional_need_gt,
                    residual_luc_emissions_gt=remaining_luc_emissions_gt
                )

            # 5. Step all projects (development progress, stochastic decay, retirement)
            climate_risk_multiplier = self.carbon_cycle.get_project_risk_multiplier()
            channel_risk_fn = self.carbon_cycle.get_channel_risk_multiplier
            reversal_tonnes_projects = self.projects_broker.step_projects(
                self.co2_level,
                self.global_inflation,
                climate_risk_multiplier=climate_risk_multiplier,
                channel_risk_fn=channel_risk_fn
            )

            # 6. Auditor verifies operational projects and mints XCR
            operational_projects = self.projects_broker.get_operational_projects()
            development_projects = [p for p in self.projects_broker.projects if p.status == ProjectStatus.DEVELOPMENT]
            failed_projects = [p for p in self.projects_broker.projects if p.status == ProjectStatus.FAILED]
            total_sequestration = 0.0
            cdr_sequestration = 0.0
            conventional_mitigation = 0.0
            xcr_minted_this_year = 0.0
            xcr_burned_this_year = 0.0  # Track burning separately
            cobenefit_pool = 0.0
            cobenefit_bonus_xcr = 0.0
            cobenefit_candidates = []
            cdr_sequestration_tonnes = 0.0
            conv_sequestration_tonnes = 0.0

            reversal_tonnes_audits = 0.0

            avoided_deforestation_tonnes = 0.0
            remaining_structural_tonnes = max(
                0.0,
                (self.bau_emissions_gt_per_year * 1e9) - self.structural_conventional_capacity_tonnes
            )
            land_use_change_gtco2 = self.land_use_change_gtc * self.carbon_cycle.params.gtco2_per_gtc
            remaining_luc_tonnes = max(0.0, land_use_change_gtco2 * 1e9)

            if capacity > 0:
                for project in operational_projects:
                    if self.enable_audits:
                        xcr_change_raw, reversal = self.auditor.verify_and_mint_xcr(project)
                        audit_passed = xcr_change_raw > 0
                    else:
                        audit_passed = True
                        xcr_change_raw = 0.0
                        reversal = 0.0

                    # Apply capacity multiplier and brake factor to XCR minting
                    # Capacity: institutional learning (0-100% over 5 years)
                    # Brake: CEA stability control (reduces when ratio > 10:1)
                    brake_factor = self.cea.brake_factor
                    reversal_tonnes_audits += reversal

                    credited_tonnes = 0.0
                    if audit_passed:
                        if project.channel == ChannelType.CDR:
                            credited_tonnes = project.annual_sequestration_tonnes
                        elif project.channel == ChannelType.CONVENTIONAL:
                            remaining_project_tonnes = max(
                                0.0,
                                project.annual_sequestration_tonnes - project.structural_credited_tonnes
                            )
                            credit = min(remaining_project_tonnes, remaining_structural_tonnes)
                            credited_tonnes = credit
                            if credit > 0:
                                project.structural_credited_tonnes += credit
                                self.structural_conventional_capacity_tonnes += credit
                                remaining_structural_tonnes -= credit
                        elif project.channel == ChannelType.AVOIDED_DEFORESTATION:
                            credit = min(project.annual_sequestration_tonnes, remaining_luc_tonnes)
                            credited_tonnes = credit
                            remaining_luc_tonnes -= credit
                            avoided_deforestation_tonnes += credit

                        xcr_change_raw = credited_tonnes * project.r_value

                    xcr_change_adjusted = xcr_change_raw * capacity * brake_factor

                    if audit_passed and xcr_change_raw > 0:
                        # Successful verification - MINT XCR (hold back a co-benefit pool slice)
                        pool_contribution = xcr_change_adjusted * self.projects_broker.cobenefit_pool_fraction
                        project_mint = xcr_change_adjusted - pool_contribution
                        xcr_minted_this_year += project_mint
                        total_sequestration += credited_tonnes
                        project.total_sequestered_tonnes += credited_tonnes
                        if project.channel == ChannelType.CDR:
                            cdr_sequestration += credited_tonnes
                            cdr_sequestration_tonnes += credited_tonnes
                        elif project.channel == ChannelType.CONVENTIONAL:
                            conventional_mitigation += credited_tonnes
                            conv_sequestration_tonnes += credited_tonnes
                        # Update cumulative deployment for learning curves
                        self.projects_broker.update_cumulative_deployment(
                            project.channel,
                            credited_tonnes
                        )
                        project.total_xcr_minted += project_mint
                        cobenefit_pool += pool_contribution
                        if project.co_benefit_score > 0:
                            cobenefit_candidates.append((project, project.co_benefit_score))

                        # Track XCR earned by country (use adjusted amount)
                        if project.country in self.countries:
                            self.countries[project.country]["xcr_earned"] += project_mint
                    elif not audit_passed:
                        # Failed audit - BURN XCR (negative value)
                        xcr_burned_this_year += abs(xcr_change_adjusted)  # Track as positive

                # Redistribute co-benefit pool across eligible projects (proportional to score)
                if cobenefit_pool > 0 and cobenefit_candidates:
                    total_score = sum(score for _, score in cobenefit_candidates)
                    if total_score > 0:
                        for project, score in cobenefit_candidates:
                            bonus = cobenefit_pool * (score / total_score)
                            xcr_minted_this_year += bonus
                            cobenefit_bonus_xcr += bonus
                            project.total_xcr_minted += bonus
                            if project.country in self.countries:
                                self.countries[project.country]["xcr_earned"] += bonus

            # Update XCR supply from minting and burning
            self.total_xcr_supply += xcr_minted_this_year - xcr_burned_this_year

            # 7. Central bank defends floor with CQE
            price_support, inflation_impact, xcr_purchased = self.central_bank.defend_floor(
                self.investor_market.market_price_xcr,
                self.total_xcr_supply,
                self.global_inflation,
                self.inflation_target,
                year
            )

            # Track XCR purchased by countries (distributed proportionally to CQE contributions)
            if xcr_purchased > 0:
                total_cqe = sum(c['base_cqe'] for c in self.countries.values())
                for country_name, country_data in self.countries.items():
                    country_share = country_data['base_cqe'] / total_cqe if total_cqe > 0 else 0
                    country_data['xcr_purchased_equiv'] += xcr_purchased * country_share

            # Apply price support and inflation impact
            if price_support > 0:
                # CQE buying pressure pushes price toward floor
                self.investor_market.market_price_xcr += price_support
                self.global_inflation += inflation_impact
                # Hard mean-reversion clamp toward target to avoid runaway CPI
                if self.global_inflation > self.inflation_target:
                    over_shoot = self.global_inflation - self.inflation_target
                    self.global_inflation -= over_shoot * 0.6  # Pull 60% back toward target
                    self.global_inflation = min(self.global_inflation, self.inflation_target * 1.5)

            # No hard clamp: floor can slip if CQE is unwilling or budget-limited

            # 8. Update climate state using carbon cycle (emissions, sinks, feedbacks)
            ppm_per_gtc = self.carbon_cycle.params.ppm_per_gtc
            gtc_per_gtco2 = 1 / self.carbon_cycle.params.gtco2_per_gtc
            bau_emissions_gtc = self.bau_emissions_gt_per_year * gtc_per_gtco2
            bau_increase_ppm = bau_emissions_gtc * ppm_per_gtc

            # Structural decarbonization reduces human emissions baseline
            structural_conventional_gt = self.structural_conventional_capacity_tonnes / 1e9
            human_emissions_gtco2 = max(
                0.0, self.bau_emissions_gt_per_year - structural_conventional_gt
            )
            actual_emissions_gtc = human_emissions_gtco2 * gtc_per_gtco2

            # CDR + co-benefits remove CO2 from stock
            removal_gtc = cdr_sequestration / 1e9 * gtc_per_gtco2

            reversal_tonnes_total = reversal_tonnes_projects + reversal_tonnes_audits
            reversal_gtc = reversal_tonnes_total / 1e9 * gtc_per_gtco2

            net_emissions_gtc = actual_emissions_gtc + reversal_gtc
            avoided_deforestation_gtc = avoided_deforestation_tonnes / 1e9 * gtc_per_gtco2
            land_use_change_gtc_effective = max(
                0.0, self.land_use_change_gtc - avoided_deforestation_gtc
            )

            climate_state = self.carbon_cycle.step(
                emissions_gtc=net_emissions_gtc,
                sequestration_gtc=removal_gtc,
                land_use_change_gtc=land_use_change_gtc_effective
            )
            self.co2_level = climate_state["CO2_ppm"]

            # BAU emissions peak then plateau, then decline late-century (population-driven)
            if year < self.bau_peak_year:
                bau_growth_rate = self.bau_growth_rate_pre_peak
            elif year < self.bau_decline_start_year:
                bau_growth_rate = self.bau_post_peak_plateau_rate
            else:
                bau_growth_rate = self.bau_decline_rate_post_peak

            self.bau_emissions_gt_per_year = max(
                0.0, self.bau_emissions_gt_per_year * (1 + bau_growth_rate)
            )

            # 9. Update BAU trajectory (no intervention scenario, with natural sinks)
            bau_climate = self.bau_carbon_cycle.step(
                emissions_gtc=bau_emissions_gtc,
                sequestration_gtc=0.0,
                land_use_change_gtc=self.land_use_change_gtc
            )
            bau_co2 = bau_climate["CO2_ppm"]

            # Calculate transparency metrics for this year
            # Technology costs (learning-adjusted)
            cdr_cost = self.projects_broker.calculate_marginal_cost(ChannelType.CDR)
            conv_cost = self.projects_broker.calculate_marginal_cost(ChannelType.CONVENTIONAL)

            # Cumulative deployment by channel (in GtCO2 for readability)
            cdr_cumulative = self.projects_broker.cumulative_deployment[ChannelType.CDR] / 1e9
            conv_cumulative = self.projects_broker.cumulative_deployment[ChannelType.CONVENTIONAL] / 1e9

            # Policy multipliers
            cdr_policy = self.cea.calculate_policy_r_multiplier(ChannelType.CDR, year)
            conv_policy = self.cea.calculate_policy_r_multiplier(ChannelType.CONVENTIONAL, year)

            # Effective R-values (base × policy)
            benchmark_cdr_cost = cdr_cost
            cdr_r_base, cdr_r_eff = self.cea.calculate_project_r_value(
                ChannelType.CDR, cdr_cost, benchmark_cdr_cost, year
            )
            conv_r_base, conv_r_eff = self.cea.calculate_project_r_value(
                ChannelType.CONVENTIONAL, conv_cost, benchmark_cdr_cost, year
            )

            # Profitability signals (market_price * R_eff * brake - cost)
            brake_factor = self.cea.brake_factor
            cdr_profit = (self.investor_market.market_price_xcr * cdr_r_eff * brake_factor) - cdr_cost if cdr_r_eff > 0 else 0
            conv_profit = (self.investor_market.market_price_xcr * conv_r_eff * brake_factor) - conv_cost if conv_r_eff > 0 else 0

            # Conventional capacity utilization
            conv_capacity_util = self.projects_broker.get_conventional_capacity_utilization(year)
            conv_capacity_available = self.projects_broker.is_conventional_capacity_available(year)
            conv_capacity_factor = self.projects_broker.get_conventional_capacity_factor(year)

            # Record results with expanded transparency columns
            results.append({
                # Original columns
                "Year": year,
                "CO2_ppm": self.co2_level,
                "BAU_CO2_ppm": bau_co2,
                "CO2_Avoided": bau_co2 - self.co2_level,
                "Inflation": self.global_inflation,
                "XCR_Supply": self.total_xcr_supply,
                "XCR_Minted": xcr_minted_this_year,
                "XCR_Burned_Annual": xcr_burned_this_year,
                "XCR_Burned_Cumulative": self.auditor.total_xcr_burned,
                "Cobenefit_Bonus_XCR": cobenefit_bonus_xcr,
                "Market_Price": self.investor_market.market_price_xcr,
                "Price_Floor": self.price_floor,
                "Sentiment": self.investor_market.sentiment,
                "Projects_Total": len(self.projects_broker.projects),
                "Projects_Operational": len(operational_projects),
                "Projects_Development": len(development_projects),
                "Projects_Failed": len(failed_projects),
                "Sequestration_Tonnes": total_sequestration,
                "CDR_Sequestration_Tonnes": cdr_sequestration_tonnes,
                "Conventional_Mitigation_Tonnes": conv_sequestration_tonnes,
                "Avoided_Deforestation_Tonnes": avoided_deforestation_tonnes,
                "Reversal_Tonnes": reversal_tonnes_total,
                "Human_Emissions_GtCO2": human_emissions_gtco2,
                "Conventional_Installed_GtCO2": structural_conventional_gt,
                "CEA_Warning": self.cea.warning_8to1_active,
                "CQE_Spent": self.central_bank.total_cqe_spent,
                "XCR_Purchased": xcr_purchased,
                "Active_Countries": len(self.countries),
                "CQE_Budget_Total": self.central_bank.total_cqe_budget,
                "Capacity": capacity,

                # Climate physics
                "Temperature_Anomaly": climate_state["Temperature_Anomaly"],
                "Ocean_Uptake_GtC": climate_state["Ocean_Uptake_GtC"],
                "Land_Uptake_GtC": climate_state["Land_Uptake_GtC"],
                "Airborne_Fraction": climate_state["Airborne_Fraction"],
                "Ocean_Sink_Capacity": climate_state["Ocean_Sink_Capacity"],
                "Land_Sink_Capacity": climate_state["Land_Sink_Capacity"],
                "Permafrost_Emissions_GtC": climate_state["Permafrost_Emissions_GtC"],
                "Fire_Emissions_GtC": climate_state["Fire_Emissions_GtC"],
                "Cumulative_Emissions_GtC": climate_state["Cumulative_Emissions_GtC"],
                "Climate_Risk_Multiplier": climate_state["Climate_Risk_Multiplier"],
                "C_Ocean_Surface_GtC": climate_state["C_Ocean_Surface_GtC"],
                "C_Land_GtC": climate_state["C_Land_GtC"],

                # NEW: Technology costs (learning-adjusted)
                "CDR_Cost_Per_Tonne": cdr_cost,
                "Conventional_Cost_Per_Tonne": conv_cost,

                # NEW: Cumulative deployment (learning curve progress)
                "CDR_Cumulative_GtCO2": cdr_cumulative,
                "Conventional_Cumulative_GtCO2": conv_cumulative,

                # NEW: Policy multipliers (channel prioritization)
                "CDR_Policy_Multiplier": cdr_policy,
                "Conventional_Policy_Multiplier": conv_policy,

                # NEW: Effective R-values (base × policy)
                "CDR_R_Base": cdr_r_base,
                "CDR_R_Effective": cdr_r_eff,
                "Conventional_R_Base": conv_r_base,
                "Conventional_R_Effective": conv_r_eff,

                # NEW: Profitability signals
                "CDR_Profitability": cdr_profit,
                "Conventional_Profitability": conv_profit,

                # NEW: Conventional capacity constraints
                "Conventional_Capacity_Utilization": conv_capacity_util,
                "Conventional_Capacity_Available": conv_capacity_available,
                "Conventional_Capacity_Factor": conv_capacity_factor,

                # NEW: Capital market flows (private investor demand)
                "Net_Capital_Flow": net_capital_flow,
                "Capital_Demand_Premium": capital_demand_premium,
                "Forward_Guidance": forward_guidance,
                "Capital_Inflow_Cumulative": self.capital_market.cumulative_capital_inflow,
                "Capital_Outflow_Cumulative": self.capital_market.cumulative_capital_outflow,

                # NEW: CEA brake and CQE budget tracking
                "CEA_Brake_Factor": self.cea.brake_factor,
                "Annual_CQE_Spent": self.central_bank.annual_cqe_spent,
                "Annual_CQE_Budget": self.central_bank.total_cqe_budget,
                "CQE_Budget_Utilization": (self.central_bank.annual_cqe_spent / self.central_bank.total_cqe_budget
                                           if self.central_bank.total_cqe_budget > 0 else 0.0)
            })

        return pd.DataFrame(results)

    def get_equity_summary(self) -> Dict:
        """Calculate equity flows between OECD and non-OECD countries

        Returns dict with:
        - oecd_earned: Total XCR earned by OECD countries
        - oecd_purchased: Total XCR purchased (via CQE) by OECD countries
        - non_oecd_earned: Total XCR earned by non-OECD countries
        - non_oecd_purchased: Total XCR purchased by non-OECD countries
        - net_transfer_to_south: Net XCR flow to non-OECD (positive = South gains)
        - country_details: List of (country, oecd, net_xcr, historical_emissions) tuples
        """
        oecd_earned = 0.0
        oecd_purchased = 0.0
        non_oecd_earned = 0.0
        non_oecd_purchased = 0.0
        country_details = []

        for country_name in self.all_countries.keys():
            country = self.all_countries[country_name]
            if not country["active"]:
                continue  # Only count active countries

            earned = country["xcr_earned"]
            purchased = country["xcr_purchased_equiv"]
            net_xcr = earned - purchased
            oecd = country["oecd"]
            hist_emissions = country["historical_emissions_gtco2"]

            if oecd:
                oecd_earned += earned
                oecd_purchased += purchased
            else:
                non_oecd_earned += earned
                non_oecd_purchased += purchased

            country_details.append({
                "country": country_name,
                "oecd": oecd,
                "xcr_earned": earned,
                "xcr_purchased": purchased,
                "net_xcr": net_xcr,
                "historical_emissions_gtco2": hist_emissions,
                "gdp_tril": country["gdp_tril"]
            })

        # Net transfer to South (positive = South benefits)
        oecd_net = oecd_earned - oecd_purchased
        non_oecd_net = non_oecd_earned - non_oecd_purchased
        net_transfer_to_south = non_oecd_net  # Positive = South gains XCR

        return {
            "oecd_earned": oecd_earned,
            "oecd_purchased": oecd_purchased,
            "oecd_net": oecd_net,
            "non_oecd_earned": non_oecd_earned,
            "non_oecd_purchased": non_oecd_purchased,
            "non_oecd_net": non_oecd_net,
            "net_transfer_to_south": net_transfer_to_south,
            "country_details": sorted(country_details, key=lambda x: abs(x["net_xcr"]), reverse=True)
        }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Initialize and run simulation
    sim = GCR_ABM_Simulation(years=50, enable_audits=True)
    df = sim.run_simulation()

    # Display results
    print("\n" + "="*80)
    print("GCR ABM SIMULATION RESULTS")
    print("="*80)
    print(f"\nFirst 10 years:")
    print(df.head(10).to_string(index=False))

    print(f"\n\nLast 10 years:")
    print(df.tail(10).to_string(index=False))

    print(f"\n\nFinal Summary:")
    print(f"  CO2 Reduction: {420.0 - df.iloc[-1]['CO2_ppm']:.2f} ppm")
    print(f"  Total Projects: {df.iloc[-1]['Projects_Total']:.0f}")
    print(f"    - Operational (delivering): {df.iloc[-1]['Projects_Operational']:.0f}")
    print(f"    - Development (not yet): {df.iloc[-1]['Projects_Development']:.0f}")
    print(f"    - Failed: {df.iloc[-1]['Projects_Failed']:.0f}")
    failure_rate = (df.iloc[-1]['Projects_Failed'] / df.iloc[-1]['Projects_Total']) * 100 if df.iloc[-1]['Projects_Total'] > 0 else 0
    print(f"  Failure Rate: {failure_rate:.1f}%")
    print(f"  Total XCR Supply: {df.iloc[-1]['XCR_Supply']:.2e}")
    print(f"  Total XCR Burned: {df.iloc[-1]['XCR_Burned_Cumulative']:.2e}")
    print(f"  Final Market Price: ${df.iloc[-1]['Market_Price']:.2f}")
    print(f"  Final Sentiment: {df.iloc[-1]['Sentiment']:.3f}")
    print(f"  Final Inflation: {df.iloc[-1]['Inflation']*100:.2f}%")

    # Equity Analysis
    equity = sim.get_equity_summary()
    print(f"\n\nClimate Equity & Wealth Transfer Analysis:")
    print("-"*80)
    print(f"OECD Countries (Global North):")
    print(f"  XCR Earned (from projects):    {equity['oecd_earned']:.2e}")
    print(f"  XCR Purchased (via CQE):       {equity['oecd_purchased']:.2e}")
    print(f"  Net Position:                  {equity['oecd_net']:.2e} ({'surplus' if equity['oecd_net'] > 0 else 'deficit'})")
    print(f"\nNon-OECD Countries (Global South):")
    print(f"  XCR Earned (from projects):    {equity['non_oecd_earned']:.2e}")
    print(f"  XCR Purchased (via CQE):       {equity['non_oecd_purchased']:.2e}")
    print(f"  Net Position:                  {equity['non_oecd_net']:.2e} ({'surplus' if equity['non_oecd_net'] > 0 else 'deficit'})")
    print(f"\nNet Wealth Transfer:")
    transfer_direction = "North → South" if equity['net_transfer_to_south'] > 0 else "South → North"
    print(f"  {abs(equity['net_transfer_to_south']):.2e} XCR ({transfer_direction})")
    print(f"  At ${df.iloc[-1]['Market_Price']:.2f}/XCR = ${abs(equity['net_transfer_to_south']) * df.iloc[-1]['Market_Price']:.2e} USD")
    print("-"*80)
    print("="*80)
