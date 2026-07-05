#!/usr/bin/env python3
"""
Logic tests for the adaptive EPS firmware state machine.

This script mirrors the policy thresholds in src/ESP32 Firmware.cpp so the
control logic can be checked without an ESP32/Arduino build environment.
"""

from __future__ import annotations

from dataclasses import dataclass


SOLAR_DAYLIGHT_ADC = 500
SOLAR_STRONG_ADC = 2200
SOLAR_WEAK_ADC = 800

PAYLOAD_HOT_OFF_C = 85.0
PAYLOAD_HOT_ON_C = 75.0
BATTERY_HEATER_ON_C = -5.0
BATTERY_HEATER_OFF_C = 5.0
BATTERY_HEATER_STRONG_C = -10.0
BATTERY_CRITICAL_COLD_C = -15.0
CHARGE_MIN_TEMP_C = 0.0
CHARGE_MAX_TEMP_C = 45.0

SOC_CONTINUOUS_PAYLOAD_PCT = 85.0
SOC_SCHEDULED_PAYLOAD_PCT = 60.0
SOC_PAYLOAD_OFF_PCT = 40.0
SOC_LOW_POWER_ENTER_PCT = 25.0
SOC_LOW_POWER_EXIT_PCT = 35.0
SOC_HEATER_MIN_PCT = 30.0
CHARGE_SOC_STOP_PCT = 95.0

MAX_SOLAR_GENERATION_W = 2.37
FIXED_BUS_LOAD_W = 0.6637
PAYLOAD_ACTIVE_W = 0.123
HEATER_ACTIVE_W = 0.898
MIN_POWER_MARGIN_W = 0.10
STRONG_POWER_MARGIN_W = 0.15


@dataclass
class Latches:
    thermal: bool = False
    low_soc: bool = False
    heater: bool = False
    fault: bool = False


@dataclass(frozen=True)
class State:
    solar_adc: int
    batt_temp_c: float
    payload_temp_c: float
    soc_pct: float
    batt_temp_raw: int = 3102
    payload_temp_raw: int = 3102
    soc_raw: int = 3000

    @property
    def daylight(self) -> bool:
        return self.solar_adc >= SOLAR_DAYLIGHT_ADC

    @property
    def strong_sunlight(self) -> bool:
        return self.solar_adc >= SOLAR_STRONG_ADC

    @property
    def weak_sunlight(self) -> bool:
        return self.solar_adc < SOLAR_WEAK_ADC

    @property
    def generated_power_w(self) -> float:
        if self.solar_adc < SOLAR_DAYLIGHT_ADC:
            return 0.0
        normalized = (self.solar_adc - SOLAR_DAYLIGHT_ADC) / (4095 - SOLAR_DAYLIGHT_ADC)
        return max(0.0, min(1.0, normalized)) * MAX_SOLAR_GENERATION_W


def update_latches(state: State, latches: Latches) -> None:
    if state.payload_temp_c >= PAYLOAD_HOT_OFF_C:
        latches.thermal = True
    elif state.payload_temp_c <= PAYLOAD_HOT_ON_C:
        latches.thermal = False

    if state.soc_pct <= SOC_LOW_POWER_ENTER_PCT:
        latches.low_soc = True
    elif state.soc_pct >= SOC_LOW_POWER_EXIT_PCT:
        latches.low_soc = False

    if state.batt_temp_c <= BATTERY_HEATER_ON_C:
        latches.heater = True
    elif state.batt_temp_c >= BATTERY_HEATER_OFF_C:
        latches.heater = False


def detect_fault(state: State, latches: Latches) -> bool:
    sensor_out_of_range = (
        state.soc_raw <= 5 or state.batt_temp_raw <= 5 or state.payload_temp_raw <= 5
    )
    return latches.fault or sensor_out_of_range


def estimate_demand_w(payload_on: bool, heater_on: bool) -> float:
    demand = FIXED_BUS_LOAD_W
    if payload_on:
        demand += PAYLOAD_ACTIVE_W
    if heater_on:
        demand += HEATER_ACTIVE_W
    return demand


def estimate_margin_w(state: State, payload_on: bool, heater_on: bool) -> float:
    return state.generated_power_w - estimate_demand_w(payload_on, heater_on)


def select_mode(state: State, latches: Latches) -> str:
    if detect_fault(state, latches):
        return "FAULT_SAFE"
    if latches.thermal:
        return "THERMAL_SAFE"
    if not state.daylight:
        return "ECLIPSE_SURVIVAL"
    if latches.low_soc or state.soc_pct < SOC_PAYLOAD_OFF_PCT:
        return "LOW_SOC_SAFE"
    if state.weak_sunlight and state.batt_temp_c < BATTERY_HEATER_OFF_C:
        return "PRE_ECLIPSE_PREP"
    if (
        state.soc_pct < SOC_SCHEDULED_PAYLOAD_PCT
        or estimate_margin_w(state, True, latches.heater) < MIN_POWER_MARGIN_W
    ):
        return "SUNLIGHT_POWER_SAVE"
    if (
        state.strong_sunlight
        and state.soc_pct >= SOC_CONTINUOUS_PAYLOAD_PCT
        and estimate_margin_w(state, True, latches.heater) >= STRONG_POWER_MARGIN_W
    ):
        return "SUNLIGHT_SCIENCE"
    return "SUNLIGHT_SCHEDULED"


