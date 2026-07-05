#include <Arduino.h>
#include <math.h>
#include "esp_sleep.h"

/*
  Adaptive EPS power-management controller for the CubeSat payload subsystem.

  Control goals:
  - Collect payload data aggressively when sunlight, SOC, and power margin allow it.
  - Reduce payload cadence when stored energy or solar generation is weak.
  - Turn the payload rail off during eclipse, thermal lockout, low-SOC survival,
    and fault conditions.
  - Keep battery heating as a survival-critical policy, independent of payload
    collection.
  - Enable charging only when sunlight, battery temperature, and SOC are safe.

  Hardware boundary:
  This firmware controls a payload load switch, battery heater switch, and charge
  enable line. It does not replace the full spacecraft EPS.
*/

// Pins 32-39 are RTC-capable ADC pins on ESP32 and can be read immediately
// after timer wake without powering the payload rail.
#define SOLAR_SENSE_PIN       34
#define BATTERY_TEMP_PIN      32
#define PAYLOAD_TEMP_PIN      35
#define ALBEDO_SENSOR_PIN     33
#define SOC_SENSE_PIN         39

#define PAYLOAD_SWITCH_PIN    23
#define HEATER_SWITCH_PIN     22
#define CHARGE_ENABLE_PIN     21

#define uS_TO_S_FACTOR        1000000ULL

// Timing policy.
static const uint32_t HEARTBEAT_S                 = 60;
static const uint32_t CONTINUOUS_WINDOW_S         = 60;
static const uint32_t SCHEDULED_WINDOW_S          = 57;  // balanced-safe: about 95 percent duty
static const uint32_t REDUCED_WINDOW_S            = 21;  // balanced-safe: about 35 percent duty
static const uint32_t PRE_ECLIPSE_WINDOW_S        = 48;  // cold-season tune: about 80 percent duty
static const uint32_t THERMAL_RECHECK_S           = 60;
static const uint32_t MIN_SLEEP_S                 = 1;

// ADC thresholds. Replace these with bench-calibrated constants before flight.
static const int SOLAR_DAYLIGHT_ADC               = 500;
static const int SOLAR_STRONG_ADC                 = 2200;
static const int SOLAR_WEAK_ADC                   = 800;

// Thermal limits.
static const float PAYLOAD_HOT_OFF_C              = 85.0f;
static const float PAYLOAD_HOT_ON_C               = 75.0f;
static const float BATTERY_HEATER_ON_C            = -5.0f;
static const float BATTERY_HEATER_OFF_C           = 5.0f;
static const float BATTERY_HEATER_STRONG_C        = -10.0f;
static const float BATTERY_CRITICAL_COLD_C        = -15.0f;
static const float CHARGE_MIN_TEMP_C              = 0.0f;
static const float CHARGE_MAX_TEMP_C              = 45.0f;

// SOC limits.
static const float SOC_CONTINUOUS_PAYLOAD_PCT     = 85.0f;
static const float SOC_SCHEDULED_PAYLOAD_PCT      = 60.0f;
static const float SOC_PAYLOAD_OFF_PCT            = 40.0f;
static const float SOC_LOW_POWER_ENTER_PCT        = 25.0f;
static const float SOC_LOW_POWER_EXIT_PCT         = 35.0f;
static const float SOC_HEATER_MIN_PCT             = 30.0f;
static const float CHARGE_SOC_STOP_PCT            = 95.0f;

// Power model used for onboard policy decisions. These are deliberately coarse
// and should be replaced by measured current telemetry if the final EPS exposes
// it to the controller.
static const float MAX_SOLAR_GENERATION_W         = 2.37f;   // Quetzal-style 1U sunlight estimate
static const float FIXED_BUS_LOAD_W               = 0.6637f; // Quetzal full-bus context, payload excluded
static const float PAYLOAD_ACTIVE_W               = 0.123f;
static const float HEATER_ACTIVE_W                = 0.898f;
static const float MIN_POWER_MARGIN_W             = 0.10f;
static const float STRONG_POWER_MARGIN_W          = 0.15f;

enum OperatingMode {
  MODE_BOOT,
  MODE_SUNLIGHT_SCIENCE,
  MODE_SUNLIGHT_SCHEDULED,
  MODE_SUNLIGHT_POWER_SAVE,
  MODE_PRE_ECLIPSE_PREP,
  MODE_ECLIPSE_SURVIVAL,
  MODE_LOW_SOC_SAFE,
  MODE_THERMAL_SAFE,
  MODE_FAULT_SAFE
};

