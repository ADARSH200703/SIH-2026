# AERIS-TWIN — Version History & Checkpoint Log

This document maintains the chronological version history, verified checkpoints, test results, known limitations, and rollback targets for **AERIS-TWIN (Aero Engine Reliability & Intelligence System)** under SIH26054.

---

## Checkpoint Registry

| Version | Checkpoint Tag / Name | Git Commit | Date | Status | Rollback Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v1.0.0** | `checkpoint: final-validated` | `aa03683` / current | 2026-09-07 | **VERIFIED STABLE** | `checkpoint: telemetry-stable` |
| **v0.4.0** | `checkpoint: digital-twin-stable` | `aa03683` | 2026-09-07 | **VERIFIED STABLE** | `checkpoint: telemetry-stable` |
| **v0.3.0** | `checkpoint: telemetry-stable` | `aa03683` | 2026-09-07 | **VERIFIED STABLE** | `checkpoint: audit-fixes` |
| **v0.2.0** | `checkpoint: audit-fixes` | `c3635fa` | 2026-09-06 | **VERIFIED STABLE** | `checkpoint: baseline` |
| **v0.1.0** | `checkpoint: baseline` | `0328226` | 2026-09-06 | **BASELINE** | Initial Commit |

---

## Detailed Version Logs

### v1.0.0 — Final Validated Full-System Release
* **Date**: 2026-09-07
* **Checkpoint**: `checkpoint: final-validated`
* **Changes**:
  - Implemented 8 operating regime classifications (`SHUTDOWN`, `START`, `IDLE`, `LOW_LOAD`, `CLIMB`, `CRUISE`, `HIGH_LOAD`, `DESCENT`, `TRANSIENT`) in `AeroPistonPhysicsModel`.
  - Added sensor calibration drift detection (`DRIFTING`) and unified `reset()` methods across `SensorTrustEngine`, `ResidualEngine`, `RealtimeAlertEngine`, `EngineDegradationModel`, and `TwinUpdateService`.
  - Linked Realtime 6-channel cards to Field Inspection modal displaying live/expected values, residual z-scores, temporal slope $d(res)/dt$, sensor trust score, data age, and explainable evidence.
  - Added `docs/ROLLBACK.md` and complete recovery runbook.
* **Tests Passed**:
  - All 23 pytest backend integration tests: `100% PASS`
  - Frontend production build (`vite build`): `PASS` (zero errors)
  - Disconnect, Staleness, and Nominal/Anomalous Live Ingestion tests: `PASS`
* **Known Limitations**:
  - Direct hardware CAN transceiver interface (SocketCAN/CANalyst-II) requires physical hardware dongle; supported via UDP/MAVLink adapter and `dev_telemetry_sender.py`.

---

### v0.3.0 — Real-Time Telemetry & Strict Mode Separation
* **Date**: 2026-09-07
* **Checkpoint**: `checkpoint: telemetry-stable`
* **Commit**: `aa03683ee05199e29c633f32250f281451a897a9`
* **Changes**:
  - Removed client-side fake telemetry auto-ticker from `src/js/engineSimulator.js`.
  - Enforced strict disconnection rendering in `src/js/realtimeMonitor.js` (`N/A`, `NO LIVE DATA`, `SOURCE: DISCONNECTED`, `DATA AGE: --`).
  - Fixed `LiveStreamSource.get_frame()` in `backend/simulation/sources.py` to pop frames strictly from the buffer without synthetic duplication.
  - Implemented standalone CLI telemetry producer `dev_telemetry_sender.py` for deterministic live testing.
  - Updated 6-channel titles in `index.html` to reflect actual aero-piston parameters.
* **Tests Passed**:
  - `test_mode_switching_and_rate_config`: PASS
  - `test_live_telemetry_ingestion`: PASS
  - `test_sensor_trust_validation`: PASS
  - `test_alert_debouncing_and_transitions`: PASS
  - `test_replay_and_mavlink_sources`: PASS
  - `test_live_stream_disconnection_and_staleness`: PASS
  - `test_deterministic_live_telemetry_flow`: PASS
* **Rollback Target**: `c3635fa`

---

### v0.2.0 — Audit Verification & Physics Enhancements
* **Date**: 2026-09-06
* **Checkpoint**: `checkpoint: audit-fixes`
* **Commit**: `c3635fa26930e55bac90f2327f9015e53fd8a4bd`
* **Changes**:
  - Added brake torque and angular velocity mathematical formulations in `aero_engine_model.py`.
  - Replaced gas-turbine terminology with aero-piston nomenclature throughout alerts and evidence generators.
  - Enhanced unit test assertions across all 6 classified fault modes.
* **Tests Passed**:
  - All 16 backend and intelligence audit verification tests: PASS

---

### v0.1.0 — Initial Comprehensive Baseline
* **Date**: 2026-09-06
* **Checkpoint**: `checkpoint: baseline`
* **Commit**: `032822616de8031bbeb4f359f6011c57e1e72551`
* **Changes**:
  - Complete AERIS digital twin platform codebase: FastAPI backend, physics simulation, ML pipeline (Isolation Forest, GBDT fault classifier), 3D Three.js engine visualization, HUD ground station dashboard.
