# AERIS-TWIN Hardware Telemetry Subsystem
### Physical Sensor Acquisition & ESP32 Wireless Telemetry Gateway

---

## ⚡ PHYSICAL PROTOTYPE INTEGRATION (v1)

### System Overview & Hardware Architecture
The v1 physical prototype is a dedicated DC motor electromechanical testbed interfaced directly to a standalone **ESP32** microcontroller.

> [!IMPORTANT]
> **Microcontroller Configuration**: In v1, the **ESP32 is the ONLY microcontroller**.  
> **Arduino Uno is NOT USED in v1.**

```
┌─────────────────────────────────────────────────────────────┐
│ 3× 18650 Battery Pack (11.1V – 12.6V DC)                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ ACS712 Hall-Effect Current Transducer                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ L298N Dual H-Bridge Motor Driver                            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ DC Geared Motor (+ Pulse/Optical RPM Sensor)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ Analog & Digital Pulses
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ ESP32 Microcontroller (Wi-Fi 802.11 b/g/n)                  │
│ Firmware: hardware/esp32_gateway/aeris_esp32_gateway.ino    │
│ Profile: MOTOR_PROTOTYPE                                    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Wi-Fi / HTTPS POST / WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ AERIS-TWIN Backend (POST /api/telemetry/hardware)           │
│ - Hardware Device Authentication (X-Device-API-Key)         │
│ - Profile Normalization: MOTOR_PROTOTYPE                    │
│ - Live / Stale / Disconnected State Tracking                │
│ - Zero Fake Aero-Engine Parameters Injected                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ WebSocket Stream
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ AERIS-TWIN Dashboard & Hardware Cockpit UI                  │
└─────────────────────────────────────────────────────────────┘
```

### Physical Sensor Mapping & Conversions
- **Current**: `ACS712` &rarr; Voltage Divider &rarr; ESP32 ADC (`GPIO 34`) &rarr; `current_a` (Amperes)
- **Voltage**: `3×18650 Battery` &rarr; 100kΩ/22kΩ Resistor Divider &rarr; ESP32 ADC (`GPIO 35`) &rarr; `voltage_v` (Volts)
- **Power**: Derived electrically as $P = V \times I$ &rarr; `power_w` (Watts)
- **RPM**: Optical / Hall Pulse Sensor &rarr; ESP32 GPIO (`GPIO 25`, Interrupt) &rarr; `rpm`
- **Temperature**: Thermal Sensor / Thermistor &rarr; ESP32 ADC (`GPIO 32`) &rarr; `temperature_c` (°C)
- **Vibration**: Vibration / Accelerometer Transducer &rarr; `vibration`
- **Motor Load**: Derived strictly from real physical current draw relative to continuous rated current &rarr; `motor_load_pct` (%)

---

### ⚠️ Critical Electrical & Safety Guidelines

> [!CAUTION]
> **1. ACS712 5V Sensor Output vs ESP32 3.3V ADC Limit:**
> - Many ACS712 breakout modules are powered by **5.0V** and produce an analog output centered at $V_{CC}/2 \approx 2.5\text{V}$ at 0A, swinging up toward 5.0V at high current.
> - The **ESP32 ADC pins are NOT 5V tolerant** (max 3.3V / 3.6V absolute maximum).
> - **Verify the exact ACS712 module output voltage before connecting OUT to an ESP32 ADC pin!**
> - Always utilize a resistor voltage divider or logic level shifter if the ACS712 signal can exceed 3.3V.
>
> **2. 3×18650 Battery Voltage Direct Connection Hazard:**
> - A 3S 18650 pack delivers **9.0V to 12.6V DC**.
> - **DO NOT connect battery voltage directly to an ESP32 ADC pin!**
> - A calibrated resistor voltage divider (e.g. $R_1 = 100\text{ k}\Omega, R_2 = 22\text{ k}\Omega$) MUST be used to step 12.6V down to $\le 2.27\text{V}$.

---

### Communication & Telemetry Specification
- **Communication Protocol**: ESP32 &rarr; Wi-Fi &rarr; HTTPS POST &rarr; AERIS-TWIN Backend
- **Endpoint**: `POST /api/telemetry/hardware`
- **Authentication**: `X-Device-API-Key: aeris-device-secret-key-2026` or `api_key` payload field
- **Profile Identifier**: `MOTOR_PROTOTYPE`

#### Example `MOTOR_PROTOTYPE` JSON Payload:
```json
{
  "device_id": "AERIS-ESP32-001",
  "profile": "MOTOR_PROTOTYPE",
  "sequence_number": 1,
  "timestamp": 1773280000.0,
  "rpm": 1850.0,
  "current_a": 2.65,
  "voltage_v": 11.8,
  "power_w": 31.27,
  "temperature_c": 38.5,
  "vibration": 0.85,
  "motor_load_pct": 45.0,
  "wifi_rssi": -58,
  "firmware_version": "v1.4.2-motor",
  "source": "PHYSICAL_SENSOR"
}
```

