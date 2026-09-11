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
#define AERIS_DEVICE_ID       "AERIS-ESP32-001"
#define AERIS_PROFILE         "MOTOR_PROTOTYPE"
#define AERIS_DEVICE_API_KEY  "aeris-device-secret-key-2026"
#define AERIS_FIRMWARE_VER    "v1.4.2-motor"

// Pin Definitions on ESP32 (Standalone Physical Prototype v1)
#define PIN_ADC_CURRENT       34   // Connected to ACS712 OUT via voltage divider (DO NOT connect 5V directly to ESP32 ADC)
#define PIN_ADC_VOLTAGE       35   // Connected to 3S Battery pack via 100k/22k divider
#define PIN_RPM_SENSOR        25   // Optical / Hall pulse sensor GPIO
#define PIN_TEMP_SENSOR       32   // NTC thermistor / thermal sensor ADC pin

// Telemetry Timing & Buffer Settings
#define TRANSMIT_INTERVAL_MS  100  // 10 Hz telemetry streaming rate
#define HTTP_TIMEOUT_MS       3000 // 3 seconds timeout for HTTP POST
#define QUEUE_MAX_FRAMES      30   // Ring buffer capacity for network dropouts

// Status LED Pin (Built-in LED on GPIO 2 for most NodeMCU/DevKit ESP32 boards)
#define PIN_STATUS_LED        2

#endif // AERIS_CONFIG_H
