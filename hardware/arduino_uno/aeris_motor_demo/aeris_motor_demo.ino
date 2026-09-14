/*
 * AERIS-TWIN — ARDUINO UNO PHYSICAL TELEMETRY INTEGRATION
 * Firmware: hardware/arduino_uno/aeris_motor_demo/aeris_motor_demo.ino
 * Target: Arduino Uno (ATmega328P) @ 16 MHz
 * Communication: USB Serial @ 115200 Baud (Newline-Delimited JSON)
 * Profile: MOTOR_PROTOTYPE
 *
 * ============================================================================
 * PHYSICAL TESTBED ARCHITECTURE & SIGNAL CHAIN
 * ============================================================================
 *
 *   3S 18650 Battery Pack (9.0V - 12.6V DC)
 *         │
 *         ├───► Voltage Divider (100kΩ / 22kΩ) ──► Arduino Analog Pin A1
 *         │
 *         ▼
 *   ACS712 Current Sensor Module (VCC = 5V) ────► Arduino Analog Pin A0
 *         │
 *         ▼
 *   L298N Dual H-Bridge Motor Driver
 *         ├── Control: Arduino Digital Pins 8 (IN1), 9 (IN2), 10 (ENA PWM)
 *         │
 *         ▼
 *   DC Geared Motor (+ Optional Optical/Hall RPM pulse on Digital Pin 2)
 *         │
 *         ▼
 *   Arduino Uno (ATmega328P)
 *         │ USB Serial (115200 Baud)
 *         ▼
 *   Laptop / Host (Python Serial Bridge: hardware/arduino_uno/serial_bridge.py)
 *         │ HTTP POST (Content-Type: application/json)
 *         ▼
 *   AERIS-TWIN FastAPI Backend (/api/telemetry/hardware)
 *
 * ============================================================================
 * CRITICAL ELECTRICAL & HARDWARE SAFETY NOTICES
 * ============================================================================
 * 1. 3S 18650 BATTERY VOLTAGE SAFETY:
 *    - A 3S 18650 lithium-ion pack delivers 9.0V (discharged) to 12.6V (fully charged).
 *    - NEVER connect the battery pack voltage directly to an Arduino pin!
 *    - Maximum safe voltage on Arduino Uno 5V pins is 5.0V (absolute maximum 5.5V).
 *    - A calibrated resistor divider MUST be used:
 *        R1 = 100 kΩ (between Battery (+) and Arduino A1)
 *        R2 = 22 kΩ (between Arduino A1 and Arduino GND)
 *        Divider Ratio = (100k + 22k) / 22k = 5.545:1
 *        Max input to A1 at 12.6V = 12.6V / 5.545 = 2.27V (well within safe 0-5V range).
 *
 * 2. ACS712 CURRENT SENSOR SAFETY & CALIBRATION:
 *    - The ACS712 module is powered from the Arduino 5V pin.
 *    - Its analog output (OUT) is centered at VCC/2 (~2.5V = ~512 ADC counts) at 0A.
 *    - Sensitivity varies by model variant:
 *        * ACS712-05B (5A Model):  185 mV/A (0.185 V/A) -> Select ACS712_MODEL_5A below
 *        * ACS712-20A (20A Model): 100 mV/A (0.100 V/A) -> Select ACS712_MODEL_20A below
 *        * ACS712-30A (30A Model):  66 mV/A (0.066 V/A) -> Select ACS712_MODEL_30A below
 *    - Connect ACS712 OUT directly to Arduino Analog Pin A0.
 *
 * 3. COMMON GROUND:
 *    - The Battery negative terminal, L298N GND terminal, and Arduino GND pin
 *      MUST be tied together to establish a common ground reference.
 *    - Motor power and Arduino logic power supplies remain separate.
 *
 * 4. STRICT DATA INTEGRITY:
 *    - If a physical sensor is not connected, set its ENABLE define to 0.
 *    - When disabled, this firmware outputs 'null' over JSON.
 *    - NEVER invent or simulate sensor readings for missing physical transducers.
 * ============================================================================
 */

