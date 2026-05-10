# LEO Cube Satellite Power Management System 

<p align="center">
  <img src="docs/cubesat.png" alt="LEO CubeSat" width="250"/>
</p>

**AESS Sustainability Hackathon 2026 | Challenge 1: Sustainable Electronics**

##  The Mission: Albedo Weather Monitoring
Welcome to the future of energy-efficient space exploration! This repository houses the firmware, schematics, and technical documentation for a **CubeSat Albedo Weather Satellite** sensing node. 

Our primary mission is to measure Earth's albedo (solar reflectance). However, conventional satellites often waste massive amounts of energy running "always-on" architectures even when there is no sunlight to measure. We built this subsystem to completely eliminate that waste.

##  The Core Concept: Eclipse-Aware Power Gating
Our strategy relies on ruthless, **hardware-level power gating** tied directly to the satellite's orbital mechanics. 

* **The 100-Minute Orbit:** Our CubeSat operates on a 100-minute orbit, spending roughly 30 minutes in the Earth's shadow (eclipse). Since we cannot measure albedo in the dark, we use a **MOSFET** as an electronic drawbridge to physically sever the power rail to our sensor array (LM35 and VEML7700) during this entire 30-minute window.
* **The 60-Second Heartbeat:** The main ESP32 controller doesn't stay awake waiting for the sun. It plunges into an ultra-low-power deep sleep, waking up briefly every **60 seconds** just to check if the required turn-on conditions (exiting the eclipse) have been met. 

##  Sustainability Impact: Active Thermal Armor
Space is an environment of extremes. Beyond just saving battery life, our power management system actively protects the hardware to prolong the satellite's useful mission lifetime. 

If our LM35 sensor detects that the subsystem temperature has reached a critical threshold of **120°C**, the ESP32 triggers the MOSFET to instantly cut the sensor power rail. This automatic thermal shutdown prevents catastrophic heat damage and ensures the node survives harsh solar radiation spikes.

##  The Hardware Stack
* **The Brain:** ESP32 (Executing the 60-second deep-sleep polling cycle)
* **The Senses:** LM35 (Thermal limit monitor) & VEML7700 (High-accuracy ambient light/albedo sensor)
* **The Gatekeeper:** N-Channel MOSFET (Active power cutoff during eclipse and thermal events)

##  Project Architecture
```text
├── README.md        # Project overview, tools, and instructions
├── /docs            # Diagrams, design notes, and power budgets
├── /src             # ESP32 C/C++ firmware and power-gating logic
├── /simulation      # Power analytical calculations (100-min orbit models)
├── /results         # Baseline vs. optimized power plots
└── /hardware        # Schematics, PCB files, and wiring diagrams
