# AERIS-TWIN Autonomous Engineering Report

**Project**: AERIS-TWIN — Aero Engine Reliability & Intelligence System  
**System Class**: Research Prototype & Technology Demonstrator for Decision Support  
**Version**: v2.5.0-SIH-Ready  
**Evaluation Scope**: SIH 2026 Defence & Aerospace Propulsion Monitoring  

---

## 1. Executive Baseline Summary

Prior to this engineering cycle, AERIS-TWIN had an initial architecture combining frontend HUD visualizations and a FastAPI backend with physics and ML modules. However, several scientific integrity and hardware integration gaps were identified:
1. Telemetry streams did not enforce strict profile isolation between the physical DC motor testbed (`MOTOR_PROTOTYPE`) and the computational aero-engine model (`AERO_ENGINE`).
2. Transducer checks in some modules silently defaulted uninstalled motor prototype channels to aero-engine nominals (e.g. oil pressure = 4.3 Bar, fuel flow = 5.2 L/h).
3. Hardware diagnostics lacked dedicated live stream statistics (moving-window ingestion rate in Hz, packet age in ms, sequence anomaly tracking, drop count).
4. Anomaly detection and fault classification lacked transparent `"WHY IS THIS ANOMALOUS?"` contributor breakdowns and defensible epistemic qualifiers.
5. Prognostics (RUL) required explicit data sufficiency labeling and prediction intervals to prevent the perception of a guaranteed countdown timer.
6. DOM ID collisions existed between Cockpit overview and AI Lab tabs in the frontend.

---

## 2. Comprehensive Architectural Changes

### 2.1 Telemetry Profiles & Scientific Separation
Two strictly isolated telemetry profiles are defined and enforced at both the API gateway and the physics layer:
- **`AERO_ENGINE`**: Computational model of the Rotax 914 F turbocharged 4-cylinder aero piston engine ($RPM$, $CHT$, $EGT$, $MAP$, $Oil Pressure$, $Oil Temperature$, $Fuel Flow$, $Vibration$, $Altitude$, $Airspeed$).
- **`MOTOR_PROTOTYPE`**: Real benchtop electromechanical testbed telemetry ($Current_a$, $Voltage_v$, $Power_w$, $RPM$, $Temperature_c$, $Vibration$, $Motor Load$). **Zero aero-engine parameters are ever fabricated or defaulted.** Missing optional channels (such as shaft RPM or bus voltage before sensor attachment) are explicitly tagged as `NOT_INSTALLED` / `UNAVAILABLE`.

### 2.2 Physics-Informed Digital Twins
1. **Aero Piston Twin (`AeroPistonPhysicsModel`)**: Implements 0D lumped-parameter thermodynamics, ISA atmospheric lapse modeling up to 30,000 ft, turbocharger boost curves, and brake specific fuel consumption (BSFC).
2. **Motor Prototype Twin (`MotorPrototypePhysicsModel`)**: Implements first-principles electro-mechanical armature equations:
   $$\text{Back-EMF: } E = K_e \cdot \omega$$
   $$\text{Armature Voltage: } V = I \cdot R_a + E$$
   $$\text{Electrical Power: } P_{elec} = V \cdot I$$
   $$\text{Steady-State Temperature: } T_{ss} = T_{amb} + P_{loss} \cdot R_{th}$$

### 2.3 Sensor Trust & Packet Health Engine
- Multi-check transducer evaluation: Hard physical bounds, step jumps, stuck signal frozen variance ($< 10^{-6}$ over 15 samples), high-frequency flutter, and cross-channel consistency (e.g. $P_{elec} \approx V \cdot I$, $CHT$ vs $EGT$).
- Monotonic timestamp verification with clock skew rejection ($> 60$s in future flagged).
- Real-time packet health tracking: sequence gap detection, duplicate packet rejection, packet age ($ms$), moving-window rate ($Hz$).

