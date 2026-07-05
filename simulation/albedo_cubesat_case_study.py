#!/usr/bin/env python3
"""
Design-under-test case for an albedo-focused 1U CubeSat.

The published spacecraft in multi_cubesat_logic_benchmark.py remain source
baselines. This file adds a plausible project spacecraft that uses the same
adaptive state machine, a lower battery-heater assumption, and the payload duty
parameters found in the energy/data sweep.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from multi_cubesat_logic_benchmark import (
    ARCHITECTURE_BY_NAME,
    LOG_DIR,
    SATELLITES,
    Architecture,
    SatelliteProfile,
    TestCase,
    build_cases,
    simulate,
    summarize_pair,
)


YEAR_DAYS = 365.25
USABLE_SOLAR_EFFICIENCY = 0.85


ALBEDO_PROFILE = SatelliteProfile(
    name="Aether-Albedo-1",
    size_class="1U assumed",
    standby_w=0.66370,
    payload_active_w=0.123,
    peak_total_w=0.997,
    heater_w=0.6735,
    battery_wh=14.8,
    solar_w=2.37,
    nominal_orbit_min=94.469,
    nominal_eclipse_min=31.5,
    source_confidence="Medium design-under-test",
    source_notes=(
        "Assumed albedo 1U profile. Quetzal-1 public EPS values provide the "
        "1S2P 14.8 Wh battery, 0.6637 W heater-off bus, 2.37 W transferred "
        "solar input, and orbit scale. The project albedo payload keeps the "
        "0.123 W active sensor load. Heater power is set to 0.6735 W, which is "
        "75 percent of the Quetzal-1 0.898 W heater and is treated as a "
        "thermal-design assumption requiring bench or thermal-vac validation."
    ),
)


ALBEDO_TUNED_ARCHITECTURE = Architecture(
    name="albedo_tuned_95data",
    description=(
        "Same adaptive payload/heater state machine, tuned for the cold-season "
        "science-preserving schedule: 95 percent scheduled duty, 35 percent "
        "power-save duty, and 80 percent pre-eclipse duty with heater pulse "
        "logic unchanged."
    ),
    science_duty=1.00,
    scheduled_duty=0.95,
    power_save_duty=0.35,
    pre_eclipse_duty=0.80,
    heater_low_duty=0.20,
    heater_strong_duty=0.35,
    heater_survival_duty=1.00,
)


@dataclass(frozen=True)
class AssumptionRow:
    parameter: str
    value: str
    source_or_basis: str
    confidence: str
    note: str


@dataclass(frozen=True)
class AlbedoComparisonRow:
    test_case: str
    architecture: str
    baseline_avg_power_w: float
    adaptive_avg_power_w: float
    energy_saved_pct: float
    data_retention_pct: float
    baseline_min_soc_pct: float
    adaptive_min_soc_pct: float
    baseline_heater_on_min: int
    adaptive_heater_on_min: int
    baseline_cold_charge_risk_min: int
    adaptive_cold_charge_risk_min: int
    modes_seen: str
    interpretation: str


@dataclass(frozen=True)
class ReferencePowerRow:
    test_case: str
    source: str
    size_class: str
    design: str
    avg_power_w: float
    avg_power_w_per_u: float
    energy_wh: float
    data_units: float
    min_soc_pct: float
    heater_on_min: int
    note: str


@dataclass(frozen=True)
class SourceDeltaRow:
    test_case: str
    our_design: str
    source_baseline: str
    source_size_class: str
    our_avg_power_w: float
    source_avg_power_w: float
    avg_power_delta_w: float
    avg_power_reduction_pct: float
    our_avg_power_w_per_u: float
    source_avg_power_w_per_u: float
    per_u_reduction_pct: float
    our_data_units: float
    source_data_units: float
    our_min_soc_pct: float
    source_min_soc_pct: float
    interpretation: str


@dataclass(frozen=True)
class BatteryHealthRow:
    test_case: str
    design: str
    years: float
    average_load_w: float
    net_energy_per_day_wh: float
    sustainable_energy_balance: int
    estimated_days_to_empty: float
    data_retention_pct: float
    equivalent_full_cycles: float
    low_soc_days: float
    critical_soc_days: float
    cold_charge_hours: float
    estimated_capacity_remaining_pct: float
    interpretation: str


OUR_ARCHITECTURES = ("improved_firmware", ALBEDO_TUNED_ARCHITECTURE.name)


def write_csv(path: Path, rows: list[object]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def energy_wh(rows) -> float:
    return sum(row.power_w for row in rows) / 60.0


def data_units(rows) -> float:
    return sum(row.data_units for row in rows)


def usable_generation_wh(rows) -> float:
    return sum(
        (row.generated_w * USABLE_SOLAR_EFFICIENCY if row.charge_allowed else 0.0) / 60.0
        for row in rows
    )


def discharge_wh(rows) -> float:
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
    sustainable: bool,
) -> float:
    calendar_fade_pct = 1.5 * years
    cycle_fade_pct = 0.018 * equivalent_full_cycles
    low_soc_fade_pct = 0.00010 * low_soc_hours
    critical_soc_fade_pct = 0.00040 * critical_soc_hours
    cold_charge_fade_pct = 0.02 * cold_charge_hours
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


def size_units(size_class: str) -> float:
    if size_class.startswith("1U"):
        return 1.0
    if size_class.startswith("3U"):
        return 3.0
    if size_class.startswith("6U"):
        return 6.0
    return 1.0


def assumptions() -> list[AssumptionRow]:
    return [
        AssumptionRow(
            parameter="Form factor",
            value="1U CubeSat",
            source_or_basis="Quetzal-1 1U reference from supplied EPS flight-proven PDF",
            confidence="medium-high",
            note="Used because the project concept is a compact albedo payload, not a high-power 3U/6U instrument.",
        ),
        AssumptionRow(
            parameter="Battery capacity",
            value="14.8 Wh",
            source_or_basis="Quetzal-1: two 3.7 V, 2000 mAh Li-ion polymer cells in parallel",
            confidence="high for baseline transfer",
            note="Kept equal to the 1U flight reference for a conservative battery comparison.",
        ),
        AssumptionRow(
            parameter="Solar input",
            value="2.37 W",
            source_or_basis="Existing Quetzal-1 transferred solar-generation assumption in project benchmark",
            confidence="medium",
            note="Appropriate for a 1U body-mounted-panel scale, but final value depends on panel layout and pointing.",
        ),
        AssumptionRow(
            parameter="Heater-off bus load",
            value="0.66370 W",
            source_or_basis="Quetzal-1 public heater-off spacecraft/EPS load",
            confidence="high for reference, medium for transfer",
            note="Used as the no-logic bus burden so the comparison remains conservative.",
        ),
        AssumptionRow(
            parameter="Albedo payload active load",
            value="0.123 W",
            source_or_basis="Current project albedo payload load used in firmware benchmark",
            confidence="medium",
            note="Represents a low-power visible/albedo sensing payload, not a high-power active instrument.",
        ),
        AssumptionRow(
            parameter="Battery heater on-power",
            value="0.6735 W",
            source_or_basis="75 percent of Quetzal-1 0.898 W heater; NASA SmallSat thermal-control guidance supports low heater power as plausible for low-mass SmallSats",
            confidence="medium assumption",
            note="This is the main hardware assumption and must be validated with thermal testing.",
        ),
        AssumptionRow(
            parameter="Adaptive payload settings",
            value="100% science, 95% scheduled, 35% power-save, 80% pre-eclipse",
            source_or_basis="Cold payload schedule sweep preserving at least 95% data with meaningful cold-case energy savings",
            confidence="model-derived",
            note="Payload is still shut off in eclipse, fault, thermal-safe, and low-SOC-safe modes.",
        ),
        AssumptionRow(
            parameter="Adaptive heater settings",
            value="20% low pulse, 35% strong pulse, 100% critical cold heater",
            source_or_basis="Current firmware heater policy held constant during payload schedule tuning",
            confidence="model-derived",
            note="Charge remains inhibited below 0 C and above 45 C.",
        ),
    ]


def selected_cases(profile: SatelliteProfile) -> list[TestCase]:
    cases = [
        case
        for case in build_cases(profile)
        if case.name in {
            "nominal_1_day",
            "long_eclipse_1_day",
            "high_beta_1_day",
            "mode_sweep_1_day",
            "projection_30_day",
        }
    ]
    cases.extend(
        [
            TestCase(
                name="cold_nominal_eclipse_30_day",
                duration_min=30 * 24 * 60,
                orbit_min=profile.nominal_orbit_min,
                eclipse_min=profile.nominal_eclipse_min,
                initial_soc_pct=82.0,
                initial_battery_temp_c=5.0,
                sun_temp_c=22.0,
                eclipse_temp_c=-20.0,
            ),
            TestCase(
                name="cold_long_eclipse_30_day",
                duration_min=30 * 24 * 60,
                orbit_min=profile.nominal_orbit_min,
                eclipse_min=min(profile.nominal_orbit_min - 5.0, profile.nominal_eclipse_min + 10.0),
                initial_soc_pct=82.0,
                initial_battery_temp_c=5.0,
                sun_temp_c=22.0,
                eclipse_temp_c=-20.0,
            ),
        ]
    )
    return cases


def interpretation(row) -> str:
    if row.energy_saved_pct >= 5.0 and row.adaptive_data_retention_pct >= 95.0:
        return "Target hit: high data retention with meaningful energy reduction."
    if row.adaptive_data_retention_pct >= 95.0:
        return "Science-preserving case; energy saving is small because the heater is not active much."
    return "Stress/survival case; not a nominal science-collection claim."


def battery_interpretation(
    sustainable: bool,
    days_to_empty: float,
    data_retention_pct: float,
    cold_charge_hours: float,
    capacity_pct: float,
) -> str:
    if not sustainable:
        return f"Power-negative; estimated depletion in {days_to_empty:.1f} days if repeated."
    if cold_charge_hours > 0:
        return "Energy-positive but unsafe: repeated cold-charge exposure accelerates degradation risk."
    if data_retention_pct < 95.0:
        return "Battery-safe in the proxy, but science return is degraded under this cold/stress pattern."
    if capacity_pct < 80.0:
        return "Energy-positive and cold-charge safe, but accumulated cycling is high."
    return "Energy-positive, cold-charge safe, and acceptable in the generic degradation proxy."


def build_health_rows(
    case: TestCase,
    design: str,
    rows,
    baseline_data: float,
    years_list: tuple[float, ...] = (1.0, 3.0, 5.0),
) -> list[BatteryHealthRow]:
    duration_h = len(rows) / 60.0
    pattern_consumed = energy_wh(rows)
    pattern_generated = usable_generation_wh(rows)
    pattern_net = pattern_generated - pattern_consumed
    daily_net = pattern_net * 24.0 / duration_h
    pattern_discharge = discharge_wh(rows)
    low_soc_min = sum(row.soc_pct < 40.0 for row in rows)
    critical_soc_min = sum(row.soc_pct < 25.0 for row in rows)
    cold_charge_min = sum(row.cold_charge_risk for row in rows)
    pattern_data = data_units(rows)

    if daily_net < 0.0:
        initial_available_wh = ALBEDO_PROFILE.battery_wh * case.initial_soc_pct / 100.0
        days_to_empty = initial_available_wh / abs(daily_net)
    else:
        days_to_empty = -1.0

    output: list[BatteryHealthRow] = []
    for years in years_list:
        repeats = years * YEAR_DAYS * 24.0 / duration_h
        checkpoint_days = years * YEAR_DAYS
        sustainable = pattern_net >= -1e-9
        if days_to_empty > 0.0 and days_to_empty < checkpoint_days:
            sustainable = False

        efc = pattern_discharge * repeats / ALBEDO_PROFILE.battery_wh
        low_soc_days = low_soc_min * repeats / 1440.0
        critical_soc_days = critical_soc_min * repeats / 1440.0
        cold_charge_hours = cold_charge_min * repeats / 60.0
        data_retention = pattern_data / baseline_data * 100.0 if baseline_data else 0.0
        capacity_pct = capacity_remaining_pct(
            years=years,
            equivalent_full_cycles=efc,
            low_soc_hours=low_soc_days * 24.0,
            critical_soc_hours=critical_soc_days * 24.0,
            cold_charge_hours=cold_charge_hours,
            sustainable=sustainable,
        )
        output.append(
            BatteryHealthRow(
                test_case=case.name,
                design=design,
                years=years,
                average_load_w=pattern_consumed / duration_h,
                net_energy_per_day_wh=daily_net,
                sustainable_energy_balance=int(sustainable),
                estimated_days_to_empty=days_to_empty,
                data_retention_pct=data_retention,
                equivalent_full_cycles=efc,
                low_soc_days=low_soc_days,
                critical_soc_days=critical_soc_days,
                cold_charge_hours=cold_charge_hours,
                estimated_capacity_remaining_pct=capacity_pct,
                interpretation=battery_interpretation(
                    sustainable=sustainable,
                    days_to_empty=days_to_empty,
                    data_retention_pct=data_retention,
                    cold_charge_hours=cold_charge_hours,
                    capacity_pct=capacity_pct,
                ),
            )
        )
    return output


def run_case_study() -> tuple[
    list[AlbedoComparisonRow],
    list[ReferencePowerRow],
    list[SourceDeltaRow],
    list[BatteryHealthRow],
]:
    ARCHITECTURE_BY_NAME[ALBEDO_TUNED_ARCHITECTURE.name] = ALBEDO_TUNED_ARCHITECTURE

    comparison_rows: list[AlbedoComparisonRow] = []
    reference_rows: list[ReferencePowerRow] = []
    source_delta_rows: list[SourceDeltaRow] = []
    health_rows: list[BatteryHealthRow] = []
    our_adaptive_by_case: dict[tuple[str, str], ReferencePowerRow] = {}

    for case in selected_cases(ALBEDO_PROFILE):
        baseline = simulate(ALBEDO_PROFILE, case, "baseline")
        baseline_data = data_units(baseline)
        health_rows.extend(build_health_rows(case, "baseline", baseline, baseline_data))
        for architecture_name in OUR_ARCHITECTURES:
            architecture = ARCHITECTURE_BY_NAME[architecture_name]
            adaptive = simulate(ALBEDO_PROFILE, case, architecture_name)
            health_rows.extend(build_health_rows(case, architecture_name, adaptive, baseline_data))
            summary = summarize_pair(
                ALBEDO_PROFILE,
                case,
                architecture,
                baseline,
                adaptive,
            )
            comparison_rows.append(
                AlbedoComparisonRow(
                    test_case=case.name,
                    architecture=architecture_name,
                    baseline_avg_power_w=summary.baseline_avg_power_w,
                    adaptive_avg_power_w=summary.adaptive_avg_power_w,
                    energy_saved_pct=summary.energy_saved_pct,
                    data_retention_pct=summary.adaptive_data_retention_pct,
                    baseline_min_soc_pct=summary.baseline_min_soc_pct,
                    adaptive_min_soc_pct=summary.adaptive_min_soc_pct,
                    baseline_heater_on_min=summary.baseline_heater_on_min,
                    adaptive_heater_on_min=summary.adaptive_heater_on_min,
                    baseline_cold_charge_risk_min=summary.baseline_cold_charge_risk_min,
                    adaptive_cold_charge_risk_min=summary.adaptive_cold_charge_risk_min,
                    modes_seen=summary.adaptive_modes_seen,
                    interpretation=interpretation(summary),
                )
            )

        duration_h = case.duration_min / 60.0
        design_rows = [
            ("same-hardware baseline, no adaptive logic", baseline, "Our assumed albedo CubeSat hardware without adaptive payload/charge logic."),
        ]
        for architecture_name in OUR_ARCHITECTURES:
            design_rows.append(
                (
                    f"our adaptive logic ({architecture_name})",
                    simulate(ALBEDO_PROFILE, case, architecture_name),
                    f"Our assumed albedo CubeSat using {architecture_name}.",
                )
            )
        for design_name, rows, note in design_rows:
            avg_power = energy_wh(rows) / duration_h
            reference_rows.append(
                row := ReferencePowerRow(
                    test_case=case.name,
                    source=ALBEDO_PROFILE.name,
                    size_class=ALBEDO_PROFILE.size_class,
                    design=design_name,
                    avg_power_w=avg_power,
                    avg_power_w_per_u=avg_power / size_units(ALBEDO_PROFILE.size_class),
                    energy_wh=energy_wh(rows),
                    data_units=data_units(rows),
                    min_soc_pct=min(row.soc_pct for row in rows),
                    heater_on_min=sum(row.heater_on for row in rows),
                    note=note,
                )
            )
            for architecture_name in OUR_ARCHITECTURES:
                if design_name == f"our adaptive logic ({architecture_name})":
                    our_adaptive_by_case[(case.name, architecture_name)] = row

    for profile in SATELLITES:
        case_by_name = {case.name: case for case in build_cases(profile)}
        for case_name in [
            "nominal_1_day",
            "long_eclipse_1_day",
            "high_beta_1_day",
            "mode_sweep_1_day",
            "projection_30_day",
        ]:
            if case_name not in case_by_name:
                continue
            case = case_by_name[case_name]
            rows = simulate(profile, case, "baseline")
            duration_h = case.duration_min / 60.0
            avg_power = energy_wh(rows) / duration_h
            reference_rows.append(
                ReferencePowerRow(
                    test_case=case_name,
                    source=profile.name,
                    size_class=profile.size_class,
                    design="published-load baseline, no project logic",
                    avg_power_w=avg_power,
                    avg_power_w_per_u=avg_power / size_units(profile.size_class),
                    energy_wh=energy_wh(rows),
                    data_units=data_units(rows),
                    min_soc_pct=min(row.soc_pct for row in rows),
                    heater_on_min=sum(row.heater_on for row in rows),
                    note=profile.source_notes,
                )
            )
            for architecture_name in OUR_ARCHITECTURES:
                our = our_adaptive_by_case[(case_name, architecture_name)]
                source_w_per_u = avg_power / size_units(profile.size_class)
                our_w_per_u = our.avg_power_w / size_units(ALBEDO_PROFILE.size_class)
                reduction_pct = (avg_power - our.avg_power_w) / avg_power * 100.0 if avg_power else 0.0
                per_u_reduction_pct = (
                    (source_w_per_u - our_w_per_u) / source_w_per_u * 100.0
                    if source_w_per_u
                    else 0.0
                )
                if profile.name == "Quetzal-1" and case_name == "nominal_1_day":
                    delta_note = "Near parity with the 1U source baseline; our payload adds load and the heater is inactive."
                elif profile.name == "Quetzal-1" and case_name == "long_eclipse_1_day":
                    delta_note = "Meaningful 1U cold-case reduction from lower heater power and adaptive charge/payload policy."
                elif profile.size_class != "1U":
                    delta_note = "Lower absolute power, but size and mission class are different; use as context, not a direct win claim."
                elif reduction_pct > 0:
                    delta_note = "Lower average power than the source baseline for this modeled case."
                else:
                    delta_note = "Higher average power than the source baseline for this modeled case."
                source_delta_rows.append(
                    SourceDeltaRow(
                        test_case=case_name,
                        our_design=architecture_name,
                        source_baseline=profile.name,
                        source_size_class=profile.size_class,
                        our_avg_power_w=our.avg_power_w,
                        source_avg_power_w=avg_power,
                        avg_power_delta_w=our.avg_power_w - avg_power,
                        avg_power_reduction_pct=reduction_pct,
                        our_avg_power_w_per_u=our_w_per_u,
                        source_avg_power_w_per_u=source_w_per_u,
                        per_u_reduction_pct=per_u_reduction_pct,
                        our_data_units=our.data_units,
                        source_data_units=data_units(rows),
                        our_min_soc_pct=our.min_soc_pct,
                        source_min_soc_pct=min(row.soc_pct for row in rows),
                        interpretation=delta_note,
                    )
                )

    write_csv(LOG_DIR / "albedo_cubesat_assumptions.csv", assumptions())
    write_csv(LOG_DIR / "albedo_cubesat_logic_comparison.csv", comparison_rows)
    write_csv(LOG_DIR / "albedo_cubesat_reference_power_comparison.csv", reference_rows)
    write_csv(LOG_DIR / "albedo_cubesat_source_delta.csv", source_delta_rows)
    write_csv(LOG_DIR / "albedo_cubesat_battery_health_projection.csv", health_rows)
    return comparison_rows, reference_rows, source_delta_rows, health_rows


def main() -> None:
    comparison_rows, reference_rows, source_delta_rows, health_rows = run_case_study()
    print("Aether-Albedo-1 adaptive logic results")
    for row in comparison_rows:
        if row.architecture == "improved_firmware":
            print(
                f"{row.test_case}: avg {row.baseline_avg_power_w:.3f}W -> "
                f"{row.adaptive_avg_power_w:.3f}W, saved={row.energy_saved_pct:.2f}%, "
                f"data={row.data_retention_pct:.2f}%, minSOC="
                f"{row.baseline_min_soc_pct:.1f}/{row.adaptive_min_soc_pct:.1f}%"
            )
    print("")
    print("Nominal average-power comparison")
    for row in reference_rows:
        if row.test_case == "nominal_1_day":
            print(
                f"{row.source} ({row.design}): {row.avg_power_w:.3f} W "
                f"({row.avg_power_w_per_u:.3f} W/U)"
            )
    print("")
    print("Our adaptive albedo CubeSat versus no-project-logic sources")
    for row in source_delta_rows:
        if row.our_design == "improved_firmware" and row.test_case in {"nominal_1_day", "long_eclipse_1_day"}:
            print(
                f"{row.test_case} vs {row.source_baseline}: "
                f"{row.avg_power_reduction_pct:.2f}% average-power reduction "
                f"({row.our_avg_power_w:.3f}W vs {row.source_avg_power_w:.3f}W)"
            )
    print("")
    print("5-year battery-health proxy")
    for row in health_rows:
        if (
            row.design in {"baseline", "improved_firmware"}
            and row.years == 5.0
            and row.test_case in {"projection_30_day", "cold_long_eclipse_30_day"}
        ):
            print(
                f"{row.test_case} {row.design}: cap={row.estimated_capacity_remaining_pct:.1f}% "
                f"efc={row.equivalent_full_cycles:.0f} cold_charge={row.cold_charge_hours:.0f}h "
                f"{row.interpretation}"
            )


if __name__ == "__main__":
    main()
