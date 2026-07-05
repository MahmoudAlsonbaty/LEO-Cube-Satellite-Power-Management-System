#!/usr/bin/env python3
"""
Cold-season repeated-eclipse analytical stress model.

This model compares a simplified Quetzal-derived no-charge-temperature-gate
baseline against the tuned Aether-Albedo-1 adaptive controller under identical
orbit, thermal, solar, SOC, and battery-capacity assumptions.

It is intentionally not an average year-round performance claim. The scenario
set emphasizes repeated cold eclipses because that is where heater pulsing,
payload scheduling, and charge-temperature gating are expected to matter.
"""

from __future__ import annotations

import argparse
import csv
import html
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from albedo_cubesat_case_study import ALBEDO_PROFILE, USABLE_SOLAR_EFFICIENCY
from multi_cubesat_logic_benchmark import (
    ARCHITECTURE_BY_NAME,
    LOG_DIR,
    Architecture,
    Latches,
    Sample,
    SatelliteProfile,
    TestCase,
    adaptive_payload_duty,
    baseline_payload_duty,
    event_overrides,
    heater_allowed,
    heater_duty_fraction,
    orbit_phase,
    select_adaptive_mode,
    simulate,
    update_latches,
)


YEAR_DAYS = 365.25
OUR_ARCHITECTURE_NAME = "improved_firmware"
FIG_DIR = LOG_DIR.parent / "figures"
NOMINAL_YEAR_SCENARIO = "warm_nominal_year"
REALISTIC_COLD_SEASON_YEAR = "realistic_cold_season_year"
STRESS_COLD_SEASON_YEAR = "cold_long_eclipse_stress_year"
COLD_SEASON_TRANSITION_DAYS = 5
COLD_SEASON_CORE_DAYS = 35
COLD_SEASON_RECOVERY_DAYS = 5
COLD_SEASON_START_DAYS = (35, 215)


@dataclass(frozen=True)
class AnalyticalScenario:
    name: str
    duration_days: float
    orbit_min: float
    eclipse_min: float
    initial_soc_pct: float
    initial_battery_temp_c: float
    sun_temp_c: float
    eclipse_temp_c: float
    note: str
    force_events: bool = False


@dataclass(frozen=True)
class AnalyticalRow:
    scenario: str
    design: str
    years: float
    duration_days: float
    orbit_min: float
    eclipse_min: float
    initial_soc_pct: float
    initial_battery_temp_c: float
    sun_temp_c: float
    eclipse_temp_c: float
    average_power_w: float
    peak_power_w: float
    pattern_consumed_energy_wh: float
    pattern_usable_solar_generated_wh: float
    net_wh_per_day: float
    projected_consumed_energy_kwh: float
    projected_usable_solar_generated_kwh: float
    heater_energy_wh_per_pattern: float
    projected_heater_energy_kwh: float
    payload_energy_wh_per_pattern: float
    projected_payload_energy_kwh: float
    data_units: float
    data_retention_pct: float
    min_soc_pct: float
    projected_equivalent_full_cycles: float
    low_soc_exposure_days: float
    critical_soc_exposure_days: float
    cold_charge_exposure_hours: float
    cold_charge_energy_wh: float
    cold_charge_severity_degree_hours: float
    estimated_capacity_remaining_pct: float
    sustainable_energy_balance: int
    days_to_depletion_if_power_negative: float
    dominant_mode: str
    mode_breakdown_pct: str
    interpretation: str


@dataclass(frozen=True)
class DesignAssumptionRow:
    design: str
    heater_power_w: float
    payload_policy: str
    heater_policy: str
    charge_policy: str
    note: str


@dataclass(frozen=True)
class ComparisonRow:
    scenario: str
    years: float
    baseline_design: str
    adaptive_design: str
    baseline_average_power_w: float
    adaptive_average_power_w: float
    average_power_reduction_pct: float
    baseline_consumed_energy_kwh: float
    adaptive_consumed_energy_kwh: float
    consumed_energy_reduction_pct: float
    baseline_heater_energy_kwh: float
    adaptive_heater_energy_kwh: float
    heater_energy_reduction_pct: float
    adaptive_data_retention_pct: float
    baseline_min_soc_pct: float
    adaptive_min_soc_pct: float
    baseline_cold_charge_hours: float
    adaptive_cold_charge_hours: float
    baseline_capacity_remaining_pct: float
    adaptive_capacity_remaining_pct: float
    capacity_proxy_delta_pct: float
    baseline_days_to_depletion: float
    adaptive_days_to_depletion: float
    interpretation: str


@dataclass(frozen=True)
class ScenarioAssumptionRow:
    scenario: str
    duration_days: float
    orbit_min: float
    eclipse_min: float
    initial_soc_pct: float
    initial_battery_temp_c: float
    sun_temp_c: float
    eclipse_temp_c: float
    note: str


def quetzal_baseline_profile() -> SatelliteProfile:
    return replace(
        ALBEDO_PROFILE,
        name="Quetzal-derived no-charge-temp-gate baseline",
        heater_w=0.898,
        source_notes=(
            "Simplified Quetzal-scale 1U comparison baseline. It uses the same "
            "14.8 Wh battery, 2.37 W solar input, 0.66370 W heater-off bus load, "
            "and 0.123 W albedo payload used by the project comparison, but keeps "
            "the Quetzal-style 0.898 W heater. The baseline mode intentionally "
            "does not include charge-temperature gating, so it is not a claim "
            "about real Quetzal flight behavior."
        ),
    )


def quetzal_style_protected_profile() -> SatelliteProfile:
    return replace(
        ALBEDO_PROFILE,
        name="Quetzal-style protected heater baseline",
        heater_w=0.898,
        source_notes=(
            "Modest reconstructed Quetzal-style baseline. It keeps the same "
            "Quetzal-scale bus, battery, solar, payload, and 0.898 W heater, "
            "but adds a source-backed heater-protected charge assumption. The heater "
            "turns on at 3 C and off at 5 C. Charging is normally inhibited "
            "below 0 C, but this modest estimate allows limited heater-assisted "
            "charging down to -0.5 C. This is still not exact Quetzal flight behavior."
        ),
    )


