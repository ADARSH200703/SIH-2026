"""
TwinUpdateService for AERIS-TWIN
Central computational engine orchestrating the full 16-stage pipeline:
Telemetry -> Validation -> Sensor Trust -> Physics Model -> Residuals ->
Anomaly Detection -> Fault Classification -> Consensus -> Digital Twin State ->
Degradation -> Health -> RUL + Uncertainty -> Mission Risk -> Decisions -> Alerts & Debouncing -> Evidence.
"""
import time
from typing import Dict, Any, List, Optional
from collections import deque

from .physics.aero_engine_model import AeroPistonPhysicsModel
from .physics.residual_engine import ResidualEngine
from .intelligence.sensor_trust import SensorTrustEngine
from .intelligence.anomaly_detector import EngineAnomalyDetector
from .intelligence.fault_classifier import EngineFaultClassifier
from .intelligence.consensus_engine import TwinConsensusEngine
from .intelligence.degradation_model import EngineDegradationModel
from .intelligence.rul_engine import EngineRULEngine
from .intelligence.alert_engine import RealtimeAlertEngine
from .mission.mission_risk import MissionRiskEngine
from .mission.what_if_engine import WhatIfSimulationEngine
from .mission.decision_engine import MissionDecisionEngine
from .simulation.mavlink_adapter import TelemetryGatewayAdapter
from .database import log_telemetry_packet, log_twin_execution, log_event
from .models.twin_state import DigitalTwinState, DashboardView, SubState

