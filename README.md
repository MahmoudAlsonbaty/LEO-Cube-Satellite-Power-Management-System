# LEO Cube Satellite Power Management System 

<p align="center">
  <img src="docs/cubesat.png" alt="LEO CubeSat" width="250"/>
</p>

**AESS Sustainability Hackathon 2026 | Challenge 1: Sustainable Electronics**

*Extreme temperatures and zero gravity are the ultimate stress test for technology. A vague yet very descriptive vision of space. If your software, hardware, or team can survive the environment of low-Earth orbit, it can revolutionize any industry on the planet.*

**We are Aether Avionics, and this is how we're contributing to space sustainability and development.**

## The Hidden Hero: CubeSats
When looking into space technology, we often tend to think of large structures—space rovers, rocketships, and space stations. But there’s a hidden hero of space technology that is just as impactful: **CubeSats**. This revolution shrinks the future of space exploration into a 10cm cube fitting in the palm of your hand. 

These devices unlock infinite possibilities, forming the basis for Albedo missions that are now an integral part of monitoring agricultural health, mapping urban infrastructure, and so much more. Built to swarm Low-Earth Orbit, they are praised for their one-size-fits-all approach. However, innovation always demands a trade-off, and this small size brings a unique set of disadvantages.

Statistical research by NASA indicates that roughly **41% of small satellites experienced total or partial failure**, with battery issues being the primary culprit. Up to **50% of university-built CubeSats fail within the first six months** due to battery lifespan.

### The Eclipse Dilemma
This satellite orbits the Earth every **100 minutes**. For around a quarter of every orbit (~30 minutes), it’s in complete darkness. The solar panels produce no power, but components are still consuming energy. This leads to battery degradation and power shortages, forcing missions to be terminated. Leaving systems on 24/7 is a simple oversight, yet a fatal flaw. For example, during the Quetzal-1 mission, this caused a battery failure that ended up cutting an ambitious 900-day mission into a brutal 200-day mission. 

It didn’t have to end that soon. That’s why we introduce to you our **Low Earth Orbit CubeSat Power Management System**.

## Our Solution
With this system, we ensure that energy isn't just power; it's time. Extending battery life doesn't just save energy; it extends the lifetime of the CubeSat. Our system conserves energy in two crucial ways:

1. **Eclipse Cutoff:** During the eclipse, the CubeSat saves energy by cutting off power to components that aren’t mission-critical. Sensors measure and send data to the microcontroller at regular intervals. Input data is processed to check if the light received at the solar panels is below the threshold corresponding to an eclipse. When positive, the microcontroller shuts off power to Albedo Sensors (which are only needed when sunlight is coincident on them). The microcontroller then goes into deep sleep until a voltage above a certain threshold is detected on the solar panel sensing pin, indicating the satellite is back in direct sunlight.
2. **AI Power Optimization:** While operating in sunlight, our AI model improves our components' efficiency so power is spent where it’s needed. The model evaluates:
    - Time until the next eclipse
    - The eclipse duration
    - Current battery health 
    - Power from solar cells
    - Power consumed by all components
    
    With this data, we determine one of 3 states: **Full operation mode**, **Simple Power Saving Mode**, and **Extreme power saving mode**. Each state changes the periodic sensing time for each sensor or turns off the component completely. This saves **6-10% power** compared to our baseline from the Quetzal-1 Mission, because every watt in space counts.

## Hardware Integration & Active Thermal Armor
We designed a PCB that features a dual-layer design, where the secondary layer serves as a dedicated copper ground plane to minimize signal interference. This strategic architecture also functions as an efficient heatsink for thermal management. 

Furthermore, if our thermal sensor detects that the subsystem temperature has reached a critical threshold of **120°C**, the microcontroller triggers the MOSFET to instantly cut the sensor power rail, preventing catastrophic heat damage.

## Sustainable Development Goals (SDGs)
The impact of our project extends beyond its technical objective towards a healthier space and a sustainable future. We align with 5 out of the 17 SDGs:
* **SDG 7:** By reducing unnecessary energy consumption and improving power efficiency. 
* **SDG 9:** Through improving CubeSat reliability and operational efficiency. 
* **SDG 12:** Due to extending the CubeSats operation and lifespan; it reduces the needs of replacement satellites. 
* **SDG 13:** Through more sustainable space operations and continuous environment monitoring. 
* **SDG 17:** By sharing it under an open license, enabling knowledge sharing and encouraging collaborations.