---

### 🛡️ Prototype Scope & Disclaimer
The AERIS-TWIN physical motor prototype integration validates the end-to-end embedded acquisition, wireless telemetry streaming, schema validation, and real-time cockpit monitoring architecture. It is an experimental research testbed and is **NOT** flight-certified engine monitoring or safety-critical control software.

---

## 1. System Architecture (Legacy Aero-Engine Testbed)

```
+-----------------------------------------------------------------------------------+
| PHYSICAL SENSOR RIG (UAV Aero-Engine Testbed)                                     |
|  - Hall Effect RPM Sensor (Pin D2 / INT0)                                         |
|  - CHT Temperature Probe (Pin A0)                                                 |
|  - Oil Pressure Transducer (Pin A1)                                               |
|  - Piezoelectric Vibration Sensor (Pin A2)                                        |
|  - Fuel Flow Meter (Pin A3)                                                       |
|  - Throttle Position / Engine Load (Pin A4)                                       |
+-----------------------------------------------------------------------------------+
                                         │ (Analog / Digital 0-5V signals)
                                         ▼
+-----------------------------------------------------------------------------------+
| ARDUINO UNO (Sensor Acquisition & Engineering Conversion)                         |
|  - Firmware: hardware/arduino_uno/aeris_sensor_acquisition.ino                      |
|  - 10 Hz Non-blocking sampling loop                                               |
|  - Exponential Moving Average (EMA) noise filtering                               |
|  - Physics-based unit conversions (°C, bar, mm/s, L/h, RPM, %)                     |
+-----------------------------------------------------------------------------------+
                                         │ UART (115200 Baud, Newline-delimited JSON)
                                         │ (Arduino TX -> Voltage Divider -> ESP32 RX2)
                                         ▼
+-----------------------------------------------------------------------------------+
| ESP32 GATEWAY (Wireless Telemetry Bridge)                                         |
|  - Firmware: hardware/esp32_gateway/aeris_esp32_gateway.ino                         |
|  - Wi-Fi 802.11 b/g/n Auto-reconnect Manager with RSSI monitoring                 |
|  - 30-Frame Ring Buffer for zero-drop packet retention                            |
|  - Hardware Authentication: X-Device-API-Key + Device Identity                    |
|  - Standalone bench-test fallback mode                                            |
+-----------------------------------------------------------------------------------+
                                         │ Secure HTTPS POST / WebSocket Ingestion
                                         │ Endpoint: /api/telemetry/hardware
                                         ▼
+-----------------------------------------------------------------------------------+
| AERIS-TWIN CLOUD / LOCAL BACKEND (FastAPI + Digital Twin + AI/ML)                  |
|  - Real-time packet normalization & device authentication                         |
|  - Thermodynamic model computation & health index calculation                     |
|  - Instant WebSocket broadcast to AERIS-TWIN Cockpit Dashboard                    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Hardware Wiring & Pinout Guide

### Pin Connection Matrix

| Sensor / Channel | Physical Sensor Type | Arduino Uno Pin | Output Signal / Range |
| :--- | :--- | :--- | :--- |
| **Engine RPM** | Hall Effect / Optical Disc | `Pin D2` (INT0) | 0-5V Pulse / Interrupt |
| **CHT Temperature** | NTC Thermistor / Linearized | `Pin A0` | 0.5V - 4.5V (25°C - 250°C) |
| **Oil Pressure** | 0-10 Bar Pressure Transducer | `Pin A1` | 0.5V - 4.5V (0 - 10 bar) |
| **Vibration** | Piezoelectric / Analog Accel | `Pin A2` | 0V - 5.0V (0 - 15 mm/s RMS) |
| **Fuel Flow** | Turbine Flow Meter / Analog | `Pin A3` | 0V - 5.0V (0 - 30 L/h) |
| **Engine Load** | Throttle Potentiometer | `Pin A4` | 0V - 5.0V (0% - 100%) |
| **Status LED** | Onboard Diagnostic LED | `Pin D13` | Active High Flash |

### Arduino Uno to ESP32 Interconnect

| Arduino Uno Pin | Direction | ESP32 Pin | Notes |
| :--- | :---: | :--- | :--- |
| **Pin 1 (TX)** | &rarr; | **GPIO 16 (RX2)** | **CRITICAL**: Use 5V &rarr; 3.3V Voltage Divider (see below) |
| **Pin 0 (RX)** | &larr; | **GPIO 17 (TX2)** | Direct connection (3.3V logic triggers 5V TTL reliably) |
| **GND** | &mdash; | **GND** | **MANDATORY**: Common ground between both microcontrollers |
| **5V / VIN** | &mdash; | **5V / VIN** | Common 5V DC supply (USB or external battery pack) |

> [!CAUTION]
> **Logic Level Warning**: Arduino Uno GPIO pins operate at **5.0V**, while the ESP32 is a **3.3V** microcontroller. Connecting Arduino Pin 1 (TX) directly to ESP32 GPIO 16 without a voltage divider or bidirectional logic level shifter can permanently damage the ESP32 GPIO pin.

### 5V to 3.3V Voltage Divider Diagram

```
Arduino Uno TX (Pin 1, 5V) ───────[ 1.0 kΩ Resistor ]───────┬───────> ESP32 RX2 (GPIO 16, 3.3V)
                                                            │
                                                   [ 2.0 kΩ Resistor ]
                                                            │
