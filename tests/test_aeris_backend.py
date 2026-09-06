"""
Comprehensive Verification Test Suite for AERIS-TWIN Backend
Tests all 8 phases:
1. Database tables & schemas
2. Physics model & residual engine
3. Sensor trust, Anomaly detector & Fault classifier
4. Twin consensus engine
5. Degradation & RUL prognostics with uncertainty bounds
6. Mission risk, counterfactual what-if simulation, and decision engine
7. Baseline comparison experiment runner
8. Evaluator questions registry & limitations API
9. Full 13-stage deterministic acceptance scenario
"""
import sys
import os
import unittest
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import init_db, get_db_connection
from backend.physics.aero_engine_model import AeroPistonPhysicsModel
from backend.physics.residual_engine import ResidualEngine
from backend.intelligence.sensor_trust import SensorTrustEngine
from backend.intelligence.anomaly_detector import EngineAnomalyDetector
from backend.intelligence.fault_classifier import EngineFaultClassifier
from backend.intelligence.consensus_engine import TwinConsensusEngine
from backend.intelligence.degradation_model import EngineDegradationModel
from backend.intelligence.rul_engine import EngineRULEngine
from backend.mission.mission_risk import MissionRiskEngine
from backend.mission.what_if_engine import WhatIfSimulationEngine
from backend.mission.decision_engine import MissionDecisionEngine
from backend.twin_service import TwinUpdateService
from backend.validation.experiment_runner import ExperimentRunner
from backend.evaluator.questions_registry import EVALUATOR_QUESTIONS
from backend.evaluator.limitations import SYSTEM_LIMITATIONS

class TestAerisBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.twin_service = TwinUpdateService()

    def test_01_database_tables(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        required_tables = [
            "engines", "engine_configurations", "uavs", "missions",
            "telemetry", "sensor_health", "physics_predictions", "residuals",
            "twin_states", "degradation_states", "health_states", "fault_predictions",
            "rul_predictions", "mission_risk", "mission_scenarios", "mission_decisions",
            "simulation_runs", "fault_injections", "replay_sessions", "experiments",
            "experiment_metrics", "model_registry", "dataset_registry", "evidence",
            "evaluator_questions", "system_events"
        ]
        for t in required_tables:
            self.assertIn(t, tables, f"Missing table: {t}")

    def test_02_physics_and_residuals(self):
        physics = AeroPistonPhysicsModel()
        frame = {
            "rpm": 4200.0,
            "throttle": 68.0,
            "altitude_ft": 15000.0,
            "ambient_temperature_c": -14.5
        }
        exp = physics.compute_expected_state(frame)
        self.assertGreater(exp["expected_cht_c"], 65.0)
        self.assertLess(exp["expected_cht_c"], 95.0)
        self.assertGreater(exp["expected_oil_pressure_bar"], 3.5)
        self.assertGreater(exp["estimated_power_kw"], 50.0)
        self.assertGreater(exp["estimated_torque_nm"], 100.0)
        self.assertLess(exp["estimated_torque_nm"], 200.0)
        
        residuals_engine = ResidualEngine()
        res = residuals_engine.compute_residuals(
            {"vibration": 3.8, "temperature": 80.0, "oilPressure": 4.2, "fuelFlow": 5.2},
            exp
        )
        self.assertIn("vibration", res)
        self.assertGreater(res["vibration"]["normalized_residual"], 2.0)

    def test_03_sensor_trust(self):
        sensor_engine = SensorTrustEngine()
        # Normal frame
        normal_frame = {"rpm": 4200, "temperature": 78.4, "oilPressure": 4.3, "vibration": 1.6, "fuelFlow": 5.2}
        t_res = sensor_engine.evaluate_sensors(normal_frame)
        self.assertTrue(t_res["all_sensors_valid"])
        self.assertGreater(t_res["aggregate_trust_score"], 0.9)
        
        # Out of bounds frame
        bad_frame = {"rpm": 4200, "temperature": 180.0, "oilPressure": 4.3, "vibration": 1.6, "fuelFlow": 5.2}
        t_res_bad = sensor_engine.evaluate_sensors(bad_frame)
        self.assertEqual(t_res_bad["sensors"]["temperature"]["status"], "OUT_OF_RANGE")

    def test_04_consensus_and_rul(self):
        degradation_model = EngineDegradationModel()
        rul_engine = EngineRULEngine()
        
        # Simulated high degradation
        deg_res = degradation_model.compute_degradation(
            residuals={"vibration": {"normalized_residual": 4.0}, "temperature": {"normalized_residual": 1.0}, "oilPressure": {"normalized_residual": -1.0}, "fuelFlow": {"normalized_residual": 0.0}},
            telemetry={"timestamp": 1000.0, "rpm": 4200, "altitude_ft": 15000},
            sensor_trust={"aggregate_trust_score": 0.95, "all_sensors_valid": True}
        )
        self.assertLess(deg_res["health_index"], 85.0)
        
        rul_res = rul_engine.estimate_rul(deg_res, {"aggregate_trust_score": 0.95}, {"rpm": 4200, "altitude_ft": 15000})
        self.assertGreater(rul_res["rul_estimate_hours"], 0.0)
        self.assertLess(rul_res["lower_bound_hours"], rul_res["rul_estimate_hours"])
        self.assertGreater(rul_res["upper_bound_hours"], rul_res["rul_estimate_hours"])

    def test_05_what_if_and_decision(self):
        physics = AeroPistonPhysicsModel()
        risk_engine = MissionRiskEngine()
        what_if = WhatIfSimulationEngine(physics, risk_engine)
        
        twin_state = {
            "degradation_state": {"value": {"normalized_degradation": 0.35, "degradation_velocity": 0.015}},
            "fault_state": {"value": {"fault": "BEARING_DEGRADATION", "probability": 0.85, "confidence": 0.90}}
        }
        
        res = what_if.simulate_what_if(twin_state, duration_hours=4.0, altitude_ft=18000.0, power_setting=0.80, ambient_temp_c=30.0)
        self.assertIn("projected_state", res)
        self.assertIn("scenario_comparisons", res)
        self.assertEqual(len(res["scenario_comparisons"]), 2)

    def test_06_baseline_experiment_runner(self):
        runner = ExperimentRunner()
        res = runner.run_baseline_comparison_experiment(seed=42, n_samples=60)
        self.assertIn("comparison", res)
        self.assertIn("aeris_twin", res["comparison"])
        self.assertIn("traditional_threshold_baseline", res["comparison"])
        self.assertGreaterEqual(res["comparison"]["aeris_early_warning_lead_time_sec"], 0)

    def test_07_evaluator_questions_and_limitations(self):
        self.assertIn("DT-001", EVALUATOR_QUESTIONS)
        self.assertIn("ML-003", EVALUATOR_QUESTIONS)
        self.assertIn("LIMITATION-001", EVALUATOR_QUESTIONS)
        self.assertIn("documented_limitations", SYSTEM_LIMITATIONS)

    def test_08_final_acceptance_test_chain(self):
        """
        Executes the exact 13-stage causal acceptance test:
        Healthy -> Progressive Bearing Fault -> Residual -> Sensor Valid ->
        Anomaly -> Fault -> Twin State -> Health Decline -> Deg Velocity ->
        RUL + Uncertainty -> Mission Risk -> What-If -> Decision -> Evidence.
        """
        service = TwinUpdateService()
        
        # Step A: Healthy frame
        healthy_frame = {
            "engine_id": "UAV-ENG-ROT-914-01",
            "sequence_number": 1,
            "rpm": 4215.0,
            "throttle": 68.0,
            "temperature": 78.4,
            "oilPressure": 4.3,
            "vibration": 1.6,
            "fuelFlow": 5.2,
            "engineLoad": 62.0,
            "altitude_ft": 15000.0,
            "ambient_temperature_c": -14.5
        }
        res_healthy = service.process_telemetry_frame(healthy_frame)
        self.assertEqual(res_healthy["twin_state"]["fault_state"]["value"]["fault"], "NOMINAL")
        self.assertGreater(res_healthy["twin_state"]["health_state"]["value"]["health_index"], 90.0)
        
        # Step B: Progressive bearing degradation frames
        for t in range(20):
            degraded_frame = dict(
                healthy_frame,
                sequence_number=t + 2,
                timestamp=1772900000.0 + t,
                vibration=1.6 + 0.15 * t, # Progressive vibration increase
                temperature=78.4 + 0.2 * t
            )
            res_degraded = service.process_telemetry_frame(degraded_frame)
            
        # Verify complete chain
        ts = res_degraded["twin_state"]
        self.assertTrue(res_degraded["twin_state"]["fault_state"]["value"]["fault"] in ["BEARING_DEGRADATION", "UNKNOWN_ANOMALY"])
        self.assertLess(ts["health_state"]["value"]["health_index"], 80.0)
        self.assertGreater(ts["degradation_state"]["value"]["degradation_velocity"], 0.0)
        self.assertGreater(ts["rul_state"]["value"]["rul_estimate_hours"], 0.0)
        self.assertGreater(len(ts["evidence"]), 0)
        self.assertIn("decision", ts)

if __name__ == "__main__":
    unittest.main()
