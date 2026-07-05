# Annual Analytical EPS Model

## Purpose

This model compares the Aether-Albedo-1 adaptive controller against two
Quetzal-scale baselines over a common one-year simulation period, then projects
the annual result to 1-, 3-, and 5-year checkpoints.

The nominal, realistic cold-season, and stress-year cases use the same
spacecraft scale, orbit period, battery capacity, solar input, initial SOC,
initial battery temperature, payload load, fixed bus load, and degradation
proxy. The only scenario differences are the seasonal eclipse and thermal
profiles.

## Compared Designs

| Design label | Meaning |
| --- | --- |
| `no_charge_temp_gate_baseline` | Harsh diagnostic Quetzal-scale stress baseline with no charge-temperature gate. This is not real Quetzal-1 behavior. |
| `quetzal_style_heater_protected_baseline` | Source-backed Quetzal-style protected estimate with 0.898 W heater hardware, full heater power while thermostat-latched at 3 C, heater off at 5 C, and limited heater-assisted charging down to -0.5 C. |
| `our_adaptive_albedo` | Aether-Albedo-1 design-under-test with 0.6735 W heater assumption, tuned `100/95/35/80/0` payload schedule, `20/35/100` heater pulsing, and charge allowed only from 0 C to 45 C. |

## Annual Scenario Set

| Scenario | Simulated period | Eclipse / thermal profile | Purpose |
| --- | ---: | --- | --- |
| `warm_nominal_year` | 365.25 days | 31.5 min eclipse, 30 C sun, -10 C eclipse for the full year | Nominal control case. |
| `realistic_cold_season_year` | 365.25 days | Two 45-day seasonal windows; each has 5 transition days, 35 low-beta cold days with 36.0 min eclipses, and 5 recovery days | Source-backed realistic seasonal case. |
| `cold_long_eclipse_stress_year` | 365.25 days | Two 45-day stress windows using repeated 41.5 min cold eclipses at 22 C sun and -20 C eclipse | Analytical stress case. |

All three start at 88% SOC and 12 C battery temperature. The annual model
continues SOC and temperature without resetting inside seasonal windows.

## Battery Proxy

The model now uses a severity-aware cold-charge penalty:

```text
capacity_remaining_pct =
  100
  - 1.5 * years
  - 0.018 * equivalent_full_cycles
  - 0.00010 * low_soc_hours
  - 0.00040 * critical_soc_hours
  - 0.10 * cold_charge_hours
  - 0.03 * cold_charge_wh
  - 0.05 * cold_charge_degree_hours
  - 10 if the pattern is power-negative
```

This is still a comparative proxy, not a cell-qualified battery-life model.

## Results Versus Protected Baseline

| Scenario | Year | Protected avg power | Our avg power | Energy saved | Heater saved | Data retained | Cold charge | Battery proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `warm_nominal_year` | 1 | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 94.34% -> 94.35% |
| `warm_nominal_year` | 3 | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 83.02% -> 83.04% |
| `warm_nominal_year` | 5 | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 71.70% -> 71.73% |
| `realistic_cold_season_year` | 1 | 0.803 W | 0.751 W | 6.51% | 90.48% | 98.29% | 0 h -> 0 h | 93.45% -> 94.28% |
| `realistic_cold_season_year` | 3 | 0.803 W | 0.751 W | 6.51% | 90.48% | 98.29% | 0 h -> 0 h | 80.36% -> 82.83% |
| `realistic_cold_season_year` | 5 | 0.803 W | 0.751 W | 6.51% | 90.48% | 98.29% | 0 h -> 0 h | 67.26% -> 71.38% |
| `cold_long_eclipse_stress_year` | 1 | 0.827 W | 0.756 W | 8.59% | 86.73% | 98.19% | 0 h -> 0 h | 82.59% -> 94.23% |
| `cold_long_eclipse_stress_year` | 3 | 0.827 W | 0.756 W | 8.59% | 86.73% | 98.19% | 0 h -> 0 h | 67.76% -> 82.69% |
| `cold_long_eclipse_stress_year` | 5 | 0.827 W | 0.756 W | 8.59% | 86.73% | 98.19% | 0 h -> 0 h | 52.94% -> 71.14% |

