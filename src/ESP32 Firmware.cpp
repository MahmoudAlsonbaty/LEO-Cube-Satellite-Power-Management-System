#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include <math.h>
 // Ensure Velxio supports this specific Adafruit library

// --- Pin Definitions ---
#define PHOTO_SENSOR_PIN 34  
#define MOSFET_PIN       25  

// --- Configuration ---
#define ECLIPSE_THRESHOLD 500       
#define SLEEP_SECONDS 5         
#define uS_TO_S_FACTOR 1000000ULL 

RTC_DATA_ATTR int bootCount = 0;
Adafruit_BMP280 bmp; 

// === Helper Function: Calculate True LUX (Velxio 5V Hardware Bypass) ===
float getLUX(int rawADC) {
  // Prevent ADC glitches
  if (rawADC < 0) rawADC = 0;
  if (rawADC > 4095) rawADC = 4095;
  
  // The ESP32 maxes out at 4095 (3.3V). 
  // Because the simulator's sensor is scaled for 5V at 1000 Lux,
  // 3.3V corresponds to exactly 660 Lux.
  float lux = ((float)rawADC / 4095.0) * 660.0;
  
  return lux;
}

// === Helper Function: Handle Sleep State ===
// === Helper Function: Handle Sleep State (SIMULATION VERSION) ===
void enterDeepSleep(const char* logMessage) {
  Serial.println(logMessage);
  
  // Cut ground to all sensors (if you re-add the MOSFET later)
  digitalWrite(MOSFET_PIN, HIGH); 
  
  Serial.println("Entering SIMULATED Deep Sleep for 5 Seconds...");
  Serial.flush(); 
  
  // 1. Wait the 5 seconds using standard delay (which the simulator supports)
  delay(SLEEP_SECONDS * 1000);
  
  // 2. Force a software reboot to mimic waking up from deep sleep!
  ESP.restart(); 
}

void setup() {
  Serial.begin(115200);
  delay(1000); 
  
  bootCount++;
  Serial.printf("\n--- Albedo Node Boot (Wake Cycle: %d) ---\n", bootCount);

  pinMode(MOSFET_PIN, OUTPUT);
  pinMode(PHOTO_SENSOR_PIN, INPUT);
  
  // 1. Power Peripherals
  digitalWrite(MOSFET_PIN, LOW);
  
  // Keep the 500ms delay to allow Velxio's SPICE engine to resolve the MOSFET ground
  delay(500); 
  
  // 2. Initialize BMP I2C Sensor
  if (!bmp.begin(0x77) && !bmp.begin(0x76)) {
    Serial.println("WARNING: Could not find a valid BMP sensor, check wiring!");
  }
  
  // Dummy read to clear ESP32 ADC buffer quirks in simulation
  analogRead(PHOTO_SENSOR_PIN); 
  delay(20);
  
  Serial.println("System Initialized. Entering Active Monitoring Loop.");
}

void loop() {
  // 1. Read the raw light value
  int photoRaw = analogRead(PHOTO_SENSOR_PIN);
  
  // DEBUG: Uncomment this if you need to see exactly what Velxio is feeding the pin
  // Serial.printf("DEBUG - Raw Light ADC Value: %d\n", photoRaw);

  // 2. ECLIPSE CHECK -> Triggers Deep Sleep
  if (photoRaw < ECLIPSE_THRESHOLD) {
    enterDeepSleep("Status: Eclipse detected. Cutting power and sleeping.");
    return; // Safety return, though esp_deep_sleep_start() prevents reaching here
  } 
  
  // 3. Read Temperature 
  float tempC = bmp.readTemperature(); 
  
  // 4. THERMAL THROTTLE CHECK -> Triggers Deep Sleep
  if (tempC > 80.0) {
    Serial.printf("CRITICAL: Temp is %.1f C. Exceeds 120C limit!\n", tempC);
    enterDeepSleep("Action: Thermal Throttle Initiated. Cutting power and sleeping.");
    return;
  }
  
  // 5. Active Daylight Output (Only reached if both checks pass)
  float lux = getLUX(photoRaw);
  Serial.printf("Temp: %.1f C | Light: %.1f Lux\n", tempC, lux);
  
  // 6. Sampling Rate
  // This is a standard pause. The ESP32 stays awake, sensors stay on.
  // Set to 1000ms (1 second) for responsive output, change if needed.
  delay(1000); 
}