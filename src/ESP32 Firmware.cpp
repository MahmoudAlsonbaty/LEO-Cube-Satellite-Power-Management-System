#include <math.h> 

// --- Pin Definitions ---
#define SOLAR_SENSE_PIN  34  
#define MOSFET_PIN       23  
#define NTC_SENSOR_PIN   32  
#define PHOTO_SENSOR_PIN 33  

// --- Configuration ---
#define ECLIPSE_THRESHOLD 500  
#define SLEEP_SECONDS 5       
#define uS_TO_S_FACTOR 1000000ULL 



RTC_DATA_ATTR int bootCount = 0;

// === Helper Function: Calculate True NTC Temperature ===
float getTemperatureC(int adcValue) {

  if (adcValue <= 620) return 125.0;
  if (adcValue >= 4095) return -40.0;

  float x1 = 620.0,  y1 = 125.0;  // Hot Endpoint
  float x2 = 3102, y2 = 25.0;   // Middle Point (ADC Midpoint)
  float x3 = 4095.0, y3 = -40.0;  // Cold Endpoint
  
  float x = (float)adcValue;
  
  // Lagrange Polynomial Math
  float term1 = y1 * ((x - x2) * (x - x3)) / ((x1 - x2) * (x1 - x3));
  float term2 = y2 * ((x - x1) * (x - x3)) / ((x2 - x1) * (x2 - x3));
  float term3 = y3 * ((x - x1) * (x - x2)) / ((x3 - x1) * (x3 - x2));

  
  return term1 + term2 + term3;
}

float getLUX(int adcValue) {
  // Cap the extremes to prevent simulator glitches
  if (adcValue == 3102) return 500.0;


  float x1 = 0,  y1 = 0;  // Hot Endpoint
  float x2 = 3102, y2 = 500;   // Middle Point (ADC Midpoint)
  float x3 = 4095.0, y3 = 1000;  // Cold Endpoint
  
  float x = (float)adcValue;
  
  // Lagrange Polynomial Math
  float term1 = y1 * ((x - x2) * (x - x3)) / ((x1 - x2) * (x1 - x3));
  float term2 = y2 * ((x - x1) * (x - x3)) / ((x2 - x1) * (x2 - x3));
  float term3 = y3 * ((x - x1) * (x - x2)) / ((x3 - x1) * (x3 - x2));

  
  return term1 + term2 + term3;
}

void setup() {
  Serial.begin(115200);
  delay(3000); 
  
  bootCount++;
  Serial.println("\n--- Albedo Node Boot ---");

  pinMode(SOLAR_SENSE_PIN, INPUT);
  pinMode(MOSFET_PIN, OUTPUT);
  
  int solarVoltage = analogRead(SOLAR_SENSE_PIN);

  if (solarVoltage < ECLIPSE_THRESHOLD) {
    Serial.println("Status: Eclipse detected. Cutting sensor ground.");
    digitalWrite(MOSFET_PIN, LOW); 
    // esp_sleep_enable_timer_wakeup(SLEEP_SECONDS * uS_TO_S_FACTOR);
    // esp_deep_sleep_start();
    delay(SLEEP_SECONDS * 1000);
  } else {
    Serial.println("Status: Daylight. Powering up sensors.");
    digitalWrite(MOSFET_PIN, HIGH);
    delay(100); 
    
    int ntcRaw = analogRead(NTC_SENSOR_PIN);
    int photoRaw = analogRead(PHOTO_SENSOR_PIN);
    
    float tempC = getTemperatureC(ntcRaw);
    
    // --- THERMAL THROTTLE CHECK ---
    if (tempC > 120.0) {
      Serial.print("CRITICAL: Temp is "); Serial.print(tempC, 1); Serial.println(" C. Exceeds 120C limit!");
      Serial.println("Action: Thermal Throttle Initiated. Cutting power and sleeping.");
      digitalWrite(MOSFET_PIN, LOW);
      
      // esp_sleep_enable_timer_wakeup(SLEEP_SECONDS * uS_TO_S_FACTOR);
      // esp_deep_sleep_start();
      delay(SLEEP_SECONDS * 1000);
      return; // Exit setup early so we don't process the rest
    }
  
    int lux = getLUX(photoRaw);
    
    Serial.print("Initial Temp: "); Serial.print(tempC, 1); Serial.println(" C");
    Serial.print("Initial Light: "); Serial.print(lux); Serial.println(" Lux");
    delay(2000); 
  }
}

void loop() {
  int solarVoltage = analogRead(SOLAR_SENSE_PIN);
  
  if (solarVoltage < ECLIPSE_THRESHOLD) {
    Serial.println("Transition: Entering Eclipse. Cutting power and sleeping.");
    digitalWrite(MOSFET_PIN, LOW);
    // esp_sleep_enable_timer_wakeup(SLEEP_SECONDS * uS_TO_S_FACTOR);
    // esp_deep_sleep_start();
    delay(SLEEP_SECONDS * 1000);
  } else {
    Serial.println("--- Active Sampling ---");
    int ntcRaw = analogRead(NTC_SENSOR_PIN);
    int photoRaw = analogRead(PHOTO_SENSOR_PIN);
    
    // Mathematical Conversion
    float tempC = getTemperatureC(ntcRaw);
    
    // --- THERMAL THROTTLE CHECK ---
    if (tempC > 120.0) {
      Serial.print("CRITICAL: Temp is "); Serial.print(tempC, 1); Serial.println(" C. Exceeds 120C limit!");
      Serial.println("Action: Thermal Throttle Initiated. Cutting power and sleeping.");
      digitalWrite(MOSFET_PIN, LOW);
      
      // esp_sleep_enable_timer_wakeup(SLEEP_SECONDS * uS_TO_S_FACTOR);
      // esp_deep_sleep_start();
      delay(SLEEP_SECONDS * 1000);
      return; // Skip the rest of the loop and start over after waking up
    }

    int lux = map(photoRaw, 0, 4095, 0, 1000);
    

    Serial.print("Temp: "); Serial.print(tempC, 1); Serial.print(" C | ");
    Serial.print("Light: "); Serial.print(getLUX(photoRaw)); Serial.println(" Lux");
    
    delay(1000); 
  }
}