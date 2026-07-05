#!/usr/bin/env python3
"""
Cold-season payload schedule tuning for the albedo CubeSat EPS study.

This sweep keeps heater and charge safety logic fixed and changes only payload
duty ratios. It targets the cold-long-eclipse 30-day case before the analytical
model is built.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from itertools import product

from albedo_cubesat_case_study import ALBEDO_PROFILE, build_health_rows, selected_cases
from multi_cubesat_logic_benchmark import (
    ARCHITECTURE_BY_NAME,
    LOG_DIR,
    Architecture,
    simulate,
    summarize_pair,
)


SCHEDULED_DUTIES = (0.95, 0.97, 1.00)
POWER_SAVE_DUTIES = (0.35, 0.50, 0.65, 0.80)
PRE_ECLIPSE_DUTIES = (0.25, 0.50, 0.60, 0.70, 0.80, 0.90)


@dataclass(frozen=True)
class ColdPayloadSweepRow:
    test_case: str
    scheduled_duty: float
    power_save_duty: float
    pre_eclipse_duty: float
    energy_saved_pct: float
    data_retention_pct: float
    adaptive_avg_power_w: float
    adaptive_min_soc_pct: float
    cold_charge_minutes: int
    five_year_capacity_remaining_pct: float
    five_year_equivalent_full_cycles: float
    baseline_five_year_capacity_remaining_pct: float
    beats_battery_baseline: int
    meets_data_gate: int
    meets_cold_charge_gate: int
    meets_energy_gate: int
    feasible: int
    modes_seen: str


def energy_gate(saved_pct: float) -> bool:
    return saved_pct >= 8.0


def write_csv(path, rows: list[ColdPayloadSweepRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def run_sweep() -> list[ColdPayloadSweepRow]:
    case = next(
        case
        for case in selected_cases(ALBEDO_PROFILE)
        if case.name == "cold_long_eclipse_30_day"
    )
    baseline = simulate(ALBEDO_PROFILE, case, "baseline")
    baseline_data = sum(row.data_units for row in baseline)
    baseline_health_5y = next(
        row
        for row in build_health_rows(case, "baseline", baseline, baseline_data)
        if row.years == 5.0
    )

    rows: list[ColdPayloadSweepRow] = []
    for scheduled, power_save, pre_eclipse in product(
        SCHEDULED_DUTIES,
        POWER_SAVE_DUTIES,
        PRE_ECLIPSE_DUTIES,
    ):
        name = (
            f"cold_payload_s{round(scheduled * 100):03d}"
            f"_p{round(power_save * 100):03d}"
            f"_e{round(pre_eclipse * 100):03d}"
        )
        architecture = Architecture(
            name=name,
            description="Cold-season payload schedule tuning candidate.",
            science_duty=1.00,
            scheduled_duty=scheduled,
            power_save_duty=power_save,
            pre_eclipse_duty=pre_eclipse,
            heater_low_duty=0.20,
            heater_strong_duty=0.35,
            heater_survival_duty=1.00,
        )
        ARCHITECTURE_BY_NAME[name] = architecture
        adaptive = simulate(ALBEDO_PROFILE, case, name)
        summary = summarize_pair(ALBEDO_PROFILE, case, architecture, baseline, adaptive)
        health_5y = next(
            row
            for row in build_health_rows(case, name, adaptive, baseline_data)
            if row.years == 5.0
        )

        beats_battery_baseline = (
            health_5y.estimated_capacity_remaining_pct
            > baseline_health_5y.estimated_capacity_remaining_pct
        )
        meets_data = summary.adaptive_data_retention_pct >= 95.0
        meets_cold_charge = summary.adaptive_cold_charge_risk_min == 0
        meets_energy = energy_gate(summary.energy_saved_pct)
        rows.append(
            ColdPayloadSweepRow(
                test_case=case.name,
                scheduled_duty=scheduled,
                power_save_duty=power_save,
                pre_eclipse_duty=pre_eclipse,
                energy_saved_pct=summary.energy_saved_pct,
                data_retention_pct=summary.adaptive_data_retention_pct,
                adaptive_avg_power_w=summary.adaptive_avg_power_w,
                adaptive_min_soc_pct=summary.adaptive_min_soc_pct,
                cold_charge_minutes=summary.adaptive_cold_charge_risk_min,
                five_year_capacity_remaining_pct=health_5y.estimated_capacity_remaining_pct,
                five_year_equivalent_full_cycles=health_5y.equivalent_full_cycles,
                baseline_five_year_capacity_remaining_pct=(
                    baseline_health_5y.estimated_capacity_remaining_pct
                ),
                beats_battery_baseline=int(beats_battery_baseline),
                meets_data_gate=int(meets_data),
                meets_cold_charge_gate=int(meets_cold_charge),
                meets_energy_gate=int(meets_energy),
                feasible=int(
                    meets_data
                    and meets_cold_charge
                    and meets_energy
                    and beats_battery_baseline
                ),
                modes_seen=summary.adaptive_modes_seen,
            )
        )
    return rows


def main() -> None:
    rows = run_sweep()
    write_csv(LOG_DIR / "cold_payload_schedule_sweep.csv", rows)

    feasible = [row for row in rows if row.feasible]
    ranked = sorted(
        feasible or rows,
        key=lambda row: (
            -row.feasible,
            -row.energy_saved_pct,
            -row.data_retention_pct,
            -row.five_year_capacity_remaining_pct,
        ),
    )
    print(f"Rows swept: {len(rows)}")
    print(f"Feasible rows: {len(feasible)}")
    print("Top candidates:")
    for row in ranked[:10]:
        print(
            f"sched={row.scheduled_duty:.2f} power_save={row.power_save_duty:.2f} "
            f"pre={row.pre_eclipse_duty:.2f} saved={row.energy_saved_pct:.2f}% "
            f"data={row.data_retention_pct:.2f}% cold_charge={row.cold_charge_minutes}min "
            f"cap5={row.five_year_capacity_remaining_pct:.1f}%"
        )


if __name__ == "__main__":
    main()
