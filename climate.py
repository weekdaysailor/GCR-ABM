import math
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CarbonCycleParams:
    """Tunable parameters for the four-reservoir climate module."""

    ppm_per_gtc: float = 0.47  # 1 GtC -> 0.47 ppm
    gtco2_per_gtc: float = 3.67
    preindustrial_co2_ppm: float = 280.0
    preindustrial_gtc: float = 590.0
    target_co2_ppm: float = 350.0

    # Ocean carbon cycle
    k_ocean: float = 0.012  # Fraction of atmospheric disequilibrium absorbed per year
    k_mix: float = 0.01  # Surface-to-deep mixing rate
    beta_temp_coeff: float = 0.03  # 3% reduction per °C above reference
    beta_temp_ref: float = 1.0
    gamma_coeff: float = 0.0015  # Revelle factor sensitivity
    surface_ocean_eq_gtc: float = 1000.0
    deep_ocean_gtc: float = 37000.0

    # Land carbon cycle
    land_gtc: float = 2000.0
    k_land: float = 15.0
    forest_area_factor: float = 1.0
    respiration_base: float = 2.0
    respiration_q10: float = 2.0
    respiration_t_ref: float = 1.0
    fire_base: float = 0.5
    fire_alpha: float = 0.3
    fire_threshold: float = 1.5
    land_use_change_gtc: float = 1.0

    # Temperature response
    tcre: float = 0.45  # °C per 1000 GtC
    committed_max: float = 0.5
    committed_tau_years: float = 30.0
    baseline_temp_anomaly: float = 1.2
    initial_cumulative_emissions_gtc: float = 650.0

    # Feedbacks
    permafrost_vulnerable_gtc: float = 100.0
    permafrost_rate: float = 0.005
    permafrost_threshold: float = 1.5
    amoc_temp_threshold: float = 2.0
    amoc_max_reduction: float = 0.2  # 20% reduction at +4°C and above


