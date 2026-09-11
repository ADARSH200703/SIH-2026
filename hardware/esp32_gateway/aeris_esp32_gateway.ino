/*
 * AERIS-TWIN — PHYSICAL PROTOTYPE INTEGRATION v1
 * Hardware Subsystem: Standalone ESP32 Motor Prototype Telemetry Gateway
 *
 * Physical Architecture:
 *   3x18650 battery pack (11.1V - 12.6V)
 *         ↓
 *      ACS712 Current Sensor (Hall-effect current transducer)
 *         ↓
 *       L298N Dual H-Bridge Motor Driver
 *         ↓
 *      DC Geared Motor
 *         ↓
 *      ESP32 Microcontroller (The ONLY microcontroller in v1; Arduino Uno is NOT used)
 *         ↓ Wi-Fi / HTTPS POST / WebSocket
 *      AERIS-TWIN Backend (/api/telemetry/hardware)
 *
 * ============================================================================
 * CRITICAL HARDWARE & ELECTRICAL SAFETY NOTICES
 * ============================================================================
 * 1. ACS712 SENSOR ADC SAFETY:
 *    - The ACS712 is powered by 5.0V and outputs VCC/2 (~2.5V) at 0A, increasing by 66-185 mV/A.
 *    - Under high load, its output can exceed 3.3V.
 *    - WARNING: Verify the exact ACS712 module output voltage before connecting OUT
 *      to an ESP32 ADC pin!
 *    - Use a voltage divider (e.g. 10 kΩ / 20 kΩ) or level shifter if OUT can exceed 3.3V.
 *
 * 2. 3x18650 BATTERY VOLTAGE MEASUREMENT SAFETY:
 *    - A 3S 18650 battery pack delivers 9.0V (empty) to 12.6V (fully charged).
 *    - NEVER connect battery voltage directly to an ESP32 ADC pin!
 *    - A calibrated resistor voltage divider (e.g. R1=100 kΩ, R2=22 kΩ for a 5.54:1 ratio)
 *      MUST be used to step down 12.6V to ~2.27V safe for ESP32 ADC (0-3.3V).
 * ============================================================================
 *
 * Required Libraries:
 *  - WiFi (Built-in ESP32)
 *  - HTTPClient (Built-in ESP32)
 *  - ArduinoJson (by Benoit Blanchon, v6.x or v7.x)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==========================================
// CONFIGURATION PARAMETERS
// ==========================================
#ifndef WIFI_SSID
#define WIFI_SSID             "Your_WiFi_SSID"
#define WIFI_PASSWORD         "Your_WiFi_Password"
#endif

#ifndef AERIS_BACKEND_URL
#define AERIS_BACKEND_URL     "http://192.168.1.100:8000" // Or Render cloud backend URL
#define AERIS_API_ENDPOINT    "/api/telemetry/hardware"
#define AERIS_DEVICE_ID       "AERIS-ESP32-001"
#define AERIS_PROFILE         "MOTOR_PROTOTYPE"
#define AERIS_DEVICE_API_KEY  "aeris-device-secret-key-2026"
#define AERIS_FIRMWARE_VER    "v1.4.2-motor"
#endif

// Pin Definitions on ESP32
#define PIN_STATUS_LED        2    // Onboard diagnostic LED
#define PIN_ADC_CURRENT       34   // ADC1_CH6 (Connected to ACS712 OUT via voltage divider)
#define PIN_ADC_VOLTAGE       35   // ADC1_CH7 (Connected to 3S Battery via 100k/22k divider)
#define PIN_RPM_SENSOR        25   // Optical / Hall pulse sensor GPIO
#define PIN_TEMP_SENSOR       32   // NTC thermistor / thermal sensor ADC pin

#define SAMPLING_INTERVAL_MS  100  // 10 Hz ingestion rate
#define HTTP_TIMEOUT_MS       3500

// Calibration Constants
#define ACS712_VREF           3.30f  // ESP32 ADC reference voltage
#define ACS712_ZERO_VOLTS     1.65f  // Zero-current voltage after 3.3V divider
#define ACS712_SENSITIVITY    0.066f // Volts per Ampere (for 30A module, adjust for 5A or 20A)
#define VOLTAGE_DIVIDER_RATIO 5.545f // (100k + 22k) / 22k

// ==========================================
// TELEMETRY FRAME DATA STRUCTURE
// ==========================================
struct MotorTelemetryFrame {
    uint32_t sequence_number;
    float rpm;
    float current_a;
    float voltage_v;
    float power_w;
    float temperature_c;
    float vibration;
    float motor_load_pct;
    int wifi_rssi;
    uint32_t timestamp_ms;
};

// State Variables
uint32_t g_seq = 0;
uint32_t g_last_sample_ms = 0;
uint32_t g_last_wifi_check_ms = 0;
volatile uint32_t g_pulse_count = 0;
uint32_t g_last_rpm_calc_ms = 0;
float g_calculated_rpm = 0.0f;

// Interrupt Service Routine for RPM Pulse Counting
void IRAM_ATTR rpm_isr() {
    g_pulse_count++;
}

// ==========================================
// SENSOR ACQUISITION & PHYSICAL CONVERSION
// ==========================================
MotorTelemetryFrame read_physical_sensors() {
    MotorTelemetryFrame frame;
    g_seq++;
    frame.sequence_number = g_seq;
    frame.timestamp_ms = millis();
    frame.wifi_rssi = (WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : -99;

    // 1. RPM Calculation (Windowed pulse rate)
    uint32_t now = millis();
    uint32_t dt = now - g_last_rpm_calc_ms;
    if (dt >= 200) {
        noInterrupts();
        uint32_t pulses = g_pulse_count;
        g_pulse_count = 0;
        interrupts();
        // Assuming 1 pulse per shaft revolution (adjust for encoder CPR / gear ratio)
        g_calculated_rpm = (pulses * 60000.0f) / (float)dt;
        g_last_rpm_calc_ms = now;
    }
    frame.rpm = g_calculated_rpm;

    // 2. Current Measurement (ACS712 via ADC)
    // 32-sample averaging for ADC noise reduction
    uint32_t adc_curr_sum = 0;
    for (int i = 0; i < 32; i++) {
        adc_curr_sum += analogRead(PIN_ADC_CURRENT);
    }
    float raw_adc_curr = (float)adc_curr_sum / 32.0f;
    float v_out_curr = (raw_adc_curr / 4095.0f) * ACS712_VREF;
    float current_val = abs(v_out_curr - ACS712_ZERO_VOLTS) / max(0.01f, ACS712_SENSITIVITY);
    frame.current_a = max(0.0f, current_val);

    // 3. Battery Voltage (3S 18650 Pack via Resistor Divider)
    uint32_t adc_volt_sum = 0;
    for (int i = 0; i < 32; i++) {
        adc_volt_sum += analogRead(PIN_ADC_VOLTAGE);
    }
    float raw_adc_volt = (float)adc_volt_sum / 32.0f;
    float pin_voltage = (raw_adc_volt / 4095.0f) * 3.3f;
    frame.voltage_v = max(0.0f, pin_voltage * VOLTAGE_DIVIDER_RATIO);

    // 4. Electrical Power: P = V × I
    frame.power_w = frame.voltage_v * frame.current_a;

    // 5. Temperature (°C) from Thermistor ADC
    uint32_t adc_temp_sum = 0;
    for (int i = 0; i < 16; i++) {
        adc_temp_sum += analogRead(PIN_TEMP_SENSOR);
    }
    float raw_temp = (float)adc_temp_sum / 16.0f;
    // Normalized linear scaling approximation (replace with Steinhart-Hart equation for NTC)
    frame.temperature_c = 25.0f + (raw_temp / 4095.0f) * 60.0f;

    // 6. Vibration (placeholder for I2C MPU6050 accelerometer if attached, else nominal)
    frame.vibration = 0.85f;

    // 7. Motor Load (%) derived from current draw relative to rated max (5.0A)
    frame.motor_load_pct = min(100.0f, max(0.0f, (frame.current_a / 5.0f) * 100.0f));

    return frame;
}

// ==========================================
// WI-FI CONNECTION MANAGER
// ==========================================
void connect_wifi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.print(F("[WIFI] Connecting to: "));
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint32_t start_ms = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start_ms < 10000) {
        delay(250);
        Serial.print(F("."));
        digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println(F("\n[WIFI] Connected Successfully!"));
        Serial.print(F("[WIFI] IP: "));
        Serial.println(WiFi.localIP());
        Serial.printf("[WIFI] RSSI: %d dBm\n", WiFi.RSSI());
        digitalWrite(PIN_STATUS_LED, HIGH);
    } else {
        Serial.println(F("\n[WIFI] Wi-Fi connection timed out. Retrying in loop..."));
        digitalWrite(PIN_STATUS_LED, LOW);
    }
}

// ==========================================
// HTTP TELEMETRY TRANSMITTER
// ==========================================
bool transmit_telemetry(const MotorTelemetryFrame &frame) {
    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }

    HTTPClient http;
    String url = String(AERIS_BACKEND_URL) + String(AERIS_API_ENDPOINT);

    http.begin(url);
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-API-Key", AERIS_DEVICE_API_KEY);
    http.addHeader("X-Device-ID", AERIS_DEVICE_ID);

    // Construct clean MOTOR_PROTOTYPE JSON document
    StaticJsonDocument<384> doc;
    doc["device_id"] = AERIS_DEVICE_ID;
    doc["profile"] = AERIS_PROFILE;
    doc["sequence_number"] = frame.sequence_number;
    doc["timestamp"] = (double)(millis()) / 1000.0;
    doc["rpm"] = round(frame.rpm * 10.0f) / 10.0f;
    doc["current_a"] = round(frame.current_a * 1000.0f) / 1000.0f;
    doc["voltage_v"] = round(frame.voltage_v * 100.0f) / 100.0f;
    doc["power_w"] = round(frame.power_w * 100.0f) / 100.0f;
    doc["temperature_c"] = round(frame.temperature_c * 10.0f) / 10.0f;
    doc["vibration"] = round(frame.vibration * 1000.0f) / 1000.0f;
    doc["motor_load_pct"] = round(frame.motor_load_pct * 10.0f) / 10.0f;
    doc["wifi_rssi"] = frame.wifi_rssi;
    doc["firmware_version"] = AERIS_FIRMWARE_VER;
    doc["source"] = "PHYSICAL_SENSOR";

    String payload;
    serializeJson(doc, payload);

    uint32_t t0 = millis();
    int code = http.POST(payload);
    uint32_t latency = millis() - t0;

    bool ok = (code == 200 || code == 201);
    if (ok) {
        Serial.printf("[HTTP] TX #%u OK (%d) | Latency: %ums | I: %.2fA | V: %.2fV | P: %.1fW | RPM: %.0f\n",
                      frame.sequence_number, code, latency, frame.current_a, frame.voltage_v, frame.power_w, frame.rpm);
        digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    } else {
        Serial.printf("[HTTP] TX #%u FAILED: HTTP %d (%s)\n", frame.sequence_number, code, http.errorToString(code).c_str());
    }

    http.end();
    return ok;
}

// ==========================================
// SETUP
// ==========================================
void setup() {
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    // ADC input configuration
    pinMode(PIN_ADC_CURRENT, INPUT);
    pinMode(PIN_ADC_VOLTAGE, INPUT);
    pinMode(PIN_TEMP_SENSOR, INPUT);

    // RPM Pulse input with pullup
    pinMode(PIN_RPM_SENSOR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_RPM_SENSOR), rpm_isr, RISING);

    // Configure 12-bit ADC resolution and 11dB attenuation for 0-3.3V range
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    Serial.begin(115200);
    delay(1000);

    Serial.println(F("================================================================"));
    Serial.println(F(" AERIS-TWIN — PHYSICAL MOTOR PROTOTYPE TELEMETRY GATEWAY v1    "));
    Serial.println(F(" Target: ESP32 Standalone (3x18650 -> ACS712 -> L298N -> Motor) "));
    Serial.println(F(" Profile: MOTOR_PROTOTYPE (Arduino Uno is NOT used in v1)      "));
    Serial.printf(F(" Device ID: %s | Firmware: %s\n"), AERIS_DEVICE_ID, AERIS_FIRMWARE_VER);
    Serial.println(F("================================================================"));

    connect_wifi();
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
    // 1. Maintain Wi-Fi health
    if (millis() - g_last_wifi_check_ms > 5000) {
        g_last_wifi_check_ms = millis();
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println(F("[WIFI] Reconnecting..."));
            WiFi.reconnect();
        }
    }

    // 2. Non-blocking 10 Hz Telemetry Loop
    if (millis() - g_last_sample_ms >= SAMPLING_INTERVAL_MS) {
        g_last_sample_ms = millis();
        MotorTelemetryFrame frame = read_physical_sensors();
        transmit_telemetry(frame);
    }

    delay(2);
}