### 2.4 Explainable Anomaly Detection ("WHY IS THIS ANOMALOUS?")
- Unsupervised Isolation Forest (100 estimators) operating on normalized physics residual vectors $[\sigma_{rpm}, \sigma_{cht}, \sigma_{oil}, \sigma_{vib}, \sigma_{fuel}, \sigma_{curr}, \sigma_{volt}]$.
- Rich explainability payload returned with every evaluation:
  ```json
  {
    "anomaly": true,
    "score": 0.82,
    "contributors": [
      {"signal": "current_a", "measured": 6.8, "expected": 1.9, "residual": 4.9, "residual_sigma": 3.8, "impact": 0.58},
      {"signal": "voltage_v", "measured": 10.2, "expected": 11.8, "residual": -1.6, "residual_sigma": -2.4, "impact": 0.28}
    ],
    "reason": "Electrical/mechanical load anomaly with high armature current and bus voltage sag",
    "confidence": "HIGH"
  }
  ```

### 2.5 Credible Fault Classification & Honest RUL
- Defensible qualifiers: `LIKELY`, `SUSPECTED`, `POSSIBLE`, `INSUFFICIENT_DATA`.
- DC motor prototype failure modes (`ELECTRICAL_LOAD_ANOMALY (Overcurrent)`, `SUPPLY_VOLTAGE_SAG (Low Voltage)`, `THERMAL_OVERHEAT`, `MECHANICAL_IMBALANCE`) are strictly isolated from aero engine combustion/lubrication faults.
- RUL engine projects multi-subsystem degradation state $D(t)$ along rolling degradation velocity $\frac{dD}{dt}$ towards critical boundary ($D_{failure} = 0.75$), outputting 90% prediction intervals $[lower\_bound, upper\_bound]$ conditioned on data sufficiency and sensor trust score.
- Explicit airworthiness disclaimer attached: *"Engineering estimate based on empirical degradation trend — not a guaranteed countdown"*.

### 2.6 Decision Support & Safe Command Labelling
- Control buttons and advisory panels are explicitly labelled **"Simulated Advisory Action (Decision Support)"** with non-flight-critical disclaimers.
- Zero claim of direct autonomous flight control or in-flight throttle actuation.

---

## 3. Hardware Integration (ESP32 Gateway)

- **Firmware**: `hardware/esp32_gateway/aeris_esp32_gateway.ino`
- **Target Microcontroller**: ESP32-WROOM-32 DevKit (3.3V Logic)
- **Sensor Array**:
  - `ACS712` (Hall-effect current sensor) $\rightarrow$ 32-sample ADC oversampling on `GPIO 34` $\rightarrow$ $Current_a$
  - `3S 18650 Battery Pack` $\rightarrow$ 100k$\Omega$/22k$\Omega$ voltage divider on `GPIO 35` $\rightarrow$ $Voltage_v$
  - `Optical/Hall Pulse Sensor` $\rightarrow$ Hardware ISR pulse counter on `GPIO 25` $\rightarrow$ $RPM$
  - `NTC Thermistor` $\rightarrow$ ADC on `GPIO 32` $\rightarrow$ $Temperature_c$
- **Communication Flow**:
  $$\text{Sensors} \rightarrow \text{ESP32 (C++/ArduinoJson)} \xrightarrow{\text{Wi-Fi HTTP POST}} \text{FastAPI } (\texttt{/api/telemetry/hardware}) \xrightarrow{\text{WebSocket}} \text{Frontend Dashboard}$$
- **Zero Browser-to-ESP32 Direct Connection**: The backend remains the single source of truth.

---

## 4. SIH Evaluator Q&A and System Limitations Registry

1. **15 Core SIH Evaluator Questions (Q1 – Q15)**:
   - Full registry implemented in `backend/evaluator/questions_registry.py` and queryable via `GET /api/evaluator/questions` and `GET /api/evaluator/questions/{id}`.
