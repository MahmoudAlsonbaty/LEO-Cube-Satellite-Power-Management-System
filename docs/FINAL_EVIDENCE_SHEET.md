# Final Evidence Sheet

## Problem

Cold-season eclipses force a CubeSat EPS to balance science data collection,
battery heating, and safe charging. A simple or weakly protected baseline can
waste heater energy or allow cold-charge exposure during colder orbital
periods.

## Core Function

The Aether-Albedo-1 controller selects operating modes from solar, SOC,
battery-temperature, payload-temperature, and fault inputs. It controls:

- payload rail duty cycle
- battery heater pulse duty
- charge enable / inhibit

## Baselines and Improved Case

| Design | Description |
| --- | --- |
| `no_charge_temp_gate_baseline` | Diagnostic Quetzal-scale stress baseline with no battery charge-temperature gate. |
| `quetzal_style_heater_protected_baseline` | Source-backed Quetzal-style protected estimate: 0.898 W heater hardware, full heater power while thermostat-latched at 3 C, heater off at 5 C, charge allowed above 0 C with imperfect heater-assisted charging down to -0.5 C. |
| `our_adaptive_albedo` | Tuned controller: payload enabled for 60/57/21/48/0 s per 60 s heartbeat, heater enabled for 12/21/60 s per 60 s heartbeat, 0.6735 W heater assumption, and strict 0 C to 45 C charge gate. |

## Common Test Conditions

All main scenarios are simulated as full annual patterns, then projected to 1-,
3-, and 5-year checkpoints.

| Parameter | Value |
| --- | ---: |
| Annual model period | 365.25 days |
| Orbit period | 94.469 min |
| Nominal eclipse duration | 31.5 min |
| Initial SOC | 88% |
| Initial battery temperature | 12 C |
| Battery | 14.8 Wh |
| Solar input | 2.37 W |
| Fixed bus load | 0.66370 W |
| Payload active load | 0.123 W |

## Scenario Set

| Scenario | Annual schedule |
| --- | --- |
| `warm_nominal_year` | Full nominal year: 31.5 min eclipse, 30 C sun, -10 C eclipse. |
| `realistic_cold_season_year` | Same nominal year plus two 45-day windows; each has 5 transition days, 35 low-beta cold days with 36.0 min eclipse, and 5 recovery days. |
| `cold_long_eclipse_stress_year` | Same nominal year plus two 45-day stress windows: repeated 41.5 min cold eclipses at 22 C sun / -20 C eclipse. |

## Primary Technical KPI

Five-year projection versus the protected baseline:

| Scenario | Protected avg power | Our avg power | Energy saved | Heater saved | Data retained | Cold charge | Battery proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `warm_nominal_year` | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 71.70% -> 71.73% |
| `realistic_cold_season_year` | 0.803 W | 0.751 W | 6.51% | 90.48% | 98.29% | 0 h -> 0 h | 67.26% -> 71.38% |
| `cold_long_eclipse_stress_year` | 0.827 W | 0.756 W | 8.59% | 86.73% | 98.19% | 0 h -> 0 h | 52.94% -> 71.14% |

Percentage calculations for the stress-year checkpoint:

```text
total energy reduction = (36.236 - 33.122) / 36.236 = 8.59%
heater energy reduction = (4.362 - 0.579) / 4.362 = 86.73%
capacity-proxy improvement = 71.14 - 52.94 = 18.20 percentage points
```

## Component Breakdown

Five-year cold long-eclipse stress-year checkpoint:

| Component | Protected baseline | Our controller |
| --- | ---: | ---: |
| Fixed bus, lumped heater-off spacecraft load | 29.090 kWh | 29.090 kWh |
| Payload | 2.735 kWh | 3.390 kWh |
| Heater | 4.362 kWh | 0.579 kWh |
| Peak/other event overhead | 0.049 kWh | 0.063 kWh |
| Total consumed | 36.236 kWh | 33.122 kWh |

The fixed bus is not a communication-box-only measurement. It includes EPS
control electronics, OBC/housekeeping, communication standby, regulator
overhead, and other heater-off spacecraft loads that are not separately broken
out in this model.

## No-Temperature-Gate Diagnostic

| Scenario | No-gate cold charge | Our cold charge | No-gate battery proxy | Our battery proxy |
| --- | ---: | ---: | ---: | ---: |
| `realistic_cold_season_year` | 0.8 h | 0 h | 71.44% | 71.38% |
| `cold_long_eclipse_stress_year` | 171.3 h | 0 h | 44.11% | 71.14% |

The no-temperature-gate baseline is not the primary fair comparison. It is a
diagnostic case showing charge-gate value. The realistic annual case has very
little cold-charge exposure, so the proxy does not separate it strongly; the
stress-year case does.

## Limitation

This is an analytical model, not a reconstruction of real Quetzal-1 flight
telemetry and not a cell-qualified lifetime prediction. Bench thermal testing,
representative battery-stack testing, calibrated SOC sensing, and cell-specific
cycle data are required before flight-equivalent claims.

## Evidence Files

| Evidence | File |
| --- | --- |
| Core firmware | `src/ESP32 Firmware.cpp` |
| Analytical model | `simulation/cold_season_analytical_model.py` |
| Mode smoke tests | `simulation/test_adaptive_eps_logic.py` |
| Full assumptions, parameters, formulas, and citations | `docs/ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md` |
| Flight-proven EPS research notes | `docs/FLIGHT_PROVEN_EPS_RESEARCH_NOTES.md` |
| Results CSV | `results/validation_logs/cold_season_analytical_model.csv` |
| Comparison CSV | `results/validation_logs/cold_season_analytical_comparison.csv` |
| Assumption CSV | `results/validation_logs/cold_season_analytical_design_assumptions.csv` |
| Main charts | `results/figures/realistic_cold_season_year_*.png` and `results/figures/cold_long_eclipse_stress_year_*.png` |

## Reproduction

```bash
python3 simulation/cold_season_analytical_model.py --summary-only
python3 simulation/test_adaptive_eps_logic.py
python3 simulation/validate_final_outputs.py
```
