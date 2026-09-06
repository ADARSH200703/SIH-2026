# AERIS-TWIN — MALE UAV Aero Piston Engine Digital Twin

**AERIS-TWIN** (*Aero Engine Reliability & Intelligence System*) is a research-grade prototype and technology demonstrator for real-time telemetry evaluation, physics-informed digital twinning, anomaly detection, fault classification, and predictive health monitoring of aero-piston engines used in **Medium-Altitude Long-Endurance (MALE) UAVs**, including architectures such as the Rotax 914 turbocharged platform.

> [!NOTE]
> **Prototype Demonstrator Scope:** AERIS-TWIN is an advanced decision-support and technology-demonstration platform. It provides explainable and traceable evidence for UAV propulsion monitoring without manufacturing unverified metrics or claiming airworthiness or flight qualification.

---

## 10-Stage Real-Time Evaluation Pipeline

```text
Telemetry Source
(Live CAN / UDP / MAVLink / Simulation)
        │
        ▼
[Stage 1] Data Ingestion & Sequence Ordering
        │
        ▼
[Stage 2] Timestamp & Data-Age Validation
        │
        ▼
[Stage 3] Sensor Trust & Signal Quality Scoring
          (Range / Frozen / Jump / Variance)
        │
        ▼
[Stage 4] Digital Twin State Prediction
          (Mean-Value Thermodynamic & Mechanical Model)
        │
        ▼
[Stage 5] Residual Calculation & Normalized Z-Score Tracking
          (Δ = Actual − Expected)
        │
        ▼
[Stage 6] Anomaly Detection
          (Isolation Forest / Multivariate Latent Space)
        │
        ▼
[Stage 7] Fault Risk & Mode Classification
          (GBDT / Physics-Informed Signature Matching)
        │
        ▼
[Stage 8] Subsystem Degradation Tracking
          (Mechanical / Thermal / Combustion / Lubrication)
        │
        ▼
[Stage 9] Engine Health Index & RUL Estimation
          (Degradation-Velocity Extrapolation)
        │
        ▼
[Stage 10] Real-Time HUD Dashboard, Debounced Alerts
           & Counterfactual Mission Decision Support
```

---

## Core Architecture & Subsystems

| Subsystem                | Architecture & Methodology                                                                                                                                                               |
| :----------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Physics Model**        | Mean-value aero-piston thermodynamics using ISA tropospheric lapse behaviour, turbocharger pressure relationships, BSFC-based fuel modelling, and hydrodynamic journal-bearing friction. |
| **Sensor Trust Engine**  | Multi-criteria signal validation using physical range checking, zero-variance/frozen detection, gradient-jump detection, and noise-variance analysis.                                    |
| **Residual Engine**      | Rolling 60-sample sliding-window residual analysis with online mean/sigma normalization and temporal slope tracking `d(res)/dt`.                                                         |
| **Anomaly Detection**    | Unsupervised Isolation Forest operating on a multidimensional normalized residual representation.                                                                                        |
| **Fault Classifier**     | Multi-class classification for `BEARING_DEGRADATION`, `THERMAL_OVERHEAT`, `COMBUSTION_MISFIRE`, `LUBRICATION_DEGRADATION`, `SENSOR_DRIFT`, and `NOMINAL`.                                |
| **Prognostics / RUL**    | Degradation-velocity tracking with upper/lower prediction intervals and a 1200 h standard Time-Between-Overhauls baseline calibration.                                                   |
| **Decision Engine**      | Evidence-backed counterfactual flight advisories including `PROCEED`, `ALTITUDE_STEP_DOWN`, `THROTTLE_REDUCTION`, and `ABORT_RTB`.                                                       |
| **Deterministic Replay** | Cached telemetry-frame replay with pause, resume, seek, and variable playback speeds from 0.5× to 4.0×.                                                                                  |

---

## Technology Stack

### Backend

* Python 3.11+
* FastAPI
* Uvicorn
* WebSockets
* Pydantic v2

### Intelligence & Scientific Computing

* Scikit-Learn
* NumPy
* SciPy

### Data & Storage

* SQLite time-series log
* Schema migrations

### Ground Control Station

* HTML5
* Vanilla CSS
* Glassmorphism HUD styling
* JavaScript ES Modules

### 3D Digital Twin

* Three.js
* WebGL
* Procedural engine visualization
* Exploded view
* Thermal visualization
* Wireframe representation

### Visual Analytics

* Chart.js
* HTML5 Canvas
* Real-time rolling telemetry waveforms
* 2D latent-space visualization

### Avionics Audio

* Web Audio API
* RPM-modulated engine rumble
* Procedural alert chimes

---

## Quick Start

### Option 1 — Windows One-Click Launcher

```cmd
run.bat
```

### Option 2 — Manual Launch

#### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

#### 2. Start the backend

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Install frontend dependencies

```bash
npm install
```

#### 4. Start the frontend

```bash
npm run dev
```

---

### Option 3 — Docker Compose