#include <Arduino.h>

// ==========================================
// 1. DEVICE IDENTITY & CONFIGURATION
// ==========================================
#define DEVICE_ID               "AERIS-UNO-001"
#define TELEMETRY_PROFILE       "MOTOR_PROTOTYPE"
#define TELEMETRY_SOURCE        "PHYSICAL_SENSOR"
#define FIRMWARE_VERSION        "v1.0.0-uno-serial"

// Serial baud rate (must match serial_bridge.py)
#define SERIAL_BAUD_RATE        115200

// Sampling rate: 10 Hz = 100 ms loop interval
#define TELEMETRY_INTERVAL_MS   100

// ==========================================
// 2. HARDWARE SENSOR FEATURE TOGGLES
// Set to 1 if physically connected; set to 0 if not connected.
// Unconnected channels output 'null' in JSON (no fake defaults).
// ==========================================
#define SENSOR_CURRENT_ENABLED  1   // ACS712 on Analog Pin A0
#define SENSOR_VOLTAGE_ENABLED  1   // Battery divider on Analog Pin A1
#define SENSOR_RPM_ENABLED      0   // Hall/Optical pulse on Digital Pin 2 (Set 1 if connected)
#define SENSOR_TEMP_ENABLED     0   // NTC Thermistor on Analog Pin A2 (Set 1 if connected)
#define SENSOR_VIB_ENABLED      0   // Piezo / Analog accelerometer on A3 (Set 1 if connected)
#define SENSOR_LOAD_ENABLED     0   // Motor load sensor (Set 1 if derived from PWM / torque)

// L298N Motor Driver Control (Set 1 to enable autonomous/PWM motor control from Uno)
#define MOTOR_DRIVER_ENABLED    1

// ==========================================
// 3. PIN DEFINITIONS
// ==========================================
const uint8_t PIN_ACS712_CURRENT   = A0;  // ACS712 Current Sensor Analog Out
const uint8_t PIN_BATTERY_VOLTAGE  = A1;  // 3S Battery Voltage Divider Out
const uint8_t PIN_TEMP_SENSOR      = A2;  // Optional Thermistor Analog Out
const uint8_t PIN_VIB_SENSOR       = A3;  // Optional Vibration Analog Out
const uint8_t PIN_RPM_INTERRUPT    = 2;   // Digital Pin 2 (INT0) Optical/Hall pulse
const uint8_t PIN_STATUS_LED       = 13;  // Onboard Activity LED

// L298N Motor Driver Pins
const uint8_t PIN_MOTOR_IN1        = 8;   // L298N IN1 Direction
const uint8_t PIN_MOTOR_IN2        = 9;   // L298N IN2 Direction
const uint8_t PIN_MOTOR_ENA        = 10;  // L298N ENA Speed (PWM)

// ==========================================
// 4. SENSOR CALIBRATION PARAMETERS
// ==========================================
// Arduino Uno 5V ADC reference
const float ARDUINO_VREF = 5.00f;
const float ADC_COUNTS = 1023.0f;

// ACS712 Current Sensor Configuration
// Choose module sensitivity in V/A:
// 5A Model: 0.185 V/A | 20A Model: 0.100 V/A | 30A Model: 0.066 V/A
#define ACS712_SENSITIVITY_V_PER_A  0.185f  // Default: 5A module (185 mV/A)
const float ACS712_ZERO_VOLTS = 2.50f;      // Quiescent voltage at 0A (~VCC/2)

// Battery Resistor Divider Configuration
// R1 = 100 kΩ, R2 = 22 kΩ -> Ratio = (100 + 22) / 22 = 5.54545
const float VOLTAGE_DIVIDER_RATIO = 5.54545f;

// ==========================================
// 5. GLOBAL TELEMETRY STATE
// ==========================================
uint32_t g_sequence_number = 0;
uint32_t g_last_telemetry_tx_ms = 0;
uint32_t g_last_rpm_calc_ms = 0;

// RPM pulse counting via hardware interrupt
volatile uint32_t g_rpm_pulse_count = 0;
float g_calculated_rpm = 0.0f;

