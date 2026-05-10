# LEO Cube Satellite Power Management System 

<p align="center">
  <img src="docs/cubesat.png" alt="LEO CubeSat" width="250"/>
</p>

**AESS Sustainability Hackathon 2026 | Challenge 1: Sustainable Electronics**

##  The Mission
Welcome to the future of energy-efficient space exploration! This repository houses the firmware, schematics, and technical documentation for a next-generation Low Earth Orbit (LEO) CubeSat sensing node. 

In space, power is everything. Conventional satellite subsystems often rely on "always-on" architectures that bleed energy, generate excess thermal stress, and artificially shorten mission lifespans. We built this project to fix that.

##  The Core Concept: Ruthless Power Gating
Our strategy is simple but incredibly effective: **hardware-level power gating**. 

Instead of letting idle sensors drain the battery, we use a **MOSFET** as an electronic drawbridge. The system physically severs the power rail to our environmental sensors (LM35 and VEML7700) the exact millisecond they finish reporting their data. 

By duty-cycling these sensors and plunging the main ESP32 controller into deep sleep between data bursts, we absolutely slash the baseline current draw. The result? A radically extended mission lifetime, cooler operating temperatures, and more power available for critical payloads. 

##  The Hardware Stack
* **The Brain:** ESP32 (Utilizing extreme deep-sleep modes)
* **The Senses:** LM35 (Temperature) & VEML7700 (High-Accuracy Ambient Light)
* **The Gatekeeper:** N-Channel MOSFET (Active power cutoff for the sensor array)

## Project Architecture
```text
├── README.md        # Project overview, tools, and instructions
├── /docs            # Diagrams, design notes, and power budgets
├── /src             # ESP32 C/C++ firmware and power-gating logic
├── /simulation      # Power analytical calculations and comparisons
├── /results         # Baseline vs. optimized power plots
└── /hardware        # Schematics, PCB files, and wiring diagrams
