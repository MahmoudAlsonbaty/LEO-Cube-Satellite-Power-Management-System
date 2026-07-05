# AI and External Resource Disclosure

## AI Assistance

AI assistance was used to:

| Area | AI contribution | Human/team responsibility |
| --- | --- | --- |
| Repository review | Identified gaps in the original firmware, simulation, and README | Team must verify all final claims before submission |
| Firmware refactor | Drafted an ESP32 operating-mode state machine for sleep, duty cycling, thermal safety, heater, and charge control | Team must compile on the target ESP32 board and verify pin mapping |
| Validation model | Built an executable Python analytical model that produces CSV traces, KPI summaries, and cold long-eclipse comparison plots | Team must replace estimated parameters with final bench measurements if available |
| Visualization | Built dependency-light SVG/PNG bar charts from validation CSV logs using Python and Pillow | Team must ensure figures are regenerated after any model or assumption change |
| Documentation | Drafted architecture, evidence sheet, reproduction instructions, safety declaration, and presentation outline | Team must check compliance with hackathon upload format |

No AI-generated result should be presented as live hardware measurement unless it
has been measured on the bench. The repository labels measured repository data,
datasheet estimates, and flight-reference context separately.

## External Technical Sources

| Source | Use |
| --- | --- |
| `01_Challenge_1_Finalist_Requirements_and_Deadlines.docx.pdf` | Finalist requirements, deliverable checklist, scoring context, and repository evidence expectations |
| Quetzal-1 public EPS paper and supplied/reference material | Battery capacity, heater scale, bus-load context, heater-threshold context, and 1U comparison basis |
| Published 1U CubeSat LEO beta-angle thermal analysis | Source-backed beta-season framing for the realistic cold-season case |
| Published LEO small-satellite beta = 0 thermal study | Source-backed 35-36 min low-beta eclipse duration for the realistic cold-season case |
| CubeSat EPS power-budget reference material | General duty-cycle, orbit-average-power, and eclipse-fraction framing |
| Original repository `results/Power Budget.xlsx` | Legacy comparison only; no longer the primary baseline |
| Espressif ESP32-WROOM-32 datasheet | Controller capabilities and deep-sleep estimate context |
| TI TPS22919 datasheet/product information | Load switch on-state IQ, off-state leakage, controlled rise time, and short protection |
| TI TPS62740 product information | Low-IQ regulator estimate and light-load efficiency context |
| Microchip MCP73831 product information | Single-cell Li-ion/Li-poly charge-controller context |

## Libraries and Tools

| Tool | Use |
| --- | --- |
| Python 3 standard library | Simulation and CSV generation |
| Pillow | Final SVG/PNG chart support where available |
| pdfinfo / pdftotext / pdftoppm | Reading and checking the finalist requirements PDF |
| Mermaid Markdown | Architecture diagram in documentation |
| Git | Repository checkout and change tracking |

The consolidated source and parameter audit trail is
`docs/ASSUMPTIONS_PARAMETERS_AND_CITATIONS.md`.

## Prior Work

The final design continues the Phase 1 concept of eclipse-aware albedo payload
power gating from the original repository. The revised final phase replaces the
headline repo-derived baseline with a Quetzal-1 flight-reference baseline and
adds actual sleep entry in firmware, duty-cycle scheduling, thermal and SOC
modes, charge gating, multi-case validation, and traceable logs.