void isr_rpm_pulse() {
    g_rpm_pulse_count++;
}

// ==========================================
// 6. SENSOR MEASUREMENT HELPERS (Strict Physical Readings)
// ==========================================

// Read ACS712 Current (Amperes) with 32-sample noise averaging
float read_physical_current() {
    uint32_t adc_sum = 0;
    for (int i = 0; i < 32; i++) {
        adc_sum += analogRead(PIN_ACS712_CURRENT);
    }
    float avg_adc = (float)adc_sum / 32.0f;
    float pin_volts = (avg_adc / ADC_COUNTS) * ARDUINO_VREF;
    
    // I = |V_out - V_zero| / Sensitivity
    float current_a = fabs(pin_volts - ACS712_ZERO_VOLTS) / ACS712_SENSITIVITY_V_PER_A;
    if (current_a < 0.03f) {
        current_a = 0.0f; // Zero floor for sensor ADC quantization noise
    }
    return current_a;
}

// Read Battery Voltage (Volts) via resistor divider
float read_physical_voltage() {
    uint32_t adc_sum = 0;
    for (int i = 0; i < 32; i++) {
        adc_sum += analogRead(PIN_BATTERY_VOLTAGE);
    }
    float avg_adc = (float)adc_sum / 32.0f;
    float pin_volts = (avg_adc / ADC_COUNTS) * ARDUINO_VREF;
    float battery_volts = pin_volts * VOLTAGE_DIVIDER_RATIO;
    return battery_volts;
}

// Read RPM if pulse sensor is enabled and connected
float read_physical_rpm(uint32_t elapsed_ms) {
    if (elapsed_ms == 0) return g_calculated_rpm;
    
    noInterrupts();
    uint32_t pulses = g_rpm_pulse_count;
    g_rpm_pulse_count = 0;
    interrupts();

    // 1 pulse per shaft revolution
    g_calculated_rpm = (pulses * 60000.0f) / (float)elapsed_ms;
    return g_calculated_rpm;
}

// Read Temperature (°C) if thermistor is connected
float read_physical_temperature() {
    int raw = analogRead(PIN_TEMP_SENSOR);
    if (raw <= 10 || raw >= 1020) return 0.0f;
    float pin_volts = (raw / ADC_COUNTS) * ARDUINO_VREF;
    float temp_c = 25.0f + ((pin_volts - 2.5f) * 30.0f);
    return temp_c;
}

// Read Vibration if analog transducer is connected
float read_physical_vibration() {
    int raw = analogRead(PIN_VIB_SENSOR);
    float pin_volts = (raw / ADC_COUNTS) * ARDUINO_VREF;
    float vib_mms = (pin_volts / ARDUINO_VREF) * 10.0f;
    return vib_mms;
}

// ==========================================
// 7. SETUP
// ==========================================
void setup() {
    // 1. Initialize Hardware UART at 115200 Baud
    Serial.begin(SERIAL_BAUD_RATE);
    while (!Serial && millis() < 2000) {
        // Wait briefly for serial interface on native USB boards
    }

    // 2. Setup Diagnostic Status LED
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    // 3. Configure Analog Input Pins
    pinMode(PIN_ACS712_CURRENT, INPUT);
    pinMode(PIN_BATTERY_VOLTAGE, INPUT);

    // 4. Configure RPM Interrupt if enabled
#if SENSOR_RPM_ENABLED
    pinMode(PIN_RPM_INTERRUPT, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_RPM_INTERRUPT), isr_rpm_pulse, FALLING);
#endif

    // 5. Configure Optional L298N Motor Control
#if MOTOR_DRIVER_ENABLED
    pinMode(PIN_MOTOR_IN1, OUTPUT);
    pinMode(PIN_MOTOR_IN2, OUTPUT);
    pinMode(PIN_MOTOR_ENA, OUTPUT);

    // Spin motor forward at moderate baseline duty cycle (~65% PWM)
    digitalWrite(PIN_MOTOR_IN1, HIGH);
    digitalWrite(PIN_MOTOR_IN2, LOW);
    analogWrite(PIN_MOTOR_ENA, 170); // 170 / 255 = ~66% PWM duty