def our_adaptive_profile() -> SatelliteProfile:
    return replace(
        ALBEDO_PROFILE,
        name="Aether-Albedo-1 adaptive controller",
        source_notes=(
            "Aether-Albedo-1 design-under-test: Quetzal-scale bus/battery/solar "
            "context, 0.123 W payload, 0.6735 W heater-power assumption, tuned "
            "100/95/35/80/0 payload schedule, 20/35/100 heater pulsing, and "
            "0 C to 45 C charge-temperature gate."
        ),
    )


def design_assumptions() -> list[DesignAssumptionRow]:
    return [
        DesignAssumptionRow(
            design="no_charge_temp_gate_baseline",
            heater_power_w=0.898,
            payload_policy="Full payload in daylight; payload off in eclipse or emergency safe mode.",
            heater_policy="Full heater duty when the generic cold latch is active.",
            charge_policy="Charging allowed in daylight below 95% SOC, with no battery-temperature gate.",
            note="Harsh stress baseline used only to show why charge-temperature gating matters.",
        ),
        DesignAssumptionRow(
            design="quetzal_style_heater_protected_baseline",
            heater_power_w=0.898,
            payload_policy="Full payload in daylight; payload off in eclipse or emergency safe mode.",
            heater_policy="Source-backed protected estimate: full heater power while thermostat is latched on at 3 C and off at 5 C.",
            charge_policy="Charging allowed in daylight below 95% SOC above 0 C, with imperfect heater-assisted charging permitted down to -0.5 C.",
            note="Middle baseline. It is more realistic than no charge gate, but not a perfect reconstruction of Quetzal-1.",
        ),
        DesignAssumptionRow(
            design="our_adaptive_albedo",
            heater_power_w=0.6735,
            payload_policy="Tuned 100/95/35/80/0 payload duty by firmware mode.",
            heater_policy="20% low pulse, 35% strong pulse, 100% critical cold survival heat.",
            charge_policy="Charging allowed only in sunlight, SOC < 95%, no fault, and 0 C to 45 C battery temperature.",
            note="Design-under-test controller with tuned cold-season science-preserving schedule.",
        ),
    ]


def scenarios() -> list[AnalyticalScenario]:
    nominal_orbit = ALBEDO_PROFILE.nominal_orbit_min
    nominal_eclipse = ALBEDO_PROFILE.nominal_eclipse_min
    initial_soc_pct = 88.0
    initial_battery_temp_c = 12.0
    return [
        AnalyticalScenario(
            name=NOMINAL_YEAR_SCENARIO,
            duration_days=YEAR_DAYS,
            orbit_min=nominal_orbit,
            eclipse_min=nominal_eclipse,
            initial_soc_pct=initial_soc_pct,
            initial_battery_temp_c=initial_battery_temp_c,
            sun_temp_c=30.0,
            eclipse_temp_c=-10.0,
            note=(
                "One full nominal year. This is the control case: same spacecraft, "
                "orbit, battery, solar input, and starting state as the cold-season "
                "models, without the colder seasonal block."
            ),
        ),
        AnalyticalScenario(
            name=REALISTIC_COLD_SEASON_YEAR,
            duration_days=YEAR_DAYS,
            orbit_min=nominal_orbit,
            eclipse_min=nominal_eclipse,
            initial_soc_pct=initial_soc_pct,
            initial_battery_temp_c=initial_battery_temp_c,
            sun_temp_c=30.0,
            eclipse_temp_c=-10.0,
            note=(
                "One full year with the same nominal conditions except for two "
                "45-day cold-season windows. Each window has 5 transition days, "
                "35 consecutive low-beta cold days with 36 min eclipses, then "
                "5 recovery days."
            ),
        ),
        AnalyticalScenario(
            name=STRESS_COLD_SEASON_YEAR,
            duration_days=YEAR_DAYS,
            orbit_min=nominal_orbit,
            eclipse_min=nominal_eclipse,
            initial_soc_pct=initial_soc_pct,
            initial_battery_temp_c=initial_battery_temp_c,
            sun_temp_c=30.0,
            eclipse_temp_c=-10.0,
            note=(
                "One full year with the same nominal conditions except for two "
                "45-day analytical stress windows using repeated 41.5 min cold "
                "eclipses at 22 C sunlight and -20 C eclipse."
            ),
        ),
    ]


def to_test_case(scenario: AnalyticalScenario) -> TestCase:
    return TestCase(
        name=scenario.name,
        duration_min=round(scenario.duration_days * 24.0 * 60.0),
        orbit_min=scenario.orbit_min,
        eclipse_min=scenario.eclipse_min,
        initial_soc_pct=scenario.initial_soc_pct,
        initial_battery_temp_c=scenario.initial_battery_temp_c,
        sun_temp_c=scenario.sun_temp_c,
        eclipse_temp_c=scenario.eclipse_temp_c,
        force_events=scenario.force_events,
    )


def energy_wh(rows: list[Sample]) -> float:
    return sum(row.power_w for row in rows) / 60.0


