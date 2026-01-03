import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
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
    r_value: float  # Assigned at creation based on cost-effectiveness
    status: ProjectStatus = ProjectStatus.DEVELOPMENT
    years_in_development: int = 0
    total_xcr_minted: float = 0.0
    health: float = 1.0  # 1.0 = healthy, decays over time with stochastic events

    def step(self):
        """Advance project by one year"""
        if self.status == ProjectStatus.DEVELOPMENT:
            self.years_in_development += 1
            if self.years_in_development >= self.development_years:
                self.status = ProjectStatus.OPERATIONAL
        elif self.status == ProjectStatus.OPERATIONAL:
            # Stochastic decay: natural failures (fires, leaks, tech failure)
            if np.random.rand() < 0.02:  # 2% annual failure rate
                self.health *= np.random.uniform(0.8, 0.95)

# ============================================================================
# AGENT CLASSES
# ============================================================================

class CEA:
    """Carbon Exchange Authority - The central governor"""

    def __init__(self, target_co2_ppm: float = 350.0, initial_co2_ppm: float = 420.0):
        self.target_co2_ppm = target_co2_ppm
        self.initial_co2_ppm = initial_co2_ppm
        self.roadmap_co2 = initial_co2_ppm  # Updated each year based on roadmap

        # Stability monitoring
        self.warning_8to1_active = False
        self.brake_10to1_active = False

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
                          year: int, total_years: int) -> tuple[float, bool]:
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

    def update_policy(self, current_co2_ppm: float, market_cap_xcr: float,
                     total_cqe_budget: float, global_inflation: float):
        """Update CEA policy based on system state

        Monitors stability ratio and issues warnings to investors.
        Actual control mechanisms:
        - Price floor adjustments (based on roadmap progress)
        - CQE sigmoid damping (central bank willingness to defend floor)
        - Investor sentiment response to warnings
        """
        # Stability Ratio monitoring
        ratio = market_cap_xcr / total_cqe_budget if total_cqe_budget > 0 else 0
        self.warning_8to1_active = ratio >= 8.0
        self.brake_10to1_active = ratio >= 10.0

    def calculate_project_r_value(self, channel: ChannelType,
                                  marginal_cost: float, price_floor: float) -> float:
        """Calculate R value for a project based on cost-effectiveness

        From Chen paper:
        - CDR (Channel 1): R = 1 (fixed)
        - Conventional (Channel 2): R = marginal_cost / price_floor
        - Co-benefits (Channel 3): R adjusted by co-benefit value
        """
        if channel == ChannelType.CDR:
            return 1.0
        elif channel == ChannelType.CONVENTIONAL:
            # R represents cost-effectiveness relative to CDR baseline
            r = marginal_cost / price_floor
            return max(0.1, r)  # Minimum R to prevent division issues
        else:  # COBENEFITS
            # Simplified: assume co-benefits reduce effective cost by 20%
            r = (marginal_cost * 0.8) / price_floor
            return max(0.1, r)


class CentralBankAlliance:
    """Central Bank Alliance - Price floor defenders via CQE"""

    def __init__(self, countries: Dict[str, Dict], price_floor: float = 100.0):
        self.countries = countries
        self.price_floor_rcc = price_floor
        self.total_cqe_budget = sum(c['base_cqe'] for c in countries.values()) * 1e12
        self.total_cqe_spent = 0.0  # Track total M0 created

    def defend_floor(self, market_price_xcr: float, total_xcr_supply: float,
                    global_inflation: float) -> tuple[float, float, float]:
        """Defend price floor using sigmoid-damped CQE

        Returns: (price_support, inflation_impact, xcr_purchased)
        """
        # Sigmoid damping: willingness decreases as inflation rises
        k = 12.0  # Sharpness of brake
        willingness = 1 / (1 + np.exp(k * (global_inflation - 0.03)))

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
            xcr_purchased = total_xcr_supply * intervention_strength * 0.01  # Buy up to 1% of supply
            fiat_created = xcr_purchased * self.price_floor_rcc
            self.total_cqe_spent += fiat_created

            # Inflation impact: proportional to money creation relative to budget
            # Damped by willingness
            inflation_impact = (fiat_created / self.total_cqe_budget) * 0.001 * willingness

            return price_support, inflation_impact, xcr_purchased

        return 0.0, 0.0, 0.0