#endif

    g_last_telemetry_tx_ms = millis();
    g_last_rpm_calc_ms = millis();
}

// ==========================================
// 8. MAIN LOOP — 10 Hz MACHINE-READABLE JSON OUTPUT
// ==========================================
void loop() {
    uint32_t now_ms = millis();

    // Transmit telemetry frame at exact configured interval (10 Hz = 100 ms)
    if (now_ms - g_last_telemetry_tx_ms >= TELEMETRY_INTERVAL_MS) {
        uint32_t dt_rpm_ms = now_ms - g_last_rpm_calc_ms;
        g_last_rpm_calc_ms = now_ms;
        g_last_telemetry_tx_ms = now_ms;
        g_sequence_number++;

        // Blink Status LED on each transmit cycle
        digitalWrite(PIN_STATUS_LED, (g_sequence_number % 2 == 0) ? HIGH : LOW);

        // Read physical sensors
#if SENSOR_CURRENT_ENABLED
        float current_a = read_physical_current();
#endif

#if SENSOR_VOLTAGE_ENABLED
        float voltage_v = read_physical_voltage();
#endif

#if SENSOR_RPM_ENABLED
        float rpm = read_physical_rpm(dt_rpm_ms);
#endif

#if SENSOR_TEMP_ENABLED
        float temp_c = read_physical_temperature();
#endif

#if SENSOR_VIB_ENABLED
        float vib = read_physical_vibration();
#endif

        // ====================================================================
        // Format & Stream ONE Machine-Readable Newline-Delimited JSON Object
        // Missing physical sensors strictly output 'null' (zero fabrication).
        // ====================================================================
        Serial.print(F("{\"device_id\":\""));
        Serial.print(F(DEVICE_ID));
        Serial.print(F("\",\"profile\":\""));
        Serial.print(F(TELEMETRY_PROFILE));
        Serial.print(F("\",\"source\":\""));
        Serial.print(F(TELEMETRY_SOURCE));
        Serial.print(F("\",\"sequence_number\":"));
        Serial.print(g_sequence_number);
        Serial.print(F(",\"timestamp_ms\":"));
        Serial.print(now_ms);

        // RPM Channel (real value or null)
        Serial.print(F(",\"rpm\":"));
#if SENSOR_RPM_ENABLED
        Serial.print(rpm, 1);
#else
        Serial.print(F("null"));
#endif

        // Current (A) Channel (real value or null)
        Serial.print(F(",\"current_a\":"));
#if SENSOR_CURRENT_ENABLED
        Serial.print(current_a, 3);
#else
        Serial.print(F("null"));
#endif

        // Voltage (V) Channel (real value or null)
        Serial.print(F(",\"voltage_v\":"));
#if SENSOR_VOLTAGE_ENABLED
        Serial.print(voltage_v, 2);
#else
        Serial.print(F("null"));
#endif

        // Temperature (°C) Channel (real value or null)
        Serial.print(F(",\"temperature_c\":"));
#if SENSOR_TEMP_ENABLED
        Serial.print(temp_c, 1);
#else
        Serial.print(F("null"));
#endif

        // Vibration Channel (real value or null)
        Serial.print(F(",\"vibration\":"));
#if SENSOR_VIB_ENABLED
        Serial.print(vib, 2);
#else
        Serial.print(F("null"));
#endif

        // Motor Load (%) Channel (real value or null)
        Serial.print(F(",\"motor_load_pct\":"));
#if SENSOR_LOAD_ENABLED
        float load_pct = constrain((current_a / 3.0f) * 100.0f, 0.0f, 100.0f);
        Serial.print(load_pct, 1);
#else
        Serial.print(F("null"));
#endif

        Serial.print(F(",\"firmware_version\":\""));
        Serial.print(F(FIRMWARE_VERSION));
        Serial.println(F("\"}"));
    }
}