def simulate_quetzal_style_protected(profile: SatelliteProfile, case: TestCase) -> list[Sample]:
    soc_pct = case.initial_soc_pct
    battery_temp_c = case.initial_battery_temp_c
    payload_temp_c = 25.0
    heater_latched = False
    rows: list[Sample] = []

    for t_min in range(case.duration_min):
        daylight, solar_factor, weak_sunlight = orbit_phase(t_min, case)
        generated_w = profile.solar_w * solar_factor if daylight else 0.0

        thermal_target = case.sun_temp_c if daylight else case.eclipse_temp_c
        battery_temp_c += (thermal_target - battery_temp_c) * 0.025

        forced_soc, forced_payload_temp, fault = event_overrides(t_min, case)
        if forced_soc is not None:
            soc_pct = forced_soc
        if forced_payload_temp is not None:
            payload_temp_c = forced_payload_temp

        if battery_temp_c <= 3.0:
            heater_latched = True
        elif battery_temp_c >= 5.0:
            heater_latched = False

        if fault:
            mode = "QUETZAL_STYLE_FAULT_SAFE"
            payload_duty = 0.0
        elif payload_temp_c >= 95.0 or soc_pct <= 15.0:
            mode = "QUETZAL_STYLE_EMERGENCY_SAFE"
            payload_duty = 0.0
        elif daylight:
            mode = "QUETZAL_STYLE_SUN_PAYLOAD"
            payload_duty = 1.0
        else:
            mode = "QUETZAL_STYLE_ECLIPSE"
            payload_duty = 0.0

        heater_on = heater_latched
        heater_duty = 1.0 if heater_on else 0.0
        charge_allowed = (
            daylight
            and not fault
            and soc_pct < 95.0
            and (battery_temp_c >= 0.0 or (heater_on and battery_temp_c >= -0.5))
        )

        power_w = profile.standby_w + profile.payload_active_w * payload_duty
        if heater_on:
            power_w += profile.heater_w * heater_duty

        if profile.peak_total_w > profile.standby_w + profile.payload_active_w:
            peak_extra_w = profile.peak_total_w - profile.standby_w - profile.payload_active_w
            if daylight and payload_duty > 0 and (t_min % round(case.orbit_min)) < 1:
                power_w += peak_extra_w

        usable_generation_w = generated_w * USABLE_SOLAR_EFFICIENCY if charge_allowed else 0.0
        net_w = usable_generation_w - power_w
        battery_delta_wh = net_w / 60.0
        if battery_delta_wh >= 0:
            available_room_wh = profile.battery_wh * (100.0 - soc_pct) / 100.0
            battery_delta_wh = min(battery_delta_wh, available_room_wh)
        else:
            available_wh = profile.battery_wh * soc_pct / 100.0
            battery_delta_wh = max(battery_delta_wh, -available_wh)
        soc_pct += battery_delta_wh / profile.battery_wh * 100.0
        soc_pct = min(100.0, max(0.0, soc_pct))

        battery_temp_c += heater_duty * 0.08
        payload_temp_target = battery_temp_c + 12.0 + 45.0 * payload_duty
        payload_temp_c += (payload_temp_target - payload_temp_c) * 0.04

        data_units = payload_duty if daylight and not fault else 0.0
        cold_charge_risk = int(battery_delta_wh > 0 and battery_temp_c < 0.0)
        rows.append(
            Sample(
                satellite=profile.name,
                size_class=profile.size_class,
                test_case=case.name,
                design="quetzal_style_heater_protected_baseline",
                t_min=t_min,
                mode=mode,
                daylight=int(daylight),
                solar_factor=solar_factor,
                power_w=power_w,
                generated_w=generated_w,
                battery_delta_wh=battery_delta_wh,
                soc_pct=soc_pct,
                battery_temp_c=battery_temp_c,
                payload_temp_c=payload_temp_c,
                payload_duty=payload_duty,
                heater_on=int(heater_on),
                charge_allowed=int(charge_allowed),
                data_units=data_units,
                cold_charge_risk=cold_charge_risk,
            )
        )
    return rows


def usable_generation_wh(rows: list[Sample]) -> float:
    return sum(
        (row.generated_w * USABLE_SOLAR_EFFICIENCY if row.charge_allowed else 0.0) / 60.0
        for row in rows
    )


def scenario_params_at_minute(
    scenario: AnalyticalScenario,
    t_min: int,
) -> tuple[float, float, float]:
    if scenario.name not in {REALISTIC_COLD_SEASON_YEAR, STRESS_COLD_SEASON_YEAR}:
        return scenario.eclipse_min, scenario.sun_temp_c, scenario.eclipse_temp_c

    day = t_min // (24 * 60)
    nominal = (ALBEDO_PROFILE.nominal_eclipse_min, 30.0, -10.0)
    season_day = None
    cold_window_days = (
        COLD_SEASON_TRANSITION_DAYS
        + COLD_SEASON_CORE_DAYS
        + COLD_SEASON_RECOVERY_DAYS
    )
    for start_day in COLD_SEASON_START_DAYS:
        candidate = day - start_day
        if 0 <= candidate < cold_window_days:
            season_day = candidate
            break
    if season_day is None:
        return nominal

    if scenario.name == STRESS_COLD_SEASON_YEAR:
        return min(scenario.orbit_min - 5.0, ALBEDO_PROFILE.nominal_eclipse_min + 10.0), 22.0, -20.0

    if 0 <= season_day < COLD_SEASON_TRANSITION_DAYS:
        return ALBEDO_PROFILE.nominal_eclipse_min, 25.0, -12.0
    if COLD_SEASON_TRANSITION_DAYS <= season_day < (
        COLD_SEASON_TRANSITION_DAYS + COLD_SEASON_CORE_DAYS
    ):
        return 36.0, 22.0, -20.0
    if COLD_SEASON_TRANSITION_DAYS + COLD_SEASON_CORE_DAYS <= season_day < (
        COLD_SEASON_TRANSITION_DAYS
        + COLD_SEASON_CORE_DAYS
        + COLD_SEASON_RECOVERY_DAYS
    ):
        return ALBEDO_PROFILE.nominal_eclipse_min, 25.0, -12.0
    return nominal


def dynamic_case_at_minute(scenario: AnalyticalScenario, t_min: int) -> TestCase:
    eclipse_min, sun_temp_c, eclipse_temp_c = scenario_params_at_minute(scenario, t_min)
    return TestCase(
        name=scenario.name,
        duration_min=round(scenario.duration_days * 24.0 * 60.0),
        orbit_min=scenario.orbit_min,
        eclipse_min=eclipse_min,
        initial_soc_pct=scenario.initial_soc_pct,
        initial_battery_temp_c=scenario.initial_battery_temp_c,
        sun_temp_c=sun_temp_c,
        eclipse_temp_c=eclipse_temp_c,
        force_events=scenario.force_events,
    )