class ProjectsBroker:
    """Projects & Broker - Manages portfolio of mitigation projects"""

    def __init__(self, countries: Dict[str, Dict]):
        self.countries = countries
        self.projects: List[Project] = []
        self.next_project_id = 1

        # Marginal cost curves by channel (simplified)
        self.base_costs = {
            ChannelType.CDR: 100.0,  # Starts at price floor
            ChannelType.CONVENTIONAL: 80.0,  # Initially cheaper
            ChannelType.COBENEFITS: 70.0  # Co-benefits reduce costs
        }

    def calculate_marginal_cost(self, channel: ChannelType) -> float:
        """Calculate current marginal cost (increases with deployment)"""
        # Count existing projects in this channel
        channel_projects = [p for p in self.projects if p.channel == channel]

        # Learning curve: costs decrease 5% per doubling of capacity
        # But also resource depletion: costs increase with number of projects
        base = self.base_costs[channel]
        count = len(channel_projects)

        # Simplified: small increase per project
        marginal_cost = base * (1 + 0.02 * count)
        return marginal_cost

    def initiate_projects(self, market_price_xcr: float, price_floor: float, cea: CEA, current_year: int):
        """Initiate new projects where economics are favorable

        Project starts when: (price_floor / R) >= marginal_cost
        Which means: price_floor >= marginal_cost * R
        Or equivalently: XCR revenue covers costs
        """
        for channel in ChannelType:
            marginal_cost = self.calculate_marginal_cost(channel)
            r_value = cea.calculate_project_r_value(channel, marginal_cost, price_floor)

            # Economics check: revenue per tonne = price / R
            revenue_per_tonne = market_price_xcr / r_value

            if revenue_per_tonne >= marginal_cost:
                # Profitable - initiate project
                # Dynamically select country based on channel type and active countries
                active_countries = list(self.countries.keys())

                if not active_countries:
                    continue  # No active countries yet

                # Prefer certain regions/tiers for each channel
                if channel == ChannelType.CDR:
                    # CDR: Prefer tropical/developing countries with land
                    preferred = [c for c in active_countries
                                if self.countries[c].get('region') in ['South America', 'Africa', 'Asia']]
                    country_pool = preferred if preferred else active_countries
                elif channel == ChannelType.CONVENTIONAL:
                    # Conventional: Prefer developed economies with infrastructure
                    preferred = [c for c in active_countries
                                if self.countries[c].get('tier') == 1]
                    country_pool = preferred if preferred else active_countries
                else:  # COBENEFITS
                    # Co-benefits: Prefer developing countries (ecosystem restoration)
                    preferred = [c for c in active_countries
                                if self.countries[c].get('tier') in [2, 3]]
                    country_pool = preferred if preferred else active_countries

                country = np.random.choice(country_pool)

                # Project parameters
                dev_years = np.random.randint(2, 5)  # 2-4 years development
                annual_seq = np.random.uniform(1e5, 1e6)  # 100k-1M tonnes/year

                project = Project(
                    id=f"P{self.next_project_id:04d}",
                    channel=channel,
                    country=country,
                    start_year=current_year,
                    development_years=dev_years,
                    annual_sequestration_tonnes=annual_seq,
                    marginal_cost_per_tonne=marginal_cost,
                    r_value=r_value
                )

                self.projects.append(project)
                self.countries[country]['projects'].append(project.id)
                self.next_project_id += 1

    def step_projects(self):
        """Advance all projects by one year"""
        for project in self.projects:
            if project.status != ProjectStatus.FAILED:
                project.step()

    def get_operational_projects(self) -> List[Project]:
        """Return list of operational projects ready for verification"""
        return [p for p in self.projects if p.status == ProjectStatus.OPERATIONAL]


class InvestorMarket:
    """Investor Market - Aggregate sentiment and price discovery"""

    def __init__(self, price_floor: float = 100.0):
        self.sentiment = 1.0  # 0.0 (panic) to 1.0 (full trust)
        self.price_floor = price_floor
        self.market_price_xcr = price_floor + (50 * self.sentiment)

    def update_sentiment(self, cea_warning: bool, global_inflation: float):
        """Update investor sentiment based on system state"""
        # Decay factors
        if cea_warning:
            self.sentiment *= 0.9  # Linear decay on warning

        if global_inflation > 0.04:
            self.sentiment *= 0.85  # Exponential decay on high inflation

        # Recovery if stable
        if not cea_warning and global_inflation <= 0.03:
            self.sentiment = min(1.0, self.sentiment + 0.05)

        # Price discovery: Base price affected by sentiment
        # Can drop below floor if sentiment is very low
        base_price = self.price_floor * (0.5 + 0.5 * self.sentiment)  # 50%-100% of floor
        sentiment_premium = 50 * self.sentiment
        self.market_price_xcr = base_price + sentiment_premium


