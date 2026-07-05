#!/usr/bin/env python3
"""
Multi-reference CubeSat EPS logic benchmark.

This is a logic-only comparison. It keeps each reference spacecraft's published
load scale and applies the adaptive payload/heater/charge policy from the ESP32
firmware. It does not claim a new heater, battery, solar array, or EPS hardware.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "results" / "validation_logs"


MODES = (
    "SUNLIGHT_SCIENCE",
    "SUNLIGHT_SCHEDULED",
    "SUNLIGHT_POWER_SAVE",
    "PRE_ECLIPSE_PREP",
    "ECLIPSE_SURVIVAL",
    "LOW_SOC_SAFE",
    "THERMAL_SAFE",
    "FAULT_SAFE",
)


@dataclass(frozen=True)
class SatelliteProfile:
    name: str
    size_class: str
    standby_w: float
    payload_active_w: float
    peak_total_w: float
    heater_w: float
    battery_wh: float
    solar_w: float
    nominal_orbit_min: float
    nominal_eclipse_min: float
    source_confidence: str
    source_notes: str


@dataclass(frozen=True)
class TestCase:
    name: str
    duration_min: int
    orbit_min: float
    eclipse_min: float
    initial_soc_pct: float
    initial_battery_temp_c: float
    sun_temp_c: float
    eclipse_temp_c: float
    force_events: bool = False


@dataclass(frozen=True)
class Architecture:
    name: str
    description: str
    science_duty: float
    scheduled_duty: float
    power_save_duty: float
    pre_eclipse_duty: float
    soc_continuous_payload_pct: float = 85.0
    soc_scheduled_payload_pct: float = 60.0
    soc_payload_off_pct: float = 40.0
    soc_low_power_enter_pct: float = 25.0
    soc_low_power_exit_pct: float = 35.0
    heater_min_soc_pct: float = 30.0
    heater_low_duty: float = 1.0
    heater_strong_duty: float = 1.0
    heater_survival_duty: float = 1.0
    min_power_margin_w: float = 0.10
    strong_power_margin_w: float = 0.15
    safe_charge_temperature: bool = True


@dataclass
class Latches:
    heater: bool = False
    thermal: bool = False
    low_soc: bool = False


@dataclass
class Sample:
    satellite: str
    size_class: str
    test_case: str
    design: str
    t_min: int
    mode: str
    daylight: int
    solar_factor: float
    power_w: float
    generated_w: float
    battery_delta_wh: float
    soc_pct: float
    battery_temp_c: float
    payload_temp_c: float
    payload_duty: float
    heater_on: int
    charge_allowed: int
    data_units: float
    cold_charge_risk: int


@dataclass
class ComparisonSummary:
    satellite: str
    size_class: str
    test_case: str
    architecture: str
    duration_h: float
    baseline_energy_wh: float
    adaptive_energy_wh: float
    energy_saved_wh: float
    energy_saved_pct: float
    baseline_avg_power_w: float
    adaptive_avg_power_w: float
    baseline_data_units: float
    adaptive_data_units: float
    adaptive_data_retention_pct: float
    baseline_min_soc_pct: float
    adaptive_min_soc_pct: float
    baseline_max_dod_pct: float
    adaptive_max_dod_pct: float
    baseline_low_soc_min: int
    adaptive_low_soc_min: int
    baseline_critical_soc_min: int
    adaptive_critical_soc_min: int
    baseline_equiv_full_cycles: float
    adaptive_equiv_full_cycles: float
    baseline_cold_charge_risk_min: int
    adaptive_cold_charge_risk_min: int
    baseline_heater_on_min: int
    adaptive_heater_on_min: int
    adaptive_modes_seen: str
    source_confidence: str
    source_notes: str


@dataclass
class ArchitectureScore:
    architecture: str
    rank: int
    score: float
    nominal_data_retention_pct: float
    all_case_data_retention_pct: float
    average_energy_saved_pct: float
    stress_energy_saved_pct: float
    nominal_energy_saved_pct: float
    average_min_soc_improvement_pct: float
    critical_soc_minutes_delta: int
    cold_charge_risk_minutes: int
    passes_nominal_data_gate: int
    passes_cold_charge_gate: int
    interpretation: str


def write_csv(path: Path, rows: Iterable[object]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_dict_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


SATELLITES = [
    SatelliteProfile(
        name="Quetzal-1",
        size_class="1U",
        standby_w=0.66370,
        payload_active_w=0.123,
        peak_total_w=0.997,
        heater_w=0.898,
        battery_wh=14.8,
        solar_w=2.37,
        nominal_orbit_min=94.469,
        nominal_eclipse_min=35.0,
        source_confidence="High load/battery, medium solar-generation transfer",
        source_notes=(
            "Supplied EPS reference: 1S2P 4000 mAh pack, 0.664 W heater-off, "
            "0.997 W heater-on excluding payload; project albedo payload adds 0.123 W."
        ),
    ),
    SatelliteProfile(
        name="MinXSS-1",
        size_class="3U",
        standby_w=5.31,
        payload_active_w=2.70,
        peak_total_w=24.39,
        heater_w=0.0,
        battery_wh=29.6,
        solar_w=22.84,
        nominal_orbit_min=93.0,
        nominal_eclipse_min=28.0,
        source_confidence="High",
        source_notes=(
            "JoSS paper: 2S2P 4 Ah Li-poly pack, 22.84 W max generated, "
            "5.31 W Safe and 8.01 W Science orbit-average consumption; "
            "supplied reference lists 24.39 W peak."
        ),
    ),
    SatelliteProfile(
        name="Aalto-1",
        size_class="3U",
        standby_w=3.295,
        payload_active_w=19.295,
        peak_total_w=22.59,
        heater_w=0.0,
        battery_wh=30.0,
        solar_w=5.0,
        nominal_orbit_min=90.0,
        nominal_eclipse_min=35.0,
        source_confidence="Medium-high loads, medium battery/solar transfer",
        source_notes=(
            "Acta Astronautica/Aalto references: 3.295 W standby, 22.59 W peak; "
            "Aalto EPS mission-design source lists 30 Wh battery and at least "
            "5 W EOL solar output."
        ),
    ),
]


ARCHITECTURES = [
    Architecture(
        name="science_first",
        description=(
            "Maximize nominal data. Keep full payload duty in healthy sunlight, "
            "use half-rate data in weak/pre-eclipse states, and shed payload only "
            "for low SOC, eclipse, thermal, or fault states."
        ),
        science_duty=1.00,
        scheduled_duty=1.00,
        power_save_duty=0.50,
        pre_eclipse_duty=0.50,
    ),
    Architecture(
        name="balanced_safe",
        description=(
            "Mild nominal throttling with stronger reduction under weak margin. "
            "This is the middle-ground policy."
        ),
        science_duty=1.00,
        scheduled_duty=0.95,
        power_save_duty=0.35,
        pre_eclipse_duty=0.25,
    ),
    Architecture(
        name="improved_firmware",
        description=(
            "Balanced-safe payload behavior plus heater pulse control. Normal cold "
            "uses a 20 percent heater pulse, colder eclipse uses 35 percent, and "
            "critical cold still permits full survival heat. The pre-eclipse "
            "payload window is raised to 80 percent for the cold-season "
            "science-preserving schedule."
        ),
        science_duty=1.00,
        scheduled_duty=0.95,
        power_save_duty=0.35,
        pre_eclipse_duty=0.80,
        heater_low_duty=0.20,
        heater_strong_duty=0.35,
        heater_survival_duty=1.00,
    ),
    Architecture(
        name="current_adaptive",
        description=(
            "Current firmware-style policy used in the previous benchmark: full "
            "science mode, 60 percent scheduled mode, 20 percent power-save mode, "
            "payload off during pre-eclipse prep."
        ),
        science_duty=1.00,
        scheduled_duty=0.60,
        power_save_duty=0.20,
        pre_eclipse_duty=0.00,
    ),
    Architecture(
        name="aggressive_saver",
        description=(
            "Energy-first policy. It intentionally sacrifices data earlier and is "
            "included to show the cost of over-optimizing power."
        ),
        science_duty=0.90,
        scheduled_duty=0.50,
        power_save_duty=0.10,
        pre_eclipse_duty=0.00,
        soc_continuous_payload_pct=90.0,
        soc_scheduled_payload_pct=65.0,
    ),
]


ARCHITECTURE_BY_NAME = {arch.name: arch for arch in ARCHITECTURES}


def build_cases(profile: SatelliteProfile) -> list[TestCase]:
    two_orbits = round(profile.nominal_orbit_min * 2)
    return [
        TestCase(
            name="short_2_orbit",
            duration_min=two_orbits,
            orbit_min=profile.nominal_orbit_min,
            eclipse_min=profile.nominal_eclipse_min,
            initial_soc_pct=88.0,
            initial_battery_temp_c=12.0,
            sun_temp_c=30.0,
            eclipse_temp_c=-10.0,
        ),
        TestCase(
            name="nominal_1_day",
            duration_min=24 * 60,
            orbit_min=profile.nominal_orbit_min,
            eclipse_min=profile.nominal_eclipse_min,
            initial_soc_pct=88.0,
            initial_battery_temp_c=12.0,
            sun_temp_c=30.0,
            eclipse_temp_c=-10.0,
        ),
        TestCase(
            name="long_eclipse_1_day",
            duration_min=24 * 60,
            orbit_min=profile.nominal_orbit_min,
            eclipse_min=min(profile.nominal_orbit_min - 5.0, profile.nominal_eclipse_min + 10.0),
            initial_soc_pct=82.0,
            initial_battery_temp_c=5.0,
            sun_temp_c=22.0,
            eclipse_temp_c=-20.0,
        ),
        TestCase(
            name="high_beta_1_day",
            duration_min=24 * 60,
            orbit_min=profile.nominal_orbit_min,
            eclipse_min=0.0,
            initial_soc_pct=90.0,
            initial_battery_temp_c=18.0,
            sun_temp_c=35.0,
            eclipse_temp_c=18.0,
        ),
        TestCase(
            name="mode_sweep_1_day",
            duration_min=24 * 60,
            orbit_min=profile.nominal_orbit_min,
            eclipse_min=profile.nominal_eclipse_min,
            initial_soc_pct=90.0,
            initial_battery_temp_c=-6.0,
            sun_temp_c=20.0,
            eclipse_temp_c=-18.0,
            force_events=True,
        ),
        TestCase(
            name="projection_30_day",
            duration_min=30 * 24 * 60,
            orbit_min=profile.nominal_orbit_min,
            eclipse_min=profile.nominal_eclipse_min,
            initial_soc_pct=88.0,
            initial_battery_temp_c=12.0,
            sun_temp_c=30.0,
            eclipse_temp_c=-10.0,
        ),
    ]


def orbit_phase(t_min: int, case: TestCase) -> tuple[bool, float, bool]:
    if case.eclipse_min <= 0:
        return True, 1.0, False
    phase = t_min % case.orbit_min
    sun_min = case.orbit_min - case.eclipse_min
    daylight = phase < sun_min
    if not daylight:
        return False, 0.0, False

    edge_min = min(8.0, max(1.0, sun_min / 5.0))
    weak = phase < edge_min or phase > sun_min - edge_min
    return True, 0.45 if weak else 1.0, weak


def event_overrides(t_min: int, case: TestCase) -> tuple[float | None, float | None, bool]:
    if not case.force_events:
        return None, None, False

    hour = t_min / 60.0
    forced_soc = None
    forced_payload_temp = None
    fault = False
    if 3.0 <= hour < 3.5:
        forced_soc = 55.0
    if 5.0 <= hour < 5.5:
        forced_soc = 22.0
    if 7.0 <= hour < 8.0:
        forced_payload_temp = 92.0
    if 10.0 <= hour < 10.5:
        fault = True
    return forced_soc, forced_payload_temp, fault


def update_latches(
    soc_pct: float,
    battery_temp_c: float,
    payload_temp_c: float,
    latches: Latches,
    architecture: Architecture,
) -> None:
    if battery_temp_c <= -5.0:
        latches.heater = True
    elif battery_temp_c >= 5.0:
        latches.heater = False

    if payload_temp_c >= 85.0:
        latches.thermal = True
    elif payload_temp_c <= 75.0:
        latches.thermal = False

    if soc_pct <= architecture.soc_low_power_enter_pct:
        latches.low_soc = True
    elif soc_pct >= architecture.soc_low_power_exit_pct:
        latches.low_soc = False


def select_adaptive_mode(
    profile: SatelliteProfile,
    architecture: Architecture,
    soc_pct: float,
    daylight: bool,
    solar_factor: float,
    weak_sunlight: bool,
    battery_temp_c: float,
    fault: bool,
    latches: Latches,
) -> str:
    generated_w = profile.solar_w * solar_factor if daylight else 0.0
    demand_with_payload = profile.standby_w + profile.payload_active_w
    if latches.heater:
        demand_with_payload += profile.heater_w
    margin_w = generated_w - demand_with_payload

    if fault:
        return "FAULT_SAFE"
    if latches.thermal:
        return "THERMAL_SAFE"
    if not daylight:
        return "ECLIPSE_SURVIVAL"
    if latches.low_soc or soc_pct < architecture.soc_payload_off_pct:
        return "LOW_SOC_SAFE"
    if weak_sunlight and battery_temp_c < 5.0:
        return "PRE_ECLIPSE_PREP"
    if soc_pct < architecture.soc_scheduled_payload_pct or margin_w < architecture.min_power_margin_w:
        return "SUNLIGHT_POWER_SAVE"
    if solar_factor >= 0.95 and soc_pct >= 85.0 and margin_w >= 0.15:
        if soc_pct < architecture.soc_continuous_payload_pct or margin_w < architecture.strong_power_margin_w:
            return "SUNLIGHT_SCHEDULED"
        return "SUNLIGHT_SCIENCE"
    return "SUNLIGHT_SCHEDULED"


def adaptive_payload_duty(mode: str, architecture: Architecture) -> float:
    if mode == "SUNLIGHT_SCIENCE":
        return architecture.science_duty
    if mode == "SUNLIGHT_SCHEDULED":
        return architecture.scheduled_duty
    if mode == "SUNLIGHT_POWER_SAVE":
        return architecture.power_save_duty
    if mode == "PRE_ECLIPSE_PREP":
        return architecture.pre_eclipse_duty
    return 0.0


def baseline_payload_duty(soc_pct: float, payload_temp_c: float, daylight: bool) -> tuple[str, float]:
    if payload_temp_c >= 95.0 or soc_pct <= 15.0:
        return "BASELINE_EMERGENCY_SAFE", 0.0
    if daylight:
        return "BASELINE_SUN_PAYLOAD", 1.0
    return "BASELINE_ECLIPSE", 0.0


def heater_allowed(
    design: str,
    architecture: Architecture | None,
    soc_pct: float,
    battery_temp_c: float,
    latches: Latches,
    mode: str,
) -> bool:
    if not latches.heater:
        return False
    if battery_temp_c <= -15.0:
        return True
    if design != "baseline":
        heater_min_soc = architecture.heater_min_soc_pct if architecture else 30.0
        if mode in {"FAULT_SAFE", "LOW_SOC_SAFE"} and soc_pct < heater_min_soc:
            return False
        return soc_pct >= heater_min_soc
    return True


def heater_duty_fraction(
    architecture: Architecture | None,
    battery_temp_c: float,
    mode: str,
    heater_on: bool,
) -> float:
    if not heater_on:
        return 0.0
    if architecture is None:
        return 1.0
    if battery_temp_c <= -15.0:
        return architecture.heater_survival_duty
    if battery_temp_c <= -10.0 or mode == "ECLIPSE_SURVIVAL":
        return architecture.heater_strong_duty
    return architecture.heater_low_duty


def simulate(profile: SatelliteProfile, case: TestCase, design: str) -> list[Sample]:
    architecture = None if design == "baseline" else ARCHITECTURE_BY_NAME[design]
    soc_pct = case.initial_soc_pct
    battery_temp_c = case.initial_battery_temp_c
    payload_temp_c = 25.0
    latches = Latches()
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
        elif design == "baseline":
            mode, payload_duty = baseline_payload_duty(soc_pct, payload_temp_c, daylight)
            charge_allowed = daylight and soc_pct < 95.0
        else:
            raise ValueError(f"Unknown design: {design}")

        heater_on = heater_allowed(design, architecture, soc_pct, battery_temp_c, latches, mode)
        heater_duty = heater_duty_fraction(architecture, battery_temp_c, mode, heater_on)
        power_w = profile.standby_w + profile.payload_active_w * payload_duty
        if heater_on:
            power_w += profile.heater_w * heater_duty

        if profile.peak_total_w > profile.standby_w + profile.payload_active_w:
            peak_extra_w = profile.peak_total_w - profile.standby_w - profile.payload_active_w
            peak_window_min = 2 if profile.name == "MinXSS-1" else 1
            if daylight and payload_duty > 0 and (t_min % round(case.orbit_min)) < peak_window_min:
                power_w += peak_extra_w

        usable_generation_w = generated_w * 0.85 if charge_allowed else 0.0
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
                data_units=data_units,
                cold_charge_risk=cold_charge_risk,
            )
        )
    return rows


def summarize_pair(
    profile: SatelliteProfile,
    case: TestCase,
    architecture: Architecture,
    baseline: list[Sample],
    adaptive: list[Sample],
) -> ComparisonSummary:
    def energy(rows: list[Sample]) -> float:
        return sum(row.power_w for row in rows) / 60.0

    def data(rows: list[Sample]) -> float:
        return sum(row.data_units for row in rows)

    def discharge_wh(rows: list[Sample]) -> float:
        return -sum(min(0.0, row.battery_delta_wh) for row in rows)

    baseline_energy = energy(baseline)
    adaptive_energy = energy(adaptive)
    baseline_data = data(baseline)
    adaptive_data = data(adaptive)
    modes_seen = sorted({row.mode for row in adaptive})
    duration_h = case.duration_min / 60.0

    return ComparisonSummary(
        satellite=profile.name,
        size_class=profile.size_class,
        test_case=case.name,
        architecture=architecture.name,
        duration_h=duration_h,
        baseline_energy_wh=baseline_energy,
        adaptive_energy_wh=adaptive_energy,
        energy_saved_wh=baseline_energy - adaptive_energy,
        energy_saved_pct=(baseline_energy - adaptive_energy) / baseline_energy * 100.0 if baseline_energy else 0.0,
        baseline_avg_power_w=baseline_energy / duration_h,
        adaptive_avg_power_w=adaptive_energy / duration_h,
        baseline_data_units=baseline_data,
        adaptive_data_units=adaptive_data,
        adaptive_data_retention_pct=adaptive_data / baseline_data * 100.0 if baseline_data else 0.0,
        baseline_min_soc_pct=min(row.soc_pct for row in baseline),
        adaptive_min_soc_pct=min(row.soc_pct for row in adaptive),
        baseline_max_dod_pct=100.0 - min(row.soc_pct for row in baseline),
        adaptive_max_dod_pct=100.0 - min(row.soc_pct for row in adaptive),
        baseline_low_soc_min=sum(row.soc_pct < 40.0 for row in baseline),
        adaptive_low_soc_min=sum(row.soc_pct < 40.0 for row in adaptive),
        baseline_critical_soc_min=sum(row.soc_pct < 25.0 for row in baseline),
        adaptive_critical_soc_min=sum(row.soc_pct < 25.0 for row in adaptive),
        baseline_equiv_full_cycles=discharge_wh(baseline) / profile.battery_wh,
        adaptive_equiv_full_cycles=discharge_wh(adaptive) / profile.battery_wh,
        baseline_cold_charge_risk_min=sum(row.cold_charge_risk for row in baseline),
        adaptive_cold_charge_risk_min=sum(row.cold_charge_risk for row in adaptive),
        baseline_heater_on_min=sum(row.heater_on for row in baseline),
        adaptive_heater_on_min=sum(row.heater_on for row in adaptive),
        adaptive_modes_seen=";".join(modes_seen),
        source_confidence=profile.source_confidence,
        source_notes=profile.source_notes,
    )


def score_architectures(summaries: list[ComparisonSummary]) -> list[ArchitectureScore]:
    scores: list[ArchitectureScore] = []
    stress_cases = {"long_eclipse_1_day", "mode_sweep_1_day"}
    nominal_cases = {"short_2_orbit", "nominal_1_day"}
    primary_satellites = {"Quetzal-1", "MinXSS-1"}

    for architecture in ARCHITECTURES:
        rows = [row for row in summaries if row.architecture == architecture.name]
        primary_nominal = [
            row
            for row in rows
            if row.satellite in primary_satellites and row.test_case in nominal_cases
        ]
        stress_rows = [row for row in rows if row.test_case in stress_cases]

        nominal_data = (
            sum(row.adaptive_data_retention_pct for row in primary_nominal) / len(primary_nominal)
            if primary_nominal
            else 0.0
        )
        all_data = sum(row.adaptive_data_retention_pct for row in rows) / len(rows)
        avg_energy = sum(row.energy_saved_pct for row in rows) / len(rows)
        stress_energy = sum(row.energy_saved_pct for row in stress_rows) / len(stress_rows)
        nominal_energy = sum(row.energy_saved_pct for row in primary_nominal) / len(primary_nominal)
        soc_improvement = sum(row.adaptive_min_soc_pct - row.baseline_min_soc_pct for row in rows) / len(rows)
        critical_soc_delta = sum(row.adaptive_critical_soc_min - row.baseline_critical_soc_min for row in rows)
        cold_charge_risk = sum(row.adaptive_cold_charge_risk_min for row in rows)

        passes_nominal_data_gate = int(nominal_data >= 95.0)
        passes_cold_charge_gate = int(cold_charge_risk == 0)
        nominal_data_penalty = max(0.0, 95.0 - nominal_data) * 6.0
        critical_soc_penalty = max(0, critical_soc_delta) * 0.015
        cold_charge_penalty = cold_charge_risk * 0.05

        score = (
            avg_energy
            + 0.75 * stress_energy
            + 1.25 * nominal_energy
            + 1.50 * soc_improvement
            - nominal_data_penalty
            - critical_soc_penalty
            - cold_charge_penalty
        )
        if not passes_nominal_data_gate:
            score -= 25.0
        if not passes_cold_charge_gate:
            score -= 15.0

        if passes_nominal_data_gate and passes_cold_charge_gate:
            interpretation = "Best-candidate class: preserves nominal science while still adding protection."
        elif not passes_nominal_data_gate:
            interpretation = "Rejected for nominal mission use: data loss is too high."
        else:
            interpretation = "Rejected for safety: leaves cold-charge risk in the model."

        scores.append(
            ArchitectureScore(
                architecture=architecture.name,
                rank=0,
                score=score,
                nominal_data_retention_pct=nominal_data,
                all_case_data_retention_pct=all_data,
                average_energy_saved_pct=avg_energy,
                stress_energy_saved_pct=stress_energy,
                nominal_energy_saved_pct=nominal_energy,
                average_min_soc_improvement_pct=soc_improvement,
                critical_soc_minutes_delta=critical_soc_delta,
                cold_charge_risk_minutes=cold_charge_risk,
                passes_nominal_data_gate=passes_nominal_data_gate,
                passes_cold_charge_gate=passes_cold_charge_gate,
                interpretation=interpretation,
            )
        )

    scores.sort(key=lambda row: row.score, reverse=True)
    for rank, row in enumerate(scores, start=1):
        row.rank = rank
    return scores


def reference_selection_rows() -> list[dict[str, object]]:
    return [
        {
            "reference": "Quetzal-1",
            "included": "yes",
            "reason": "Enough public battery topology, bus load, heater load, and orbit/EPS behavior for a full 1U logic comparison.",
        },
        {
            "reference": "MinXSS-1",
            "included": "yes",
            "reason": "Enough public 3U battery, solar, Science/Safe/Phoenix power, and orbit cases for a full logic comparison.",
        },
        {
            "reference": "Aalto-1",
            "included": "yes-with-caveat",
            "reason": "Good public standby/peak load table and usable battery/solar values from public mission-design sources; treated as medium confidence.",
        },
        {
            "reference": "BIRDS bus",
            "included": "no",
            "reason": "Excellent telemetry/SOC dataset, but not a complete standalone load budget for energy/data-rate comparison.",
        },
        {
            "reference": "SwissCube",
            "included": "no",
            "reason": "Strong thermal/heater threshold reference, but public bus/load details are incomplete for full energy/data benchmark.",
        },
        {
            "reference": "CSSWE",
            "included": "no",
            "reason": "Good architecture and battery Wh reference, but public load schedule is not complete enough for data-rate comparison.",
        },
        {
            "reference": "MarCO-A/B",
            "included": "no",
            "reason": "Excellent 6U solar/battery architecture reference, but public average/peak spacecraft load schedule is not exposed enough for the full comparison.",
        },
        {
            "reference": "RainCube / ISARA",
            "included": "no",
            "reason": "Useful high-power payload or array scenarios, but public EPS/battery/load schedules are incomplete.",
        },
    ]


def run_all(write_traces: bool = False) -> tuple[list[ComparisonSummary], list[dict[str, object]]]:
    summaries: list[ComparisonSummary] = []
    coverage: list[dict[str, object]] = []
    all_adaptive_modes: set[str] = set()
    trace_rows: list[Sample] = []

    for profile in SATELLITES:
        for case in build_cases(profile):
            baseline = simulate(profile, case, "baseline")
            for architecture in ARCHITECTURES:
                adaptive = simulate(profile, case, architecture.name)
                summary = summarize_pair(profile, case, architecture, baseline, adaptive)
                summaries.append(summary)
                modes = sorted({row.mode for row in adaptive})
                all_adaptive_modes.update(modes)
                coverage.append(
                    {
                        "satellite": profile.name,
                        "test_case": case.name,
                        "architecture": architecture.name,
                        **{mode: int(mode in modes) for mode in MODES},
                        "modes_seen": ";".join(modes),
                    }
                )
                if (
                    write_traces
                    and architecture.name in {"improved_firmware", "science_first", "current_adaptive"}
                    and case.name in {"short_2_orbit", "mode_sweep_1_day"}
                ):
                    trace_rows.extend(baseline)
                    trace_rows.extend(adaptive)

    write_csv(LOG_DIR / "multi_cubesat_logic_benchmark_summary.csv", summaries)
    write_csv(LOG_DIR / "multi_cubesat_architecture_scores.csv", score_architectures(summaries))
    write_dict_csv(LOG_DIR / "multi_cubesat_mode_coverage.csv", coverage)
    write_dict_csv(LOG_DIR / "multi_cubesat_reference_selection.csv", reference_selection_rows())
    if write_traces:
        write_csv(LOG_DIR / "multi_cubesat_logic_traces.csv", trace_rows)

    missing = sorted(set(MODES) - all_adaptive_modes)
    return summaries, [{"missing_mode": mode} for mode in missing]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-CubeSat adaptive EPS logic benchmark.")
    parser.add_argument("--write-traces", action="store_true", help="Write selected minute-level traces.")
    parser.add_argument("--assert-full-mode-coverage", action="store_true", help="Fail if any adaptive firmware mode is untested.")
    parser.add_argument("--summary-only", action="store_true", help="Print compact summary rows.")
    args = parser.parse_args()

    summaries, missing = run_all(write_traces=args.write_traces)
    if args.assert_full_mode_coverage and missing:
        raise SystemExit(f"Missing adaptive mode coverage: {', '.join(row['missing_mode'] for row in missing)}")
    if args.summary_only:
        for row in score_architectures(summaries):
            print(
                f"rank {row.rank}: {row.architecture} score={row.score:.2f} "
                f"nominal_data={row.nominal_data_retention_pct:.2f}% "
                f"avg_save={row.average_energy_saved_pct:.2f}% "
                f"stress_save={row.stress_energy_saved_pct:.2f}%"
            )
        print("")
        for row in summaries:
            if row.architecture in {"improved_firmware", "science_first", "current_adaptive"} and row.test_case in {"nominal_1_day", "mode_sweep_1_day"}:
                print(
                    f"{row.architecture} {row.satellite} {row.test_case}: saved={row.energy_saved_pct:.2f}% "
                    f"data={row.adaptive_data_retention_pct:.2f}% "
                    f"minSOC baseline/adaptive={row.baseline_min_soc_pct:.1f}/{row.adaptive_min_soc_pct:.1f}%"
                )


if __name__ == "__main__":
    main()
