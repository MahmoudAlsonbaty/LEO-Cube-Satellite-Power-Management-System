#!/usr/bin/env python3
"""Validate final Aether-Albedo-1 analytical outputs.

This script intentionally checks relationships between generated CSV values
instead of hard-coding only the rounded headline numbers. It is meant to catch
stale documentation tables, incomplete result files, and broken projection math
after model edits.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "results" / "validation_logs"
DOCS_TO_SCAN = [
    ROOT / "README.md",
    ROOT / "docs" / "ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md",
    ROOT / "docs" / "COLD_SEASON_ANALYTICAL_MODEL.md",
    ROOT / "docs" / "FINAL_EVIDENCE_SHEET.md",
    ROOT / "docs" / "FINAL_TECHNICAL_DOCUMENTATION.md",
    ROOT / "docs" / "FINAL_PRESENTATION_5_MINUTE_OUTLINE.md",
    ROOT / "docs" / "ALBEDO_CUBESAT_CASE_STUDY.md",
    ROOT / "docs" / "FLIGHT_PROVEN_EPS_RESEARCH_NOTES.md",
    ROOT / "docs" / "FINAL_REPO_VALIDATION_AUDIT.md",
]

EXPECTED_SCENARIOS = {
    "warm_nominal_year",
    "realistic_cold_season_year",
    "cold_long_eclipse_stress_year",
}
EXPECTED_DESIGNS = {
    "no_charge_temp_gate_baseline",
    "quetzal_style_heater_protected_baseline",
    "our_adaptive_albedo",
}
EXPECTED_YEARS = {1.0, 3.0, 5.0}

STALE_PATTERNS = [
    r"latched at 1 C",
    r"25% thermostatic",
    r"Modest Quetzal-style baseline",
    r"0\.50%",
    r"0\.70%",
    r"60\.96%",
    r"48\.12%",
    r"one annual cold-season block",
    r"one annual cold-season stress block",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def close(actual: float, expected: float, tol: float = 1e-9) -> bool:
    return math.isclose(actual, expected, rel_tol=tol, abs_tol=tol)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_model_rows(rows: list[dict[str, str]]) -> None:
    keys = {
        (row["scenario"], row["design"], float(row["years"]))
        for row in rows
    }
    expected = {
        (scenario, design, year)
        for scenario in EXPECTED_SCENARIOS
        for design in EXPECTED_DESIGNS
        for year in EXPECTED_YEARS
    }
    assert_true(keys == expected, f"unexpected scenario/design/year coverage: {keys ^ expected}")

    for row in rows:
        years = float(row["years"])
        checks = [
            ("pattern_consumed_energy_wh", "projected_consumed_energy_kwh"),
            ("pattern_usable_solar_generated_wh", "projected_usable_solar_generated_kwh"),
            ("heater_energy_wh_per_pattern", "projected_heater_energy_kwh"),
            ("payload_energy_wh_per_pattern", "projected_payload_energy_kwh"),
        ]
        for pattern_field, projected_field in checks:
            expected = float(row[pattern_field]) * years / 1000.0
            actual = float(row[projected_field])
            assert_true(
                close(actual, expected),
                f"{row['scenario']} {row['design']} {years}: {projected_field} mismatch",
            )


def validate_comparisons(
    rows: list[dict[str, str]],
    comparisons: list[dict[str, str]],
) -> None:
    by_key = {
        (row["scenario"], row["design"], float(row["years"])): row
        for row in rows
    }
    assert_true(len(comparisons) == 18, "expected 18 comparison rows")

    for comp in comparisons:
        years = float(comp["years"])
        baseline = by_key[(comp["scenario"], comp["baseline_design"], years)]
        adaptive = by_key[(comp["scenario"], comp["adaptive_design"], years)]

        def reduction(base_field: str, adaptive_field: str) -> float:
            base = float(baseline[base_field])
            adap = float(adaptive[adaptive_field])
            return (base - adap) / base * 100.0 if base else 0.0

        expected_values = {
            "average_power_reduction_pct": reduction("average_power_w", "average_power_w"),
            "consumed_energy_reduction_pct": reduction(
                "projected_consumed_energy_kwh",
                "projected_consumed_energy_kwh",
            ),
            "heater_energy_reduction_pct": reduction(
                "projected_heater_energy_kwh",
                "projected_heater_energy_kwh",
            ),
            "capacity_proxy_delta_pct": (
                float(adaptive["estimated_capacity_remaining_pct"])
                - float(baseline["estimated_capacity_remaining_pct"])
            ),
        }
        for field, expected in expected_values.items():
            actual = float(comp[field])
            assert_true(
                close(actual, expected),
                f"{comp['scenario']} {comp['baseline_design']} {years}: {field} mismatch",
            )


def validate_headline_targets(rows: list[dict[str, str]]) -> None:
    by_key = {
        (row["scenario"], row["design"], float(row["years"])): row
        for row in rows
    }
    for scenario in ("realistic_cold_season_year", "cold_long_eclipse_stress_year"):
        adaptive = by_key[(scenario, "our_adaptive_albedo", 5.0)]
        assert_true(float(adaptive["data_retention_pct"]) >= 95.0, f"{scenario}: data target missed")
        assert_true(float(adaptive["cold_charge_exposure_hours"]) == 0.0, f"{scenario}: cold charge target missed")

    stress_baseline = by_key[(
        "cold_long_eclipse_stress_year",
        "quetzal_style_heater_protected_baseline",
        5.0,
    )]
    stress_adaptive = by_key[("cold_long_eclipse_stress_year", "our_adaptive_albedo", 5.0)]
    assert_true(
        float(stress_adaptive["estimated_capacity_remaining_pct"])
        > float(stress_baseline["estimated_capacity_remaining_pct"]),
        "stress-year capacity proxy should beat protected baseline",
    )


def validate_docs() -> None:
    stale = []
    for path in DOCS_TO_SCAN:
        text = path.read_text(encoding="utf-8")
        for pattern in STALE_PATTERNS:
            if re.search(pattern, text):
                stale.append(f"{path.relative_to(ROOT)}: {pattern}")
    assert_true(not stale, "stale final-doc phrases found:\n" + "\n".join(stale))


def main() -> None:
    model_rows = read_rows(RESULT_DIR / "cold_season_analytical_model.csv")
    comparison_rows = read_rows(RESULT_DIR / "cold_season_analytical_comparison.csv")

    validate_model_rows(model_rows)
    validate_comparisons(model_rows, comparison_rows)
    validate_headline_targets(model_rows)
    validate_docs()

    print("PASS final analytical output validation")
    print(f"checked model rows: {len(model_rows)}")
    print(f"checked comparison rows: {len(comparison_rows)}")
    print("checked final docs for stale obsolete phrases")


if __name__ == "__main__":
    main()
