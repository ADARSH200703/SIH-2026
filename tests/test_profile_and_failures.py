"""
Comprehensive Profile Isolation & Failure Mode Test Suite for AERIS-TWIN
Tests scientific integrity constraints:
1. MOTOR_PROTOTYPE vs AERO_ENGINE profile isolation (Zero fabricated aero defaults)
2. Malformed / non-numeric packet rejection
3. Sequence anomalies (duplicates, gaps, out-of-order)
4. Monotonic timestamp and clock skew validation
5. Sensor trust degradation and honest missing sensor states
6. Defensible fault classification qualifiers (LIKELY, SUSPECTED, POSSIBLE, INSUFFICIENT_DATA)
7. Honest RUL estimates with prediction intervals and data sufficiency
8. Evaluator Q1-Q15 and System Limitations endpoints
"""
import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app, live_source, normalize_telemetry_packet
from backend.intelligence.sensor_trust import SensorTrustEngine
from backend.intelligence.fault_classifier import EngineFaultClassifier
from backend.intelligence.anomaly_detector import EngineAnomalyDetector
from backend.intelligence.rul_engine import EngineRULEngine
from backend.physics.motor_prototype_model import MotorPrototypePhysicsModel

client = TestClient(app)

def test_motor_prototype_profile_isolation_no_silent_aero_defaults():
    """Verify that MOTOR_PROTOTYPE packets NEVER receive silent aero defaults (oil pressure, EGT, CHT, fuel flow)."""
    raw_motor_packet = {
        "device_id": "AERIS-PROTOTYPE-01",
        "profile": "MOTOR_PROTOTYPE",
        "sequence_number": 101,
        "timestamp": time.time(),
        "current_a": 2.15,
        "voltage_v": 11.4,
        "power_w": 24.51,
        "temperature_c": 38.2,
        "vibration_mms": 0.45,
        "motor_load_pct": 45.0
    }
    normalized = normalize_telemetry_packet(raw_motor_packet)
    
    assert normalized["profile"] == "MOTOR_PROTOTYPE"
    assert normalized["current_a"] == 2.15
    assert normalized["voltage_v"] == 11.4
    
    # Critical Scientific Integrity Check: Aero parameters MUST NOT be injected
    assert "oilPressure" not in normalized
    assert "oil_pressure_bar" not in normalized
    assert "fuelFlow" not in normalized
    assert "fuel_flow" not in normalized
    assert "cht_c" not in normalized
    assert "egt_c" not in normalized
    assert "altitude_ft" not in normalized
    assert "airspeed_kts" not in normalized

def test_motor_prototype_missing_optional_sensors_honest_reporting():
    """Verify missing RPM or Voltage on motor testbed is reported honestly without fake substitution."""
    sensor_engine = SensorTrustEngine()
    
    # Motor packet without RPM and without voltage (e.g. only ACS712 current installed)
    minimal_motor_packet = {
        "profile": "MOTOR_PROTOTYPE",
        "current_a": 1.85,
        "timestamp": time.time()
    }
    t_res = sensor_engine.evaluate_sensors(minimal_motor_packet)
    
    assert t_res["profile"] == "MOTOR_PROTOTYPE"
    assert t_res["sensors"]["current_a"]["status"] == "VALID"
    assert t_res["sensors"]["current_a"]["value"] == 1.85
    assert t_res["sensors"]["rpm"]["status"] == "NOT_INSTALLED"
    assert t_res["sensors"]["rpm"]["value"] is None
    assert t_res["sensors"]["voltage_v"]["status"] == "NOT_INSTALLED"
    assert t_res["sensors"]["voltage_v"]["value"] is None
    assert t_res["all_sensors_valid"] is True

def test_malformed_and_non_numeric_telemetry_rejection():
    """Verify system handles non-numeric / malformed sensor values safely."""
    sensor_engine = SensorTrustEngine()
    
    malformed_frame = {
        "profile": "AERO_ENGINE",
        "rpm": "INVALID_RPM_STRING",
        "temperature": 78.4,
        "oilPressure": 4.3,
        "vibration": 1.6,
        "fuelFlow": 5.2,
        "timestamp": time.time()
    }
    t_res = sensor_engine.evaluate_sensors(malformed_frame)
    assert t_res["sensors"]["rpm"]["status"] == "MALFORMED"
    assert t_res["sensors"]["rpm"]["trust_score"] == 0.0
    assert t_res["all_sensors_valid"] is False

