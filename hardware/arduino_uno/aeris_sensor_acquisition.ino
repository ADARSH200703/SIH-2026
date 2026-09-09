/*
 * AERIS-TWIN Aero-Engine Digital Twin
 * Hardware Subsystem: Arduino Uno Sensor Acquisition & Engineering Conversion
 *
 * Description:
 *  Acquires multi-channel sensor signals representing UAV aero-engine parameters,
 *  performs analog-to-digital conversions, filtering, and engineering unit scaling,
 *  and transmits formatted JSON telemetry frames over UART (115200 baud) to the
 *  ESP32 Wireless Telemetry Gateway.
 *
 * Supported Sensor Channels & Pins:
 *  - RPM: Digital Pin 2 (External Interrupt 0, Hall Effect / Opto-interrupter)
 *  - CHT (Cylinder Head Temp): Analog Pin A0 (NTC Thermistor / Linearized Temp Sensor)
 *  - Oil Pressure: Analog Pin A1 (0.5V - 4.5V 0-10 bar Pressure Transducer)
 *  - Vibration: Analog Pin A2 (Piezoelectric / Piezo Disk or Analog Accelerometer)
 *  - Fuel Flow: Analog Pin A3 (Analog Flow Sensor / Potentiometer simulation)
 *  - Engine Load / Throttle: Analog Pin A4 (Rotary Throttle Potentiometer)
 *
 * Output Rate: 10 Hz (100 ms loop interval)
 * Protocol: Newline-delimited JSON
 */

#include <Arduino.h>

// ==========================================
// FEATURE TOGGLES & CONFIGURATION
// ==========================================
#define SENSOR_RPM_ENABLED      1
#define SENSOR_CHT_ENABLED      1
#define SENSOR_OIL_ENABLED      1
#define SENSOR_VIB_ENABLED      1
#define SENSOR_FUEL_ENABLED     1
#define SENSOR_LOAD_ENABLED     1

// Simulation fallback: If true, channels with disconnected/floating pins will generate
// realistic nominal flight telemetry curves instead of zero/noise.
#define BENCH_TEST_SIM_FALLBACK 0

// Baud rate for UART to ESP32
#define UART_BAUD_RATE          115200

// Sampling interval in milliseconds (10 Hz = 100 ms)
#define TELEMETRY_INTERVAL_MS   100

// ==========================================
// PIN DEFINITIONS
// ==========================================
const uint8_t PIN_RPM_INTERRUPT = 2;   // INT0
const uint8_t PIN_CHT_ANALOG    = A0;  // Temp (CHT)
const uint8_t PIN_OIL_ANALOG    = A1;  // Oil Pressure
const uint8_t PIN_VIB_ANALOG    = A2;  // Vibration
const uint8_t PIN_FUEL_ANALOG   = A3;  // Fuel Flow
const uint8_t PIN_LOAD_ANALOG   = A4;  // Throttle / Engine Load
const uint8_t PIN_STATUS_LED    = 13;  // Onboard Heartbeat LED

// ==========================================
// GLOBAL STATE & RPM TRACKING
// ==========================================
volatile uint32_t g_rpm_pulse_count = 0;
volatile uint32_t g_last_pulse_time_us = 0;
uint32_t g_last_rpm_calc_ms = 0;
uint32_t g_last_telemetry_tx_ms = 0;
uint32_t g_sequence_id = 0;

// Low-pass filter smoothing factors (Exponential Moving Average, alpha = 0.25)
const float EMA_ALPHA = 0.25f;
float g_filtered_cht = 145.0f;
float g_filtered_oil = 4.2f;
float g_filtered_vib = 1.8f;
float g_filtered_fuel = 8.5f;
float g_filtered_load = 65.0f;
float g_calculated_rpm = 5400.0f;

// ==========================================
// INTERRUPT SERVICE ROUTINES
// ==========================================
void isr_rpm_pulse() {
    g_rpm_pulse_count++;
    g_last_pulse_time_us = micros();
}