enum PayloadPolicy {
  PAYLOAD_CONTINUOUS_SUNLIGHT,
  PAYLOAD_SCHEDULED_SUNLIGHT,
  PAYLOAD_REDUCED_CADENCE,
  PAYLOAD_PRE_ECLIPSE_LOW_DUTY,
  PAYLOAD_OFF
};

enum HeaterPolicy {
  HEATER_OFF,
  HEATER_PULSE_LOW,
  HEATER_PULSE_STRONG,
  HEATER_SURVIVAL
};

struct TelemetryState {
  int solarRaw;
  int battTempRaw;
  int payloadTempRaw;
  int socRaw;
  bool daylight;
  bool strongSunlight;
  bool weakSunlight;
  float battTempC;
  float payloadTempC;
  float socPct;
  float generatedPowerW;
};

RTC_DATA_ATTR uint32_t bootCount = 0;
RTC_DATA_ATTR uint32_t sunWakeCounter = 0;
RTC_DATA_ATTR bool thermalLockout = false;
RTC_DATA_ATTR bool lowSocLockout = false;
RTC_DATA_ATTR bool heaterLatched = false;
RTC_DATA_ATTR bool faultLatched = false;

const char *modeName(OperatingMode mode) {
  switch (mode) {
    case MODE_BOOT: return "BOOT";
    case MODE_SUNLIGHT_SCIENCE: return "SUNLIGHT_SCIENCE";
    case MODE_SUNLIGHT_SCHEDULED: return "SUNLIGHT_SCHEDULED";
    case MODE_SUNLIGHT_POWER_SAVE: return "SUNLIGHT_POWER_SAVE";
    case MODE_PRE_ECLIPSE_PREP: return "PRE_ECLIPSE_PREP";
    case MODE_ECLIPSE_SURVIVAL: return "ECLIPSE_SURVIVAL";
    case MODE_LOW_SOC_SAFE: return "LOW_SOC_SAFE";
    case MODE_THERMAL_SAFE: return "THERMAL_SAFE";
    case MODE_FAULT_SAFE: return "FAULT_SAFE";
    default: return "UNKNOWN";
  }
}

const char *payloadPolicyName(PayloadPolicy policy) {
  switch (policy) {
    case PAYLOAD_CONTINUOUS_SUNLIGHT: return "CONTINUOUS_SUNLIGHT";
    case PAYLOAD_SCHEDULED_SUNLIGHT: return "SCHEDULED_SUNLIGHT";
    case PAYLOAD_REDUCED_CADENCE: return "REDUCED_CADENCE";
    case PAYLOAD_PRE_ECLIPSE_LOW_DUTY: return "PRE_ECLIPSE_LOW_DUTY";
    case PAYLOAD_OFF: return "OFF";
    default: return "UNKNOWN";
  }
}

const char *heaterPolicyName(HeaterPolicy policy) {
  switch (policy) {
    case HEATER_OFF: return "OFF";
    case HEATER_PULSE_LOW: return "PULSE_LOW";
    case HEATER_PULSE_STRONG: return "PULSE_STRONG";
    case HEATER_SURVIVAL: return "SURVIVAL";
    default: return "UNKNOWN";
  }
}

float interpolate3(int adcValue, float x1, float y1, float x2, float y2, float x3, float y3) {
  float x = (float)adcValue;
  float term1 = y1 * ((x - x2) * (x - x3)) / ((x1 - x2) * (x1 - x3));
  float term2 = y2 * ((x - x1) * (x - x3)) / ((x2 - x1) * (x2 - x3));
  float term3 = y3 * ((x - x1) * (x - x2)) / ((x3 - x1) * (x3 - x2));
  return term1 + term2 + term3;
}

float getTemperatureC(int adcValue) {
  if (adcValue <= 620) return 125.0f;
  if (adcValue >= 4095) return -40.0f;
  return interpolate3(adcValue, 620.0f, 125.0f, 3102.0f, 25.0f, 4095.0f, -40.0f);
}

float getLux(int adcValue) {
  if (adcValue <= 0) return 0.0f;
  if (adcValue >= 4095) return 1000.0f;
  return interpolate3(adcValue, 0.0f, 0.0f, 3102.0f, 500.0f, 4095.0f, 1000.0f);
}

float getSocPct(int adcValue) {
  float soc = ((float)adcValue / 4095.0f) * 100.0f;
  if (soc < 0.0f) return 0.0f;
  if (soc > 100.0f) return 100.0f;
  return soc;
}