def select_payload_policy(state: State, latches: Latches, mode: str) -> str:
    if mode in {
        "ECLIPSE_SURVIVAL",
        "THERMAL_SAFE",
        "FAULT_SAFE",
        "LOW_SOC_SAFE",
    }:
        return "OFF"
    if state.soc_pct < SOC_PAYLOAD_OFF_PCT:
        return "OFF"
    if mode == "PRE_ECLIPSE_PREP":
        return "PRE_ECLIPSE_LOW_DUTY"
    if mode == "SUNLIGHT_POWER_SAVE":
        return "REDUCED_CADENCE"
    if mode == "SUNLIGHT_SCIENCE":
        return "CONTINUOUS_SUNLIGHT"
    return "SCHEDULED_SUNLIGHT"


def heater_policy(state: State, latches: Latches, mode: str) -> tuple[str, int]:
    if not latches.heater:
        return "OFF", 0
    if state.batt_temp_c <= BATTERY_CRITICAL_COLD_C:
        return "SURVIVAL", 60
    if mode == "FAULT_SAFE":
        return ("PULSE_LOW", 12) if state.soc_pct >= SOC_HEATER_MIN_PCT else ("OFF", 0)
    if mode == "LOW_SOC_SAFE" and state.soc_pct < SOC_HEATER_MIN_PCT:
        return "OFF", 0
    if state.soc_pct < SOC_HEATER_MIN_PCT:
        return "OFF", 0
    if state.batt_temp_c <= BATTERY_HEATER_STRONG_C or mode == "ECLIPSE_SURVIVAL":
        return "PULSE_STRONG", 21
    return "PULSE_LOW", 12


def charge_allowed(state: State, latches: Latches) -> bool:
    return (
        state.daylight
        and state.soc_pct < CHARGE_SOC_STOP_PCT
        and CHARGE_MIN_TEMP_C <= state.batt_temp_c <= CHARGE_MAX_TEMP_C
        and not detect_fault(state, latches)
    )


def evaluate(state: State, latches: Latches | None = None) -> tuple[str, str, str, int, bool]:
    latches = latches or Latches()
    update_latches(state, latches)
    mode = select_mode(state, latches)
    policy = select_payload_policy(state, latches, mode)
    heater_mode, heater_pulse_s = heater_policy(state, latches, mode)
    charger = charge_allowed(state, latches)
    return mode, policy, heater_mode, heater_pulse_s, charger


def assert_case(name: str, state: State, expected: tuple[str, str, str, int, bool]) -> None:
    actual = evaluate(state)
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected}, got {actual}")
    print(f"PASS {name}: {actual}")


def main() -> None:
    assert_case(
        "healthy strong sunlight maximizes data",
        State(solar_adc=4095, batt_temp_c=20.0, payload_temp_c=30.0, soc_pct=90.0),
        ("SUNLIGHT_SCIENCE", "CONTINUOUS_SUNLIGHT", "OFF", 0, True),
    )
    assert_case(
        "normal sunlight uses scheduled data collection",
        State(solar_adc=1900, batt_temp_c=20.0, payload_temp_c=30.0, soc_pct=75.0),
        ("SUNLIGHT_SCHEDULED", "SCHEDULED_SUNLIGHT", "OFF", 0, True),
    )
    assert_case(
        "low-but-not-critical SOC reduces payload cadence",
        State(solar_adc=4095, batt_temp_c=20.0, payload_temp_c=30.0, soc_pct=55.0),
        ("SUNLIGHT_POWER_SAVE", "REDUCED_CADENCE", "OFF", 0, True),
    )
    assert_case(
        "critical low SOC shuts payload off",
        State(solar_adc=4095, batt_temp_c=20.0, payload_temp_c=30.0, soc_pct=22.0),
        ("LOW_SOC_SAFE", "OFF", "OFF", 0, True),
    )
    assert_case(
        "eclipse disables payload and charging",
        State(solar_adc=0, batt_temp_c=20.0, payload_temp_c=30.0, soc_pct=80.0),
        ("ECLIPSE_SURVIVAL", "OFF", "OFF", 0, False),
    )
    assert_case(
        "cold eclipse enables bounded heater pulse",
        State(solar_adc=0, batt_temp_c=-8.0, payload_temp_c=10.0, soc_pct=80.0),
        ("ECLIPSE_SURVIVAL", "OFF", "PULSE_STRONG", 21, False),
    )
    assert_case(
        "thermal lockout disables payload even in sunlight",
        State(solar_adc=4095, batt_temp_c=20.0, payload_temp_c=90.0, soc_pct=90.0),
        ("THERMAL_SAFE", "OFF", "OFF", 0, True),
    )
    assert_case(
        "pre-eclipse cold case keeps trickle payload and heater pulse",
        State(solar_adc=650, batt_temp_c=-6.0, payload_temp_c=20.0, soc_pct=80.0),
        ("PRE_ECLIPSE_PREP", "PRE_ECLIPSE_LOW_DUTY", "PULSE_LOW", 12, False),
    )
    assert_case(
        "unsafe cold charging is inhibited while heater runs",
        State(solar_adc=4095, batt_temp_c=-8.0, payload_temp_c=20.0, soc_pct=90.0),
        ("SUNLIGHT_SCIENCE", "CONTINUOUS_SUNLIGHT", "PULSE_LOW", 12, False),
    )
    assert_case(
        "critical cold heater stays in survival mode",
        State(solar_adc=0, batt_temp_c=-16.0, payload_temp_c=0.0, soc_pct=20.0),
        ("ECLIPSE_SURVIVAL", "OFF", "SURVIVAL", 60, False),
    )


if __name__ == "__main__":
    main()
