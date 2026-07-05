# Aether-Albedo-1 CubeSat Power Management System

<p align="center">
  <img src="docs/System Block Diagram.png" alt="Aether-Albedo-1 system block diagram" width="650"/>
</p>

**IEEE AESS Sustainability Hackathon 2026 | Challenge 1: Sustainable Electronics for Space Systems**

## The Mission: Smarter Albedo Sensing In LEO

This repository contains the firmware, hardware files, analytical models, validation logs, and final documentation for **Aether-Albedo-1**, a CubeSat albedo payload and EPS power-management subsystem.

The mission is still the same at heart: collect useful Earth albedo measurements without wasting scarce spacecraft energy. The updated system goes beyond the original eclipse power-gating concept. It now manages payload duty cycle, battery heater pulses, charge safety, thermal protection, low-SOC survival behavior, and fault-safe operation as one adaptive controller.

This is a bounded subsystem, not a full satellite EPS. The repo focuses on one practical question:

> How can a CubeSat albedo payload preserve science opportunity while reducing heater waste and avoiding unsafe cold charging during cold-season orbital conditions?

## The Core Concept: Adaptive EPS Heartbeat

The original project used a simple eclipse-aware MOSFET cutoff. The updated controller keeps that low-power spirit, but makes the decision logic richer and more realistic.

- **The 60-Second Heartbeat:** The controller thinks in 60 s windows. Instead of staying fully active or fully off, it assigns payload and heater duty cycles based on sunlight, battery temperature, payload temperature, SOC, and fault state.
- **Cold-Season Survival:** In eclipse and cold battery conditions, the payload can be shut down while the heater receives bounded pulses. Critical cold can trigger full survival heating.
- **Charge Safety Gate:** Charging is enabled only in sunlight, below 95% SOC, with no fault, and with battery temperature from **0 C to 45 C**.
- **Science First, Safely:** In healthy sunlight, the albedo payload can run continuously or near-continuously. In weak margin or low-SOC cases, the controller reduces cadence instead of blindly draining the battery.

## Sustainability Impact: Less Heater Waste, Safer Battery Behavior

Spacecraft energy savings are not always dramatic at the full-year level because fixed spacecraft loads dominate. So the final claim is intentionally narrow and validated:

**Aether-Albedo-1 preserves more than 98% of daylight science opportunity while reducing heater energy in annual cold-season cases and improving the modeled 5-year battery-health proxy versus a protected heater baseline.**

Five-year projection versus the protected Quetzal-style baseline:

| Scenario | Protected avg power | Our avg power | Energy saved | Heater saved | Data retained | Battery-health proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `warm_nominal_year` | 0.747 W | 0.746 W | 0.14% | 0.00% | 98.73% | 71.70% -> 71.73% |
| `realistic_cold_season_year` | 0.803 W | 0.751 W | 6.51% | 90.48% | 98.29% | 67.26% -> 71.38% |
| `cold_long_eclipse_stress_year` | 0.827 W | 0.756 W | 8.59% | 86.73% | 98.19% | 52.94% -> 71.14% |

For the cold long-eclipse stress-year case, the 5-year accounting is:

```text
total energy saved = (36.236 - 33.122) / 36.236 = 8.59%
heater energy saved = (4.362 - 0.579) / 4.362 = 86.73%
battery-proxy improvement = 71.14 - 52.94 = 18.20 percentage points
```

The fixed bus load is held constant in both designs, so the strongest improvement appears where the controller has authority: heater use, cold-charge avoidance, and payload duty scheduling.

## The Controller Stack

- **The Brain:** ESP32 firmware implementing adaptive mode selection and output control.
- **The Payload Rail:** Albedo sensing payload controlled through scheduled duty windows.
- **The Thermal Guard:** Battery heater pulses at 20%, 35%, or 100% duty depending on cold severity.
- **The Charge Gate:** Charge enable only when sunlight, SOC, battery temperature, and fault state are safe.
- **The Evidence Engine:** Annual analytical model, CSV validation logs, plots, and smoke tests.

## Operating Modes

| Mode | Payload duty | 60 s heartbeat equivalent |
| --- | ---: | ---: |
| `SUNLIGHT_SCIENCE` | 100% | 60 s on |
| `SUNLIGHT_SCHEDULED` | 95% | 57 s on |
| `SUNLIGHT_POWER_SAVE` | 35% | 21 s on |
| `PRE_ECLIPSE_PREP` | 80% | 48 s on |
| `ECLIPSE_SURVIVAL` | 0% | 0 s on |
| `LOW_SOC_SAFE` | 0% | 0 s on |
| `THERMAL_SAFE` | 0% | 0 s on |
| `FAULT_SAFE` | 0% | 0 s on |

Heater policy:

| Battery condition | Heater action | 60 s heartbeat equivalent |
| --- | --- | ---: |
| Normal cold | Low pulse | 12 s on |
| Strong cold | Strong pulse | 21 s on |
| Critical cold | Survival heat | 60 s on |

## Analytical Model

The final model compares three designs under the same spacecraft scale, orbit period, solar input, battery capacity, initial SOC, initial battery temperature, and degradation proxy.