float estimateGeneratedPowerW(int solarRaw) {
  if (solarRaw < SOLAR_DAYLIGHT_ADC) return 0.0f;
  float normalized = (float)(solarRaw - SOLAR_DAYLIGHT_ADC) /
                     (float)(4095 - SOLAR_DAYLIGHT_ADC);
  if (normalized < 0.0f) normalized = 0.0f;
  if (normalized > 1.0f) normalized = 1.0f;
  return normalized * MAX_SOLAR_GENERATION_W;
}

float estimateDemandW(bool payloadOn, bool heaterOn) {
  float demand = FIXED_BUS_LOAD_W;
  if (payloadOn) demand += PAYLOAD_ACTIVE_W;
  if (heaterOn) demand += HEATER_ACTIVE_W;
  return demand;
}

float estimateMarginW(const TelemetryState &state, bool payloadOn, bool heaterOn) {
  return state.generatedPowerW - estimateDemandW(payloadOn, heaterOn);
}

void setPayloadRail(bool enabled) {
  digitalWrite(PAYLOAD_SWITCH_PIN, enabled ? HIGH : LOW);
}

void setHeater(bool enabled) {
  digitalWrite(HEATER_SWITCH_PIN, enabled ? HIGH : LOW);
}

void setCharger(bool enabled) {
  digitalWrite(CHARGE_ENABLE_PIN, enabled ? HIGH : LOW);
}

TelemetryState readTelemetryState() {
  TelemetryState state;
  state.solarRaw = analogRead(SOLAR_SENSE_PIN);
  state.battTempRaw = analogRead(BATTERY_TEMP_PIN);
  state.payloadTempRaw = analogRead(PAYLOAD_TEMP_PIN);
  state.socRaw = analogRead(SOC_SENSE_PIN);
  state.daylight = state.solarRaw >= SOLAR_DAYLIGHT_ADC;
  state.strongSunlight = state.solarRaw >= SOLAR_STRONG_ADC;
  state.weakSunlight = state.solarRaw < SOLAR_WEAK_ADC;
  state.battTempC = getTemperatureC(state.battTempRaw);
  state.payloadTempC = getTemperatureC(state.payloadTempRaw);
  state.socPct = getSocPct(state.socRaw);
  state.generatedPowerW = estimateGeneratedPowerW(state.solarRaw);
  return state;
}

void updatePersistentSafetyFlags(const TelemetryState &state) {
  if (state.payloadTempC >= PAYLOAD_HOT_OFF_C) {
    thermalLockout = true;
  } else if (state.payloadTempC <= PAYLOAD_HOT_ON_C) {
    thermalLockout = false;
  }

  if (state.socPct <= SOC_LOW_POWER_ENTER_PCT) {
    lowSocLockout = true;
  } else if (state.socPct >= SOC_LOW_POWER_EXIT_PCT) {
    lowSocLockout = false;
  }

  if (state.battTempC <= BATTERY_HEATER_ON_C) {
    heaterLatched = true;
  } else if (state.battTempC >= BATTERY_HEATER_OFF_C) {
    heaterLatched = false;
  }
}

bool detectFault(const TelemetryState &state) {
  bool sensorOutOfRange = state.socRaw <= 5 || state.battTempRaw <= 5 || state.payloadTempRaw <= 5;
  return faultLatched || sensorOutOfRange;
}

bool chargeAllowed(const TelemetryState &state) {
  return state.daylight &&
         state.socPct < CHARGE_SOC_STOP_PCT &&
         state.battTempC >= CHARGE_MIN_TEMP_C &&
         state.battTempC <= CHARGE_MAX_TEMP_C &&
         !detectFault(state);
}

OperatingMode selectOperatingMode(const TelemetryState &state) {
  if (detectFault(state)) {
    return MODE_FAULT_SAFE;
  }
  if (thermalLockout) {
    return MODE_THERMAL_SAFE;
  }
  if (!state.daylight) {
    return MODE_ECLIPSE_SURVIVAL;
  }
  if (lowSocLockout || state.socPct < SOC_PAYLOAD_OFF_PCT) {
    return MODE_LOW_SOC_SAFE;
  }
  if (state.weakSunlight && state.battTempC < BATTERY_HEATER_OFF_C) {
    return MODE_PRE_ECLIPSE_PREP;
  }
  if (state.socPct < SOC_SCHEDULED_PAYLOAD_PCT ||
      estimateMarginW(state, true, heaterLatched) < MIN_POWER_MARGIN_W) {
    return MODE_SUNLIGHT_POWER_SAVE;
  }
  if (state.strongSunlight &&
      state.socPct >= SOC_CONTINUOUS_PAYLOAD_PCT &&
      estimateMarginW(state, true, heaterLatched) >= STRONG_POWER_MARGIN_W) {
    return MODE_SUNLIGHT_SCIENCE;
  }
  return MODE_SUNLIGHT_SCHEDULED;
}