// ==========================================
// SENSOR CONVERSION HELPERS
// ==========================================

// RPM Calculation (Pulses per revolution = 1)
float read_rpm(uint32_t elapsed_ms) {
    if (!SENSOR_RPM_ENABLED) return 0.0f;
    
    // Disable interrupts briefly to read and reset pulse counter
    noInterrupts();
    uint32_t pulses = g_rpm_pulse_count;
    g_rpm_pulse_count = 0;
    interrupts();

    if (elapsed_ms == 0) return g_calculated_rpm;

    // RPM = (pulses / (elapsed_ms / 1000.0)) * 60.0
    float instant_rpm = (pulses * 60000.0f) / (float)elapsed_ms;

#if BENCH_TEST_SIM_FALLBACK
    if (pulses == 0) {
        // Subtle drift around nominal 5450 RPM for bench testing without optical wheel
        instant_rpm = 5400.0f + (sin(millis() / 2000.0f) * 150.0f);
    }
#endif

    // Smooth RPM
    g_calculated_rpm = (EMA_ALPHA * instant_rpm) + ((1.0f - EMA_ALPHA) * g_calculated_rpm);
    if (g_calculated_rpm < 0.0f) g_calculated_rpm = 0.0f;
    if (g_calculated_rpm > 12000.0f) g_calculated_rpm = 12000.0f;

    return g_calculated_rpm;
}

// CHT Sensor (0-5V mapped to 20°C - 300°C)
float read_cht() {
    if (!SENSOR_CHT_ENABLED) return 0.0f;
    int raw = analogRead(PIN_CHT_ANALOG); // 0 to 1023
    float voltage = (raw / 1023.0f) * 5.0f;
    
    // Linear / thermistor scaling approximation: 0.5V=25°C, 4.5V=250°C
    float temp_c = 25.0f + ((voltage - 0.5f) / 4.0f) * 225.0f;

#if BENCH_TEST_SIM_FALLBACK
    if (raw < 15) { // Unconnected / grounded pin
        temp_c = 145.0f + (sin(millis() / 5000.0f) * 8.0f);
    }
#endif

    g_filtered_cht = (EMA_ALPHA * temp_c) + ((1.0f - EMA_ALPHA) * g_filtered_cht);
    return g_filtered_cht;
}

// Oil Pressure (0.5V - 4.5V mapped to 0.0 - 10.0 bar)
float read_oil_pressure() {
    if (!SENSOR_OIL_ENABLED) return 0.0f;
    int raw = analogRead(PIN_OIL_ANALOG);
    float voltage = (raw / 1023.0f) * 5.0f;
    
    float pressure_bar = ((voltage - 0.5f) / 4.0f) * 10.0f;
    if (pressure_bar < 0.0f) pressure_bar = 0.0f;

#if BENCH_TEST_SIM_FALLBACK
    if (raw < 15) {
        pressure_bar = 4.2f + (cos(millis() / 4000.0f) * 0.3f);
    }
#endif

    g_filtered_oil = (EMA_ALPHA * pressure_bar) + ((1.0f - EMA_ALPHA) * g_filtered_oil);
    return g_filtered_oil;
}

// Vibration Peak/RMS (0-5V mapped to 0.0 - 15.0 mm/s)
float read_vibration() {
    if (!SENSOR_VIB_ENABLED) return 0.0f;
    int raw = analogRead(PIN_VIB_ANALOG);
    float voltage = (raw / 1023.0f) * 5.0f;
    
    float vib_mms = (voltage / 5.0f) * 15.0f;

#if BENCH_TEST_SIM_FALLBACK
    if (raw < 15) {
        vib_mms = 1.85f + (sin(millis() / 1500.0f) * 0.4f);
    }
#endif

    g_filtered_vib = (EMA_ALPHA * vib_mms) + ((1.0f - EMA_ALPHA) * g_filtered_vib);
    return g_filtered_vib;
}

