# Equipment and Safety Declaration

## Intended Final Demo

The demo is a low-power electronic subsystem demonstration for a CubeSat albedo
sensor power controller. It can be shown either as:

| Demo type | Equipment |
| --- | --- |
| Executable model | Laptop running Python 3 and repository files |
| Bench proof of concept | ESP32 board, low-voltage USB or current-limited bench supply, VEML7700/light sensor, temperature sensor or potentiometer-based emulator, load switch/MOSFET rail, optional current monitor |

## Electrical Safety

| Item | Declaration |
| --- | --- |
| Supply voltage | Low-voltage DC only; intended 3.3 V logic rail and single-cell Li-ion class battery emulation |
| Current | Current-limited bench supply recommended; no high-current payload required for final demo |
| Battery | If a real Li-ion/Li-poly cell is used, it must include protection and be charged only through an approved charge controller. For judging, a bench supply or battery emulator is preferred |
| RF | No RF transmission is required or authorized for this demo |
| Lasers | None |
| Acoustic | None |
| Pressure systems | None |
| Hazardous chemicals | None |
| Mechanical motion | None |

## Thermal Safety

The firmware includes payload thermal lockout and cold-battery heater logic for
model validation. The live demo should emulate temperature using a sensor,
resistor network, potentiometer, or controlled low-power heater only. Do not
heat a battery cell during the demo.

## Demo Constraints

| Constraint | Mitigation |
| --- | --- |
| Hardware measurement uncertainty | Use current-limited supply and log measurement method; compare against executable model |
| Battery safety | Prefer battery emulator; do not charge or heat unprotected cells |
| Hot-case validation | Use ADC emulation rather than unsafe heating |
| Judge reproducibility | Keep the Python model executable with no non-standard dependencies |