PayloadPolicy selectPayloadPolicy(const TelemetryState &state, OperatingMode mode) {
  if (mode == MODE_ECLIPSE_SURVIVAL ||
      mode == MODE_THERMAL_SAFE ||
      mode == MODE_FAULT_SAFE ||
      mode == MODE_LOW_SOC_SAFE) {
    return PAYLOAD_OFF;
  }

  if (state.socPct < SOC_PAYLOAD_OFF_PCT) {
    return PAYLOAD_OFF;
  }

  if (mode == MODE_PRE_ECLIPSE_PREP) {
    return PAYLOAD_PRE_ECLIPSE_LOW_DUTY;
  }

  if (mode == MODE_SUNLIGHT_POWER_SAVE) {
    return PAYLOAD_REDUCED_CADENCE;
  }

  if (mode == MODE_SUNLIGHT_SCIENCE) {
    return PAYLOAD_CONTINUOUS_SUNLIGHT;
  }

  return PAYLOAD_SCHEDULED_SUNLIGHT;
}

HeaterPolicy selectHeaterPolicy(const TelemetryState &state, OperatingMode mode) {
  if (!heaterLatched) return HEATER_OFF;

  // Critical cold overrides SOC limits because battery survival comes first.
  if (state.battTempC <= BATTERY_CRITICAL_COLD_C) return HEATER_SURVIVAL;

  if (mode == MODE_FAULT_SAFE) {
    return (state.socPct >= SOC_HEATER_MIN_PCT) ? HEATER_PULSE_LOW : HEATER_OFF;
  }

  if (mode == MODE_LOW_SOC_SAFE && state.socPct < SOC_HEATER_MIN_PCT) {
    return HEATER_OFF;
  }

  if (state.socPct < SOC_HEATER_MIN_PCT) {
    return HEATER_OFF;
  }

  if (state.battTempC <= BATTERY_HEATER_STRONG_C || mode == MODE_ECLIPSE_SURVIVAL) {
    return HEATER_PULSE_STRONG;
  }

  return HEATER_PULSE_LOW;
}

uint32_t heaterPulseSeconds(HeaterPolicy policy) {
  switch (policy) {
    case HEATER_SURVIVAL: return HEARTBEAT_S;
    case HEATER_PULSE_STRONG: return 21;
    case HEATER_PULSE_LOW: return 12;
    case HEATER_OFF: return 0;
  }
  return 0;
}

uint32_t payloadWindowSeconds(PayloadPolicy policy) {
  switch (policy) {
    case PAYLOAD_CONTINUOUS_SUNLIGHT: return CONTINUOUS_WINDOW_S;
    case PAYLOAD_SCHEDULED_SUNLIGHT: return SCHEDULED_WINDOW_S;
    case PAYLOAD_REDUCED_CADENCE: return REDUCED_WINDOW_S;
    case PAYLOAD_PRE_ECLIPSE_LOW_DUTY: return PRE_ECLIPSE_WINDOW_S;
    case PAYLOAD_OFF: return 0;
  }
  return 0;
}

uint32_t nextSleepSeconds(uint32_t activeWindowS) {
  if (activeWindowS >= HEARTBEAT_S) return MIN_SLEEP_S;
  return HEARTBEAT_S - activeWindowS;
}

void runHeaterPulse(uint32_t pulseS) {
  if (pulseS == 0) {
    setHeater(false);
    return;
  }
  setHeater(true);
  delay(pulseS * 1000UL);
  setHeater(false);
}

void enterSleep(uint32_t seconds, OperatingMode mode) {
  setPayloadRail(false);
  Serial.print("sleep_s=");
  Serial.print(seconds);
  Serial.print(", next_mode=");
  Serial.println(modeName(mode));
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)seconds * uS_TO_S_FACTOR);
  esp_deep_sleep_start();
}

