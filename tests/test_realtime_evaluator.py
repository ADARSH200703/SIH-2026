"""
Comprehensive Unit & Integration Tests for AERIS-TWIN Real-Time Data Evaluator
Tests continuous live evaluation, sensor quality checks, alert debouncing,
rate configuration, mode switching, and deterministic replay directly.
"""
import time
import pytest

from backend.main import (
    system_state, live_source, twin_service,
    set_evaluator_mode, set_target_rate, ingest_live_telemetry,
    ModeRequest, RateRequest, seek_replay, speed_replay,
    ReplaySeekRequest, ReplaySpeedRequest
)
from backend.simulation.sources import (
    LiveStreamSource, SimulationSource, FileReplaySource, MAVLinkSource
)
from backend.intelligence.alert_engine import RealtimeAlertEngine
from backend.intelligence.sensor_trust import SensorTrustEngine


def test_mode_switching_and_rate_config():
    # Switch to SIMULATION
    res_sim = set_evaluator_mode(ModeRequest(mode="SIMULATION"))
    assert res_sim["mode"] == "SIMULATION"
    assert system_state.mode == "SIMULATION"

    # Switch to LIVE
    res_live = set_evaluator_mode(ModeRequest(mode="LIVE"))
    assert res_live["mode"] == "LIVE"
    assert system_state.mode == "LIVE"

    # Rate configuration
    for rate in [1.0, 5.0, 10.0, 20.0]:
        res_r = set_target_rate(RateRequest(rate_hz=rate))
        assert res_r["target_rate_hz"] == rate
        assert system_state.target_rate_hz == rate


def test_live_telemetry_ingestion():
    set_evaluator_mode(ModeRequest(mode="LIVE"))

    test_packet = {
        "engine_id": "UAV-ENG-ROT-914-01",
        "timestamp": time.time(),
        "sequence_number": 101,
        "rpm": 4218.0,
        "temperature": 79.2,
        "oilPressure": 4.28,
        "vibration": 1.62,
        "fuelFlow": 5.18,
        "engineLoad": 62.5,
        "egt_c": 648.0,
        "source": "LIVE",
    }
    data = ingest_live_telemetry(test_packet)
    assert data["status"] == "ingested"
    assert data["mode"] == "LIVE"
    assert "latency_ms" in data
    assert "health_index" in data
    assert "anomaly_score" in data
    assert live_source.is_connected() is True


def test_sensor_trust_validation():
    trust_engine = SensorTrustEngine(history_len=20)

    # 1. Nominal frame
    res_nom = trust_engine.evaluate_sensors({
        "rpm": 4215.0, "temperature": 78.4, "oilPressure": 4.3,
        "vibration": 1.6, "fuelFlow": 5.2, "engineLoad": 62.0,
        "timestamp": time.time()
    })
    assert res_nom["aggregate_trust_score"] >= 0.95
    assert res_nom["all_sensors_valid"] is True
    assert res_nom["timestamp_validation"]["valid"] is True

    # 2. Out-of-range RPM
    res_oor = trust_engine.evaluate_sensors({
        "rpm": 9500.0, "temperature": 78.4, "oilPressure": 4.3,
        "vibration": 1.6, "fuelFlow": 5.2, "engineLoad": 62.0,
        "timestamp": time.time()
    })
    assert res_oor["sensors"]["rpm"]["status"] == "OUT_OF_RANGE"
    assert res_oor["sensors"]["rpm"]["trust_score"] <= 0.20

    # 3. Stuck sensor (16 identical samples)
    now = time.time()
    for _ in range(16):
        res_stuck = trust_engine.evaluate_sensors({
            "rpm": 4215.0, "temperature": 78.4, "oilPressure": 4.3000,
            "vibration": 1.6000, "fuelFlow": 5.2000, "engineLoad": 62.0,
            "timestamp": now
        })
    assert res_stuck["sensors"]["vibration"]["status"] == "STUCK"


