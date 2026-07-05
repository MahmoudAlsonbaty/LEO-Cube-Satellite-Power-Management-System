# Albedo CubeSat Design-Under-Test Case Study

## Purpose

This file records the project-specific spacecraft profile, `Aether-Albedo-1`.
It is an auxiliary case-study document. The final annual comparison is
`docs/COLD_SEASON_ANALYTICAL_MODEL.md` and the single audit trail is
`docs/ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md`.

## Design-Under-Test Assumptions

| Parameter | Value | Basis |
| --- | ---: | --- |
| Form factor | 1U | Compact albedo payload; Quetzal-1 used as 1U EPS reference |
| Battery | 14.8 Wh | Quetzal-style 1S2P Li-ion pack scale |
| Solar input | 2.37 W | Existing Quetzal-scale 1U model assumption |
| Heater-off bus load | 0.66370 W | Lumped Quetzal-scale heater-off spacecraft/bus context |
| Albedo payload active load | 0.123 W | Current project albedo payload model |
| Our analytical heater power | 0.6735 W | 75% of Quetzal-style 0.898 W heater |
| Protected baseline heater power | 0.898 W | Quetzal-style heater hardware scale |
| Payload policy | 100%, 95%, 35%, 80%, 0% | Final tuned firmware ratios |
| Heater policy | 20%, 35%, 100% | Final tuned firmware ratios |
| Charge gate | 0 C to 45 C | Final tuned firmware rule |

The lower-heater assumption is plausible but not flight-proven. It remains a
modeling assumption that requires bench and thermal-vac validation.

## Final Annual Model Summary

Five-year projection versus the protected Quetzal-style baseline:

| Scenario | Energy saved | Heater saved | Data retained | Cold charge | Battery proxy |
| --- | ---: | ---: | ---: | ---: | ---: |
| `warm_nominal_year` | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 71.70% -> 71.73% |
| `realistic_cold_season_year` | 6.51% | 90.48% | 98.29% | 0 h -> 0 h | 67.26% -> 71.38% |
| `cold_long_eclipse_stress_year` | 8.59% | 86.73% | 98.19% | 0 h -> 0 h | 52.94% -> 71.14% |

Interpretation: nominal operation remains near parity. The cold-season value is
not a large annual energy reduction; it is heater reduction, charge safety, and
slightly improved comparative battery-health proxy while preserving more than
98% of daylight science opportunity.

## Source Context

The source spacecraft remain:

| Source | Role |
| --- | --- |
| Quetzal-1 | Main 1U EPS/heater/battery scale reference. |
| MinXSS-1 | 3U active science power-context reference only. |
| Aalto-1 | 3U high-load multi-rail context reference only. |

The 3U comparisons are context only and are not used as the headline improvement
claim because they compare different spacecraft sizes and mission types.

## Battery-Degradation Caveat

The battery-health projection is a transparent comparative proxy:

| Aging term | Proxy assumption |
| --- | --- |
| Calendar fade | 1.5 percent per year |
| Cycle fade | 9 percent per 500 equivalent full cycles |
| Low-SOC exposure | Small penalty below 40 percent SOC |
| Critical-SOC exposure | Larger penalty below 25 percent SOC |
| Cold charging | Penalty for charge below 0 C |

This is not a cell-qualified lifetime model. It is a comparative screen for the
same assumed 14.8 Wh battery.

## Generated Files

| File | Purpose |
| --- | --- |
| `simulation/albedo_cubesat_case_study.py` | Auxiliary project-specific albedo CubeSat case-study script. |
| `simulation/cold_season_analytical_model.py` | Final annual analytical model. |
| `results/validation_logs/cold_season_analytical_model.csv` | Full annual model rows. |
| `results/validation_logs/cold_season_analytical_comparison.csv` | Baseline-versus-adaptive annual comparison rows. |

## Reproduce

```bash
python3 simulation/cold_season_analytical_model.py --summary-only
python3 simulation/albedo_cubesat_case_study.py
```