def simulate_dynamic(profile: SatelliteProfile, scenario: AnalyticalScenario, design: str) -> list[Sample]:
    architecture = None if design == "baseline" else ARCHITECTURE_BY_NAME[design]
    soc_pct = scenario.initial_soc_pct
    battery_temp_c = scenario.initial_battery_temp_c
    payload_temp_c = 25.0
    latches = Latches()
    rows: list[Sample] = []
    duration_min = round(scenario.duration_days * 24.0 * 60.0)

    for t_min in range(duration_min):
        case = dynamic_case_at_minute(scenario, t_min)
        daylight, solar_factor, weak_sunlight = orbit_phase(t_min, case)
        generated_w = profile.solar_w * solar_factor if daylight else 0.0

        thermal_target = case.sun_temp_c if daylight else case.eclipse_temp_c
        battery_temp_c += (thermal_target - battery_temp_c) * 0.025

        forced_soc, forced_payload_temp, fault = event_overrides(t_min, case)
        if forced_soc is not None:
            soc_pct = forced_soc
        if forced_payload_temp is not None:
            payload_temp_c = forced_payload_temp

        update_latches(
            soc_pct,
            battery_temp_c,
            payload_temp_c,
            latches,
            architecture or ARCHITECTURE_BY_NAME["science_first"],
        )

        if design != "baseline":
            mode = select_adaptive_mode(
                profile,
                architecture,
                soc_pct,
                daylight,
                solar_factor,
                weak_sunlight,
                battery_temp_c,
                fault,
                latches,
            )
            payload_duty = adaptive_payload_duty(mode, architecture)
            charge_allowed = (
                daylight
                and not fault
                and soc_pct < 95.0
                and (
                    not architecture.safe_charge_temperature
                    or 0.0 <= battery_temp_c <= 45.0
                )
            )
        else:
            mode, payload_duty = baseline_payload_duty(soc_pct, payload_temp_c, daylight)
            charge_allowed = daylight and soc_pct < 95.0

        heater_on = heater_allowed(design, architecture, soc_pct, battery_temp_c, latches, mode)
        heater_duty = heater_duty_fraction(architecture, battery_temp_c, mode, heater_on)
        power_w = profile.standby_w + profile.payload_active_w * payload_duty
        if heater_on:
            power_w += profile.heater_w * heater_duty

        if profile.peak_total_w > profile.standby_w + profile.payload_active_w:
            peak_extra_w = profile.peak_total_w - profile.standby_w - profile.payload_active_w
            if daylight and payload_duty > 0 and (t_min % round(case.orbit_min)) < 1:
                power_w += peak_extra_w

        usable_generation_w = generated_w * USABLE_SOLAR_EFFICIENCY if charge_allowed else 0.0
        net_w = usable_generation_w - power_w
        battery_delta_wh = net_w / 60.0
        if battery_delta_wh >= 0:
            available_room_wh = profile.battery_wh * (100.0 - soc_pct) / 100.0
            battery_delta_wh = min(battery_delta_wh, available_room_wh)
        else:
            available_wh = profile.battery_wh * soc_pct / 100.0
            battery_delta_wh = max(battery_delta_wh, -available_wh)
        soc_pct += battery_delta_wh / profile.battery_wh * 100.0
        soc_pct = min(100.0, max(0.0, soc_pct))

        battery_temp_c += heater_duty * 0.08
        payload_temp_target = battery_temp_c + 12.0 + 45.0 * payload_duty
        payload_temp_c += (payload_temp_target - payload_temp_c) * 0.04

        rows.append(
            Sample(
                satellite=profile.name,
                size_class=profile.size_class,
                test_case=scenario.name,
                design=design,
                t_min=t_min,
                mode=mode,
                daylight=int(daylight),
                solar_factor=solar_factor,
                power_w=power_w,
                generated_w=generated_w,
                battery_delta_wh=battery_delta_wh,
                soc_pct=soc_pct,
                battery_temp_c=battery_temp_c,
                payload_temp_c=payload_temp_c,
                payload_duty=payload_duty,
                heater_on=int(heater_on),
                charge_allowed=int(charge_allowed),
                data_units=payload_duty if daylight and not fault else 0.0,
                cold_charge_risk=int(battery_delta_wh > 0 and battery_temp_c < 0.0),
            )
        )
    return rows


def simulate_dynamic_quetzal_style_protected(
    profile: SatelliteProfile,
    scenario: AnalyticalScenario,
) -> list[Sample]:
    soc_pct = scenario.initial_soc_pct
    battery_temp_c = scenario.initial_battery_temp_c
    payload_temp_c = 25.0
    heater_latched = False
    rows: list[Sample] = []
    duration_min = round(scenario.duration_days * 24.0 * 60.0)

    for t_min in range(duration_min):
        case = dynamic_case_at_minute(scenario, t_min)
        daylight, solar_factor, _ = orbit_phase(t_min, case)
        generated_w = profile.solar_w * solar_factor if daylight else 0.0

        thermal_target = case.sun_temp_c if daylight else case.eclipse_temp_c
        battery_temp_c += (thermal_target - battery_temp_c) * 0.025

        forced_soc, forced_payload_temp, fault = event_overrides(t_min, case)
        if forced_soc is not None:
            soc_pct = forced_soc
        if forced_payload_temp is not None:
            payload_temp_c = forced_payload_temp

        if battery_temp_c <= 3.0:
            heater_latched = True
        elif battery_temp_c >= 5.0:
            heater_latched = False

        if fault:
            mode = "QUETZAL_STYLE_FAULT_SAFE"
            payload_duty = 0.0
        elif payload_temp_c >= 95.0 or soc_pct <= 15.0:
            mode = "QUETZAL_STYLE_EMERGENCY_SAFE"
            payload_duty = 0.0
        elif daylight:
            mode = "QUETZAL_STYLE_SUN_PAYLOAD"
            payload_duty = 1.0
        else:
            mode = "QUETZAL_STYLE_ECLIPSE"
            payload_duty = 0.0

        heater_on = heater_latched
        heater_duty = 1.0 if heater_on else 0.0
        charge_allowed = (
            daylight
            and not fault
            and soc_pct < 95.0
            and (battery_temp_c >= 0.0 or (heater_on and battery_temp_c >= -0.5))
        )

        power_w = profile.standby_w + profile.payload_active_w * payload_duty
        if heater_on:
            power_w += profile.heater_w * heater_duty

        if profile.peak_total_w > profile.standby_w + profile.payload_active_w:
            peak_extra_w = profile.peak_total_w - profile.standby_w - profile.payload_active_w
            if daylight and payload_duty > 0 and (t_min % round(case.orbit_min)) < 1:
                power_w += peak_extra_w

        usable_generation_w = generated_w * USABLE_SOLAR_EFFICIENCY if charge_allowed else 0.0
        net_w = usable_generation_w - power_w
        battery_delta_wh = net_w / 60.0
        if battery_delta_wh >= 0:
            available_room_wh = profile.battery_wh * (100.0 - soc_pct) / 100.0
            battery_delta_wh = min(battery_delta_wh, available_room_wh)
        else:
            available_wh = profile.battery_wh * soc_pct / 100.0
            battery_delta_wh = max(battery_delta_wh, -available_wh)
        soc_pct += battery_delta_wh / profile.battery_wh * 100.0
        soc_pct = min(100.0, max(0.0, soc_pct))

        battery_temp_c += heater_duty * 0.08
        payload_temp_target = battery_temp_c + 12.0 + 45.0 * payload_duty
        payload_temp_c += (payload_temp_target - payload_temp_c) * 0.04

        rows.append(
            Sample(
                satellite=profile.name,
                size_class=profile.size_class,
                test_case=scenario.name,
                design="quetzal_style_heater_protected_baseline",
                t_min=t_min,
                mode=mode,
                daylight=int(daylight),
                solar_factor=solar_factor,
                power_w=power_w,
                generated_w=generated_w,
                battery_delta_wh=battery_delta_wh,
                soc_pct=soc_pct,
                battery_temp_c=battery_temp_c,
                payload_temp_c=payload_temp_c,
                payload_duty=payload_duty,
                heater_on=int(heater_on),
                charge_allowed=int(charge_allowed),
                data_units=payload_duty if daylight and not fault else 0.0,
                cold_charge_risk=int(battery_delta_wh > 0 and battery_temp_c < 0.0),
            )
        )
    return rows