```bash
docker-compose up --build
```

---

## API Reference

### Real-Time & Telemetry Ingestion

| Method | Endpoint                   | Purpose                                                |
| :----- | :------------------------- | :----------------------------------------------------- |
| `POST` | `/api/telemetry`           | Ingest continuous or discrete telemetry frames         |
| `POST` | `/api/telemetry/live`      | High-speed live-stream ingestion                       |
| `GET`  | `/api/telemetry`           | Retrieve current telemetry state and inference         |
| `GET`  | `/api/evaluations/latest`  | Retrieve the latest 10-stage evaluation state          |
| `GET`  | `/api/evaluations/history` | Retrieve historical evaluation frame buffer            |
| `WS`   | `/ws/telemetry`            | Bidirectional telemetry stream and telecommand gateway |

### Digital Twin, Diagnostics & Prognostics

| Method | Endpoint                        | Purpose                                                             |
| :----- | :------------------------------ | :------------------------------------------------------------------ |
| `GET`  | `/twin/state`                   | Retrieve the complete Digital Twin state snapshot                   |
| `GET`  | `/visualization/state/{uav_id}` | Retrieve hierarchical 3D component and sensor state                 |
| `GET`  | `/health/{engine_id}`           | Retrieve subsystem health indices and degradation velocities        |
| `GET`  | `/faults/{engine_id}`           | Retrieve classified fault modes and traceable evidence              |
| `GET`  | `/rul/{engine_id}`              | Retrieve RUL estimates, prediction intervals, and endpoint criteria |
| `GET`  | `/sensors/{engine_id}/trust`    | Retrieve sensor-channel trust and health status                     |

### Mission & Validation

| Method | Endpoint                           | Purpose                                                      |
| :----- | :--------------------------------- | :----------------------------------------------------------- |
| `POST` | `/mission/what-if`                 | Run counterfactual mission simulations                       |
| `GET`  | `/api/events`                      | Retrieve active alerts and state-transition events           |
| `GET`  | `/experiments/baseline-comparison` | Compare performance against baseline monitoring              |
| `GET`  | `/evaluator/questions`             | Retrieve structured evaluator Q&A and technical explanations |
| `GET`  | `/system/limitations`              | Retrieve system boundaries and limitation disclosures        |

---

## Real-Time Data Flow

AERIS-TWIN is designed around a continuous telemetry-processing loop:

```text
Telemetry Source
      │
      ▼
Data Ingestion
      │
      ▼
Timestamp / Sequence Validation
      │
      ▼
Sensor Trust
      │
      ▼
Digital Twin Prediction
      │
      ▼
Residual Analysis
      │
      ▼
Anomaly Detection
      │
      ▼
Fault Classification
      │
      ▼
Health / Degradation
      │
      ▼
RUL Estimation
      │
      ▼
Mission Risk
      │
      ▼
Ground Station
```

The same evaluation pipeline can be used with live telemetry, replayed telemetry, or simulation sources.

### Data Modes & Disconnection Contract

AERIS-TWIN enforces strict operational mode isolation:
1. **LIVE Mode**: Accepts real telemetry frames strictly through confirmed telemetry channels (`POST /api/telemetry/live`, WebSocket ingestion, MAVLink). When no frame arrives within the threshold (`>3.0s` STALE, `>6.0s` DISCONNECTED), the UI strictly displays `NO LIVE DATA`, `SOURCE: DISCONNECTED`, `DATA AGE: --`, and `N/A` for all channel values. No random or mock frames are ever generated in LIVE mode.
2. **SIMULATION Mode**: Explicitly labeled (`SIMULATION` / `[SIM]`). Driven exclusively by the backend physics simulation engine (`backend/simulation/aero_simulator.py`).
3. **REPLAY Mode**: Explicitly labeled (`REPLAY`). Replays recorded multi-channel telemetry flight profiles deterministically with variable speed and pause/seek controls.

### Feeding Live Telemetry in Development

Use the included standalone telemetry producer to stream deterministic test frames into the live ingestion pipeline:

```bash
# Stream nominal cruise telemetry at 10 Hz
python dev_telemetry_sender.py --rate 10 --scenario cruise

# Stream an engine degradation scenario
python dev_telemetry_sender.py --rate 10 --scenario bearing_wear

# Send a single deterministic test frame with custom values
python dev_telemetry_sender.py --single --rpm 4215 --cht 78.4 --oil 4.3 --vib 1.6
```

---

## 3D Digital Twin

The AERIS-TWIN ground station includes an interactive 3D visualization layer intended to represent the monitored UAV and its propulsion system.

Supported interactions include:

* 360° model rotation
* Zoom in/out
* Pan
* Camera presets
* Component selection
* Engine inspection
* Exploded/cutaway visualization
* Sensor visualization
* Component health visualization
* Fault highlighting
* RUL visualization

The 3D layer is a visualization of the underlying Digital Twin state. It does not independently calculate engine health, fault risk, or RUL.

---

## Real-Time Monitoring