def test_alert_debouncing_and_transitions():
    alert_engine = RealtimeAlertEngine()

    now = time.time()
    nominal_telem = {"vibration": 1.6, "temperature": 78.4, "oilPressure": 4.3, "timestamp": now}
    nominal_res = {"vibration": {"normalized_residual": 0.1}, "temperature": {"normalized_residual": 0.2}, "oilPressure": {"normalized_residual": 0.0}}
    sensor_trust = {"aggregate_trust_score": 1.0, "sensors": {}}

    # Step 1: Nominal
    summary_1 = alert_engine.evaluate_state_transitions(
        health_index=95.0,
        anomaly_result={"anomaly": False, "score": 0.02},
        fault_result={"fault": "NOMINAL", "probability": 0.95, "severity": "NONE"},
        risk_result={"risk_level": "LOW"},
        sensor_trust=sensor_trust,
        residuals=nominal_res,
        telemetry=nominal_telem
    )
    assert summary_1["system_state"] == "NORMAL"
    assert summary_1["active_alerts_count"] == 0

    # Step 2: Fault injected -> High vibration
    fault_telem = {"vibration": 4.2, "temperature": 78.4, "oilPressure": 4.3, "timestamp": now + 1}
    fault_res = {"vibration": {"normalized_residual": 3.6}, "temperature": {"normalized_residual": 0.2}, "oilPressure": {"normalized_residual": 0.0}}

    summary_2 = alert_engine.evaluate_state_transitions(
        health_index=45.0,
        anomaly_result={"anomaly": True, "score": 0.88},
        fault_result={"fault": "BEARING_DEGRADATION", "probability": 0.89, "severity": "CRITICAL"},
        risk_result={"risk_level": "CRITICAL"},
        sensor_trust=sensor_trust,
        residuals=fault_res,
        telemetry=fault_telem
    )
    assert summary_2["system_state"] == "CRITICAL"
    assert summary_2["active_alerts_count"] >= 1

    # Step 3: Condition persists -> Verify debouncing (no duplicate alert count growth)
    for i in range(5):
        summary_persist = alert_engine.evaluate_state_transitions(
            health_index=44.0,
            anomaly_result={"anomaly": True, "score": 0.90},
            fault_result={"fault": "BEARING_DEGRADATION", "probability": 0.91, "severity": "CRITICAL"},
            risk_result={"risk_level": "CRITICAL"},
            sensor_trust=sensor_trust,
            residuals=fault_res,
            telemetry={"vibration": 4.3, "temperature": 78.4, "oilPressure": 4.3, "timestamp": now + 2 + i}
        )
        assert summary_persist["active_alerts_count"] == 1
        assert summary_persist["alerts"][0]["occurrences"] == 2 + i

    # Step 4: Condition clears
    summary_clear = alert_engine.evaluate_state_transitions(
        health_index=92.0,
        anomaly_result={"anomaly": False, "score": 0.03},
        fault_result={"fault": "NOMINAL", "probability": 0.94, "severity": "NONE"},
        risk_result={"risk_level": "LOW"},
        sensor_trust=sensor_trust,
        residuals=nominal_res,
        telemetry={"vibration": 1.6, "temperature": 78.4, "oilPressure": 4.3, "timestamp": now + 10}
    )
    assert summary_clear["system_state"] == "NORMAL"
    assert summary_clear["active_alerts_count"] == 0


def test_replay_and_mavlink_sources():
    # Test Replay Source
    frames = [
        {"rpm": 4200, "temperature": 78, "oilPressure": 4.3, "vibration": 1.6, "timestamp": 100},
        {"rpm": 4210, "temperature": 79, "oilPressure": 4.3, "vibration": 1.65, "timestamp": 101},
        {"rpm": 4220, "temperature": 80, "oilPressure": 4.2, "vibration": 1.7, "timestamp": 102},
    ]
    rep = FileReplaySource(frames=frames)
    assert rep.is_connected() is True
    rep.play()
    f1 = rep.get_frame()
    assert f1["rpm"] == 4200
    rep.seek(2)
    f3 = rep.get_frame()
    assert f3["rpm"] == 4220

    # Test MAVLink Source
    mav = MAVLinkSource()
    assert mav.is_connected() is False
    m_frame = mav.ingest_mavlink_msg("HIGHRES_IMU", {"rpm": 4350, "temperature": 81.2, "press_abs": 4.1, "zacc": 1.75})
    assert mav.is_connected() is True
    assert m_frame["rpm"] == 4350.0
    assert m_frame["source"] == "MAVLINK"
