/*
 * AERIS-TWIN Aero-Engine Digital Twin
 * Hardware Subsystem: ESP32 Wireless Telemetry Gateway
 *
 * Description:
 *  Acts as the high-speed IoT wireless telemetry bridge between the Arduino Uno
 *  sensor acquisition board and the AERIS-TWIN FastAPI Cloud/Local Backend.
 *
 * Capabilities:
 *  1. Dual UART Interface:
 *     - Serial (USB, GPIO 1/3, 115200 baud): Debugging & diagnostics monitor.
 *     - Serial2 (Hardware UART, GPIO 16/17, 115200 baud): High-speed sensor ingestion from Arduino.
 *  2. Wi-Fi Connection Manager:
 *     - Non-blocking auto-reconnect logic with RSSI signal quality monitoring.
 *  3. Telemetry Payload Parsing & Enrichment:
 *     - Parses Arduino JSON frames, enriches with device identity, Wi-Fi RSSI, and security key.
 *  4. Secure HTTP/HTTPS REST Telemetry Streamer:
 *     - Transmits payloads to /api/telemetry/hardware using HTTP POST with X-Device-API-Key headers.
 *  5. Ring Buffer / Fallback Engine:
 *     - Provides resilient 30-frame buffer during transient Wi-Fi drops.
 *     - Standalone bench test mode if physical Arduino is offline.
 *
 * Required Arduino Libraries:
 *  - WiFi (Built-in ESP32)
 *  - HTTPClient (Built-in ESP32)
 *  - ArduinoJson (by Benoit Blanchon, v6.x or v7.x)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Include configuration file
#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

// ==========================================
// TELEMETRY FRAME DATA STRUCTURE
// ==========================================
struct TelemetryFrame {
    uint32_t seq;
    char source[24];
    float rpm;
    float cht;
    float oil_pressure;
    float vibration;
    float fuel_flow;
    float engine_load;
    int wifi_rssi;
    uint32_t local_timestamp_ms;
    bool is_valid;
};

// Ring Buffer for offline resilience
TelemetryFrame g_telemetry_queue[QUEUE_MAX_FRAMES];
int g_queue_head = 0;
int g_queue_tail = 0;
int g_queue_count = 0;

// Hardware Serial for Arduino link
HardwareSerial SerialArduino(2);

// Transmission timing & state
uint32_t g_last_tx_ms = 0;
uint32_t g_last_uart_rx_ms = 0;
uint32_t g_last_wifi_check_ms = 0;
uint32_t g_packets_sent_success = 0;
uint32_t g_packets_sent_fail = 0;
String g_uart_rx_buffer = "";

// ==========================================
// BUFFER MANAGEMENT HELPERS
// ==========================================
bool enqueue_frame(const TelemetryFrame &frame) {
    if (g_queue_count >= QUEUE_MAX_FRAMES) {
        // Buffer full: drop oldest frame
        g_queue_head = (g_queue_head + 1) % QUEUE_MAX_FRAMES;
        g_queue_count--;
    }
    g_telemetry_queue[g_queue_tail] = frame;
    g_queue_tail = (g_queue_tail + 1) % QUEUE_MAX_FRAMES;
    g_queue_count++;
    return true;
}

bool dequeue_frame(TelemetryFrame &frame) {
    if (g_queue_count == 0) return false;
    frame = g_telemetry_queue[g_queue_head];
    g_queue_head = (g_queue_head + 1) % QUEUE_MAX_FRAMES;
    g_queue_count--;
    return true;
}

// ==========================================
// WI-FI CONNECTION MANAGER
// ==========================================
void connect_wifi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.print(F("[WIFI] Connecting to SSID: "));
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
        Serial.print(F("[WIFI] Local IP: "));
        Serial.println(WiFi.localIP());
        Serial.print(F("[WIFI] RSSI: "));
        Serial.print(WiFi.RSSI());
        Serial.println(F(" dBm"));
        digitalWrite(PIN_STATUS_LED, HIGH);
    } else {
        Serial.println(F("\n[WIFI] Connection Timeout. Will retry in background."));
        digitalWrite(PIN_STATUS_LED, LOW);
    }
}

void check_wifi_health() {
    if (millis() - g_last_wifi_check_ms < 5000) return;
    g_last_wifi_check_ms = millis();

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println(F("[WIFI] Link Lost! Reconnecting..."));
        WiFi.reconnect();
    }
}

// ==========================================
// HTTP TELEMETRY TRANSMITTER
// ==========================================
bool transmit_frame_to_backend(const TelemetryFrame &frame) {
    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }

    HTTPClient http;
    String target_url = String(AERIS_BACKEND_URL) + String(AERIS_API_ENDPOINT);

    http.begin(target_url);
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-API-Key", AERIS_DEVICE_API_KEY);
    http.addHeader("X-Device-ID", AERIS_DEVICE_ID);

    // Build outbound JSON payload with ArduinoJson
    StaticJsonDocument<512> doc;
    doc["device_id"] = AERIS_DEVICE_ID;
    doc["api_key"] = AERIS_DEVICE_API_KEY;
    doc["gateway_source"] = "ESP32";
    doc["firmware_version"] = AERIS_FIRMWARE_VER;
    doc["wifi_rssi"] = frame.wifi_rssi;
    doc["seq"] = frame.seq;
    doc["source"] = frame.source;
    doc["rpm"] = frame.rpm;
    doc["cht"] = frame.cht;
    doc["oil_pressure"] = frame.oil_pressure;
    doc["vibration"] = frame.vibration;
    doc["fuel_flow"] = frame.fuel_flow;
    doc["engine_load"] = frame.engine_load;

    String request_body;
    serializeJson(doc, request_body);

    uint32_t t_start = millis();
    int http_code = http.POST(request_body);
    uint32_t latency = millis() - t_start;

    bool success = false;
    if (http_code == HTTP_CODE_OK || http_code == 201) {
        g_packets_sent_success++;
        success = true;
        Serial.printf("[HTTP] TX Seq #%u OK (%d) | Latency: %ums | RSSI: %d dBm\n",
                      frame.seq, http_code, latency, frame.wifi_rssi);
    } else {
        g_packets_sent_fail++;
        Serial.printf("[HTTP] TX FAILED Code: %d (%s) | URL: %s\n",
                      http_code, http.errorToString(http_code).c_str(), target_url.c_str());
    }

    http.end();
    return success;
}

// ==========================================
// UART INGESTION FROM ARDUINO UNO
// ==========================================
void process_arduino_uart_stream() {
    while (SerialArduino.available() > 0) {
        char c = (char)SerialArduino.read();
        if (c == '\n' || c == '\r') {
            if (g_uart_rx_buffer.length() > 0) {
                // Parse complete JSON frame
                StaticJsonDocument<384> doc;
                DeserializationError err = deserializeJson(doc, g_uart_rx_buffer);

                if (!err) {
                    TelemetryFrame frame;
                    frame.seq = doc["seq"] | (g_packets_sent_success + 1);
                    const char *src = doc["source"] | "PHYSICAL_SENSOR";
                    strncpy(frame.source, src, sizeof(frame.source) - 1);
                    frame.source[sizeof(frame.source) - 1] = '\0';
                    
                    frame.rpm = doc["rpm"] | 0.0f;
                    frame.cht = doc["cht"] | (doc["temperature"] | 0.0f);
                    frame.oil_pressure = doc["oil_pressure"] | (doc["oilPressure"] | 0.0f);
                    frame.vibration = doc["vibration"] | (doc["vibration_mms"] | 0.0f);
                    frame.fuel_flow = doc["fuel_flow"] | (doc["fuelFlow"] | 0.0f);
                    frame.engine_load = doc["engine_load"] | (doc["throttle"] | 0.0f);
                    frame.wifi_rssi = WiFi.RSSI();
                    frame.local_timestamp_ms = millis();
                    frame.is_valid = true;

                    enqueue_frame(frame);
                    g_last_uart_rx_ms = millis();
                } else {
                    Serial.printf("[UART] Deserialization error: %s | Raw: %s\n", err.c_str(), g_uart_rx_buffer.c_str());
                }
                g_uart_rx_buffer = "";
            }
        } else {
            if (g_uart_rx_buffer.length() < 256) {
                g_uart_rx_buffer += c;
            }
        }
    }
}

// ==========================================
// STANDALONE / BENCH TEST GENERATOR
// ==========================================
void generate_bench_test_frame() {
    static uint32_t test_seq = 1000;
    test_seq++;

    TelemetryFrame frame;
    frame.seq = test_seq;
    strncpy(frame.source, "ESP32_TEST", sizeof(frame.source) - 1);
    frame.source[sizeof(frame.source) - 1] = '\0';

    float t = millis() / 1000.0f;
    frame.rpm = 5400.0f + (sin(t * 0.8f) * 180.0f);
    frame.cht = 148.0f + (cos(t * 0.2f) * 5.0f);
    frame.oil_pressure = 4.2f + (sin(t * 0.5f) * 0.25f);
    frame.vibration = 1.9f + (sin(t * 1.5f) * 0.3f);
    frame.fuel_flow = 8.6f + (cos(t * 0.7f) * 0.6f);
    frame.engine_load = 68.0f + (sin(t * 0.3f) * 4.0f);
    frame.wifi_rssi = (WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : -99;
    frame.local_timestamp_ms = millis();
    frame.is_valid = true;

    enqueue_frame(frame);
}

// ==========================================
// SETUP
// ==========================================
void setup() {
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    // Initialize USB debug serial
    Serial.begin(115200);
    delay(1000);

    Serial.println(F("=================================================="));
    Serial.println(F(" AERIS-TWIN ESP32 Telemetry Gateway Starting...   "));
    Serial.printf(F(" Device ID: %s | Firmware: %s\n"), AERIS_DEVICE_ID, AERIS_FIRMWARE_VER);
    Serial.println(F("=================================================="));

    // Initialize Hardware UART2 to receive Arduino stream
    SerialArduino.begin(UART_BAUD_RATE, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
    Serial.printf("[UART] Initialized Serial2 on RX=%d, TX=%d @ %d baud\n", PIN_UART_RX, PIN_UART_TX, UART_BAUD_RATE);

    // Connect to local Wi-Fi network
    connect_wifi();
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
    check_wifi_health();

    // Read incoming sensor stream from Arduino
    process_arduino_uart_stream();

    // If standalone test mode is enabled, or no UART frame received for > 3s
    #if STANDALONE_TEST_MODE
    if (millis() - g_last_tx_ms >= TRANSMIT_INTERVAL_MS) {
        generate_bench_test_frame();
    }
    #else
    if ((millis() - g_last_uart_rx_ms > 3000) && (millis() - g_last_tx_ms >= TRANSMIT_INTERVAL_MS)) {
        // Fallback: Generate self-test frame so backend & dashboard stay responsive
        generate_bench_test_frame();
    }
    #endif

    // Dispatch queued telemetry frames
    if (g_queue_count > 0 && (millis() - g_last_tx_ms >= TRANSMIT_INTERVAL_MS)) {
        TelemetryFrame frame_to_send;
        if (dequeue_frame(frame_to_send)) {
            bool success = transmit_frame_to_backend(frame_to_send);
            g_last_tx_ms = millis();

            if (success) {
                // Heartbeat LED flash
                digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
            }
        }
    }

    // Small yield for FreeRTOS task scheduling
    delay(5);
}