def simulate_design_for_scenario(
    profile: SatelliteProfile,
    scenario: AnalyticalScenario,
    sim_design: str,
) -> list[Sample]:
    if scenario.name in {REALISTIC_COLD_SEASON_YEAR, STRESS_COLD_SEASON_YEAR}:
        if sim_design == "quetzal_style_heater_protected_baseline":
            return simulate_dynamic_quetzal_style_protected(profile, scenario)
        return simulate_dynamic(profile, scenario, sim_design)
    case = to_test_case(scenario)
    if sim_design == "quetzal_style_heater_protected_baseline":
        return simulate_quetzal_style_protected(profile, case)
    return simulate(profile, case, sim_design)


def discharge_wh(rows: list[Sample]) -> float:
    return sum(
        max(
            0.0,
            row.power_w
            - (row.generated_w * USABLE_SOLAR_EFFICIENCY if row.charge_allowed else 0.0),
        )
        / 60.0
        for row in rows
    )


def capacity_remaining_pct(
    years: float,
    equivalent_full_cycles: float,
    low_soc_hours: float,
    critical_soc_hours: float,
    cold_charge_hours: float,
    cold_charge_wh: float,
    cold_charge_degree_hours: float,
    sustainable: bool,
) -> float:
    calendar_fade_pct = 1.5 * years
    cycle_fade_pct = 0.018 * equivalent_full_cycles
    low_soc_fade_pct = 0.00010 * low_soc_hours
    critical_soc_fade_pct = 0.00040 * critical_soc_hours
    cold_charge_fade_pct = (
        0.10 * cold_charge_hours
        + 0.03 * cold_charge_wh
        + 0.05 * cold_charge_degree_hours
    )
    estimated = 100.0 - (
        calendar_fade_pct
        + cycle_fade_pct
        + low_soc_fade_pct
        + critical_soc_fade_pct
        + cold_charge_fade_pct
    )
    if not sustainable:
        estimated -= 10.0
    return max(0.0, min(100.0, estimated))


def heater_energy_wh(
    rows: list[Sample],
    profile: SatelliteProfile,
    architecture: Architecture | None,
) -> float:
    if rows and rows[0].design == "quetzal_style_heater_protected_baseline":
        return sum(profile.heater_w * int(row.heater_on) / 60.0 for row in rows)
    return sum(
        profile.heater_w
        * heater_duty_fraction(
            architecture,
            row.battery_temp_c,
            row.mode,
            bool(row.heater_on),
        )
        / 60.0
        for row in rows
    )


def payload_energy_wh(rows: list[Sample], profile: SatelliteProfile) -> float:
    return sum(profile.payload_active_w * row.payload_duty / 60.0 for row in rows)


def mode_breakdown(rows: list[Sample]) -> tuple[str, str]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.mode] = counts.get(row.mode, 0) + 1
    total = len(rows)
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    dominant = ordered[0][0] if ordered else "UNKNOWN"
    return dominant, ";".join(f"{mode}:{count / total * 100.0:.1f}" for mode, count in ordered)


def interpretation(
    design: str,
    scenario_name: str,
    sustainable: bool,
    days_to_depletion: float,
    data_retention_pct: float,
    cold_charge_hours: float,
    capacity_pct: float,
) -> str:
    if not sustainable:
        return f"Power-negative if repeated; estimated depletion in {days_to_depletion:.1f} days."
    if cold_charge_hours > 0:
        return "Energy-positive but contains modeled cold-charge exposure."
    if design == "our_adaptive_albedo" and scenario_name.startswith("cold"):
        if data_retention_pct >= 95.0 and capacity_pct > 65.0:
            return "Cold-season target hit: science-preserving, cold-charge safe, and healthier battery proxy."
        return "Cold-charge safe, but science or aging margin needs review."
    return "Energy-positive analytical comparison row."