// Fuel Flow Rate (0-5V mapped to 0.0 - 30.0 L/h)
float read_fuel_flow() {
    if (!SENSOR_FUEL_ENABLED) return 0.0f;
    int raw = analogRead(PIN_FUEL_ANALOG);
    float voltage = (raw / 1023.0f) * 5.0f;
    
    float flow_lph = (voltage / 5.0f) * 30.0f;

#if BENCH_TEST_SIM_FALLBACK
    if (raw < 15) {
        flow_lph = 8.5f + (sin(millis() / 3000.0f) * 0.8f);
    }
#endif

    g_filtered_fuel = (EMA_ALPHA * flow_lph) + ((1.0f - EMA_ALPHA) * g_filtered_fuel);
    return g_filtered_fuel;
}

// Throttle / Engine Load (0-5V mapped to 0.0% - 100.0%)
float read_engine_load() {
    if (!SENSOR_LOAD_ENABLED) return 0.0f;
    int raw = analogRead(PIN_LOAD_ANALOG);
    float load_pct = (raw / 1023.0f) * 100.0f;

#if BENCH_TEST_SIM_FALLBACK
    if (raw < 15) {
        load_pct = 68.0f + (sin(millis() / 6000.0f) * 5.0f);
    }
#endif

    g_filtered_load = (EMA_ALPHA * load_pct) + ((1.0f - EMA_ALPHA) * g_filtered_load);
    return g_filtered_load;
}

// ==========================================
// SETUP
// ==========================================
void setup() {
    // Initialize Hardware UART
    Serial.begin(UART_BAUD_RATE);
    while (!Serial && millis() < 2000) {
        // Wait for serial port connection (relevant for native USB boards)
    }

    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    // Setup RPM Interrupt
    if (SENSOR_RPM_ENABLED) {
        pinMode(PIN_RPM_INTERRUPT, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(PIN_RPM_INTERRUPT), isr_rpm_pulse, FALLING);
    }

    // Set analog reference to default 5V
    analogReference(DEFAULT);

    g_last_rpm_calc_ms = millis();
    g_last_telemetry_tx_ms = millis();
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
    uint32_t current_ms = millis();

    // Check if telemetry transmission interval elapsed
    if (current_ms - g_last_telemetry_tx_ms >= TELEMETRY_INTERVAL_MS) {
        uint32_t dt_rpm_ms = current_ms - g_last_rpm_calc_ms;
        g_last_rpm_calc_ms = current_ms;
        g_last_telemetry_tx_ms = current_ms;

        // Sample and convert all channels
        float rpm = read_rpm(dt_rpm_ms);
        float cht = read_cht();
        float oil = read_oil_pressure();
        float vib = read_vibration();
        float fuel = read_fuel_flow();
        float load = read_engine_load();

        g_sequence_id++;

        // Blink Status LED on each transmit
        digitalWrite(PIN_STATUS_LED, (g_sequence_id % 10 < 5) ? HIGH : LOW);

        // Format compact JSON frame onto Serial output
        // Protocol: Standard newline-delimited JSON
        Serial.print(F("{\"seq\":"));
        Serial.print(g_sequence_id);
        Serial.print(F(",\"source\":\"PHYSICAL_SENSOR\""));
        Serial.print(F(",\"rpm\":"));
        Serial.print(rpm, 1);
        Serial.print(F(",\"cht\":"));
        Serial.print(cht, 2);
        Serial.print(F(",\"oil_pressure\":"));
        Serial.print(oil, 2);
        Serial.print(F(",\"vibration\":"));
        Serial.print(vib, 2);
        Serial.print(F(",\"fuel_flow\":"));
        Serial.print(fuel, 2);
        Serial.print(F(",\"engine_load\":"));
        Serial.print(load, 1);
        Serial.println(F("}"));
    }
}