The system can evaluate continuous telemetry and update:

* Engine health
* Anomaly score
* Fault risk
* Operating state
* Digital Twin deviation
* Sensor trust
* Health trends
* Risk trends
* Active alerts
* Evaluation events

Simulation and live-data modes are kept conceptually separate so that simulated telemetry is not presented as real operational telemetry.

---

## Fault & Degradation Scenarios

The prototype supports progressive degradation scenarios rather than relying only on random sensor noise.

Example scenarios include:

* Bearing degradation
* Thermal overheating
* Combustion misfire
* Lubrication degradation
* Sensor drift
* Sensor failure
* Missing telemetry
* Noisy telemetry

A typical progression can be represented as:

```text
Healthy
   ↓
Early Degradation
   ↓
Anomaly
   ↓
Warning
   ↓
Critical Condition
```

---

## RUL & Predictive Health

RUL represents the estimated remaining useful operating time relative to a defined degradation or maintenance boundary.

AERIS-TWIN exposes:

* RUL estimate
* Lower prediction bound
* Upper prediction bound
* Confidence
* Degradation velocity
* Endpoint definition
* Model validity information

RUL should be treated as an engineering estimate rather than a guaranteed failure countdown.

Where real engine failure-to-degradation data is unavailable, simulation-based results must remain explicitly identified as prototype estimates.

---

## Mission What-If Analysis

The mission decision layer allows the system to evaluate alternative operating profiles.

Example inputs:

* Mission duration
* Altitude
* Power setting
* Engine load
* Environmental conditions

The system can compare scenarios such as:

```text
Current Mission
       │
       ├── Alternative A
       ├── Alternative B
       └── Alternative C
```

and evaluate:

* Mission risk
* Expected degradation
* Post-mission engine health
* Estimated RUL impact
* Recommended action

Possible recommendations include:

```text
PROCEED
PROCEED_WITH_POWER_DERATING
ALTITUDE_STEP_DOWN
THROTTLE_REDUCTION
SHORTEN_MISSION
ABORT_RTB
```

These are decision-support outputs and are not direct flight-control commands.

---

## Deterministic Replay

AERIS-TWIN supports replay of recorded or generated telemetry.

Replay capabilities include:

* Play
* Pause
* Resume
* Seek
* Reset
* 0.5× speed
* 1× speed
* 2× speed
* 4× speed

Replay allows the complete evaluation pipeline to be reproduced:

```text
Telemetry
   ↓
Twin Update
   ↓
Residual
   ↓
Anomaly
   ↓
Fault
   ↓
Health
   ↓
RUL
   ↓
Mission Risk
```

This is useful for debugging, validation, demonstrations, and regression testing.

---

## Testing & Verification

Run the automated test suite:

```bash
python -m pytest tests/ -v
```

Build the production frontend:

```bash
npm run build
```

For a complete system verification, test:

* Normal telemetry
* Progressive degradation
* Fault injection
* Sensor failure
* Missing telemetry
* Replay
* Digital Twin state updates
* Real-time dashboard updates
* Mission what-if scenarios
* API responses
* WebSocket communication

---

## Prototype Transparency

AERIS-TWIN is deliberately transparent about its current limitations.

The prototype should not be interpreted as:

* Flight-qualified software
* Aviation-certified diagnostic software
* An autonomous flight-control system
* A certified safety system
* A replacement for qualified maintenance personnel

Real operational deployment would require further:

* Engine-specific calibration
* Controlled engine test-bench validation
* Hardware-in-the-loop testing
* Real-world telemetry validation
* Failure/degradation datasets
* UAV flight testing
* Safety and certification processes

---

## Security & Data Integrity

The system is designed with prototype-level data-integrity considerations.

Where implemented, telemetry and flight records should support:

* Timestamp validation
* Sequence validation
* Data integrity checking
* Tamper detection
* Explicit stale-data states
* Environment-based secret management

The system should fail conservatively when telemetry becomes unreliable rather than silently treating invalid data as valid.

---

## Project Philosophy

AERIS-TWIN is designed around one central idea:

> **Do not wait for a threshold violation to discover that an engine is becoming unhealthy. Understand its behaviour, track its degradation, estimate what may happen next, and provide the operator with evidence-backed mission and maintenance decision support.**

The core architecture is:

```text
Telemetry
    ↓
Sensor Trust
    ↓
Physics Model
    ↓
Residuals
    ↓
AI / Anomaly Detection
    ↓
State Estimation
    ↓
Digital Twin
    ↓
Health & Degradation
    ↓
Fault / RUL
    ↓
Mission Risk
    ↓
Decision Support
```

---

## License & Academic Disclosure

AERIS-TWIN is developed for **academic, hackathon, research, and technology-evaluation purposes**.

All flight-related advisories are **decision-support recommendations** and require verification by qualified UAV mission operators.

The system does not directly control flight-critical aircraft functions.

**AERIS-TWIN — Aero Engine Reliability & Intelligence System**