Arduino GND ────────────────────────────────────────────────┴───────> ESP32 GND
```

---

## 3. Firmware Setup & Flashing Instructions

### Prerequisites
1. **Arduino IDE 2.x** or **VS Code + PlatformIO**.
2. **ESP32 Board Package**: In Arduino IDE &rarr; Settings &rarr; Additional Board Manager URLs:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **Libraries**:
   - `ArduinoJson` (v6.x or v7.x by Benoit Blanchon)

---

### Step 1: Flash Arduino Uno
1. Open `hardware/arduino_uno/aeris_sensor_acquisition.ino` in Arduino IDE.
2. Select Board: **Arduino Uno** and your USB COM port.
3. Click **Upload**.
4. Open the Serial Monitor at **115200 baud**. You should observe formatted JSON strings streaming at 10 Hz:
   ```json
   {"seq":1,"source":"PHYSICAL_SENSOR","rpm":5412.5,"cht":148.20,"oil_pressure":4.21,"vibration":1.82,"fuel_flow":8.55,"engine_load":65.0}
   ```

---

### Step 2: Configure & Flash ESP32 Gateway
1. Navigate to `hardware/esp32_gateway/`.
2. Copy `config.example.h` to `config.h`:
   ```bash
   cp hardware/esp32_gateway/config.example.h hardware/esp32_gateway/config.h
   ```
3. Edit `config.h` with your Wi-Fi credentials and AERIS-TWIN Backend endpoint:
   ```c
   #define WIFI_SSID             "Your_WiFi_Network"
   #define WIFI_PASSWORD         "Your_WiFi_Password"
   #define AERIS_BACKEND_URL     "https://your-render-backend.onrender.com" // Or "http://192.168.1.100:8000"
   #define AERIS_API_ENDPOINT    "/api/telemetry/hardware"
   #define AERIS_DEVICE_ID       "AERIS-UAV-HW-01"
   #define AERIS_DEVICE_API_KEY  "aeris-device-secret-key-2026"
   ```
4. Open `hardware/esp32_gateway/aeris_esp32_gateway.ino` in Arduino IDE.
5. Select Board: **ESP32 Dev Module** (or your specific ESP32 variant).
6. Click **Upload**.
7. Open the Serial Monitor at **115200 baud** to view Wi-Fi connection and HTTP dispatch logs:
   ```
   [WIFI] Connected Successfully! Local IP: 192.168.1.145 | RSSI: -54 dBm
   [UART] Initialized Serial2 on RX=16, TX=17 @ 115200 baud
   [HTTP] TX Seq #1 OK (200) | Latency: 42ms | RSSI: -54 dBm
   ```

---

## 4. Backend Ingestion & Authentication Details

The AERIS-TWIN backend exposes secure endpoints specifically for physical hardware:

### Endpoint: `POST /api/telemetry/hardware`
- **Supported Headers**:
  - `X-Device-API-Key: aeris-device-secret-key-2026`
  - `X-Device-ID: AERIS-UAV-HW-01`
  - `Content-Type: application/json`
- **Supported Body Format**:
  ```json
  {
    "device_id": "AERIS-UAV-HW-01",
    "api_key": "aeris-device-secret-key-2026",
    "gateway_source": "ESP32",
    "firmware_version": "v1.4.2-hw",
    "wifi_rssi": -58,
    "seq": 104,
    "source": "PHYSICAL_SENSOR",
    "rpm": 5420.0,
    "cht": 152.4,
    "oil_pressure": 4.18,
    "vibration": 1.95,
    "fuel_flow": 8.7,
    "engine_load": 70.0
  }
  ```

### Live Stream Health State in AERIS-TWIN:
- **`CONNECTED` / `LIVE`**: Packets received within the last 3.0 seconds.
- **`STALE`**: No packets received for >3.0 seconds.
- **`DISCONNECTED`**: No packets received for >6.0 seconds.

---

## 5. Software Simulation & Testing Without Physical Boards

You can test the entire pipeline end-to-end using the included Python hardware simulator:

```bash
# Test single authenticated packet
python dev_telemetry_sender.py --single --source ESP32_TEST --api-key aeris-device-secret-key-2026

# Stream continuous 10 Hz hardware telemetry
python dev_telemetry_sender.py --rate 10 --source PHYSICAL_SENSOR --api-key aeris-device-secret-key-2026
```
