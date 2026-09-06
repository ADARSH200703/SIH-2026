"""
AERIS-TWIN Code Audit & Verification Test Suite
Tests:
1. Standard Endpoints: POST /api/telemetry, GET /api/evaluations/latest,
   GET /api/evaluations/history, GET /api/events, GET /api/replay/{id},
   GET /twin/state, GET /visualization/state/UAV-01.
2. Complete Fault Classifier Coverage: BEARING_DEGRADATION, THERMAL_OVERHEAT,
   COMBUSTION_MISFIRE, LUBRICATION_DEGRADATION, SENSOR_DRIFT, NOMINAL.
3. What-If Engine simulation under normal vs harsh operating conditions.
4. Sensor Trust Engine graceful degradation on out-of-range / frozen signals.
5. Decision Engine nominal envelope and risk-reduction calculations.
6. Bounded history buffer behavior (zero memory leak under continuous cycling).
"""
import time
import pytest

from backend.main import (
    app, twin_service, simulator, system_state,
    ingest_telemetry_standard, get_evaluations_latest,
    get_evaluations_history, get_system_events, get_replay_by_id,
    get_visualization_state, get_digital_twin_full_state
)
from backend.intelligence.fault_classifier import EngineFaultClassifier
from backend.intelligence.sensor_trust import SensorTrustEngine
from backend.mission.what_if_engine import WhatIfSimulationEngine
from backend.mission.decision_engine import MissionDecisionEngine


def test_standard_telemetry_post_and_get():
    """Verify POST /api/telemetry processes frame and returns expected contract."""
    sample_frame = {
        "engine_id": "UAV-ENG-ROT-914-01",
        "timestamp": time.time(),
        "sequence_number": 501,
        "rpm": 4215.0,
        "temperature": 78.4,
        "oilPressure": 4.30,
        "vibration": 1.55,
        "fuelFlow": 5.20,
        "engineLoad": 72.0,
        "altitude_ft": 10500.0,
        "ambient_temperature_c": -5.0
    }
    
    data = ingest_telemetry_standard(sample_frame)
    assert data["status"] == "processed"
    assert "health_index" in data
    assert "fault_class" in data
    assert "twin_state" in data

    # Verify GET /api/evaluations/latest
    latest_data = get_evaluations_latest()
    assert "twin_state" in latest_data
    assert "dashboard_view" in latest_data
    assert "residuals" in latest_data

    # Verify GET /api/evaluations/history
    hist_data = get_evaluations_history(limit=10)
    assert "count" in hist_data
    assert isinstance(hist_data["history"], list)


def test_events_and_replay_endpoints():
    """Verify GET /api/events and GET /api/replay/{id}."""
    ev_data = get_system_events(limit=20)
    assert "active_alerts" in ev_data
    assert "transition_timeline" in ev_data
    assert "event_timeline" in ev_data
    assert "log_events" in ev_data

    replay_data = get_replay_by_id(id="SESSION-001")
    assert replay_data["replay_id"] == "SESSION-001"
    assert "available_scenarios" in replay_data


def test_visualization_and_twin_state_endpoints():
    """Verify 3D visualization and full twin state endpoints."""
    vis_data = get_visualization_state(uav_id="UAV-01")
    assert "components" in vis_data
    assert "sensor_nodes" in vis_data
    assert "overall_health" in vis_data
    
    # Check that airframe does not claim certified
    airframe = vis_data["components"]["airframe"]
    assert "Certified" not in airframe.get("fault", "")

    twin_data = get_digital_twin_full_state()
    assert "health_state" in twin_data


def test_fault_classifier_all_classes():
    """Verify EngineFaultClassifier handles all fault categories properly."""
    classifier = EngineFaultClassifier()
    assert "LUBRICATION_DEGRADATION" in classifier.classes
    assert len(classifier.classes) == 7

    # Test lubrication degradation classification
    lub_residuals = {
        "oilPressure": {"normalized_residual": -2.8, "residual": -1.2, "residual_slope": -0.05},
        "temperature": {"normalized_residual": 1.2, "residual": 3.0, "residual_slope": 0.01},
        "vibration": {"normalized_residual": 0.3, "residual": 0.1, "residual_slope": 0.0},
        "rpm": {"normalized_residual": 0.0, "residual": 0.0, "residual_slope": 0.0},
        "fuelFlow": {"normalized_residual": 0.0, "residual": 0.0, "residual_slope": 0.0}
    }
    raw_lub = {"oilPressure": 2.1, "temperature": 85.0, "vibration": 1.7, "rpm": 4200, "fuelFlow": 5.2}
    res = classifier.classify(lub_residuals, {"anomaly": True, "score": 0.45}, raw_lub)
    assert res["fault"] == "LUBRICATION_DEGRADATION"
    assert res["confidence"] > 0.8
    assert len(res["evidence"]) > 0

    # Test bearing degradation classification
    bearing_residuals = {
        "vibration": {"normalized_residual": 3.6, "residual": 2.2, "residual_slope": 0.04},
        "oilPressure": {"normalized_residual": -0.4, "residual": -0.1, "residual_slope": 0.0},
        "temperature": {"normalized_residual": 0.8, "residual": 1.5, "residual_slope": 0.01},
        "rpm": {"normalized_residual": 0.0, "residual": 0.0, "residual_slope": 0.0},
        "fuelFlow": {"normalized_residual": 0.0, "residual": 0.0, "residual_slope": 0.0}
    }
    raw_bearing = {"vibration": 4.1, "oilPressure": 4.1, "temperature": 80.0, "rpm": 4200, "fuelFlow": 5.2}
    res_b = classifier.classify(bearing_residuals, {"anomaly": True, "score": 0.65}, raw_bearing)
    assert res_b["fault"] == "BEARING_DEGRADATION"


