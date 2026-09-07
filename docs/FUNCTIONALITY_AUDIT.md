# Functionality Audit — AERIS-TWIN

This document records the end-to-end functionality audit, bug fixes, state synchronization verification, and behavioral contracts of interactive controls in the AERIS-TWIN Digital Twin platform.

---

## 1. Fixed Interactive Controls

### A. Audio Synthesizer Toggle (`#audio-toggle-btn` & Key `M`)
- **Root Cause**: `src/js/audioManager.js` declared state property `this.isMuted`, while `src/js/main.js` checked `!audio.muted` (which evaluated to `!undefined === true` continuously, breaking toggle states).
- **Fix**: 
  - Added getter properties `get muted()` and `get isLive()` to `AudioManager`.
  - Added safe `AudioContext` resume on user interaction to handle browser autoplay policies.
  - Synchronized icon (`volume_up` vs `volume_off`), text (`Audio: Live` vs `Audio: Muted`), and `.active` class state.

### B. Stream Running / Pause (`#pause-sim-btn` & Spacebar)
- **Root Cause**: The frontend previously only mutated `sim.state.isRunning` locally without notifying the FastAPI backend. Pressing Space attempted to call non-existent `sim.togglePause()`.
- **Fix**:
  - Implemented unified stream pause synchronization across WebSocket (`PAUSE_STREAM` action) and REST endpoint (`POST /api/stream/pause`).
  - Added `togglePause()` method to `EngineSimulator`.
  - Connected Spacebar shortcut to the unified `togglePause()` handler.
  - In LIVE mode: pause semantics clearly mean holding local stream evaluation and ingest without making false claims about stopping the physical aircraft engine.

### C. Mission Flight Clock Reset (`#header-mission-clock`)
- **Root Cause**: Element was styled as an interactive button with a tooltip ("Click to Reset Mission Flight Time"), but lacked an event listener.
- **Fix**:
  - Added click event listener triggering local simulation time reset (`sim.resetFlightTime(0)`), WebSocket command (`RESET_MISSION_CLOCK`), and REST call (`POST /api/flight-time/reset`).
  - Correctly resets mission display clock to `T+ 00:00:00`.

### D. Closed-Loop Mitigation Command (`#quick-mitigate-btn` & `#btn-execute-mitigation`)
- **Root Cause**: UI previously displayed misleading "Telecommand Uplinked — Mitigation Applied" in LIVE mode even when no physical flight control uplink gateway was attached.
- **Fix**:
  - **SIMULATION Mode**: Applies simulated throttle/cooling trim, resets scenario dropdown to nominal cruise, sends backend `MITIGATE` action, and logs `"Simulation Mitigation Applied — Scenario Trimmed to Nominal Cruise"`.
  - **LIVE Mode**: Strictly treated as decision-support advisory (`"Mitigation Advisory Acknowledged (Simulation-only in Test mode)"`) without fabricating unverified aircraft uplink commands.

### E. History Timeline Filters (`#hist-filter-all`, `#hist-filter-warning`, `#hist-filter-critical`)
- **Fix**: Updated `window._histFilter` to toggle active border and text styling across filter buttons when filtering events.

### F. Replay Engine API Endpoints (`POST /replay/resume` & Scrubber)
- **Fix**: Added `@app.post("/replay/resume")` alias to `@app.post("/replay/start")` in `backend/main.py` ensuring both REST paths and WebSocket actions work seamlessly.

### G. Modal Dismissals (Backdrop & Escape Key)
- **Fix**: Added global `Escape` key listener and backdrop click handlers for `#why-unhealthy-modal` and `#critical-alert-modal`.

---

## 2. Verified Working Controls

| Control Category | Control Elements | End-to-End Flow Verified | Status |
|---|---|---|---|
| **Header Navigation & Modes** | `btn-mode-live`, `btn-mode-sim`, `btn-switch-to-sim` | Updates UI banners, sends `SET_MODE`, updates backend `system_state.mode`, cleanly switches telemetry sources. | **VERIFIED** |
| **Ingestion Target Rate** | `rate-btn` (1Hz, 5Hz, 10Hz, 20Hz) | Updates UI active pill, sends `SET_RATE` over WS & `POST /api/rate`, adjusts broadcast loop frequency. | **VERIFIED** |
| **History Window Size** | `rate-btn` (30s, 60s, 120s) | Adjusts rolling buffer size in `ChartsManager` and `RealtimeMonitor`. | **VERIFIED** |
| **Scenario Picker & Quick Injections** | `scenario-dropdown`, `btn-quick-inject-bearing`, `btn-quick-inject-thermal`, `btn-quick-reset-sim` | Updates scenario target in `AeroEngineSimulator` and `EngineSimulator`, activates progressive fault injections. | **VERIFIED** |
| **Navigation Drawer** | `sidebar-toggle-btn`, `.sidebar-nav .nav-item` | Smooth view switching across `dashboard`, `realtime`, `threed`, `ai-lab`, `pipeline`, `history` with URL pushState. | **VERIFIED** |
| **3D Camera Presets** | `btn-cam-iso`, `front`, `rear`, `left`, `right`, `top`, `bottom`, `engine` | Smooth tweening camera positions in `ThreeDigitalTwin`. | **VERIFIED** |
| **3D Shaders & Inspection** | `btn-mode-solid`, `hologram`, `thermal`, `btn-engine-inspect-toggle`, `btn-explode-toggle`, `btn-toggle-sensors` | Updates material shaders, opacity, exploding displacement vectors, and sensor marker visibility. | **VERIFIED** |
| **Component Inspector** | `.component-pick-btn`, `handleComponentClick` | Inspects individual engine subsystems with live stress, expected baselines, and health percentages. | **VERIFIED** |
| **AI Prognostics Lab** | `#slider-sensitivity`, `#latent-space-canvas`, `#ai-trend-chart` | Dynamically renders 4 operating cluster regimes (C0–C3), current point coordinates, anomaly threshold rings, and multi-series trend history. | **VERIFIED** |
| **Log & Report Export** | `btn-export-logs` (JSON), `btn-export-csv` (CSV) | Generates structured telemetry audit files and downloads them directly to client disk. | **VERIFIED** |

---

## 3. Operational Modes Truthfulness

### LIVE Mode
- Ingests external physical telemetry packets via `POST /api/telemetry/live` or MAVLink stream.
- When no telemetry stream is active, displays disconnected banner and truthful `N/A` sensor values without fallback to fake simulated values.
- Stream pause holds local processing and evaluation without claiming aircraft engine shutdown.
- Mitigation is treated as operator decision-support advisory without claiming physical telecommand transmission.

### SIMULATION Mode
- Generates synthetic engine dynamics using `AeroEngineSimulator` with deterministic seed dynamics.
- Supports interactive progressive fault injection (bearing wear, thermal overheat, misfire, lubrication loss).
- Mitigation commands trim active simulation state back to nominal cruise baseline.

### REPLAY Mode
- Reads deterministic recorded sortie trajectories through `ReplayEngine`.
- Supports play, pause, seek, and variable playback speed multipliers ($0.5\times \dots 10\times$).

---

## 4. Test Suite Summary
- **Pytest Backend Suite**: 24/24 unit & integration tests passing (`tests/test_aeris_backend.py`, `tests/test_audit_verification.py`, `tests/test_realtime_evaluator.py`).
- **Production Bundle**: `npm run build` generates clean production assets in $2.14\text{s}$.