class Auditor:
    """Auditor (MRV) - Verification and risk management"""

    def __init__(self, error_rate: float = 0.02):
        self.error_rate = error_rate
        self.total_xcr_burned = 0.0

    def audit_project(self, project: Project) -> str:
        """Stochastic verification with error rate

        Returns: "PASS" or "FAIL"
        """
        if project.health < 0.9:
            # Unhealthy project - likely to fail audit
            if np.random.rand() > self.error_rate:
                return "FAIL"
        return "PASS"

    def verify_and_mint_xcr(self, project: Project) -> float:
        """Verify project and return XCR to mint (or 0 if failed)

        Returns: XCR minted (fresh supply)
        """
        audit_result = self.audit_project(project)

        if audit_result == "PASS":
            # Mint XCR: tonnes sequestered / R
            xcr_minted = project.annual_sequestration_tonnes / project.r_value
            project.total_xcr_minted += xcr_minted
            return xcr_minted
        else:
            # FAIL - clawback (burn previously minted XCR)
            clawback_amount = project.total_xcr_minted * 0.5  # Burn 50% of lifetime rewards
            self.total_xcr_burned += clawback_amount
            project.status = ProjectStatus.FAILED
            return -clawback_amount  # Negative = burn


# ============================================================================
# MAIN SIMULATION
# ============================================================================

