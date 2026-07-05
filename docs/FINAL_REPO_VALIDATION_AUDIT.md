# Final Repo Validation Audit

## Purpose

This file records the final validation and cleanup boundary for the
Aether-Albedo-1 analytical model package. It separates final evidence from
older exploratory material so that the project does not depend on stale CSVs,
workbooks, or plots.

## Final Evidence Set

| Category | Final files |
| --- | --- |
| Firmware | `src/ESP32 Firmware.cpp` |
| Annual analytical model | `simulation/cold_season_analytical_model.py` |
| Firmware smoke test | `simulation/test_adaptive_eps_logic.py` |
| Output validator | `simulation/validate_final_outputs.py` |
| Main documentation | `README.md`, `docs/FINAL_TECHNICAL_DOCUMENTATION.md`, `docs/ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md`, `docs/COLD_SEASON_ANALYTICAL_MODEL.md`, `docs/FINAL_EVIDENCE_SHEET.md` |
| Source/citation notes | `docs/FLIGHT_PROVEN_EPS_RESEARCH_NOTES.md` |
| Final CSV outputs | `results/validation_logs/cold_season_analytical_model.csv`, `results/validation_logs/cold_season_analytical_comparison.csv`, `results/validation_logs/cold_season_analytical_scenarios.csv`, `results/validation_logs/cold_season_analytical_design_assumptions.csv`, `results/validation_logs/albedo_cubesat_assumptions.csv` |
| Final figures | `results/figures/nominal_year_*`, `results/figures/realistic_cold_season_year_*`, `results/figures/cold_long_eclipse_stress_year_*` |

## Legacy Or Exploratory Material

The following files are useful development history but are not final evidence
for the current analytical claim:

| Material | Status |
| --- | --- |
| `simulation/parameter_sweep_energy_data_trade.py` and `results/validation_logs/parameter_sweep_energy_data_trade.csv` | Earlier tuning exploration; superseded by the final annual analytical model. |
| `simulation/long_duration_eps_projection.py` and `docs/LONG_DURATION_EPS_PROJECTION.md` | Earlier projection approach; superseded by `cold_season_analytical_model.py`. |
| `simulation/visualize_power_metrics.py`, `simulation/build_validation_workbook.py`, workbook/dashboard files, and July 2 figure set | Earlier visualization package; not cited by final docs. |
| Per-scenario trace CSVs such as `nominal_94p5min_*`, `long_eclipse_94p5min_*`, `hot_payload_*`, and `low_soc_survival_*` | Generated traces from earlier benchmark phases; not part of the final annual model. |
| `docs/POWER_VISUALIZATION_GUIDE.md`, `docs/REVAMPED_SYSTEM_ARCHITECTURE.md`, `docs/MULTI_CUBESAT_LOGIC_BENCHMARK.md` | Background and earlier-phase notes; final package cites the concise final docs instead. |

The final packaged project excludes the legacy/exploratory files above. They
can remain in the working repository as provenance, but they should not be used
for final percentages or claims.

## Validation Checks

The final validation script checks:

| Check | Purpose |
| --- | --- |
| Scenario/design/year coverage | Confirms 3 scenarios x 3 designs x 1/3/5-year checkpoints. |
| Projection math | Recomputes projected kWh from annual Wh and checkpoint year. |
| Comparison math | Recomputes average-power, consumed-energy, heater-energy, and capacity-proxy deltas. |
| Headline targets | Confirms our cold-season cases retain at least 95% data and have 0 h cold-charge exposure. |
| Final-doc stale phrases | Catches older obsolete values and phrasing in the final docs. |

Run:

```bash
python3 simulation/cold_season_analytical_model.py --summary-only
python3 simulation/test_adaptive_eps_logic.py
python3 simulation/validate_final_outputs.py
python3 -m py_compile simulation/cold_season_analytical_model.py simulation/test_adaptive_eps_logic.py simulation/validate_final_outputs.py
```

## Source Strength

| Item | Status |
| --- | --- |
| Quetzal 1U EPS, battery, heater, and positive power-budget context | Source-backed by the Quetzal-1 EPS paper/public page and the attached flight-proven reference. |
| BIRDS 1U EPS telemetry/orbit context | Source-backed by the public 1U EPS telemetry dataset. |
| Need for explicit thermal/heater modeling | Source-backed by NASA small-spacecraft thermal-control guidance and SwissCube/BIRDS thermal telemetry context. |
| Exact Aether-Albedo-1 heater power, payload load, derating, thermal response constants, and battery proxy coefficients | Model assumptions requiring future bench, thermal-vac, and cell-specific validation. |
| Cold-season annual schedule | Source-informed analytical assumption, not recovered Quetzal beta telemetry. |