void printTelemetry(OperatingMode mode,
                    PayloadPolicy policy,
                    const TelemetryState &state,
                    HeaterPolicy heaterPolicy,
                    uint32_t heaterPulseS,
                    bool chargerOn,
                    float lux,
                    float marginW) {
  Serial.print("mode=");
  Serial.print(modeName(mode));
  Serial.print(", payload_policy=");
  Serial.print(payloadPolicyName(policy));
  Serial.print(", boot=");
  Serial.print(bootCount);
  Serial.print(", solar_adc=");
  Serial.print(state.solarRaw);
  Serial.print(", generated_w=");
  Serial.print(state.generatedPowerW, 3);
  Serial.print(", batt_temp_c=");
  Serial.print(state.battTempC, 1);
  Serial.print(", payload_temp_c=");
  Serial.print(state.payloadTempC, 1);
  Serial.print(", soc_pct=");
  Serial.print(state.socPct, 1);
  Serial.print(", heater_policy=");
  Serial.print(heaterPolicyName(heaterPolicy));
  Serial.print(", heater_pulse_s=");
  Serial.print(heaterPulseS);
  Serial.print(", charger=");
  Serial.print(chargerOn ? "ON" : "OFF");
  Serial.print(", thermal_lockout=");
  Serial.print(thermalLockout ? "YES" : "NO");
  Serial.print(", low_soc=");
  Serial.print(lowSocLockout ? "YES" : "NO");
  Serial.print(", margin_w=");
  Serial.print(marginW, 3);
  Serial.print(", lux=");
  Serial.println(lux, 1);
}

void collectPayloadSamples(OperatingMode mode,
                           PayloadPolicy policy,
                           const TelemetryState &state,
                           HeaterPolicy heaterPolicy,
                           uint32_t heaterPulseS,
                           bool chargerOn,
                           uint32_t windowS) {
  setPayloadRail(true);
  if (heaterPulseS > 0) {
    setHeater(true);
  }
  delay(100);

  uint32_t startMs = millis();
  uint32_t endMs = startMs + windowS * 1000UL;
  uint32_t heaterEndMs = startMs + heaterPulseS * 1000UL;

  do {
    if (heaterPulseS > 0 && millis() >= heaterEndMs) {
      setHeater(false);
    }
    int luxRaw = analogRead(ALBEDO_SENSOR_PIN);
    float lux = getLux(luxRaw);
    bool heaterActiveNow = heaterPulseS > 0 && millis() < heaterEndMs;
    float marginW = estimateMarginW(state, true, heaterActiveNow);
    printTelemetry(mode, policy, state, heaterPolicy, heaterPulseS, chargerOn, lux, marginW);
    delay(5000);
  } while (millis() < endMs);

  setHeater(false);
  setPayloadRail(false);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  bootCount++;
  pinMode(SOLAR_SENSE_PIN, INPUT);
  pinMode(BATTERY_TEMP_PIN, INPUT);
  pinMode(PAYLOAD_TEMP_PIN, INPUT);
  pinMode(ALBEDO_SENSOR_PIN, INPUT);
  pinMode(SOC_SENSE_PIN, INPUT);
  pinMode(PAYLOAD_SWITCH_PIN, OUTPUT);
  pinMode(HEATER_SWITCH_PIN, OUTPUT);
  pinMode(CHARGE_ENABLE_PIN, OUTPUT);

  setPayloadRail(false);
  setHeater(false);
  setCharger(false);

  TelemetryState state = readTelemetryState();
  updatePersistentSafetyFlags(state);

  OperatingMode mode = selectOperatingMode(state);
  PayloadPolicy payloadPolicy = selectPayloadPolicy(state, mode);
  HeaterPolicy heaterPolicy = selectHeaterPolicy(state, mode);
  uint32_t heaterPulseS = heaterPulseSeconds(heaterPolicy);
  bool chargerOn = chargeAllowed(state);
  uint32_t payloadWindowS = payloadWindowSeconds(payloadPolicy);
  uint32_t activeWindowS = max(payloadWindowS, heaterPulseS);

  setCharger(chargerOn);

  if (payloadPolicy == PAYLOAD_OFF || payloadWindowS == 0) {
    if (heaterPulseS > 0) {
      runHeaterPulse(heaterPulseS);
    }
    float marginW = estimateMarginW(state, false, heaterPulseS > 0);
    printTelemetry(mode, payloadPolicy, state, heaterPolicy, heaterPulseS, chargerOn, 0.0f, marginW);

    uint32_t sleepS = (mode == MODE_THERMAL_SAFE && heaterPulseS == 0)
                        ? THERMAL_RECHECK_S
                        : nextSleepSeconds(heaterPulseS);
    enterSleep(sleepS, mode);
  }

  sunWakeCounter = 1;
  collectPayloadSamples(mode, payloadPolicy, state, heaterPolicy, heaterPulseS, chargerOn, payloadWindowS);
  enterSleep(nextSleepSeconds(activeWindowS), mode);
}

void loop() {
  // The controller returns from setup() through deep sleep. Keeping loop empty
  // prevents accidental always-on operation if sleep is disabled during tests.
}