class CarbonCycle:
    """Four-reservoir carbon cycle with temperature and feedbacks."""

    def __init__(
        self,
        initial_co2_ppm: float = 420.0,
        params: Optional[CarbonCycleParams] = None,
    ):
        self.params = params or CarbonCycleParams()

        # Carbon stocks (GtC)
        self.c_atm = self.ppm_to_gtc(initial_co2_ppm)
        self.c_ocean_surface = self.params.surface_ocean_eq_gtc
        self.c_ocean_deep = self.params.deep_ocean_gtc
        self.c_land = self.params.land_gtc
        self.c_permafrost_remaining = self.params.permafrost_vulnerable_gtc

        # Timekeeping
        self.years_elapsed = 0
        self.cumulative_emissions = self.params.initial_cumulative_emissions_gtc

        # Temperature offset to anchor to observed anomaly
        self._temperature_offset = 0.0
        base_temp = self._temperature_from_emissions(self.cumulative_emissions, 0.0)
        self._temperature_offset = self.params.baseline_temp_anomaly - base_temp
        self.temperature = self.params.baseline_temp_anomaly
        self.co2_ppm = initial_co2_ppm

        # Baseline sink capacities for degradation tracking
        self.baseline_ocean_uptake = self._calc_ocean_uptake(self.c_atm, self.temperature)
        self.baseline_land_uptake = self._calc_land_flux(self.temperature, self.params.land_use_change_gtc)["net"]
        self.baseline_land_uptake = max(self.baseline_land_uptake, 1e-6)  # Avoid divide-by-zero

        # Last-step diagnostics
        self.airborne_fraction = 0.0
        self.last_step: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # Helper conversions
    # ------------------------------------------------------------------ #
    def gtc_to_ppm(self, gtc: float) -> float:
        return gtc * self.params.ppm_per_gtc

    def ppm_to_gtc(self, ppm: float) -> float:
        return ppm / self.params.ppm_per_gtc

    # ------------------------------------------------------------------ #
    # Core physics
    # ------------------------------------------------------------------ #
    def _beta_temp(self, temperature: float) -> float:
        """Temperature sensitivity of ocean solubility."""
        beta = 1.0 - self.params.beta_temp_coeff * (temperature - self.params.beta_temp_ref)
        return max(beta, 0.0)

    def _gamma_revelle(self, c_atm: float) -> float:
        """Revelle factor response to higher atmospheric CO2."""
        delta_c = max(c_atm - self.params.preindustrial_gtc, 0.0)
        return 1.0 / (1.0 + self.params.gamma_coeff * delta_c)

    def _amoc_strength(self, temperature: float) -> float:
        """AMOC weakening reduces ocean uptake as temperature rises."""
        if temperature <= self.params.amoc_temp_threshold:
            return 1.0
        reduction = 0.1 * (temperature - self.params.amoc_temp_threshold)
        return max(1.0 - reduction, 1.0 - self.params.amoc_max_reduction)

    def _calc_ocean_uptake(self, c_atm: float, temperature: float) -> float:
        disequilibrium = max(c_atm - self.params.preindustrial_gtc, 0.0)
        beta = self._beta_temp(temperature)
        gamma = self._gamma_revelle(c_atm)
        amoc = self._amoc_strength(temperature)
        return disequilibrium * self.params.k_ocean * beta * gamma * amoc

    def _calc_mixing(self) -> float:
        """Surface-to-deep ocean mixing (positive = surface loses carbon)."""
        return self.params.k_mix * (self.c_ocean_surface - self.params.surface_ocean_eq_gtc)

    def _calc_land_flux(self, temperature: float, land_use_change_gtc: float) -> Dict[str, float]:
        """Calculate land sink components and net flux (positive = uptake)."""
        fertilization = (
            self.params.k_land
            * math.log(max(self.c_atm, 1.0) / self.params.preindustrial_gtc)
            * self.params.forest_area_factor
        )
        fertilization = max(fertilization, 0.0)

        respiration = self.params.respiration_base * (
            self.params.respiration_q10 ** ((temperature - self.params.respiration_t_ref) / 10.0)
        )

        fire = self.params.fire_base * (
            1.0 + self.params.fire_alpha * (max(0.0, temperature - self.params.fire_threshold) ** 2)
        )

        net = fertilization - respiration - fire - land_use_change_gtc
        return {
            "fertilization": fertilization,
            "respiration": respiration,
            "fire": fire,
            "net": net,
        }

    def _calc_permafrost(self, temperature: float) -> float:
        """Permafrost carbon release (positive = emission to atmosphere)."""
        if temperature < self.params.permafrost_threshold or self.c_permafrost_remaining <= 0:
            return 0.0
        release = (
            self.params.permafrost_rate
            * (temperature - self.params.permafrost_threshold)
            * self.c_permafrost_remaining
        )
        release = min(release, self.c_permafrost_remaining)
        self.c_permafrost_remaining -= release
        return release

    def _committed_warming(self, years_elapsed: float) -> float:
        """Delayed ocean heat uptake contribution."""
        return self.params.committed_max * (1.0 - math.exp(-years_elapsed / self.params.committed_tau_years))

    def _temperature_from_emissions(self, cumulative_emissions_gtc: float, years_elapsed: float) -> float:
        """Calculate temperature anomaly from cumulative emissions."""
        base = (self.params.tcre / 1000.0) * cumulative_emissions_gtc
        committed = self._committed_warming(years_elapsed)
        return base + committed + self._temperature_offset

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_project_risk_multiplier(self, temperature: Optional[float] = None) -> float:
        """Climate-dependent multiplier for project failure rates."""
        temp = temperature if temperature is not None else self.temperature
        if temp < 1.5:
            return 1.0
        if temp < 2.0:
            return 1.0 + 0.2 * (temp - 1.5)  # 1.0-1.1
        if temp < 3.0:
            return 1.1 + 0.3 * (temp - 2.0)  # 1.1-1.4
        return 1.4 + 0.5 * (temp - 3.0)  # 1.4+

    def get_channel_risk_multiplier(self, channel: str) -> float:
        """Channel-specific climate sensitivity (string to avoid import cycle)."""
        channel = channel.lower()
        if channel == "cobenefits":
            return 1.5
        if channel == "avoided_deforestation":
            return 1.4
        if channel == "conventional":
            return 1.2
        return 1.0  # CDR default

    def step(
        self,
        emissions_gtc: float,
        sequestration_gtc: float,
        land_use_change_gtc: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Advance the carbon cycle by one year.

        Args:
            emissions_gtc: Anthropogenic + reversal emissions to atmosphere (GtC/year)
            sequestration_gtc: Carbon removals (GtC/year), always treated as atmospheric drawdown
            land_use_change_gtc: Exogenous land use change emissions (GtC/year)
        Returns:
            Dictionary of state and flux diagnostics for this step.
        """
        emissions_gtc = max(emissions_gtc, 0.0)
        sequestration_gtc = max(sequestration_gtc, 0.0)
        luc = self.params.land_use_change_gtc if land_use_change_gtc is None else max(land_use_change_gtc, 0.0)
        total_emissions_for_metrics = emissions_gtc + luc

        self.years_elapsed += 1
        prev_c_atm = self.c_atm

        # Flux calculations
        f_ocean = self._calc_ocean_uptake(self.c_atm, self.temperature)
        f_mixing = self._calc_mixing()
        land_flux = self._calc_land_flux(self.temperature, luc)
        f_land_net = land_flux["net"]
        f_permafrost = self._calc_permafrost(self.temperature)

        # Guard against removing more carbon than available this step
        sink_total = max(f_ocean, 0.0) + max(f_land_net, 0.0) + sequestration_gtc
        max_sink = emissions_gtc + luc + f_permafrost + sequestration_gtc
        if sink_total > max_sink and sink_total > 0:
            scale = max_sink / sink_total
            f_ocean *= scale
            if f_land_net > 0:
                f_land_net *= scale

        # Reservoir updates
        self.c_ocean_surface = max(self.c_ocean_surface + f_ocean - f_mixing, 0.0)
        self.c_ocean_deep = max(self.c_ocean_deep + f_mixing, 0.0)
        self.c_land = max(self.c_land + f_land_net, 0.0)

        net_atm_change = emissions_gtc + f_permafrost - sequestration_gtc - f_ocean - f_land_net
        self.c_atm = max(self.c_atm + net_atm_change, 0.0)
        self.co2_ppm = self.gtc_to_ppm(self.c_atm)

        net_anthro = emissions_gtc + luc + f_permafrost - sequestration_gtc
        self.cumulative_emissions = max(self.cumulative_emissions + net_anthro, 0.0)

        self.temperature = self._temperature_from_emissions(self.cumulative_emissions, self.years_elapsed)

        # Diagnostics
        self.airborne_fraction = (
            (self.c_atm - prev_c_atm) / total_emissions_for_metrics if total_emissions_for_metrics > 0 else 0.0
        )
        ocean_capacity = f_ocean / self.baseline_ocean_uptake if self.baseline_ocean_uptake > 0 else 1.0
        land_capacity = f_land_net / self.baseline_land_uptake if self.baseline_land_uptake > 0 else 1.0

        self.last_step = {
            "Temperature_Anomaly": self.temperature,
            "Ocean_Uptake_GtC": f_ocean,
            "Land_Uptake_GtC": f_land_net,
            "Airborne_Fraction": self.airborne_fraction,
            "Ocean_Sink_Capacity": ocean_capacity,
            "Land_Sink_Capacity": land_capacity,
            "Permafrost_Emissions_GtC": f_permafrost,
            "Fire_Emissions_GtC": land_flux["fire"],
            "Cumulative_Emissions_GtC": self.cumulative_emissions,
            "Climate_Risk_Multiplier": self.get_project_risk_multiplier(self.temperature),
            "C_Ocean_Surface_GtC": self.c_ocean_surface,
            "C_Ocean_Deep_GtC": self.c_ocean_deep,
            "C_Land_GtC": self.c_land,
            "CO2_ppm": self.co2_ppm,
            "Net_Atmospheric_Change_GtC": net_atm_change,
        }
        return self.last_step