def summarize_design(
    scenario: AnalyticalScenario,
    design: str,
    profile: SatelliteProfile,
    sim_design: str,
    architecture: Architecture | None,
    baseline_data_units: float,
    years_list: list[float],
) -> list[AnalyticalRow]:
    rows = simulate_design_for_scenario(profile, scenario, sim_design)
    duration_h = len(rows) / 60.0
    consumed = energy_wh(rows)
    generated = usable_generation_wh(rows)
    net_pattern = generated - consumed
    net_day = net_pattern * 24.0 / duration_h
    heater = heater_energy_wh(rows, profile, architecture)
    payload = payload_energy_wh(rows, profile)
    data = sum(row.data_units for row in rows)
    data_retention = data / baseline_data_units * 100.0 if baseline_data_units else 0.0
    min_soc = min(row.soc_pct for row in rows)
    pattern_discharge = discharge_wh(rows)
    low_soc_min = sum(row.soc_pct < 40.0 for row in rows)
    critical_soc_min = sum(row.soc_pct < 25.0 for row in rows)
    cold_charge_min = sum(row.cold_charge_risk for row in rows)
    cold_charge_wh = sum(
        max(0.0, row.battery_delta_wh)
        for row in rows
        if row.cold_charge_risk
    )
    cold_charge_degree_hours = sum(
        max(0.0, -row.battery_temp_c) / 60.0
        for row in rows
        if row.cold_charge_risk
    )
    dominant, modes = mode_breakdown(rows)

    if net_day < 0.0:
        initial_available_wh = profile.battery_wh * scenario.initial_soc_pct / 100.0
        days_to_depletion = initial_available_wh / abs(net_day)
    else:
        days_to_depletion = -1.0

    output: list[AnalyticalRow] = []
    for years in years_list:
        repeats = years * YEAR_DAYS * 24.0 / duration_h
        checkpoint_days = years * YEAR_DAYS
        sustainable = net_pattern >= -1e-9
        if days_to_depletion > 0.0 and days_to_depletion < checkpoint_days:
            sustainable = False
        efc = pattern_discharge * repeats / profile.battery_wh
        low_soc_days = low_soc_min * repeats / 1440.0
        critical_soc_days = critical_soc_min * repeats / 1440.0
        cold_charge_hours = cold_charge_min * repeats / 60.0
        projected_cold_charge_wh = cold_charge_wh * repeats
        projected_cold_charge_degree_hours = cold_charge_degree_hours * repeats
        capacity = capacity_remaining_pct(
            years=years,
            equivalent_full_cycles=efc,
            low_soc_hours=low_soc_days * 24.0,
            critical_soc_hours=critical_soc_days * 24.0,
            cold_charge_hours=cold_charge_hours,
            cold_charge_wh=projected_cold_charge_wh,
            cold_charge_degree_hours=projected_cold_charge_degree_hours,
            sustainable=sustainable,
        )
        output.append(
            AnalyticalRow(
                scenario=scenario.name,
                design=design,
                years=years,
                duration_days=scenario.duration_days,
                orbit_min=scenario.orbit_min,
                eclipse_min=scenario.eclipse_min,
                initial_soc_pct=scenario.initial_soc_pct,
                initial_battery_temp_c=scenario.initial_battery_temp_c,
                sun_temp_c=scenario.sun_temp_c,
                eclipse_temp_c=scenario.eclipse_temp_c,
                average_power_w=consumed / duration_h,
                peak_power_w=max(row.power_w for row in rows),
                pattern_consumed_energy_wh=consumed,
                pattern_usable_solar_generated_wh=generated,
                net_wh_per_day=net_day,
                projected_consumed_energy_kwh=consumed * repeats / 1000.0,
                projected_usable_solar_generated_kwh=generated * repeats / 1000.0,
                heater_energy_wh_per_pattern=heater,
                projected_heater_energy_kwh=heater * repeats / 1000.0,
                payload_energy_wh_per_pattern=payload,
                projected_payload_energy_kwh=payload * repeats / 1000.0,
                data_units=data,
                data_retention_pct=data_retention,
                min_soc_pct=min_soc,
                projected_equivalent_full_cycles=efc,
                low_soc_exposure_days=low_soc_days,
                critical_soc_exposure_days=critical_soc_days,
                cold_charge_exposure_hours=cold_charge_hours,
                cold_charge_energy_wh=projected_cold_charge_wh,
                cold_charge_severity_degree_hours=projected_cold_charge_degree_hours,
                estimated_capacity_remaining_pct=capacity,
                sustainable_energy_balance=int(sustainable),
                days_to_depletion_if_power_negative=days_to_depletion,
                dominant_mode=dominant,
                mode_breakdown_pct=modes,
                interpretation=interpretation(
                    design=design,
                    scenario_name=scenario.name,
                    sustainable=sustainable,
                    days_to_depletion=days_to_depletion,
                    data_retention_pct=data_retention,
                    cold_charge_hours=cold_charge_hours,
                    capacity_pct=capacity,
                ),
            )
        )
    return output


def compare_rows(rows: list[AnalyticalRow]) -> list[ComparisonRow]:
    comparisons: list[ComparisonRow] = []
    by_key = {(row.scenario, row.design, row.years): row for row in rows}
    scenario_years = sorted({(row.scenario, row.years) for row in rows})
    for scenario, years in scenario_years:
        adaptive = by_key[(scenario, "our_adaptive_albedo", years)]
        for baseline_design in (
            "no_charge_temp_gate_baseline",
            "quetzal_style_heater_protected_baseline",
        ):
            baseline = by_key[(scenario, baseline_design, years)]
            consumed_delta_pct = (
                (baseline.projected_consumed_energy_kwh - adaptive.projected_consumed_energy_kwh)
                / baseline.projected_consumed_energy_kwh
                * 100.0
                if baseline.projected_consumed_energy_kwh
                else 0.0
            )
            heater_delta_pct = (
                (baseline.projected_heater_energy_kwh - adaptive.projected_heater_energy_kwh)
                / baseline.projected_heater_energy_kwh
                * 100.0
                if baseline.projected_heater_energy_kwh
                else 0.0
            )
            avg_power_delta_pct = (
                (baseline.average_power_w - adaptive.average_power_w)
                / baseline.average_power_w
                * 100.0
                if baseline.average_power_w
                else 0.0
            )
            if scenario == NOMINAL_YEAR_SCENARIO:
                note = "Nominal result remains near parity; cold-season cases carry the claim."
            elif baseline_design == "quetzal_style_heater_protected_baseline":
                note = "Source-backed Quetzal-style protected estimate; compares safe heater-driven protection against adaptive heater/payload control."
            elif (
                scenario in {REALISTIC_COLD_SEASON_YEAR, STRESS_COLD_SEASON_YEAR}
            ) and adaptive.cold_charge_exposure_hours == 0:
                note = "Cold-season result favors adaptive charge/heater/payload control."
            else:
                note = "Fault-chain screen only; do not treat as real Quetzal EOL reconstruction."
            comparisons.append(
                ComparisonRow(
                    scenario=scenario,
                    years=years,
                    baseline_design=baseline.design,
                    adaptive_design=adaptive.design,
                    baseline_average_power_w=baseline.average_power_w,
                    adaptive_average_power_w=adaptive.average_power_w,
                    average_power_reduction_pct=avg_power_delta_pct,
                    baseline_consumed_energy_kwh=baseline.projected_consumed_energy_kwh,
                    adaptive_consumed_energy_kwh=adaptive.projected_consumed_energy_kwh,
                    consumed_energy_reduction_pct=consumed_delta_pct,
                    baseline_heater_energy_kwh=baseline.projected_heater_energy_kwh,
                    adaptive_heater_energy_kwh=adaptive.projected_heater_energy_kwh,
                    heater_energy_reduction_pct=heater_delta_pct,
                    adaptive_data_retention_pct=adaptive.data_retention_pct,
                    baseline_min_soc_pct=baseline.min_soc_pct,
                    adaptive_min_soc_pct=adaptive.min_soc_pct,
                    baseline_cold_charge_hours=baseline.cold_charge_exposure_hours,
                    adaptive_cold_charge_hours=adaptive.cold_charge_exposure_hours,
                    baseline_capacity_remaining_pct=baseline.estimated_capacity_remaining_pct,
                    adaptive_capacity_remaining_pct=adaptive.estimated_capacity_remaining_pct,
                    capacity_proxy_delta_pct=(
                        adaptive.estimated_capacity_remaining_pct
                        - baseline.estimated_capacity_remaining_pct
                    ),
                    baseline_days_to_depletion=baseline.days_to_depletion_if_power_negative,
                    adaptive_days_to_depletion=adaptive.days_to_depletion_if_power_negative,
                    interpretation=note,
                )
            )
    return comparisons