class GCR_ABM_Simulation:
    """Main simulation coordinating all agents"""

    def __init__(self, years: int = 50, enable_audits: bool = True, price_floor: float = 100.0,
                 adoption_rate: float = 3.5, inflation_target: float = 0.02):
        self.years = years
        self.enable_audits = enable_audits
        self.price_floor = price_floor
        self.adoption_rate = adoption_rate  # Countries joining per year
        self.inflation_target = inflation_target  # Target inflation rate (default 2%)
        self.step = 0

        # Global state
        self.co2_level = 420.0  # ppm
        self.global_inflation = inflation_target  # Start at target
        self.total_xcr_supply = 0.0

        # BAU (Business As Usual) trajectory - no GCR intervention
        self.bau_co2_growth_rate = 0.005  # 0.5% annual CO2 growth

        # Expanded country pool (50 countries with varied characteristics)
        # Format: gdp_tril, base_cqe (as fraction of trillion), tier, region, active, adoption_year
        self.all_countries = {
            # Tier 1: High GDP economies
            "USA": {"gdp_tril": 27.0, "base_cqe": 0.5, "tier": 1, "region": "North America", "active": True, "adoption_year": 0, "projects": []},
            "China": {"gdp_tril": 18.0, "base_cqe": 0.35, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Japan": {"gdp_tril": 4.2, "base_cqe": 0.09, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Germany": {"gdp_tril": 4.5, "base_cqe": 0.1, "tier": 1, "region": "Europe", "active": True, "adoption_year": 0, "projects": []},
            "UK": {"gdp_tril": 3.5, "base_cqe": 0.08, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "France": {"gdp_tril": 3.0, "base_cqe": 0.07, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "India": {"gdp_tril": 3.7, "base_cqe": 0.06, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Italy": {"gdp_tril": 2.2, "base_cqe": 0.05, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Canada": {"gdp_tril": 2.1, "base_cqe": 0.05, "tier": 1, "region": "North America", "active": False, "adoption_year": None, "projects": []},
            "South Korea": {"gdp_tril": 1.7, "base_cqe": 0.04, "tier": 1, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Australia": {"gdp_tril": 1.7, "base_cqe": 0.04, "tier": 1, "region": "Oceania", "active": False, "adoption_year": None, "projects": []},
            "Spain": {"gdp_tril": 1.6, "base_cqe": 0.035, "tier": 1, "region": "Europe", "active": False, "adoption_year": None, "projects": []},

            # Tier 2: Medium GDP economies
            "Brazil": {"gdp_tril": 2.1, "base_cqe": 0.05, "tier": 2, "region": "South America", "active": True, "adoption_year": 0, "projects": []},
            "Mexico": {"gdp_tril": 1.5, "base_cqe": 0.03, "tier": 2, "region": "North America", "active": False, "adoption_year": None, "projects": []},
            "Indonesia": {"gdp_tril": 1.4, "base_cqe": 0.03, "tier": 2, "region": "Asia", "active": True, "adoption_year": 0, "projects": []},
            "Netherlands": {"gdp_tril": 1.1, "base_cqe": 0.025, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Saudi Arabia": {"gdp_tril": 1.1, "base_cqe": 0.025, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Turkey": {"gdp_tril": 1.0, "base_cqe": 0.02, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Switzerland": {"gdp_tril": 0.9, "base_cqe": 0.02, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Poland": {"gdp_tril": 0.8, "base_cqe": 0.018, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Argentina": {"gdp_tril": 0.6, "base_cqe": 0.015, "tier": 2, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Sweden": {"gdp_tril": 0.6, "base_cqe": 0.015, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Belgium": {"gdp_tril": 0.6, "base_cqe": 0.014, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Thailand": {"gdp_tril": 0.5, "base_cqe": 0.012, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Nigeria": {"gdp_tril": 0.5, "base_cqe": 0.01, "tier": 2, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Austria": {"gdp_tril": 0.5, "base_cqe": 0.012, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Norway": {"gdp_tril": 0.5, "base_cqe": 0.012, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "UAE": {"gdp_tril": 0.5, "base_cqe": 0.012, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Israel": {"gdp_tril": 0.5, "base_cqe": 0.012, "tier": 2, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Singapore": {"gdp_tril": 0.5, "base_cqe": 0.012, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Malaysia": {"gdp_tril": 0.4, "base_cqe": 0.01, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Philippines": {"gdp_tril": 0.4, "base_cqe": 0.01, "tier": 2, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "South Africa": {"gdp_tril": 0.4, "base_cqe": 0.01, "tier": 2, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Colombia": {"gdp_tril": 0.4, "base_cqe": 0.009, "tier": 2, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Denmark": {"gdp_tril": 0.4, "base_cqe": 0.01, "tier": 2, "region": "Europe", "active": False, "adoption_year": None, "projects": []},

            # Tier 3: Lower GDP / Developing economies
            "Kenya": {"gdp_tril": 0.13, "base_cqe": 0.003, "tier": 3, "region": "Africa", "active": True, "adoption_year": 0, "projects": []},
            "Vietnam": {"gdp_tril": 0.43, "base_cqe": 0.009, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Bangladesh": {"gdp_tril": 0.46, "base_cqe": 0.008, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Egypt": {"gdp_tril": 0.4, "base_cqe": 0.008, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Pakistan": {"gdp_tril": 0.34, "base_cqe": 0.007, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Chile": {"gdp_tril": 0.32, "base_cqe": 0.007, "tier": 3, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Peru": {"gdp_tril": 0.26, "base_cqe": 0.006, "tier": 3, "region": "South America", "active": False, "adoption_year": None, "projects": []},
            "Czech Republic": {"gdp_tril": 0.33, "base_cqe": 0.007, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Romania": {"gdp_tril": 0.3, "base_cqe": 0.006, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "New Zealand": {"gdp_tril": 0.25, "base_cqe": 0.006, "tier": 3, "region": "Oceania", "active": False, "adoption_year": None, "projects": []},
            "Portugal": {"gdp_tril": 0.28, "base_cqe": 0.006, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Greece": {"gdp_tril": 0.24, "base_cqe": 0.005, "tier": 3, "region": "Europe", "active": False, "adoption_year": None, "projects": []},
            "Iraq": {"gdp_tril": 0.26, "base_cqe": 0.005, "tier": 3, "region": "Middle East", "active": False, "adoption_year": None, "projects": []},
            "Kazakhstan": {"gdp_tril": 0.22, "base_cqe": 0.005, "tier": 3, "region": "Asia", "active": False, "adoption_year": None, "projects": []},
            "Morocco": {"gdp_tril": 0.14, "base_cqe": 0.003, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Ethiopia": {"gdp_tril": 0.16, "base_cqe": 0.003, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Ghana": {"gdp_tril": 0.08, "base_cqe": 0.002, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Tanzania": {"gdp_tril": 0.08, "base_cqe": 0.002, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
            "Uganda": {"gdp_tril": 0.05, "base_cqe": 0.001, "tier": 3, "region": "Africa", "active": False, "adoption_year": None, "projects": []},
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

        # Initialize agents
        self.cea = CEA(target_co2_ppm=350.0, initial_co2_ppm=420.0)
        self.central_bank = CentralBankAlliance(self.countries, price_floor=price_floor)
        self.projects_broker = ProjectsBroker(self.countries)
        self.investor_market = InvestorMarket(price_floor=price_floor)
        self.auditor = Auditor(error_rate=0.02)

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
            print(f"[Year {current_year}] {name} joined GCR (GDP: ${self.all_countries[name]['gdp_tril']}T, CQE: ${self.all_countries[name]['base_cqe']}T)")

        # Recalculate CQE budget in CentralBankAlliance
        self.central_bank.total_cqe_budget = sum(c['base_cqe'] for c in self.countries.values()) * 1e12

        return newly_adopted

    def run_simulation(self):
        """Execute multi-agent simulation"""
        results = []
        bau_co2 = 420.0  # BAU starting point

        for year in range(self.years):
            self.step = year

            # 0. Country adoption - new countries join GCR system
            newly_adopted = self.adopt_countries(year)

            # 1. Chaos monkey - stochastic shocks
            self.chaos_monkey()

            # 1b. Inflation correction toward 2% target
            # Central banks actively manage inflation with interest rates
            inflation_gap = self.global_inflation - self.inflation_target
            correction_rate = 0.25  # 25% correction per year (was 10%)
            # Stronger correction when far from target
            if abs(inflation_gap) > 0.02:  # More than 2pp away
                correction_rate = 0.4  # 40% when inflation problematic
            self.global_inflation -= inflation_gap * correction_rate

            # 2. Update investor sentiment
            self.investor_market.update_sentiment(
                self.cea.warning_8to1_active,
                self.global_inflation
            )

            # 3. CEA updates policy
            market_cap = self.total_xcr_supply * self.investor_market.market_price_xcr
            self.cea.update_policy(
                self.co2_level,
                market_cap,
                self.central_bank.total_cqe_budget,
                self.global_inflation
            )

            # 3b. CEA adjusts price floor based on roadmap progress
            # Periodic revisions (every 5 years) with locked-in guidance between
            self.price_floor, revision_occurred = self.cea.adjust_price_floor(
                self.co2_level,
                self.price_floor,
                year,
                self.years
            )
            # Update price floor in agents
            self.central_bank.price_floor_rcc = self.price_floor
            self.investor_market.price_floor = self.price_floor

            # 4. Projects broker initiates new projects
            self.projects_broker.initiate_projects(
                self.investor_market.market_price_xcr,
                self.price_floor,
                self.cea,
                year
            )

            # 5. Step all projects (development progress, stochastic decay)
            self.projects_broker.step_projects()

            # 6. Auditor verifies operational projects and mints XCR
            operational_projects = self.projects_broker.get_operational_projects()
            total_sequestration = 0.0
            xcr_minted_this_year = 0.0

            if self.enable_audits:
                for project in operational_projects:
                    xcr_change = self.auditor.verify_and_mint_xcr(project)
                    xcr_minted_this_year += xcr_change

                    if xcr_change > 0:
                        # Successful verification
                        total_sequestration += project.annual_sequestration_tonnes
                        # Track XCR earned by country
                        if project.country in self.countries:
                            self.countries[project.country]["xcr_earned"] += xcr_change

            # Update XCR supply from minting
            self.total_xcr_supply += xcr_minted_this_year

            # 7. Central bank defends floor with CQE
            price_support, inflation_impact, xcr_purchased = self.central_bank.defend_floor(
                self.investor_market.market_price_xcr,
                self.total_xcr_supply,
                self.global_inflation
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

            # 8. Update CO2 levels based on sequestration
            # Convert tonnes to ppm (simplified: 1 GtC ≈ 0.47 ppm)
            sequestration_gtc = total_sequestration / 1e9 / 3.67  # tonnes CO2 -> GtC
            co2_reduction_ppm = sequestration_gtc * 0.47
            self.co2_level -= co2_reduction_ppm

            # 9. Update BAU trajectory (no intervention scenario)
            bau_co2 *= (1 + self.bau_co2_growth_rate)

            # Record results
            results.append({
                "Year": year,
                "CO2_ppm": self.co2_level,
                "BAU_CO2_ppm": bau_co2,
                "CO2_Avoided": bau_co2 - self.co2_level,
                "Inflation": self.global_inflation,
                "XCR_Supply": self.total_xcr_supply,
                "XCR_Minted": xcr_minted_this_year,
                "XCR_Burned": self.auditor.total_xcr_burned,
                "Market_Price": self.investor_market.market_price_xcr,
                "Price_Floor": self.price_floor,
                "Sentiment": self.investor_market.sentiment,
                "Projects_Total": len(self.projects_broker.projects),
                "Projects_Operational": len(operational_projects),
                "Sequestration_Tonnes": total_sequestration,
                "CEA_Warning": self.cea.warning_8to1_active,
                "CQE_Spent": self.central_bank.total_cqe_spent,
                "Active_Countries": len(self.countries),
                "CQE_Budget_Total": self.central_bank.total_cqe_budget
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
    print(f"  Operational Projects: {df.iloc[-1]['Projects_Operational']:.0f}")
    print(f"  Total XCR Supply: {df.iloc[-1]['XCR_Supply']:.2e}")
    print(f"  Total XCR Burned: {df.iloc[-1]['XCR_Burned']:.2e}")
    print(f"  Final Market Price: ${df.iloc[-1]['Market_Price']:.2f}")
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
