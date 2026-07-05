# Final Presentation - 5 Minute Outline

## Slide 1 - Bounded Subsystem

Message: This is not a full satellite. It is one CubeSat albedo payload and EPS
power-management subsystem controlling payload rail, heater switch, and charge
enable.

Show: `docs/FINAL_TECHNICAL_DOCUMENTATION.md`

## Slide 2 - Annual Model Setup

Message: The model now checks all main cases over the same one-year period,
then projects that annual result to 1-, 3-, and 5-year checkpoints.

Show: `results/validation_logs/cold_season_analytical_scenarios.csv`

Scenarios:

| Scenario | Annual schedule |
| --- | --- |
| Nominal | Full nominal year. |
| Realistic cold-season | Nominal year plus two 45-day cold windows: 5 transition, 35 low-beta cold, 5 recovery days each. |
| Stress year | Nominal year plus two 45-day repeated long cold-eclipse windows. |

## Slide 3 - Control Strategy

Message: The firmware uses priority-based modes: fault, thermal, eclipse,
low-SOC, pre-eclipse prep, power-save, science, and scheduled operation.

Show: `src/ESP32 Firmware.cpp`

Key policy:

| Policy | Meaning |
| --- | --- |
| Payload `100 / 95 / 35 / 80 / 0` | 60/57/21/48/0 s enabled per 60 s heartbeat |
| Heater `20 / 35 / 100` | 12/21/60 s enabled per 60 s heartbeat |
| Charge gate | Charging only from 0 C to 45 C |

## Slide 4 - Fair Baselines

Message: We compare against two baselines. The protected baseline is the main
fair comparison; the no-temperature-gate baseline is diagnostic.

Show: `results/validation_logs/cold_season_analytical_design_assumptions.csv`

| Baseline | Use |
| --- | --- |
| `quetzal_style_heater_protected_baseline` | Main protected comparison. |
| `no_charge_temp_gate_baseline` | Diagnostic charge-gate stress comparison. |

## Slide 5 - Main Evidence

Message: Annual total-energy savings are modest because the fixed bus dominates
most of the year. The cold-season value is in heater reduction, zero modeled
cold-charge exposure for our controller, and slightly better 5-year battery
proxy while preserving more than 98% of daylight science opportunity.

Show:

- `results/figures/realistic_cold_season_year_heater_energy.png`
- `results/figures/cold_long_eclipse_stress_year_cold_charge.png`
- `results/figures/cold_long_eclipse_stress_year_capacity_proxy.png`

Five-year protected-baseline results:

| Scenario | Energy saved | Heater saved | Data retained | Cold charge | Battery proxy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nominal | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 71.70% -> 71.73% |
| Realistic cold-season | 6.51% | 90.48% | 98.29% | 0 h -> 0 h | 67.26% -> 71.38% |
| Stress year | 8.59% | 86.73% | 98.19% | 0 h -> 0 h | 52.94% -> 71.14% |

Component accounting for the stress-year 5-year checkpoint:

| Component | Protected baseline | Our controller |
| --- | ---: | ---: |
| Fixed bus | 29.090 kWh | 29.090 kWh |
| Payload | 2.735 kWh | 3.390 kWh |
| Heater | 4.362 kWh | 0.579 kWh |
| Peak/other | 0.049 kWh | 0.063 kWh |
| Total | 36.236 kWh | 33.122 kWh |

Explain the percentages:

| Calculation | Formula |
| --- | --- |
| Stress-year total saving | `(36.236 - 33.122) / 36.236 = 8.59%` |
| Stress-year heater saving | `(4.362 - 0.579) / 4.362 = 86.73%` |
| Stress-year battery proxy improvement | `71.14 - 52.94 = 18.20 percentage points` |

Note: the protected baseline avoids cold charging by spending heater energy.
That is the Quetzal-style trade: safe, but not energy-cheap in repeated cold
windows.

## Slide 6 - Limitation and Next Step

Message: The model is analytical, not flight-qualified. The next step is bench
thermal testing with a representative battery stack, calibrated SOC sensing,
and cell-specific degradation data.

Show: `docs/FINAL_EVIDENCE_SHEET.md`

## Live Demo Script

1. Run `python3 simulation/cold_season_analytical_model.py --summary-only`.
2. Run `python3 simulation/test_adaptive_eps_logic.py`.
3. Open `results/validation_logs/cold_season_analytical_comparison.csv`.
4. Open `docs/ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md`.
5. Show `results/figures/realistic_cold_season_year_heater_energy.png`.
6. Show `results/figures/cold_long_eclipse_stress_year_capacity_proxy.png`.
7. Point to the charge-temperature gate and heater pulse logic in `src/ESP32 Firmware.cpp`.
8. State the limitation: analytical annual model, not exact Quetzal telemetry or a cell-qualified lifetime prediction.