2. **7 Critical Evaluator Disclosures**:
   - Implemented in `backend/evaluator/limitations.py` and queryable via `GET /api/system/limitations`:
     1. *Flight Qualified?* NO — Research Prototype / Technology Demonstrator.
     2. *Autonomous Controller?* NO — Advisory Decision Support only.
     3. *Guaranteed RUL?* NO — Engineering estimate with dynamic uncertainty intervals.
     4. *Motor Prototype Equivalence?* NO — Benchtop DC motor testbed for electromechanical validation.
     5. *Real Data?* Physical telemetry from ESP32 prototype testbed.
     6. *Simulated Data?* Rotax 914 F aerodynamic/thermodynamic mission trajectories.
     7. *Remaining Validation?* Aero dyno testbed runs, CAN-bus HIL testbench, DO-178C qualification.

---

## 5. Automated Verification & Testing

- **Automated Test Suite**: 42/42 tests passing (`pytest tests/ -v`).
  - `test_aeris_backend.py`: Database, physics, sensor trust, consensus, decision engine.
  - `test_audit_verification.py`: Telemetry ingestion, bounded history buffers, stream pause, fault classifier.
  - `test_hardware_telemetry.py`: Hardware endpoint open/authenticated ingestion, motor prototype power auto-calculation, overcurrent detection.
  - `test_profile_and_failures.py`: Profile isolation, missing sensor honest reporting, malformed payload rejection, clock skew detection, evaluator questions, limitations disclosures, validation metrics.
  - `test_realtime_evaluator.py`: Mode switching, live stream disconnection/staleness, alert debouncing.
  - `test_frontend_dom_integrity.py`: Zero DOM ID collisions in `index.html` and synchronization with `src/js/main.js`.
- **Frontend Build**: Builds cleanly with zero errors (`npm run build` $\rightarrow$ Vite v6.4.3).

---

## 6. Live SIH Demonstration Workflow

1. **Step 1: System Startup**:
   - Start backend: `python -m uvicorn backend.main:app --port 8000 --reload`
   - Start frontend: `npm run dev` (or open `dist/index.html`)
   - Verify `AERIS-TWIN ONLINE`, mode: `LIVE`
2. **Step 2: Hardware Status Verification**:
   - Navigate to `Hardware` view (`04 // Hardware`).
   - If ESP32 is powered on and connected to Wi-Fi, view status transitions to `● Connected (LIVE)`, showing live $Current_a$, $Voltage_v$, $Power_w$, $Temperature_c$, $Vibration$, and $RPM$.
   - If ESP32 is unpowered, view honestly indicates `Awaiting ESP32 connection` (zero fake live data).
3. **Step 3: Controlled Disturbance Demonstration**:
   - Apply mechanical load to the DC motor shaft.
   - Observe physical current increase ($Current_a \uparrow$) on ACS712 channel.
   - Observe electro-mechanical Digital Twin residual deviation ($\Delta Current \uparrow, \sigma > 2.5$).
4. **Step 4: Explainability Verification**:
   - Anomaly detection triggers: `ELECTRICAL_LOAD_ANOMALY (Overcurrent / Load)` with `LIKELY` qualifier.
   - Open `"WHY IS THIS ANOMALOUS?"` on Cockpit or AI Lab tab: observe transparent contributor breakdown ($Current_a$ impact $\approx 60\%$, residual sigma $> 3.0\sigma$, Sensor Trust $100\%$).
5. **Step 5: Return to Nominal**:
   - Release motor shaft disturbance $\rightarrow$ current returns to baseline $\rightarrow$ system transitions smoothly to `NORMAL`.

---

## 7. Rollback & Checkpoint System

- `aeris-checkpoint-00-baseline`: Initial state before engineering cycle.
- `aeris-checkpoint-01-telemetry`: Telemetry profile schemas and physics model separation.
- `aeris-checkpoint-02-hardware`: Hardware endpoint hardening and ESP32 integration.
- `aeris-checkpoint-03-intelligence`: Sensor trust, explainable anomaly detection, defensible fault classification, honest RUL.
- `aeris-checkpoint-04-evaluator`: 15 Evaluator Questions, 7 System Disclosures, and Validation API.
- `aeris-checkpoint-05-frontend`: UI truthfulness, safe decision support labels, explainability cards, DOM integrity.
- `aeris-checkpoint-06-testing`: 42-test comprehensive suite passing and Vite build verification.
- `aeris-checkpoint-09-final`: Final production-grade research demonstrator.