def write_csv(path: Path, rows: list[object]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def scenario_assumption_rows() -> list[ScenarioAssumptionRow]:
    return [
        ScenarioAssumptionRow(
            scenario=row.name,
            duration_days=row.duration_days,
            orbit_min=row.orbit_min,
            eclipse_min=row.eclipse_min,
            initial_soc_pct=row.initial_soc_pct,
            initial_battery_temp_c=row.initial_battery_temp_c,
            sun_temp_c=row.sun_temp_c,
            eclipse_temp_c=row.eclipse_temp_c,
            note=row.note,
        )
        for row in scenarios()
    ]


def safe_label(design: str) -> str:
    return {
        "no_charge_temp_gate_baseline": "No temp gate",
        "quetzal_style_heater_protected_baseline": "Quetzal-style protected",
        "our_adaptive_albedo": "Our adaptive",
    }.get(design, design)


def plot_grouped_bars(
    rows: list[AnalyticalRow],
    scenario_name: str,
    metric: str,
    title: str,
    ylabel: str,
    output_stem: str,
) -> None:
    subset = [
        row
        for row in rows
        if row.scenario == scenario_name
        and row.design
        in {
            "no_charge_temp_gate_baseline",
            "quetzal_style_heater_protected_baseline",
            "our_adaptive_albedo",
        }
    ]
    years = sorted({row.years for row in subset})
    designs = [
        "no_charge_temp_gate_baseline",
        "quetzal_style_heater_protected_baseline",
        "our_adaptive_albedo",
    ]
    values = {
        (row.years, row.design): float(getattr(row, metric))
        for row in subset
    }

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    width_px = 1100
    height_px = 620
    margin_left = 96
    margin_right = 42
    margin_top = 92
    margin_bottom = 112
    plot_w = width_px - margin_left - margin_right
    plot_h = height_px - margin_top - margin_bottom
    colors = {
        "no_charge_temp_gate_baseline": "#6b7280",
        "quetzal_style_heater_protected_baseline": "#3b82f6",
        "our_adaptive_albedo": "#10b981",
    }
    all_values = [values.get((year, design), 0.0) for year in years for design in designs]
    max_value = max(all_values) if all_values else 1.0
    if max_value <= 0.0:
        max_value = 1.0
    y_max = max_value * 1.12

    def x_group(index: int) -> float:
        return margin_left + (index + 0.5) * plot_w / len(years)

    def y_pos(value: float) -> float:
        return margin_top + plot_h - (value / y_max) * plot_h

    def fmt_value(value: float) -> str:
        if value >= 1000:
            return f"{value:,.0f}"
        if value >= 100:
            return f"{value:.0f}"
        if value >= 10:
            return f"{value:.1f}"
        return f"{value:.2f}"

    # SVG output.
    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin_left}" y="44" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="{margin_left}" y="72" font-family="Arial, sans-serif" font-size="15" fill="#4b5563">{html.escape(ylabel)}</text>',
    ]
    for tick in range(5):
        value = y_max * tick / 4
        y = y_pos(value)
        svg.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width_px - margin_right}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        svg.append(f'<text x="{margin_left - 12}" y="{y + 5:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">{html.escape(fmt_value(value))}</text>')

    group_width = plot_w / len(years)
    bar_width = min(58.0, group_width / 4.4)
    for year_index, year in enumerate(years):
        center = x_group(year_index)
        for design_index, design in enumerate(designs):
            value = values.get((year, design), 0.0)
            x = center + (design_index - 1) * bar_width * 1.18 - bar_width / 2
            y = y_pos(value)
            h = margin_top + plot_h - y
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{h:.1f}" rx="4" fill="{colors[design]}"/>')
            svg.append(f'<text x="{x + bar_width / 2:.1f}" y="{max(y - 6, margin_top - 4):.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#374151">{html.escape(fmt_value(value))}</text>')
        svg.append(f'<text x="{center:.1f}" y="{height_px - 72}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#111827">{year:g} year</text>')

    legend_x = margin_left
    legend_y = height_px - 36
    for index, design in enumerate(designs):
        x = legend_x + index * 285
        svg.append(f'<rect x="{x}" y="{legend_y - 12}" width="16" height="16" rx="3" fill="{colors[design]}"/>')
        svg.append(f'<text x="{x + 24}" y="{legend_y + 1}" font-family="Arial, sans-serif" font-size="13" fill="#374151">{html.escape(safe_label(design))}</text>')
    svg.append("</svg>")
    (FIG_DIR / f"{output_stem}.svg").write_text("\n".join(svg), encoding="utf-8")

    # PNG output via Pillow.
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:  # pragma: no cover - Pillow availability is environment-specific
        print(f"SVG chart written for {output_stem}; PNG skipped: {exc}")
        return

    image = Image.new("RGB", (width_px, height_px), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        label_font = ImageFont.truetype("DejaVuSans.ttf", 15)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 12)
        tick_font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        title_font = label_font = small_font = tick_font = ImageFont.load_default()

    draw.text((margin_left, 30), title, fill="#111827", font=title_font)
    draw.text((margin_left, 58), ylabel, fill="#4b5563", font=label_font)
    for tick in range(5):
        value = y_max * tick / 4
        y = y_pos(value)
        draw.line((margin_left, y, width_px - margin_right, y), fill="#e5e7eb", width=1)
        tick_label = fmt_value(value)
        bbox = draw.textbbox((0, 0), tick_label, font=small_font)
        draw.text((margin_left - 16 - (bbox[2] - bbox[0]), y - 7), tick_label, fill="#6b7280", font=small_font)

    for year_index, year in enumerate(years):
        center = x_group(year_index)
        for design_index, design in enumerate(designs):
            value = values.get((year, design), 0.0)
            x = center + (design_index - 1) * bar_width * 1.18 - bar_width / 2
            y = y_pos(value)
            h = margin_top + plot_h - y
            draw.rounded_rectangle((x, y, x + bar_width, y + h), radius=4, fill=colors[design])
            value_label = fmt_value(value)
            bbox = draw.textbbox((0, 0), value_label, font=small_font)
            draw.text((x + bar_width / 2 - (bbox[2] - bbox[0]) / 2, max(y - 18, margin_top - 20)), value_label, fill="#374151", font=small_font)
        year_label = f"{year:g} year"
        bbox = draw.textbbox((0, 0), year_label, font=tick_font)
        draw.text((center - (bbox[2] - bbox[0]) / 2, height_px - 84), year_label, fill="#111827", font=tick_font)

    for index, design in enumerate(designs):
        x = legend_x + index * 285
        draw.rounded_rectangle((x, legend_y - 12, x + 16, legend_y + 4), radius=3, fill=colors[design])
        draw.text((x + 24, legend_y - 12), safe_label(design), fill="#374151", font=small_font)
    image.save(FIG_DIR / f"{output_stem}.png")


