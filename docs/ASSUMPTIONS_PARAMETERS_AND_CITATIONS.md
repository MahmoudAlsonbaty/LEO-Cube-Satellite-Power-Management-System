# Assumptions, Parameters, Formulas, and Citations

This file is the single audit trail for the Aether-Albedo-1 analytical model.
It lists the subsystem boundary, reference sources, model parameters, firmware
ratios, baseline definitions, formulas, and headline results. No percentage in
the project should be quoted without the corresponding formula or source values
shown here.

## Scope

| Item | Statement |
| --- | --- |
| Project name | Aether-Albedo-1 |
| Subsystem | Adaptive albedo payload and EPS power-management controller |
| Not claimed | Complete spacecraft EPS, flight-proven spacecraft, or exact Quetzal-1 replay |
| Main model label | Annual nominal/cold-season analytical EPS model |
| Realistic seasonal case label | Source-backed annual realistic low-beta cold-season model |
| Main comparison | Quetzal-scale protected baseline versus our adaptive albedo controller |

The firmware controls three outputs: payload rail enable, battery-heater switch,
and charge enable/inhibit. The model compares control logic under the same
environment and power scale.

## Source Map

| Source | Used for | How it is used |
| --- | --- | --- |
| [Quetzal-1 EPS paper, UVG Aerospace Laboratory](https://www.aeroespacial-uvg.org/en/publication/quetzal1-eps/) | 1U EPS reference, battery/heater/bus scale, real Quetzal heater behavior context | Provides the Quetzal-derived scale and flight-context warning. The model does not replay Quetzal telemetry. |
| [Quetzal-1 EPS paper, ResearchGate full-text mirror](https://www.researchgate.net/publication/371292169_Design_and_On-Orbit_Performance_of_the_Electrical_Power_System_for_the_Quetzal-1_CubeSat) | Detailed power-budget and on-orbit excerpts | Used for heater threshold context, maximum eclipse-duration context, and EPS/bus/heater interpretation. |
| [Thermal Analysis of the Impact of Six Months in a 1U CubeSat in LEO](https://www.researchgate.net/publication/376835876_THERMAL_ANALYSIS_OF_THE_IMPACT_OF_SIX_MONTHS_IN_A_1U_CUBESAT_IN_LEO) | 1U LEO beta-angle seasonal behavior | Supports a generic 1U LEO beta-angle sweep over months, including beta near 0 deg and high-beta cases. |
| [Thermal control of a small satellite in LEO using PCM-based thermal energy storage](https://www.sciencedirect.com/science/article/pii/S1110982323000947) | Low-beta cold-case eclipse duration | Uses 500 km LEO, beta = 0, about 60 min sunlight and 35 min eclipse. This supports the 35-36 min realistic cold eclipse. |
| [CubeSat Resources EPS overview](https://cubesat-resources.space/development/eps/) | General CubeSat power-budget framing | Supports duty cycles, orbit-average power, solar/battery bookkeeping, and typical LEO eclipse-fraction framing. |
| [NASA SmallSat Thermal Control state of the art](https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/) | General thermal environment framing | Supports the need to consider solar, albedo, IR, radiation balance, and mission-phase thermal constraints. |
| Local firmware and simulation files | Actual project implementation | `src/ESP32 Firmware.cpp` and `simulation/cold_season_analytical_model.py` are the executable definitions of the final controller/model. |

## Reference Caveats

| Topic | Correct statement |
| --- | --- |
| Quetzal beta angle | The model does not use a recovered Quetzal beta-angle timeline. |
| Quetzal behavior | Quetzal-1 had real heater protection and should not be described as failing because of routine cold charging. |
| Seasonal cold case | The 36 min cold-eclipse case is a generic 1U/LEO low-beta cold-season assumption, source-backed by published thermal studies. |
| Stress case | The 41.5 min repeated cold-eclipse case is analytical stress, not average year-round behavior. |
| Battery-health proxy | Comparative proxy only; not a cell-qualified lifetime prediction. |

## Spacecraft and EPS Parameters

| Parameter | Value | Source or basis | Notes |
| --- | ---: | --- | --- |
| Form factor | 1U assumed | Quetzal-style 1U reference and project scope | Design-under-test, not flight-proven. |
| Battery capacity | 14.8 Wh | Quetzal-style 1S2P Li-ion pack scale | Same capacity for baseline and our controller. |
| Solar input | 2.37 W | Existing Quetzal-scale 1U model assumption | Same input for baseline and our controller. |
| Usable solar efficiency | 0.85 | Model derating assumption | Applied when charging is allowed. |
| Fixed heater-off bus load | 0.66370 W | Quetzal-scale heater-off spacecraft/bus context | Lumped fixed bus, not communication-box-only. |
| Payload active load | 0.123 W | Albedo payload model assumption | Added only when payload duty is nonzero. |
| Protected baseline heater power | 0.898 W | Quetzal-style heater hardware scale | Used by baseline profiles. |
| Our analytical heater power | 0.6735 W | 75% of 0.898 W | Thermal-design assumption requiring bench/thermal-vac validation. |
| Firmware conservative heater estimate | 0.898 W | Firmware-side power-margin estimate | Conservative onboard estimate, not the analytical albedo heater value. |
| Peak total load marker | 0.997 W | Quetzal-scale model parameter | Generates small peak/other event overhead. |
| Nominal orbit period | 94.469 min | Quetzal/ISS-style LEO model scale | Used for all scenarios. |
| Nominal eclipse | 31.5 min | Quetzal/LEO model scale | Warm and nominal cold cases. |
| Realistic cold eclipse | 36.0 min | 1U/LEO low-beta cold-case sources | Used for 35 low-beta days inside each realistic annual cold-season window. |
| Stress eclipse | 41.5 min | Analytical stress assumption | Used only for repeated cold long-eclipse stress cases. |

## Fixed Bus Breakdown

The fixed bus is modeled as one lumped load because the current analytical
model does not separate every subsystem. It is not a communication-box-only
measurement.

| Fixed-bus subpart | Treatment |
| --- | --- |
| EPS microcontroller/sensors | Included in 0.66370 W; earlier public-reference estimate was about 0.022 W. |
| OBC / housekeeping electronics | Included in 0.66370 W. |
| Communications standby/idle | Included in 0.66370 W, but not separately measured. |
| Regulators and conversion overhead | Included in 0.66370 W. |
| Unassigned heater-off remainder | About 0.6417 W after subtracting the 0.022 W EPS microcontroller/sensor estimate. |
| Payload | Not included; modeled separately as 0.123 W active. |
| Heater | Not included; modeled separately as 0.898 W baseline or 0.6735 W ours. |

Power equation:

```text
total consumed energy =
  fixed bus energy
  + payload energy
  + heater energy
  + peak/other event energy
```

## Controller Policy

Heartbeat period: 60 s.

| Firmware mode | Payload enabled time | Duty |
| --- | ---: | ---: |
| `SUNLIGHT_SCIENCE` | 60 s per 60 s heartbeat | 100% |
| `SUNLIGHT_SCHEDULED` | 57 s per 60 s heartbeat | 95% |
| `SUNLIGHT_POWER_SAVE` | 21 s per 60 s heartbeat | 35% |
| `PRE_ECLIPSE_PREP` | 48 s per 60 s heartbeat | 80% |
| `ECLIPSE_SURVIVAL` | 0 s per 60 s heartbeat | 0% |
| `LOW_SOC_SAFE` | 0 s per 60 s heartbeat | 0% |
| `THERMAL_SAFE` | 0 s per 60 s heartbeat | 0% |
| `FAULT_SAFE` | 0 s per 60 s heartbeat | 0% |

| Heater condition | Heater enabled time | Duty |
| --- | ---: | ---: |
| Heater latch off, battery >= 5 C | 0 s per 60 s heartbeat | 0% |
| Normal cold, battery <= -5 C | 12 s per 60 s heartbeat | 20% |
| Strong cold, battery <= -10 C | 21 s per 60 s heartbeat | 35% |
| Critical cold, battery <= -15 C | 60 s per 60 s heartbeat | 100% |

Charge gate:

| Condition | Required value |
| --- | --- |
| Daylight | True |
| SOC | < 95% |
| Battery temperature | 0 C to 45 C |
| Fault | No active fault |

## Mode Priority

| Priority | Condition | Mode |
| ---: | --- | --- |
| 1 | Fault detected | `FAULT_SAFE` |
| 2 | Payload thermal lockout active | `THERMAL_SAFE` |
| 3 | No daylight | `ECLIPSE_SURVIVAL` |
| 4 | Low SOC lockout or SOC < 40% | `LOW_SOC_SAFE` |
| 5 | Weak sunlight and battery temperature < 5 C | `PRE_ECLIPSE_PREP` |
| 6 | SOC < 60% or power margin < 0.10 W | `SUNLIGHT_POWER_SAVE` |
| 7 | Strong sunlight, SOC >= 85%, margin >= 0.15 W | `SUNLIGHT_SCIENCE` |
| 8 | Other daylight condition | `SUNLIGHT_SCHEDULED` |

## Compared Designs

| Label | Meaning | Heater policy | Charge policy | Payload policy |
| --- | --- | --- | --- | --- |
| `no_charge_temp_gate_baseline` | Harsh Quetzal-scale stress baseline | Full heater duty when cold latch is active | Daylight and SOC < 95%; no temperature gate | Full daylight payload |
| `quetzal_style_heater_protected_baseline` | Source-backed Quetzal-style protected estimate | 0.898 W heater at full power while thermostat-latched at 3 C, off at 5 C | Daylight and SOC < 95%; charging above 0 C, with imperfect heater-assisted charging down to -0.5 C | Full daylight payload |
| `our_adaptive_albedo` | Final tuned controller | 0.6735 W heater with 20/35/100 pulse logic | Daylight, SOC < 95%, no fault, 0 C to 45 C | 100/95/35/80/0 duty by mode |

The `quetzal_style_heater_protected_baseline` is not exact Quetzal telemetry.
It uses the Quetzal-1 paper's heater thresholds and on/off style: full heater
power when latched, on below 3 C and off above 5 C. This makes it safer than
the no-temp-gate baseline, but not energy-cheap in repeated cold windows.

## Scenario Definitions

All main scenarios are simulated over one full `365.25 day` year. They share
the same orbit, capacity, solar input, fixed bus, payload, initial SOC, initial
battery temperature, and degradation proxy. The only scenario differences are
the annual eclipse and thermal schedules.

| Scenario | Duration | Eclipse profile | Thermal profile | Purpose |
| --- | ---: | --- | --- | --- |
| `warm_nominal_year` | 365.25 days | 31.5 min every orbit | 30 C sun, -10 C eclipse, initial battery 12 C | Nominal reference; expected near parity. |
| `realistic_cold_season_year` | 365.25 days | Nominal year plus two 45-day windows; each has 5 transition days, 35 cold days at 36.0 min eclipse, 5 recovery days | Nominal year is 30 C sun / -10 C eclipse; transition/recovery is 25 C sun / -12 C eclipse; cold block is 22 C sun / -20 C eclipse | Main source-backed realistic low-beta seasonal year. |
| `cold_long_eclipse_stress_year` | 365.25 days | Nominal year plus two 45-day stress windows at 41.5 min eclipse | Nominal year is 30 C sun / -10 C eclipse; stress windows are 22 C sun / -20 C eclipse | Annual stress case. |

## Formulas

Energy and power:

```text
energy_wh = sum(power_w per minute) / 60
average_power_w = energy_wh / duration_hours
usable_solar_wh = sum(generated_w * 0.85 when charge_allowed) / 60
net_wh_per_day = (usable_solar_wh - consumed_wh) * 24 / duration_hours
projected_kwh = pattern_wh * repeats / 1000
repeats = years * 365.25 * 24 / pattern_duration_hours
```

Percent reductions:

```text
energy_saved_pct =
  (baseline_consumed_kwh - adaptive_consumed_kwh)
  / baseline_consumed_kwh
  * 100

heater_saved_pct =
  (baseline_heater_kwh - adaptive_heater_kwh)
  / baseline_heater_kwh
  * 100

data_retained_pct =
  adaptive_data_units / full_daylight_payload_data_units * 100

capacity_proxy_delta_pct =
  adaptive_capacity_proxy_pct - baseline_capacity_proxy_pct
```

Battery proxy:

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

This is a comparative degradation proxy. It is not a cell-specific aging model.
The cold-charge term is severity-aware: it penalizes duration, actual Wh charged
while below 0 C, and the depth below 0 C.

## Key Results Versus Protected Baseline

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

## Key Results Versus No-Temperature-Gate Baseline

| Scenario | Year | No-gate avg power | Our avg power | Energy saved | Heater saved | Data retained | Cold charge | Battery proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `warm_nominal_year` | 5 | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 0 h -> 0 h | 71.70% -> 71.73% |
| `realistic_cold_season_year` | 5 | 0.779 W | 0.751 W | 3.63% | 82.08% | 98.29% | 0.8 h -> 0 h | 71.44% -> 71.38% |
| `cold_long_eclipse_stress_year` | 5 | 0.798 W | 0.756 W | 5.27% | 78.73% | 98.19% | 171.3 h -> 0 h | 44.11% -> 71.14% |

The no-temperature-gate baseline is diagnostic. In the realistic annual case it
only accumulates about `0.8 h` of cold-charge exposure over five years, so the
current battery proxy does not separate it strongly. In the stress-year case,
the same baseline becomes clearly worse.

## Realistic Cold-Season Year Component Accounting

Scenario: `realistic_cold_season_year`, two 45-day cold-season windows per
simulated year, projected to five years.

| Component | Protected baseline | Our controller | Difference |
| --- | ---: | ---: | ---: |
| 5-year consumed energy | 35.185 kWh | 32.895 kWh | 2.290 kWh saved |
| 5-year usable solar generated | 35.206 kWh | 32.920 kWh | 2.286 kWh lower use/generation admitted |
| 5-year payload energy | 3.333 kWh | 3.484 kWh | 0.150 kWh higher for our controller |
| 5-year heater energy | 2.701 kWh | 0.257 kWh | 2.444 kWh saved |
| Data retained | 94.05% | 98.29% | 4.24 percentage points higher |
| Cold-charge exposure | 0 h | 0 h | No change |
| Battery-health proxy | 67.26% | 71.38% | +4.12 percentage points |

Realistic-case calculations:

```text
total energy saved =
  (35.184912 - 32.895054) / 35.184912 * 100
  = 6.51%

heater energy saved =
  (2.701109 - 0.257212) / 2.701109 * 100
  = 90.48%

battery proxy improvement =
  71.379721 - 67.260242
  = 4.12 percentage points
```

## Stress-Year Component Accounting

Scenario: `cold_long_eclipse_stress_year`, two 45-day cold-season stress
windows per simulated year, projected to five years.

| Component | Protected baseline | Our controller | Difference |
| --- | ---: | ---: | ---: |
| 5-year consumed energy | 36.236 kWh | 33.122 kWh | 3.114 kWh saved |
| 5-year heater energy | 4.362 kWh | 0.579 kWh | 3.783 kWh saved |
| 5-year payload energy | 2.735 kWh | 3.390 kWh | 0.656 kWh higher for our controller |
| Cold-charge exposure | 0 h | 0 h | No change |
| Cold-charge energy | 0 Wh | 0 Wh | No change |
| Cold-charge severity | 0 C-h | 0 C-h | No change |
| Data retained | 79.21% | 98.19% | 18.98 percentage points higher |
| Battery-health proxy | 52.94% | 71.14% | +18.20 percentage points |

Stress-case calculations:

```text
total energy saved =
  (36.236109 - 33.122075) / 36.236109 * 100
  = 8.59%

heater energy saved =
  (4.362260 - 0.579070) / 4.362260 * 100
  = 86.73%

battery proxy improvement =
  71.143292 - 52.938352
  = 18.20 percentage points
```

The protected baseline avoids cold charge by spending heater energy. The
stress case saves more absolute heater energy than the realistic case:

```text
realistic heater saved = 2.701109 - 0.257212 = 2.444 kWh
stress heater saved = 4.362260 - 0.579070 = 3.783 kWh
```

The stress heater-saving percentage is lower because the adaptive controller
also has to heat more often during the colder, longer-eclipse windows.

## Tuned Payload Schedule Evidence

The previous cold long-eclipse firmware with pre-eclipse duty at 25% retained
only 87.91% of data in the older repeated-30-day stress pattern. The final
tuned value is 80% pre-eclipse duty, which keeps the annual stress-year data
retention at 98.19% while keeping cold-charge exposure at 0 h for our
controller.

| Mode | Old issue | Final value |
| --- | --- | --- |
| `PRE_ECLIPSE_PREP` payload duty | 25% saved energy but under-retained data | 80%, or 48 s per 60 s heartbeat |
| Data target | >=95% | 98.19% in stress-year case; 98.29% in realistic annual case |
| Cold-charge target | 0 h | 0 h for our controller |

## Final Claim Boundary

Strong claim:

> The controller preserves science data above 95%, removes modeled cold-charge
> exposure for our design, and reduces heater energy under full-year nominal,
> source-backed cold-season, and repeated cold-eclipse analytical cases.

Do not claim:

| Avoided claim | Reason |
| --- | --- |
| Average year-round energy savings are large | Nominal savings are modest at 0.14%. Cold-season annual cases reach 6.51% realistic and 8.59% stress-year savings versus the source-backed protected baseline. |
| Quetzal-1 failed because of routine cold charging | Real Quetzal behavior included heater protection; its end-of-life involved a fault chain. |
| The model uses Quetzal beta telemetry | It does not. It uses Quetzal-scale EPS values plus generic 1U/LEO low-beta cold-season assumptions. |
| The battery-health proxy is a certified lifetime prediction | It is a comparative analytical proxy. |
| The fixed bus is the communication box | The fixed bus is a lumped heater-off spacecraft load. |

## Reproduction Commands

```bash
python3 simulation/cold_season_analytical_model.py --summary-only
python3 simulation/test_adaptive_eps_logic.py
python3 simulation/validate_final_outputs.py
python3 -m py_compile simulation/cold_season_analytical_model.py simulation/test_adaptive_eps_logic.py
```

Primary output files:

| File | Purpose |
| --- | --- |
| `results/validation_logs/cold_season_analytical_model.csv` | Full model rows for all designs, scenarios, and 1/3/5-year checkpoints. |
| `results/validation_logs/cold_season_analytical_comparison.csv` | Direct baseline-versus-adaptive comparison rows. |
| `results/validation_logs/cold_season_analytical_scenarios.csv` | Scenario input assumptions. |
| `results/validation_logs/cold_season_analytical_design_assumptions.csv` | Design labels and control-policy assumptions. |
| `results/figures/nominal_year_*.png` and `.svg` | Bar charts for nominal annual capacity, cold charge, consumed energy, and heater energy. |
| `results/figures/realistic_cold_season_year_*.png` and `.svg` | Bar charts for realistic annual cold-season capacity, cold charge, consumed energy, and heater energy. |
| `results/figures/cold_long_eclipse_stress_year_*.png` and `.svg` | Bar charts for stress-year capacity, cold charge, consumed energy, and heater energy. |