class TwinUpdateService:
    def __init__(self):
        # Initialize Subsystem Modules
        self.gateway = TelemetryGatewayAdapter()
        self.physics_model = AeroPistonPhysicsModel()
        self.residual_engine = ResidualEngine(window_size=30)
        self.sensor_trust_engine = SensorTrustEngine(history_len=40)
        self.anomaly_detector = EngineAnomalyDetector()
        self.fault_classifier = EngineFaultClassifier()
        self.consensus_engine = TwinConsensusEngine()
        self.degradation_model = EngineDegradationModel(history_size=60)
        self.rul_engine = EngineRULEngine(failure_threshold=0.75)
        self.risk_engine = MissionRiskEngine()
        self.decision_engine = MissionDecisionEngine()
        self.what_if_engine = WhatIfSimulationEngine(self.physics_model, self.risk_engine)
        self.alert_engine = RealtimeAlertEngine()
        
        # State tracking & rate metrics
        self.last_twin_state: Optional[Dict[str, Any]] = None
        self.last_dashboard_view: Optional[Dict[str, Any]] = None
        # deque(maxlen=100): O(1) append + automatic oldest-drop; replaces list + pop(0)
        self.state_history: deque = deque(maxlen=100)

        self._frame_timestamps: deque = deque(maxlen=60)
        self._processing_durations: deque = deque(maxlen=60)

    def reset(self):
        """Resets all pipeline buffers, histories, alert states, and sensor trust."""
        self.residual_engine.reset()
        self.alert_engine.reset()
        self.sensor_trust_engine.reset()
        self.degradation_model.reset()
        self.state_history.clear()
        self._frame_timestamps.clear()
        self._processing_durations.clear()
        self.last_twin_state = None
        self.last_dashboard_view = None

    def process_motor_prototype_frame(self, raw_frame: Dict[str, Any], start_time: float, now_epoch: float) -> Dict[str, Any]:
        """
        Processes physical DC motor prototype telemetry without injecting aero-engine thermodynamics or fake RUL.
        Physical Testbed: 3x18650 Battery -> ACS712 Current Sensor -> L298N Motor Driver -> DC Geared Motor -> ESP32.
        """
        device_id = raw_frame.get("device_id", "AERIS-ESP32-001")
        timestamp = raw_frame.get("timestamp", now_epoch)
        seq = raw_frame.get("sequence_number", raw_frame.get("seq", 0))
        source_mode = raw_frame.get("source", "PHYSICAL_SENSOR")
        is_sim = False

        # Physical measurements (nullable/optional)
        rpm = float(raw_frame["rpm"]) if raw_frame.get("rpm") is not None else None
        current_a = float(raw_frame["current_a"]) if raw_frame.get("current_a") is not None else (float(raw_frame["current"]) if raw_frame.get("current") is not None else None)
        voltage_v = float(raw_frame["voltage_v"]) if raw_frame.get("voltage_v") is not None else (float(raw_frame["voltage"]) if raw_frame.get("voltage") is not None else None)
        
        if raw_frame.get("power_w") is not None:
            power_w = float(raw_frame["power_w"])
        elif raw_frame.get("power") is not None:
            power_w = float(raw_frame["power"])
        elif voltage_v is not None and current_a is not None:
            power_w = round(voltage_v * current_a, 2)
        else:
            power_w = None

        temperature_c = float(raw_frame["temperature_c"]) if raw_frame.get("temperature_c") is not None else (float(raw_frame["temperature"]) if raw_frame.get("temperature") is not None else (float(raw_frame["temp"]) if raw_frame.get("temp") is not None else None))
        vibration = float(raw_frame["vibration"]) if raw_frame.get("vibration") is not None else (float(raw_frame["vibration_mms"]) if raw_frame.get("vibration_mms") is not None else None)
        motor_load_pct = float(raw_frame["motor_load_pct"]) if raw_frame.get("motor_load_pct") is not None else (float(raw_frame["motor_load"]) if raw_frame.get("motor_load") is not None else (float(raw_frame["load"]) if raw_frame.get("load") is not None else None))

        # Electrical / Thermal Limit Checks & Health Estimation
        health_index = 100.0
        anomalies = []
        possible_issue = "Nominal Motor Operation"
        anomaly_score = 0.015

        if voltage_v is not None:
            if voltage_v < 9.0:
                health_index -= 35.0
                anomalies.append(f"Critical Battery Undervoltage: {voltage_v:.2f}V (< 9.0V threshold)")
                possible_issue = "Battery Critical Low Voltage (<9.0V)"
                anomaly_score = max(anomaly_score, 0.85)
            elif voltage_v < 9.9:
                health_index -= 15.0
                anomalies.append(f"Low Battery Pack: {voltage_v:.2f}V (< 9.9V cutoff)")
                possible_issue = "Battery Pack Depleted"
                anomaly_score = max(anomaly_score, 0.45)

        if current_a is not None:
            if current_a > 6.0:
                health_index -= 40.0
                anomalies.append(f"Motor Overcurrent / Jam: {current_a:.2f}A (> 6.0A limit)")
                possible_issue = "Motor Stalled / Overcurrent (>6.0A)"
                anomaly_score = max(anomaly_score, 0.90)
            elif current_a > 4.5:
                health_index -= 15.0
                anomalies.append(f"High Electrical Load: {current_a:.2f}A")
                possible_issue = "High Current Demand"
                anomaly_score = max(anomaly_score, 0.40)

        if temperature_c is not None:
            if temperature_c > 75.0:
                health_index -= 35.0
                anomalies.append(f"Thermal Overheating: {temperature_c:.1f}°C (> 75.0°C limit)")
                possible_issue = "Motor Driver Thermal Stress"
                anomaly_score = max(anomaly_score, 0.80)
            elif temperature_c > 55.0:
                health_index -= 10.0
                anomalies.append(f"Elevated Temperature: {temperature_c:.1f}°C")
                anomaly_score = max(anomaly_score, 0.35)

        if vibration is not None and vibration > 3.5:
            health_index -= 20.0
            anomalies.append(f"Excessive Vibration: {vibration:.2f} mm/s")
            possible_issue = "Motor Mechanical Imbalance"
            anomaly_score = max(anomaly_score, 0.65)

        health_index = max(10.0, min(100.0, health_index))
        anomaly_detected = len(anomalies) > 0 and anomaly_score > 0.40
        status_str = "CRITICAL" if anomaly_score >= 0.75 else ("WARNING" if anomaly_score >= 0.35 else "NORMAL")

        # Primary Evidence (Physically Honest)
        primary_evidence = [
            "Physical DC Motor Prototype Telemetry (3×18650 + ACS712 + L298N + ESP32)",
            f"Power Bus: {voltage_v if voltage_v is not None else '--'}V | Current: {current_a if current_a is not None else '--'}A | Power: {power_w if power_w is not None else '--'}W",
            "Aero-engine Rotax 914 thermodynamic model bypassed for physical motor prototype"
        ]
        if anomalies:
            primary_evidence.extend(anomalies)
        else:
            primary_evidence.append("Operating within electrical and thermal testbed boundaries")

        # Timing
        proc_duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        self._processing_durations.append(proc_duration_ms)
        self._frame_timestamps.append(now_epoch)

        if len(self._frame_timestamps) >= 2:
            time_span = self._frame_timestamps[-1] - self._frame_timestamps[0]
            eff_ingest_rate_hz = round((len(self._frame_timestamps) - 1) / max(0.01, time_span), 1)
        else:
            eff_ingest_rate_hz = 10.0

        avg_proc_ms = round(sum(self._processing_durations) / max(1, len(self._processing_durations)), 1)
        data_age_ms = round(max(0.0, (now_epoch - timestamp) * 1000.0), 1)

        stream_metrics = {
            "ingestion_rate_hz": eff_ingest_rate_hz,
            "processing_rate_hz": round(1000.0 / max(0.1, avg_proc_ms), 1),
            "evaluation_latency_ms": proc_duration_ms,
            "avg_latency_ms": avg_proc_ms,
            "data_age_ms": data_age_ms,
            "dropped_samples": 0,
            "total_samples": len(self._frame_timestamps),
            "source": source_mode,
            "profile": "MOTOR_PROTOTYPE",
            "device_id": device_id,
            "is_simulated": is_sim,
        }

        # Sensor Trust Matrix for physical channels
        sensor_trust = {
            "overall_trust_score": 0.98,
            "aggregate_trust_score": 0.98,
            "channels": {
                "current_a": {"valid": current_a is not None and current_a >= 0, "status": "VALID" if current_a is not None else "NO_DATA", "trust_score": 0.98},
                "voltage_v": {"valid": voltage_v is not None and voltage_v >= 0, "status": "VALID" if voltage_v is not None else "NO_DATA", "trust_score": 0.98},
                "rpm": {"valid": rpm is not None and rpm >= 0, "status": "VALID" if rpm is not None else "NO_DATA", "trust_score": 0.99},
                "temperature_c": {"valid": temperature_c is not None, "status": "VALID" if temperature_c is not None else "NO_DATA", "trust_score": 0.95},
                "vibration": {"valid": vibration is not None and vibration >= 0, "status": "VALID" if vibration is not None else "NO_DATA", "trust_score": 0.96},
            }
        }

        digital_twin_state = {
            "device_id": device_id,
            "profile": "MOTOR_PROTOTYPE",
            "timestamp": timestamp,
            "sequence_number": seq,
            "processing_latency_ms": proc_duration_ms,
            "stream_metrics": stream_metrics,
            "health_state": {
                "value": {
                    "health_index": round(health_index, 1),
                    "normalized_degradation": round((100.0 - health_index) / 100.0, 3),
                    "interpretation": "Physical motor prototype health based on electrical/thermal margins"
                }
            },
            "fault_state": {
                "value": {
                    "fault": possible_issue,
                    "confidence": 0.95 if anomaly_detected else 0.98
                }
            },
            "confidence": {
                "overall": 0.95,
                "sensor_trust": 0.98,
                "ai_certainty": 0.95
            },
            "primary_evidence": primary_evidence,
            "system_state": status_str,
            "alerts": [{"severity": "CRITICAL" if status_str == "CRITICAL" else "WARNING", "text": a, "timestamp": timestamp} for a in anomalies],
        }

        dashboard_view = {
            "device_id": device_id,
            "profile": "MOTOR_PROTOTYPE",
            "rpm": rpm,
            "current_a": current_a,
            "voltage_v": voltage_v,
            "power_w": power_w,
            "temperature_c": temperature_c,
            "temperature": temperature_c,
            "vibration": vibration,
            "motor_load_pct": motor_load_pct,
            "engine_load": motor_load_pct,
            "flight_time_str": "PROTOTYPE-ACTIVE",
            "flight_time_seconds": int(timestamp),
            "engine_health": int(health_index),
            "mission_reliability": int(health_index),
            "status": status_str,
            "source_mode": source_mode,
            "is_simulated": False,
            "anomaly_detected": anomaly_detected,
            "anomaly_score": round(anomaly_score, 3),
            "fault_class": possible_issue,
            "fault_probability": 0.95 if anomaly_detected else 0.05,
            "confidence_pct": 95,
            "sensor_trust_pct": 98,
            "rul_time_str": "MONITORING ONLY",
            "rul_estimate_hours": None,
            "degradation_velocity": 0.0,
            "recommended_decision": "CONTINUE MOTOR TESTBED MONITORING" if not anomaly_detected else "INSPECT MOTOR LOAD & BATTERY",
            "recommended_actions": ["Maintain DC motor operating envelope", "Monitor ACS712 current & bus voltage"] if not anomaly_detected else ["Reduce motor PWM duty cycle", "Inspect 3x18650 battery cell voltages"],
            "primary_evidence": primary_evidence,
            "stream_metrics": stream_metrics,
        }

        self.last_twin_state = digital_twin_state
        self.last_dashboard_view = dashboard_view
        self.state_history.append(digital_twin_state)

        return {
            "twin_state": digital_twin_state,
            "dashboard_view": dashboard_view,
            "residuals": {},
            "expected_physics": {},
            "sensor_trust": sensor_trust,
            "stream_metrics": stream_metrics,
            "alerts": digital_twin_state["alerts"],
            "events": [],
            "primary_evidence": primary_evidence,
            "inference": {
                "possibleIssue": possible_issue,
                "riskLevel": "HIGH" if anomaly_detected else "LOW",
                "confidence": 95,
                "estimatedTimeToFault": "MONITORING ONLY",
                "anomalyScore": round(anomaly_score, 3),
                "recommendedAction": dashboard_view["recommended_actions"],
                "timestamp": timestamp
            }
        }

    def process_telemetry_frame(self, raw_frame: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the AERIS-TWIN intelligence pipeline.
        Branches between MOTOR_PROTOTYPE and AERO_ENGINE profiles.
        """
        start_time = time.perf_counter()
        now_epoch = time.time()

        # Profile detection
        profile = raw_frame.get("profile")
        if profile == "MOTOR_PROTOTYPE" or ("current_a" in raw_frame and "oil_pressure" not in raw_frame and "oilPressure" not in raw_frame):
            return self.process_motor_prototype_frame(raw_frame, start_time, now_epoch)
        
        # Stage 1: Telemetry Ingestion & Link Health
        telemetry = self.gateway.ingest_packet(raw_frame)
        engine_id = telemetry.get("engine_id", "UAV-ENG-ROT-914-01")
        mission_id = telemetry.get("mission_id", "MSN-2026-SURV-082")
        timestamp = telemetry.get("timestamp", now_epoch)
        seq = telemetry.get("sequence_number", 0)
        source_mode = telemetry.get("source", "SIMULATION")
        is_sim = telemetry.get("is_simulated", source_mode == "SIMULATION")
        
        # Stage 2: Data Validation & Sanitization
        rpm = float(telemetry.get("rpm", 4215.0))
        cht = float(telemetry.get("temperature", 78.4))
        oil_p = float(telemetry.get("oilPressure", 4.3))
        vib = float(telemetry.get("vibration", 1.6))
        fuel = float(telemetry.get("fuelFlow", 5.2))
        load = float(telemetry.get("engineLoad", 62.0))
        
        # Stage 3: Sensor Trust Evaluation & Quality Validation
        sensor_trust = self.sensor_trust_engine.evaluate_sensors(telemetry)
        
        # Stage 4: Physics Model Expected State
        expected_physics = self.physics_model.compute_expected_state(telemetry)
        
        # Stage 5: Residual Calculation & Rolling Statistics
        residuals = self.residual_engine.compute_residuals(telemetry, expected_physics)
        
        # Stage 6: Anomaly Detection (Isolation Forest & Multi-variate Distance)
        anomaly_result = self.anomaly_detector.detect(residuals, telemetry)
        
        # Stage 7: Fault Classification (Multi-Class Physics Signature)
        fault_result = self.fault_classifier.classify(residuals, anomaly_result, telemetry)
        
        # Stage 8: Twin Consensus Matrix
        consensus_result = self.consensus_engine.evaluate_consensus(
            physics_residuals=residuals,
            sensor_trust=sensor_trust,
            anomaly_result=anomaly_result,
            fault_result=fault_result
        )
        
        # Stage 9: Degradation Estimation & Velocity
        degradation_result = self.degradation_model.compute_degradation(
            residuals=residuals,
            telemetry=telemetry,
            sensor_trust=sensor_trust
        )
        
        # Stage 10: Prognostics & Remaining Useful Life (RUL) with Bounded Uncertainty
        rul_result = self.rul_engine.estimate_rul(
            degradation_data=degradation_result,
            sensor_trust=sensor_trust,
            telemetry=telemetry
        )
        
        # Stage 11: Mission Risk Evaluation
        risk_result = self.risk_engine.evaluate_risk(
            degradation_data=degradation_result,
            fault_data=fault_result,
            rul_data=rul_result,
            telemetry=telemetry,
            planned_duration_hours=6.0
        )
        
        # Stage 12: Mission Decision Recommendation
        decision_result = self.decision_engine.recommend(
            health_data=degradation_result,
            fault_data=fault_result,
            rul_data=rul_result,
            risk_data=risk_result,
            consensus_data=consensus_result
        )
        
        # Stage 13: Alert Debouncing & State Transition Evaluation
        alert_summary = self.alert_engine.evaluate_state_transitions(
            health_index=degradation_result["health_index"],
            anomaly_result=anomaly_result,
            fault_result=fault_result,
            risk_result=risk_result,
            sensor_trust=sensor_trust,
            residuals=residuals,
            telemetry=telemetry,
        )

        # Stage 14: Compile Traceable Evidence & Explanations
        all_evidence = []
        all_evidence.extend(anomaly_result.get("evidence", []))
        all_evidence.extend(fault_result.get("evidence", []))
        all_evidence.extend(consensus_result.get("evidence", []))
        all_evidence.extend(degradation_result.get("evidence", []))
        all_evidence.extend(rul_result.get("evidence", []))
        all_evidence.extend(decision_result.get("evidence", []))

        # Build Primary Evidence Bullet Points (Formatted for UI)
        primary_evidence = []
        if fault_result.get("fault") != "NOMINAL":
            primary_evidence.append(f"Primary fault classification: {fault_result['fault'].replace('_', ' ')} (Probability: {int(fault_result['probability']*100)}%)")
        else:
            primary_evidence.append("Operating within nominal thermodynamic and kinematic envelope")

        vib_res = residuals.get("vibration", {}).get("normalized_residual", 0.0)
        if abs(vib_res) > 1.5:
            primary_evidence.append(f"Vibration residual deviation: {vib_res:+.2f}σ relative to baseline")

        cht_res = residuals.get("temperature", {}).get("normalized_residual", 0.0)
        if abs(cht_res) > 1.5:
            primary_evidence.append(f"Cylinder head thermal deviation: {cht_res:+.2f}σ")

        oil_res = residuals.get("oilPressure", {}).get("normalized_residual", 0.0)
        if abs(oil_res) > 1.5:
            primary_evidence.append(f"Oil lubrication pressure deviation: {oil_res:+.2f}σ")

        if anomaly_result.get("anomaly", False):
            primary_evidence.append(f"Isolation Forest multi-variate score: {anomaly_result['score']:.3f} (Anomaly flagged)")
        else:
            primary_evidence.append(f"Isolation Forest score: {anomaly_result['score']:.3f} (Within 95% nominal cluster)")

        primary_evidence.append(f"Sensor trust score: {int(sensor_trust['aggregate_trust_score']*100)}% (Transducer quality check)")
        primary_evidence.append(f"Digital twin consensus confidence: {int(consensus_result['overall_confidence']*100)}%")

        # Rate & Timing metrics
        proc_duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        self._processing_durations.append(proc_duration_ms)
        self._frame_timestamps.append(now_epoch)

        # Ingestion rate calculation (Hz)
        if len(self._frame_timestamps) >= 2:
            time_span = self._frame_timestamps[-1] - self._frame_timestamps[0]
            eff_ingest_rate_hz = round((len(self._frame_timestamps) - 1) / max(0.01, time_span), 1)
        else:
            eff_ingest_rate_hz = 10.0

        avg_proc_ms = round(sum(self._processing_durations) / max(1, len(self._processing_durations)), 1)
        data_age_ms = round(max(0.0, (now_epoch - timestamp) * 1000.0), 1)

        stream_metrics = {
            "ingestion_rate_hz": eff_ingest_rate_hz,
            "processing_rate_hz": round(1000.0 / max(0.1, avg_proc_ms), 1),
            "evaluation_latency_ms": proc_duration_ms,
            "avg_latency_ms": avg_proc_ms,
            "data_age_ms": data_age_ms,
            "dropped_samples": self.gateway.total_packets_dropped,
            "total_samples": self.gateway.total_packets_received,
            "source": source_mode,
            "is_simulated": is_sim,
        }

        # Stage 15: Construct Authoritative DigitalTwinState
        digital_twin_state = {
            "engine_id": engine_id,
            "uav_id": telemetry.get("uav_id", "MALE-UAV-TAPAS-04"),
            "mission_id": mission_id,
            "timestamp": timestamp,
            "sequence_number": seq,
            "processing_latency_ms": proc_duration_ms,
            "stream_metrics": stream_metrics,
            "operating_state": {
                "value": {
                    "rpm": rpm, "throttle": telemetry.get("throttle", 68.0),
                    "map_kpa": telemetry.get("map_kpa", expected_physics["expected_map_kpa"]),
                    "engine_load": load, "power_kw": expected_physics["estimated_power_kw"],
                    "flight_phase": telemetry.get("flight_phase", "CRUISE"),
                    "altitude_ft": telemetry.get("altitude_ft", 15000.0)
                },
                "confidence": 0.96, "source": "PHYSICS_ESTIMATOR", "timestamp": timestamp
            },
            "thermal_state": {
                "value": {
                    "cht_c": cht, "egt_c": telemetry.get("egt_c", 645.0),
                    "oil_temp_c": telemetry.get("oil_temperature_c", 82.1),
                    "expected_cht_c": expected_physics["expected_cht_c"],
                    "cht_residual_sigma": residuals.get("temperature", {}).get("normalized_residual", 0.0)
                },
                "confidence": 0.94, "source": "THERMAL_MODEL", "timestamp": timestamp
            },
            "mechanical_state": {
                "value": {
                    "vibration_mms": vib, "expected_vibration_mms": expected_physics["expected_vibration_mms"],
                    "vibration_residual_sigma": residuals.get("vibration", {}).get("normalized_residual", 0.0),
                    "vibration_slope": residuals.get("vibration", {}).get("residual_slope", 0.0)
                },
                "confidence": 0.93, "source": "VIBRATION_MONITOR", "timestamp": timestamp
            },
            "combustion_state": {
                "value": {
                    "fuel_flow": fuel, "expected_fuel_flow": expected_physics["expected_fuel_flow"],
                    "bsfc_g_kwh": round((fuel * 0.72 * 1000.0) / max(1.0, expected_physics["estimated_power_kw"]), 1)
                },
                "confidence": 0.91, "source": "COMBUSTION_ESTIMATOR", "timestamp": timestamp
            },
            "lubrication_state": {
                "value": {
                    "oil_pressure_bar": oil_p, "expected_oil_pressure_bar": expected_physics["expected_oil_pressure_bar"],
                    "oil_residual_sigma": residuals.get("oilPressure", {}).get("normalized_residual", 0.0)
                },
                "confidence": 0.92, "source": "HYDRODYNAMIC_MODEL", "timestamp": timestamp
            },
            "degradation_state": {
                "value": degradation_result,
                "confidence": degradation_result["confidence"], "source": "DEGRADATION_MODEL", "timestamp": timestamp
            },
            "sensor_state": {
                "value": sensor_trust,
                "confidence": sensor_trust["aggregate_trust_score"], "source": "SENSOR_TRUST_ENGINE", "timestamp": timestamp
            },
            "health_state": {
                "value": {
                    "health_index": degradation_result["health_index"],
                    "normalized_degradation": degradation_result["normalized_degradation"],
                    "interpretation": degradation_result["interpretation"]
                },
                "confidence": degradation_result["confidence"], "source": "HEALTH_INDEX_ENGINE", "timestamp": timestamp
            },
            "fault_state": {
                "value": fault_result,
                "confidence": fault_result["confidence"], "source": "FAULT_CLASSIFIER", "timestamp": timestamp
            },
            "rul_state": {
                "value": rul_result,
                "confidence": rul_result["confidence"], "source": "RUL_PROGNOSTICS_ENGINE", "timestamp": timestamp
            },
            "confidence": {
                "overall": consensus_result["overall_confidence"],
                "sensor_trust": sensor_trust["aggregate_trust_score"],
                "physics_agreement": consensus_result["physics_evidence"]["confidence"],
                "ai_certainty": fault_result["confidence"]
            },
            "consensus": consensus_result,
            "mission_risk": risk_result,
            "decision": decision_result,
            "alerts": alert_summary["alerts"],
            "system_state": alert_summary["system_state"],
            "evidence": all_evidence,
            "primary_evidence": primary_evidence
        }
        
        # Stage 16: Construct Presentation DashboardView for Frontend
        health_num = int(degradation_result["health_index"])
        status_str = alert_summary["system_state"]
        
        flight_sec = int(telemetry.get("flight_time_seconds", 9918))
        h = flight_sec // 3600
        m = (flight_sec % 3600) // 60
        s = flight_sec % 60
        flight_str = f"{h:02d}:{m:02d}:{s:02d}"
        
        dashboard_view = {
            "engine_id": engine_id,
            "rpm": rpm,
            "temperature": cht,
            "oil_pressure": oil_p,
            "vibration": vib,
            "fuel_flow": fuel,
            "engine_load": load,
            "flight_time_str": flight_str,
            "flight_time_seconds": flight_sec,
            
            # Health & Reliability
            "engine_health": health_num,
            "mission_reliability": risk_result["mission_reliability_pct"],
            "status": status_str,
            "active_scenario": telemetry.get("activeScenario", "cruise"),
            "source_mode": source_mode,
            "is_simulated": is_sim,
            
            # Diagnostics & Prognostics
            "anomaly_detected": anomaly_result["anomaly"],
            "anomaly_score": anomaly_result["score"],
            "fault_class": fault_result["fault"],
            "fault_probability": fault_result["probability"],
            "confidence_pct": int(consensus_result["overall_confidence"] * 100.0),
            "sensor_trust_pct": int(sensor_trust["aggregate_trust_score"] * 100.0),
            "rul_time_str": rul_result["rul_time_str"],
            "rul_estimate_hours": rul_result["rul_estimate_hours"],
            "rul_lower_bound_hours": rul_result["lower_bound_hours"],
            "rul_upper_bound_hours": rul_result["upper_bound_hours"],
            "degradation_velocity": degradation_result["degradation_velocity"],
            "degradation_velocity_trend": degradation_result["velocity_trend"],
            "mission_risk_index": risk_result["risk_index"],
            "consensus_status": consensus_result["consensus_status"],
            "recommended_decision": decision_result["decision"],
            "recommended_actions": decision_result["recommended_actions"],
            "alerts": alert_summary["alerts"],
            "recent_events": alert_summary["recent_events"],
            "primary_evidence": primary_evidence,
            "stream_metrics": stream_metrics,
            "link_status": self.gateway.get_link_status()
        }
        
        # Log Telemetry & Twin Execution to SQLite
        try:
            log_telemetry_packet(telemetry)
            log_twin_execution(engine_id, digital_twin_state, all_evidence)
        except Exception:
            pass
        
        self.last_twin_state = digital_twin_state
        self.last_dashboard_view = dashboard_view
        
        self.state_history.append(digital_twin_state)
        
        return {
            "twin_state": digital_twin_state,
            "dashboard_view": dashboard_view,
            "residuals": residuals,
            "expected_physics": expected_physics,
            "sensor_trust": sensor_trust,
            "stream_metrics": stream_metrics,
            "alerts": alert_summary["alerts"],
            "events": alert_summary["recent_events"],
            "primary_evidence": primary_evidence,
            "inference": {
                "possibleIssue": fault_result["fault"].replace("_", " ").title(),
                "riskLevel": risk_result["risk_level"],
                "confidence": int(consensus_result["overall_confidence"] * 100),
                "estimatedTimeToFault": rul_result["rul_time_str"],
                "anomalyScore": anomaly_result["score"],
                "probabilities": fault_result["probabilities"],
                "recommendedAction": decision_result["recommended_actions"],
                "consensus": consensus_result["consensus_status"],
                "timestamp": timestamp
            }
        }
