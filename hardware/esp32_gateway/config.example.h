#ifndef AERIS_CONFIG_H
#define AERIS_CONFIG_H

// ==============================================================================
// AERIS-TWIN ESP32 WIRELESS TELEMETRY GATEWAY CONFIGURATION
// Copy this file to config.h and customize with your local Wi-Fi and API keys.
// ==============================================================================

// Wi-Fi Network Credentials
#define WIFI_SSID             "YOUR_WIFI_SSID"
#define WIFI_PASSWORD         "YOUR_WIFI_PASSWORD"

// AERIS-TWIN Backend Configuration
// For local development on same Wi-Fi: "http://192.168.1.X:8000"
// For cloud Render deployment: "https://aeris-backend.onrender.com" (or your custom Render URL)
#define AERIS_BACKEND_URL     "http://192.168.1.100:8000"
#define AERIS_API_ENDPOINT    "/api/telemetry/hardware"

// Hardware Identity & Security Key
// This MUST match the AERIS_DEVICE_API_KEY environment variable in your backend .env
#define AERIS_DEVICE_ID       "AERIS-UAV-HW-01"
#define AERIS_DEVICE_API_KEY  "aeris-device-secret-key-2026"
#define AERIS_FIRMWARE_VER    "v1.4.2-hw"

// UART Configuration for Arduino Uno Link
#define UART_BAUD_RATE        115200
#define PIN_UART_RX           16   // ESP32 GPIO16 (RX2) -> Connect to Arduino TX (Pin 1 via voltage divider)
#define PIN_UART_TX           17   // ESP32 GPIO17 (TX2) -> Connect to Arduino RX (Pin 0)

// Operational Modes
// Set to 1 if testing ESP32 in standalone mode without physical Arduino connected
#define STANDALONE_TEST_MODE  0

// Telemetry Timing & Buffer Settings
#define TRANSMIT_INTERVAL_MS  100  // 10 Hz telemetry streaming rate
#define HTTP_TIMEOUT_MS       3000 // 3 seconds timeout for HTTP POST
#define QUEUE_MAX_FRAMES      30   // Ring buffer capacity for network dropouts

// Status LED Pin (Built-in LED on GPIO 2 for most NodeMCU/DevKit ESP32 boards)
#define PIN_STATUS_LED        2

#endif // AERIS_CONFIG_H