## Results Versus No-Temperature-Gate Baseline

| Scenario | Year | No-gate avg power | Our avg power | Energy saved | Heater saved | Data retained | Cold charge | Battery proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `warm_nominal_year` | 5 | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 71.70% -> 71.73% |
| `realistic_cold_season_year` | 5 | 0.779 W | 0.751 W | 3.63% | 82.08% | 98.29% | 0.8 h -> 0 h | 71.44% -> 71.38% |
| `cold_long_eclipse_stress_year` | 5 | 0.798 W | 0.756 W | 5.27% | 78.73% | 98.19% | 171.3 h -> 0 h | 44.11% -> 71.14% |

The no-temperature-gate baseline is diagnostic. The protected baseline is the
main comparison because it avoids making the case depend on an obviously unsafe
baseline.

## 5-Year Component Accounting

### Realistic Cold-Season Year

| Component | Protected baseline | Our controller |
| --- | ---: | ---: |
| Fixed bus | 29.090 kWh | 29.090 kWh |
| Payload | 3.333 kWh | 3.484 kWh |
| Heater | 2.701 kWh | 0.257 kWh |
| Peak/other event overhead | 0.060 kWh | 0.064 kWh |
| Total consumed | 35.185 kWh | 32.895 kWh |

```text
total energy saved = (35.185 - 32.895) / 35.185 = 6.51%
heater energy saved = (2.701 - 0.257) / 2.701 = 90.48%
battery proxy improvement = 71.38 - 67.26 = 4.12 percentage points
```

### Cold Long-Eclipse Stress Year

| Component | Protected baseline | Our controller |
| --- | ---: | ---: |
| Fixed bus | 29.090 kWh | 29.090 kWh |
| Payload | 2.735 kWh | 3.390 kWh |
| Heater | 4.362 kWh | 0.579 kWh |
| Peak/other event overhead | 0.049 kWh | 0.063 kWh |
| Total consumed | 36.236 kWh | 33.122 kWh |

```text
total energy saved = (36.236 - 33.122) / 36.236 = 8.59%
heater energy saved = (4.362 - 0.579) / 4.362 = 86.73%
battery proxy improvement = 71.14 - 52.94 = 18.20 percentage points
```

The protected baseline avoids modeled cold-charge exposure by spending much
more heater energy. This follows the Quetzal-style lesson: a protected
thermostatic baseline can be safe, but it is not energy-cheap in repeated cold
eclipse seasons.

In the stress-year case, the protected baseline is power-negative if that
annual pattern is repeated without operational relief; the model estimates
depletion risk after about 11.7 days of equivalent repeated deficit. The
realistic cold-season year remains energy-positive.

## Interpretation

The model supports this claim:

> In a full-year nominal model, the tuned controller remains near parity. When
> the same annual model includes realistic or stress cold-season windows, the
> controller keeps data retention above 98%, reduces heater energy, eliminates
> modeled cold-charge exposure for our design, and improves the comparative
> 5-year battery proxy in the stress-year case.

The model does not claim large average year-round energy savings. The annual
energy gain is modest because the fixed bus dominates most of the year.

## Generated Files

| File | Purpose |
| --- | --- |
| `simulation/cold_season_analytical_model.py` | Reproducible annual analytical model script. |
| `results/validation_logs/cold_season_analytical_model.csv` | Full design rows with power, energy, SOC, data, heater, payload, cold-charge severity, and degradation metrics. |
| `results/validation_logs/cold_season_analytical_comparison.csv` | Direct baseline-vs-adaptive comparison table. |
| `results/validation_logs/cold_season_analytical_scenarios.csv` | Scenario inputs and framing notes. |
| `results/figures/nominal_year_*.svg/png` | Nominal annual comparison charts. |
| `results/figures/realistic_cold_season_year_*.svg/png` | Realistic cold-season annual comparison charts. |
| `results/figures/cold_long_eclipse_stress_year_*.svg/png` | Stress-year annual comparison charts. |

## Reproduce

```bash
python3 simulation/cold_season_analytical_model.py --summary-only
python3 simulation/validate_final_outputs.py
```