| Design | Meaning |
| --- | --- |
| `no_charge_temp_gate_baseline` | Diagnostic stress baseline with no battery charge-temperature gate. |
| `quetzal_style_heater_protected_baseline` | Source-backed protected estimate using thermostat-style heater protection. |
| `our_adaptive_albedo` | Final tuned controller with adaptive payload duty, heater pulses, and strict 0 C to 45 C charge gate. |

Main simulation assumptions:

| Parameter | Value |
| --- | ---: |
| Annual model period | 365.25 days |
| Orbit period | 94.469 min |
| Nominal eclipse duration | 31.5 min |
| Initial SOC | 88% |
| Battery | 14.8 Wh |
| Solar input | 2.37 W |
| Fixed bus load | 0.66370 W |
| Payload active load | 0.123 W |

Scenario set:

| Scenario | Annual schedule |
| --- | --- |
| `warm_nominal_year` | Full nominal year: 31.5 min eclipse, 30 C sun, -10 C eclipse. |
| `realistic_cold_season_year` | Nominal year plus two 45-day cold windows with 36.0 min eclipses. |
| `cold_long_eclipse_stress_year` | Nominal year plus two 45-day stress windows with 41.5 min cold eclipses. |

## Project Architecture

```text
.
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- docs/
|   |-- FINAL_TECHNICAL_DOCUMENTATION.md
|   |-- ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md
|   |-- FINAL_EVIDENCE_SHEET.md
|   |-- FINAL_REPO_VALIDATION_AUDIT.md
|   |-- FLIGHT_PROVEN_EPS_RESEARCH_NOTES.md
|   |-- EQUIPMENT_AND_SAFETY_DECLARATION.md
|   |-- AI_AND_RESOURCE_DISCLOSURE.md
|   |-- Schematic Capture.png
|   `-- System Block Diagram.png
|-- hardware/
|   `-- Aether_Avionics.pdsprj
|-- results/
|   |-- figures/
|   `-- validation_logs/
|-- simulation/
|   |-- cold_season_analytical_model.py
|   |-- test_adaptive_eps_logic.py
|   `-- validate_final_outputs.py
`-- src/
    `-- ESP32 Firmware.cpp
```

## Prerequisites

To review and reproduce the final package:

- **Python 3.x:** Required for the analytical model, validation scripts, and firmware smoke tests.
- **Pillow:** Optional. Used for PNG chart generation. SVG charts are still written without it.
- **Proteus Design Suite:** Required to open `hardware/Aether_Avionics.pdsprj`.
- **Arduino IDE or PlatformIO:** Required to inspect or adapt `src/ESP32 Firmware.cpp` for ESP32 deployment.

Install Python requirements with:

```bash
pip install -r requirements.txt
```

## How To Run And Verify

Run the final analytical model:

```bash
python3 simulation/cold_season_analytical_model.py --summary-only
```

Run firmware logic smoke tests:

```bash
python3 simulation/test_adaptive_eps_logic.py
```

Validate final CSV outputs, comparison math, and documentation consistency:

```bash
python3 simulation/validate_final_outputs.py
```

Expected headline summary:

```text
cold_long_eclipse_stress_year 5y: avg 0.827W -> 0.756W, energy_saved=8.59%, heater_saved=86.73%, data=98.19%, cold_charge=0h -> 0h, cap=52.9% -> 71.1%
realistic_cold_season_year 5y: avg 0.803W -> 0.751W, energy_saved=6.51%, heater_saved=90.48%, data=98.29%, cold_charge=0h -> 0h, cap=67.3% -> 71.4%
warm_nominal_year 5y: avg 0.747W -> 0.746W, energy_saved=0.14%, heater_saved=0.00%, data=98.73%, cold_charge=0h -> 0h, cap=71.7% -> 71.7%
```

## Evidence Map

| Requirement | File |
| --- | --- |
| Core firmware | `src/ESP32 Firmware.cpp` |
| Annual analytical model | `simulation/cold_season_analytical_model.py` |
| Firmware smoke tests | `simulation/test_adaptive_eps_logic.py` |
| Final output validator | `simulation/validate_final_outputs.py` |
| Technical architecture | `docs/FINAL_TECHNICAL_DOCUMENTATION.md` |
| Assumptions, parameters, formulas, and citations | `docs/ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md` |
| Final evidence sheet | `docs/FINAL_EVIDENCE_SHEET.md` |
| Repo validation audit | `docs/FINAL_REPO_VALIDATION_AUDIT.md` |
| Flight-proven EPS research notes | `docs/FLIGHT_PROVEN_EPS_RESEARCH_NOTES.md` |
| Analytical results | `results/validation_logs/cold_season_analytical_model.csv` |
| Comparison results | `results/validation_logs/cold_season_analytical_comparison.csv` |
| Figures | `results/figures/*_year_*.png` and `.svg` |

## Claim Boundary

This project does **not** claim large average year-round energy savings, flight-qualified battery lifetime prediction, or reconstruction of real Quetzal-1 telemetry.

The defensible final claim is that, in annual cold-season analytical cases, the adaptive controller preserves more than 98% of daylight science opportunity, reduces heater energy, avoids modeled cold-charge exposure for the design-under-test, and improves the 5-year comparative battery-health proxy versus the protected heater baseline.
