# AERIS-TWIN Hardware Telemetry Subsystem
### Physical Sensor Acquisition, Arduino Uno USB Serial Bridge & ESP32 Telemetry Gateway

---

## ⚡ ARDUINO UNO PHYSICAL DEMONSTRATOR INTEGRATION

### System Overview & Hardware Architecture
The physical demonstrator is a dedicated DC motor electromechanical testbed monitored by an **Arduino Uno (ATmega328P)** communicating via **USB Serial @ 115200 Baud** to the laptop host running [`hardware/arduino_uno/serial_bridge.py`](file:///c:/Users/Adarshkumar/Downloads/Hackathon/SIH/hardware/arduino_uno/serial_bridge.py).

> [!IMPORTANT]
> **Physical Demonstrator Scope & Disclaimer:**  
> **"The Arduino motor testbed is a physical monitoring demonstrator and is not an aircraft engine or flight-qualified system."**

```
┌─────────────────────────────────────────────────────────────┐
│ 3× 18650 Battery Pack (9.0V – 12.6V DC)                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────────┐         ┌───────────────────────────┐
│ Voltage Divider           │         │ ACS712 Current Sensor     │
│ (100 kΩ / 22 kΩ = 5.545:1)│         │ (5V VCC, OUT -> Pin A0)   │
└───────────┬───────────────┘         └───────────┬───────────────┘
            │ Analog Pin A1                       │ Analog Pin A0
            └──────────────────┬──────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ L298N Dual H-Bridge Motor Driver (Common GND)               │
│ - Control: Arduino Digital Pins 8 (IN1), 9 (IN2), 10 (ENA)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ DC Geared Motor (+ Optional Optical/Hall RPM Pulse on Pin 2)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Arduino Uno (ATmega328P @ 16 MHz)                           │
│ Firmware: hardware/arduino_uno/aeris_motor_demo/            │
│ Profile: MOTOR_PROTOTYPE (Zero Fabricated Sensors)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ USB Serial (115200 Baud, 10 Hz Newline JSON)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Laptop Host / Python Serial Bridge                          │
│ Script: hardware/arduino_uno/serial_bridge.py               │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP POST (Content-Type: application/json)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ AERIS-TWIN Backend (POST /api/telemetry/hardware)           │
│ - Hardware Device Authentication (X-Device-API-Key)         │
│ - Profile Normalization: MOTOR_PROTOTYPE                    │
│ - Live / Stale / Disconnected State Tracking                │
│ - Zero Fake Aero-Engine Parameters Injected                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ WebSocket Stream (/ws/telemetry)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ AERIS-TWIN Dashboard & Hardware Cockpit UI                  │
└─────────────────────────────────────────────────────────────┘
```

---

### Physical Sensor Mapping & Pinouts (Arduino Uno)

| Channel | Transducer / Component | Arduino Uno Pin | Measurement Range & Conversion |
| :--- | :--- | :--- | :--- |
| **Current (A)** | ACS712 Hall-Effect Transducer | `Analog Pin A0` | 0.0 - 5.0A ($V_{out} = 2.5\text{V} \pm 185\text{ mV/A}$) |
| **Voltage (V)** | 3S 18650 Battery Pack | `Analog Pin A1` | 9.0 - 12.6V via 100kΩ/22kΩ divider (5.545:1 ratio) |
| **Power (W)** | Computed Electrically | Derived | $P = V \times I$ |
| **Motor RPM** | Optical / Hall Pulse Sensor | `Digital Pin 2` (INT0) | Optional pulse counter / revolution interrupt |
| **Temperature** | Thermistor / Casing Probe | `Analog Pin A2` | Optional analog temp sensor (`null` if absent) |
| **Vibration** | Piezo / Analog Accelerometer | `Analog Pin A3` | Optional vibration metric (`null` if absent) |
| **Motor Control** | L298N Dual H-Bridge | `Pins 8, 9, 10` | Pin 8 (IN1), Pin 9 (IN2), Pin 10 (ENA PWM Duty) |
| **Heartbeat LED** | Onboard Diagnostic LED | `Digital Pin 13` | Toggles on each 10 Hz telemetry transmit cycle |

---

### ⚠️ Critical Electrical & Safety Guidelines

> [!CAUTION]
> **1. 3S 18650 Battery Direct Connection Hazard:**
> - A 3S 18650 lithium battery delivers **9.0V (empty) to 12.6V (full)**.
> - **NEVER connect the battery (+) directly to an Arduino pin!**
> - The maximum safe voltage on any Arduino 5V analog pin is **5.0V**.
> - A calibrated resistor voltage divider ($R_1 = 100\text{ k}\Omega, R_2 = 22\text{ k}\Omega$, ratio $5.545:1$) MUST be used to step down 12.6V to $\le 2.27\text{V}$.
>
> **2. ACS712 Current Sensor Sensitivity & Zero Point:**
> - The ACS712 is powered by 5.0V from the Arduino and produces $V_{CC}/2 \approx 2.5\text{V}$ at 0A.
> - Verify module model: **5A (185 mV/A)**, **20A (100 mV/A)**, or **30A (66 mV/A)**.
>
> **3. Common Ground Requirement:**
> - The Battery negative terminal, L298N GND terminal, and Arduino GND pin **MUST** be connected together.

---

### Step-by-Step Guide: Running the Arduino Uno Demonstrator

#### Step 1: Upload Firmware to Arduino Uno
1. Open the Arduino IDE.
2. Open [`hardware/arduino_uno/aeris_motor_demo/aeris_motor_demo.ino`](file:///c:/Users/Adarshkumar/Downloads/Hackathon/SIH/hardware/arduino_uno/aeris_motor_demo/aeris_motor_demo.ino).
3. Select **Tools &rarr; Board &rarr; Arduino Uno** and the corresponding COM port (e.g. `COM4`).
4. Click **Upload** (Ctrl+U).

#### Step 2: Start AERIS-TWIN Backend
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 3: Run the Python Serial Bridge
```bash
# Connect Arduino over USB COM port:
python hardware/arduino_uno/serial_bridge.py --port COM4

# Or run in Mock Mode for software testing without hardware:
python hardware/arduino_uno/serial_bridge.py --mock
```

#### Step 4: Verify in Dashboard
1. Open `http://localhost:3000` (or `http://localhost:8000`).
2. Click **Hardware Connection** in the top navigation bar.
3. Switch Evaluator Mode to **LIVE**.
4. Confirm telemetry is active with profile `MOTOR_PROTOTYPE` and device `AERIS-UNO-001`.

---

## ⚡ ESP32 STANDALONE WIRELESS GATEWAY (Alternative Mode)

For wireless demonstration setups, the standalone ESP32 gateway is available in [`hardware/esp32_gateway/aeris_esp32_gateway.ino`](file:///c:/Users/Adarshkumar/Downloads/Hackathon/SIH/hardware/esp32_gateway/aeris_esp32_gateway.ino).

```bash
# Test single authenticated packet
python dev_telemetry_sender.py --single --source ESP32_TEST --api-key aeris-device-secret-key-2026

# Stream continuous 10 Hz hardware telemetry
python dev_telemetry_sender.py --rate 10 --source PHYSICAL_SENSOR --api-key aeris-device-secret-key-2026
```