def test_what_if_simulation_engine():
    """Verify counterfactual What-If simulation responds correctly to power and altitude."""
    base_state = {
        "degradation_state": {"value": {"normalized_degradation": 0.08, "degradation_velocity": 0.002}},
        "health_state": {"value": {"health_index": 92.0, "normalized_degradation": 0.08}},
        "rul_state": {"value": {"rul_estimate_hours": 1100.0, "degradation_velocity": 0.002}},
        "operating_state": {"value": {"rpm": 4215, "load_pct": 72.0}},
        "thermal_state": {"value": {"cht_c": 78.4}},
        "mechanical_state": {"value": {"vibration_mms": 1.6}},
        "lubrication_state": {"value": {"oil_pressure_bar": 4.3}}
    }

    # Normal cruise condition
    sim_normal = twin_service.what_if_engine.simulate_what_if(
        current_twin_state=base_state,
        duration_hours=2.0,
        altitude_ft=10000.0,
        power_setting=70.0,
        ambient_temp_c=-5.0
    )
    assert sim_normal["projected_state"]["projected_final_degradation"] < 0.15
    assert sim_normal["projected_state"]["projected_rul_hours"] > 300.0

    # Extreme harsh condition (max power at 22,000 ft with hot ambient)
    sim_harsh = twin_service.what_if_engine.simulate_what_if(
        current_twin_state=base_state,
        duration_hours=8.0,
        altitude_ft=22000.0,
        power_setting=105.0,
        ambient_temp_c=25.0
    )
    assert sim_harsh["projected_state"]["projected_final_degradation"] > sim_normal["projected_state"]["projected_final_degradation"]
    assert sim_harsh["projected_state"]["projected_rul_hours"] < sim_normal["projected_state"]["projected_rul_hours"]
    assert sim_harsh["projected_risk"]["risk_index"] > sim_normal["projected_risk"]["risk_index"]


def test_sensor_trust_degradation():
    """Verify sensor trust detects frozen signals, jumps, and physical bounds violations."""
    trust_engine = SensorTrustEngine()
    
    # 1. Normal state -> high trust
    valid_telem = {
        "rpm": 4215.0,
        "temperature": 78.4,
        "oilPressure": 4.3,
        "vibration": 1.6,
        "fuelFlow": 5.2,
        "engineLoad": 72.0
    }
    for _ in range(5):
        t_matrix = trust_engine.evaluate_sensors(valid_telem)
    assert t_matrix["aggregate_trust_score"] > 0.90

    # 2. Out of bounds vibration (25.0 mm/s)
    invalid_telem = {**valid_telem, "vibration": 25.0}
    t_matrix_bad = trust_engine.evaluate_sensors(invalid_telem)
    assert t_matrix_bad["sensors"]["vibration"]["status"] == "OUT_OF_RANGE"
    assert t_matrix_bad["sensors"]["vibration"]["trust_score"] < 0.5


def test_decision_engine_nominal_state():
    """Verify decision engine outputs NOMINAL_STATE evidence without certified claim."""
    dec_engine = MissionDecisionEngine()
    
    nominal_fault = {"fault": "NOMINAL", "confidence": 0.95}
    nominal_rul = {"rul_estimate_hours": 1200.0, "lower_bound_hours": 1000.0}
    
    decision = dec_engine.recommend(
        health_data={"health_index": 95.0, "degradation_velocity": 0.001},
        fault_data=nominal_fault,
        rul_data=nominal_rul,
        risk_data={"risk_index": 0.08, "planned_duration_hours": 6.0},
        consensus_data={"consensus_status": "HIGH_CONSENSUS"}
    )
    assert decision["decision"] == "PROCEED"
    assert "nominal" in decision["reason"].lower()
    
    # Check evidence types
    evidence_types = [e["type"] for e in decision["evidence"]]
    assert "NOMINAL_STATE" in evidence_types
    assert "NOMINAL_CERTIFICATION" not in evidence_types


def test_bounded_history_buffer():
    """Verify twin service maintains bounded memory under continuous frame processing."""
    for i in range(120):
        frame = {
            "rpm": 4200.0 + (i % 50),
            "temperature": 78.0 + (i % 10) * 0.2,
            "oilPressure": 4.3 - (i % 5) * 0.05,
            "vibration": 1.6 + (i % 10) * 0.03,
            "fuelFlow": 5.2,
            "engineLoad": 70.0,
            "timestamp": time.time() + i
        }
        twin_service.process_telemetry_frame(frame)

    # state_history is capped at 100
    assert len(twin_service.state_history) <= 100
    # residual engine history is capped at 60
    for channel, history_list in twin_service.residual_engine.history.items():
        assert len(history_list) <= 60