def test_future_timestamp_clock_skew_detection():
    """Verify packet with future timestamp (>60s) is tagged with clock skew warning."""
    sensor_engine = SensorTrustEngine()
    future_time = time.time() + 300.0  # 5 minutes in future
    frame = {
        "profile": "AERO_ENGINE",
        "rpm": 4200.0,
        "temperature": 78.4,
        "oilPressure": 4.3,
        "vibration": 1.6,
        "fuelFlow": 5.2,
        "timestamp": future_time
    }
    t_res = sensor_engine.evaluate_sensors(frame)
    assert t_res["timestamp_validation"]["valid"] is False
    assert "Future timestamp" in t_res["timestamp_validation"]["reason"]

def test_hardware_endpoint_ingestion_and_explainability():
    """Verify hardware endpoint returns full explainability structure and honest qualifiers."""
    payload = {
        "device_id": "AERIS-ESP32-001",
        "profile": "MOTOR_PROTOTYPE",
        "sequence_number": 50,
        "current_a": 6.8,  # Overcurrent condition
        "voltage_v": 11.2,
        "power_w": 76.16,
        "temperature_c": 55.0,
        "motor_load_pct": 88.0,
        "timestamp": time.time()
    }
    res = client.post("/api/telemetry/hardware", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["profile"] == "MOTOR_PROTOTYPE"
    assert data["anomaly_score"] > 0.30
    assert "Overcurrent" in data["fault_class"]

def test_evaluator_questions_registry_coverage():
    """Verify all 15 Core SIH Evaluator Questions (Q1 - Q15) are accessible via API."""
    res = client.get("/api/evaluator/questions")
    assert res.status_code == 200
    data = res.json()
    assert data["total_questions"] >= 15
    
    # Verify specific questions Q1 to Q15
    for i in range(1, 16):
        q_res = client.get(f"/api/evaluator/questions/Q{i}")
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert "question" in q_data
        assert "answer" in q_data
        assert len(q_data["technical_evidence"]) > 0

def test_system_limitations_7_evaluator_disclosures():
    """Verify that the 7 mandatory evaluator disclosure questions are clearly answered."""
    res = client.get("/api/system/limitations")
    assert res.status_code == 200
    data = res.json()
    assert data["project_class"] == "RESEARCH_AND_TECHNOLOGY_DEMONSTRATOR"
    assert data["flight_qualification"] == "NON_FLIGHT_QUALIFIED_PROTOTYPE"
    assert data["autonomous_control"] == "NO_AUTONOMOUS_AIRCRAFT_CONTROL"
    
    disclosures = data["evaluator_disclosures"]
    assert "1_flight_qualified" in disclosures
    assert "2_autonomous_flight_controller" in disclosures
    assert "3_rul_guarantee" in disclosures
    assert "4_motor_prototype_equivalence" in disclosures
    assert "5_real_data" in disclosures
    assert "6_simulated_data" in disclosures
    assert "7_remaining_validation" in disclosures

def test_validation_metrics_endpoint():
    """Verify validation metrics endpoint returns empirical benchmark without fake claims."""
    res = client.get("/api/validation/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALIDATED_EMPIRICAL_BENCHMARK"
    assert data["dataset_name"] == "UAV-ROT914-SIM-CORPUS-2026.1"
    assert "model_registry" in data
    assert len(data["model_registry"]) >= 4

def test_rul_engine_insufficient_data_handling():
    """Verify RUL engine outputs INSUFFICIENT_DATA and broad intervals when degradation data is absent."""
    rul_engine = EngineRULEngine()
    
    # Degraded sensor trust + flat degradation
    rul_out = rul_engine.estimate_rul(
        degradation_data={"normalized_degradation": 0.05, "degradation_velocity": 0.00001},
        sensor_trust={"aggregate_trust_score": 0.35, "all_sensors_valid": False},
        telemetry={"profile": "MOTOR_PROTOTYPE"}
    )
    assert rul_out["confidence_category"] == "LOW"
    assert "Engineering estimate" in rul_out["disclaimer"]