## Project Architecture
<pre>
├── README.md                                 # Project overview and instructions
├──.gitignore
├── LICENSE                                   # Project license
├── /docs
│   ├── cubesat.png                           # CubeSat visual placeholder
│   ├── LEO_Satellite_Power_Simulation.png    # Rendered output of power savings
│   ├── Schematic Capture.png                 # Image of the subsystem wiring
│   ├── IEEE-AESH-Hackathon-Sustainability-In-Space.pdf
│   ├── AESH Aether Avionics Presentation.pdf
│   └── System Block Diagram.png              # High-level architecture overview
├── /hardware
│   ├── PCB1.PcbDoc                           # Altium Designer PCB Document
│   └── Sheet1.SchDoc                         # Altium Designer Schematic Document
├── /results
│   └── Power Budget.xlsx                     # Detailed numerical energy calculations
├── /simulation
│   ├── CubeSat_MATLAB_Project_V23_Independent_Audit(1).zip # MATLAB Simulation and visualization
│   ├── Power_Consumption_Comparision(early model).py       # Early Python simulation
│   ├── cold_season_analytical_model.py                     # Python model
│   ├── multi_cubesat_logic_benchmark.py                    # Python logic benchmark
│   ├── test_adaptive_eps_logic.py                          # Adaptive EPS AI logic test
│   ├── early_simulation.gif                                # Early simulation animation
│   └── velxio_sketch.zip                                   # Simulation components
└── /src
    ├── ESP32_Firmware_(actual).cpp           # Main ESP32 Firmware
    └── ESP32_Firmware_simplified_(velxio).cpp# Simplified firmware 
</pre>

## Setup Instructions
To fully review, simulate, and compile the files in this repository, you will need the following tools installed:

1. **Python 3.x:** Required to run the AI logic and orbit simulation scripts in the `/simulation` directory. Ensure you have standard data visualization libraries installed (e.g., `pip install matplotlib numpy pandas`).
2. **Altium Designer:** Required to open, interact with, and view the `.PcbDoc` and `.SchDoc` files in the `/hardware` directory.
3. **MATLAB / Simulink:** Required to extract and run the CubeSat orbit visualization and simulation located in the `/simulation` zip file.
4. **Arduino IDE or PlatformIO:** Required to view and compile the `.cpp` firmware in `/src`. You must have the **ESP32 Board Package** installed via the Boards Manager.
5. **Spreadsheet Software:** (Excel, Google Sheets, etc.) required to open the `.xlsx` power budget breakdown.

## Execution Instructions
1. **MATLAB Simulation:** Extract `CubeSat_MATLAB_Project_V23_Independent_Audit(1).zip` and open the main `.m` or `.slx` file in MATLAB to visualize the CubeSat orbiting Earth successfully.
2. **AI EPS Logic Testing:** Open your terminal, navigate to the repository root, and run the Python AI logic models (e.g., `python simulation/test_adaptive_eps_logic.py`). These scripts demonstrate how the adaptive EPS logic shifts between states.
3. **Hardware & Firmware Review:** 
   - Open `/hardware/PCB1.PcbDoc` in Altium Designer to verify the dual-layer heatsink design.
   - Open `/src/ESP32_Firmware_(actual).cpp` in your IDE to review the microcontroller's deep sleep polling cycle and 120°C thermal limit cut-off.

## Velxio simulation instructions

To load the simulation into your Velxio workspace:

1. Open the Velxio application.
2. Navigate to the import/open menu.
3. Locate and select the compressed project file: `simulation/velxio_sketch.zip`.
4. Confirm to import and load the sketch.
5. Click the "Start" or "Run" button to begin the simulation.

## Parameters and Configurations
* **Orbit Duration:** 100 minutes.
* **Eclipse Duration:** ~30 minutes (roughly a quarter of the orbit).
* **Thermal Cut-off Threshold:** 120°C.
* **Deep Sleep Wake-up Heartbeat:** 60 seconds (microcontroller wakes up briefly to check for solar voltage).
* **Power Savings Achieved:** 6% - 10% (relative to the Quetzal-1 baseline).
* **AI Model Inputs:** Time to eclipse, eclipse duration, battery health, power from solar cells, and consumed power.
* **AI Model States:** 
  1. Full operation mode
  2. Simple Power Saving mode
  3. Extreme power saving mode

## Assumptions
* **Standard LEO Constraints:** The system operates under the standard environmental and orbital assumptions of Low-Earth Orbit CubeSat missions.
* **Zero Solar Generation During Eclipse:** We assume solar panels produce absolute zero power during the 30-minute shadow phase, validating our complete sensor cut-off strategy.
* **Baseline Validity:** The power consumption baseline extrapolated from the Quetzal-1 mission is a valid benchmark for standard CubeSat comparisons.
* **Constant Radiation During Sunlight:** We assume relative stability in solar radiation metrics during the sunlight phase unless modified by orbital maneuvers.

## Reproduction Steps
We designed this system to be highly transparent. You can reproduce and verify our power, thermal savings, and AI states by following these steps:

1. **Verify Baseline & Budget:** Open `results/Power Budget.xlsx` to review the base numbers and the calculations that yield the 6-10% efficiency gain.
2. **Run AI State Logic:** Execute the Python simulation scripts (e.g., `test_adaptive_eps_logic.py`) to observe how the AI transitions between Full Operation, Simple Power Saving, and Extreme Power Saving based on the input parameters.
3. **Simulate the Orbit:** Extract the MATLAB project, run the simulation, and verify the orbital mechanics visualization.
4. **Audit the Hardware gating:** Open the Altium files. Visually inspect the secondary ground plane (heatsink) and verify how the sensors are gated from the main power rail via the MOSFET.
5. **Review the Firmware:** Inspect the ESP32 code to confirm the 60-second polling interval during eclipse and the active thermal gating logic triggered at 120°C.
