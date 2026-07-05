# Flight-Proven EPS Research Notes

## Purpose

This note records the source-backed changes made after reviewing the attached
`CubeSat_EPS_Flight_Proven_Reference.pdf` and its embedded source links. It
explains why the protected baseline was changed from a low-duty heater estimate
to a source-backed Quetzal-style thermostat heater.

## Source Findings

| Source | Relevant finding | Model impact |
| --- | --- | --- |
| Attached `CubeSat_EPS_Flight_Proven_Reference.pdf` | Identifies Quetzal-1, BIRDS, and SwissCube as the strongest 1U EPS/thermal references. | Use Quetzal-1 as the protected 1U EPS/heater baseline, with BIRDS and SwissCube as validation context. |
| [Quetzal-1 EPS design and on-orbit performance](https://www.aeroespacial-uvg.org/en/publication/quetzal1-eps/) | 1U EPS with 4.2 V Li-ion battery, 2.37 W solar estimate, battery heater, and positive power budget. | Keeps the Quetzal-scale battery, solar, bus, and heater reference. |
| [Quetzal-1 EPS paper PDF](https://jossonline.com/storage/2023/05/Final-Aguilar-Nadalini-Design-and-On-Orbit-Performance-of-the-Electrical-Power-System-for-the-Quetzal-1-CubeSat.pdf) | Li-ion charge range is 0 C to 45 C; charging below 0 C risks lithium plating and safety/performance degradation. | Retains our strict 0 C to 45 C charge gate and the severity-aware cold-charge penalty. |
| [Quetzal-1 EPS paper PDF](https://jossonline.com/storage/2023/05/Final-Aguilar-Nadalini-Design-and-On-Orbit-Performance-of-the-Electrical-Power-System-for-the-Quetzal-1-CubeSat.pdf) | Heater turned on below 3 C and off above 5 C; heater power was about 0.898 W. | Protected baseline changed to full 0.898 W heater power while thermostat-latched at 3 C/5 C. |
| [Quetzal-1 EPS paper, ResearchGate mirror](https://www.researchgate.net/publication/371292169_Design_and_On-Orbit_Performance_of_the_Electrical_Power_System_for_the_Quetzal-1_CubeSat) | On orbit, the heater typically activated before eclipse exit and ran about 30 minutes per orbit for 30-36 min eclipses; at 36 min eclipse it reached about 31% orbital duty. | Rejected the old 25% low-duty protected baseline. A protected Quetzal-style baseline avoids cold charge by paying heater energy. |
| [BIRDS 1U EPS telemetry dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC9679683/) | Provides real 1U EPS telemetry for battery, solar panels, voltage, current, and temperature in an ISS-like orbit. | Supports using telemetry-style orbit validation and not relying only on constant-load assumptions. |
| [SwissCube thermal flight-data paper](https://www.researchgate.net/publication/299535685_THERMAL_MODEL_FOR_CUBESAT_A_SIMPLE_AND_EASY_MODEL_FROM_THE_SWISSCUBE%27S_THERMAL_FLIGHT_DATA) | 1U battery thermal control used about 100 mW heat below -5 C and off near +5 C, with long-duration flight thermal data. | Supports including explicit battery thermal/heater control in 1U modeling. |
| [MinXSS-1 on-orbit pointing and power performance](https://jossonline.com/wp-content/uploads/2018/01/Mason-Final-MinXSS-1-CubeSat-On-Orbit-Pointing-and-Power-Performance.pdf) | 3U mission reference for active science power and orbit/eclipse stress cases. | Kept as context only; not used as the direct 1U baseline. |

## Model Change

Old protected baseline:

```text
heater = 0.898 W * 25% while latched
heater latch on = 1 C
heater latch off = 5 C
```

Updated protected baseline:

```text
heater = 0.898 W at full power while latched
heater latch on = 3 C
heater latch off = 5 C
charge normally allowed above 0 C
limited heater-assisted charge allowed down to -0.5 C
```

## Resulting Interpretation

The protected baseline is now safer but more power-hungry. In the realistic
cold-season year, it avoids modeled cold-charge exposure, but its 5-year heater
energy rises to `2.701 kWh`, compared with `0.257 kWh` for our adaptive
controller. This raises total energy savings versus the protected baseline to
`6.51%`.

In the stress year, the protected baseline again avoids modeled cold-charge
exposure, but its 5-year heater energy rises to `4.362 kWh`, compared with
`0.579 kWh` for our controller. Total energy savings rise to `8.59%`, and the
battery proxy improves from `52.94%` to `71.14%`.

## Claim Boundary

The source-backed claim is not that Quetzal-1 failed from normal cold charging.
The source-backed claim is that a Quetzal-style protected baseline uses
thermostatic heater energy to keep the battery charge-safe, while our adaptive
controller targets the same safety outcome with lower heater energy and
payload-aware scheduling.