def make_charts(rows: list[AnalyticalRow]) -> None:
    for scenario_name, label, stem in (
        (NOMINAL_YEAR_SCENARIO, "Nominal Year", "nominal_year"),
        (REALISTIC_COLD_SEASON_YEAR, "Realistic Cold-Season Year", "realistic_cold_season_year"),
        (STRESS_COLD_SEASON_YEAR, "Cold Long-Eclipse Stress Year", "cold_long_eclipse_stress_year"),
    ):
        plot_grouped_bars(
            rows=rows,
            scenario_name=scenario_name,
            metric="estimated_capacity_remaining_pct",
            title=f"{label} Battery Proxy",
            ylabel="Estimated capacity remaining (%)",
            output_stem=f"{stem}_capacity_proxy",
        )
        plot_grouped_bars(
            rows=rows,
            scenario_name=scenario_name,
            metric="cold_charge_exposure_hours",
            title=f"{label} Cold-Charge Exposure",
            ylabel="Projected exposure (hours)",
            output_stem=f"{stem}_cold_charge",
        )
        plot_grouped_bars(
            rows=rows,
            scenario_name=scenario_name,
            metric="projected_consumed_energy_kwh",
            title=f"{label} Consumed Energy",
            ylabel="Projected consumed energy (kWh)",
            output_stem=f"{stem}_consumed_energy",
        )
        plot_grouped_bars(
            rows=rows,
            scenario_name=scenario_name,
            metric="projected_heater_energy_kwh",
            title=f"{label} Heater Energy",
            ylabel="Projected heater energy (kWh)",
            output_stem=f"{stem}_heater_energy",
        )


def run_model(years_list: list[float]) -> tuple[list[AnalyticalRow], list[ComparisonRow]]:
    ARCHITECTURE_BY_NAME[OUR_ARCHITECTURE_NAME] = ARCHITECTURE_BY_NAME[OUR_ARCHITECTURE_NAME]
    architecture = ARCHITECTURE_BY_NAME[OUR_ARCHITECTURE_NAME]
    baseline_profile = quetzal_baseline_profile()
    protected_profile = quetzal_style_protected_profile()
    adaptive_profile = our_adaptive_profile()

    rows: list[AnalyticalRow] = []
    for scenario in scenarios():
        baseline_samples = simulate_design_for_scenario(baseline_profile, scenario, "baseline")
        baseline_data_units = sum(1.0 for row in baseline_samples if row.daylight)
        rows.extend(
            summarize_design(
                scenario=scenario,
                design="no_charge_temp_gate_baseline",
                profile=baseline_profile,
                sim_design="baseline",
                architecture=None,
                baseline_data_units=baseline_data_units,
                years_list=years_list,
            )
        )
        rows.extend(
            summarize_design(
                scenario=scenario,
                design="quetzal_style_heater_protected_baseline",
                profile=protected_profile,
                sim_design="quetzal_style_heater_protected_baseline",
                architecture=None,
                baseline_data_units=baseline_data_units,
                years_list=years_list,
            )
        )
        rows.extend(
            summarize_design(
                scenario=scenario,
                design="our_adaptive_albedo",
                profile=adaptive_profile,
                sim_design=OUR_ARCHITECTURE_NAME,
                architecture=architecture,
                baseline_data_units=baseline_data_units,
                years_list=years_list,
            )
        )

    comparisons = compare_rows(rows)
    write_csv(LOG_DIR / "cold_season_analytical_model.csv", rows)
    write_csv(LOG_DIR / "cold_season_analytical_comparison.csv", comparisons)
    write_csv(LOG_DIR / "cold_season_analytical_scenarios.csv", scenario_assumption_rows())
    write_csv(LOG_DIR / "cold_season_analytical_design_assumptions.csv", design_assumptions())
    make_charts(rows)
    return rows, comparisons


def fmt_days(value: float) -> str:
    if value < 0:
        return "not depleted"
    if math.isinf(value):
        return "not depleted"
    return f"{value:.1f} d"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the cold-season repeated-eclipse analytical stress model."
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=float,
        default=[1.0, 3.0, 5.0],
        help="Projection checkpoints in years.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print compact scenario comparison rows.",
    )
    args = parser.parse_args()

    _, comparisons = run_model(args.years)
    if args.summary_only:
        print("Annual nominal/cold-season analytical EPS model")
        for row in comparisons:
            if row.years != max(args.years):
                continue
            if row.baseline_design != "quetzal_style_heater_protected_baseline":
                continue
            print(
                f"{row.scenario} {row.years:g}y: "
                f"avg {row.baseline_average_power_w:.3f}W -> {row.adaptive_average_power_w:.3f}W, "
                f"energy_saved={row.consumed_energy_reduction_pct:.2f}%, "
                f"heater_saved={row.heater_energy_reduction_pct:.2f}%, "
                f"data={row.adaptive_data_retention_pct:.2f}%, "
                f"cold_charge={row.baseline_cold_charge_hours:.0f}h -> {row.adaptive_cold_charge_hours:.0f}h, "
                f"cap={row.baseline_capacity_remaining_pct:.1f}% -> {row.adaptive_capacity_remaining_pct:.1f}%, "
                f"depletion={fmt_days(row.adaptive_days_to_depletion)}"
            )


if __name__ == "__main__":
    main()
