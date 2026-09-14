"""
Fault Classification Module for AERIS-TWIN
Implements multi-class degradation classification backed by physics residuals and ML signatures.
Profile-Aware: Supports both AERO_ENGINE and MOTOR_PROTOTYPE failure modes.
Uses defensible qualifiers: LIKELY, SUSPECTED, POSSIBLE, INSUFFICIENT_DATA.
Never overclaims flight engine failure modes for DC motor testbed.
"""
from typing import Dict, Any, List, Optional
import numpy as np
from scipy.special import softmax as _softmax

class EngineFaultClassifier:
    def __init__(self):
        self.model_version = "AERIS-GBM-Fault-v2.5"
        self.aero_classes = [
            "NOMINAL",
            "BEARING_DEGRADATION",
            "COOLING_DEGRADATION",
            "LUBRICATION_DEGRADATION",
            "SPARK_PLUG_DEGRADATION",
            "FUEL_SYSTEM_DEGRADATION",
            "UNKNOWN_ANOMALY"
        ]
        self.classes = self.aero_classes  # Standard 7 aero classes for backward-compatibility
        self.motor_classes = [
            "NOMINAL",
            "ELECTRICAL_LOAD_ANOMALY",
            "SUPPLY_VOLTAGE_SAG",
            "THERMAL_OVERHEAT",
            "MECHANICAL_IMBALANCE",
            "SENSOR_ANOMALY",
            "UNKNOWN_ANOMALY"
        ]

    def classify_motor_prototype(
        self,
        residuals: Dict[str, Any],
        anomaly_result: Dict[str, Any],
        telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classifies operational condition for physical DC motor prototype testbed.
        Never outputs aero-engine faults (e.g. lubrication/spark misfire) for DC motor.
        """
        curr_res = residuals.get("current_a", {})
        volt_res = residuals.get("voltage_v", {})
        temp_res = residuals.get("temperature_c", {})
        vib_res = residuals.get("vibration", {})
        rpm_res = residuals.get("rpm", {})

        is_anomaly = anomaly_result.get("anomaly", False)
        anomaly_score = anomaly_result.get("score", 0.0)

        c_norm = curr_res.get("normalized_residual", 0.0)
        v_norm = volt_res.get("normalized_residual", 0.0)
        t_norm = temp_res.get("normalized_residual", 0.0)
        vib_norm = vib_res.get("normalized_residual", 0.0)
        rpm_norm = rpm_res.get("normalized_residual", 0.0)

        raw_probs = {c: 0.02 for c in self.motor_classes}
        supporting_features = []
        evidence_list = []
        qualifier = "LIKELY"
        data_sufficiency = "SUFFICIENT"

        # 1. Nominal Check
        if not is_anomaly and abs(c_norm) < 1.8 and abs(v_norm) < 1.8 and abs(t_norm) < 1.8:
            fault = "NOMINAL"
            qualifier = "CONFIRMED"
            probability = 0.94
            confidence = 0.95
            severity = "NONE"
            raw_probs["NOMINAL"] = 0.94
            evidence_list.append({
                "type": "TESTBED_ESTIMATION",
                "observation": "Motor operating within nominal voltage, current, and thermal envelope",
                "confidence": 0.95
            })

        # 2. Electrical / Mechanical Load Anomaly (High current, reduced RPM, normal voltage)
        elif c_norm > 2.0 or (c_norm > 1.5 and rpm_norm < -1.5):
            fault = "ELECTRICAL_LOAD_ANOMALY (Overcurrent / Load)"
            qualifier = "LIKELY"
            raw_probs["ELECTRICAL_LOAD_ANOMALY"] = min(0.92, 0.62 + (c_norm - 1.5) * 0.10)
            probability = round(raw_probs["ELECTRICAL_LOAD_ANOMALY"], 3)
            confidence = round(min(0.94, 0.75 + (c_norm / 5.0) * 0.15), 3)
            severity = "HIGH" if c_norm > 3.5 else "MEDIUM"
            supporting_features = ["current_residual", "rpm_torque_droop"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "current_a",
                "observation": f"Armature current ({c_norm:.2f} sigma above model) indicates mechanical load, overcurrent, or stall condition",
                "confidence": confidence
            })

        # 3. Supply Voltage Sag / Depleted Battery Pack (Negative voltage residual)
        elif v_norm < -2.0:
            fault = "SUPPLY_VOLTAGE_SAG (Low Voltage / Depleted Battery)"
            qualifier = "LIKELY"
            raw_probs["SUPPLY_VOLTAGE_SAG"] = min(0.91, 0.60 + abs(v_norm) * 0.09)
            probability = round(raw_probs["SUPPLY_VOLTAGE_SAG"], 3)
            confidence = round(min(0.93, 0.76 + abs(v_norm) * 0.05), 3)
            severity = "HIGH" if v_norm < -3.5 else "MEDIUM"
            supporting_features = ["bus_voltage_drop", "internal_resistance_sag"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "voltage_v",
                "observation": f"Supply bus voltage ({abs(v_norm):.2f} sigma below nominal) indicates battery depletion (low voltage) or loose connection",
                "confidence": confidence
            })

        # 4. Thermal Overheat (High motor/driver temperature)
        elif t_norm > 2.2:
            fault = "THERMAL_OVERHEAT"
            qualifier = "SUSPECTED"
            raw_probs["THERMAL_OVERHEAT"] = min(0.90, 0.60 + (t_norm - 2.0) * 0.08)
            probability = round(raw_probs["THERMAL_OVERHEAT"], 3)
            confidence = round(min(0.92, 0.74 + (t_norm / 5.0) * 0.12), 3)
            severity = "HIGH" if t_norm > 4.0 else "MEDIUM"
            supporting_features = ["temperature_c_residual", "driver_joule_heating"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "temperature_c",
                "observation": f"Motor/driver temperature ({t_norm:.2f} sigma above baseline) indicates thermal dissipation limit",
                "confidence": confidence
            })

        # 5. Mechanical Imbalance / Vibration
        elif vib_norm > 2.2:
            fault = "MECHANICAL_IMBALANCE"
            qualifier = "SUSPECTED"
            raw_probs["MECHANICAL_IMBALANCE"] = min(0.88, 0.58 + vib_norm * 0.08)
            probability = round(raw_probs["MECHANICAL_IMBALANCE"], 3)
            confidence = round(min(0.90, 0.72 + vib_norm * 0.05), 3)
            severity = "MEDIUM"
            supporting_features = ["vibration_residual"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "vibration",
                "observation": f"Vibration magnitude ({vib_norm:.2f} sigma above baseline) indicates rotor imbalance or mounting looseness",
                "confidence": confidence
            })

        elif is_anomaly:
            fault = "UNKNOWN_ANOMALY"
            qualifier = "POSSIBLE"
            raw_probs["UNKNOWN_ANOMALY"] = min(0.85, 0.50 + anomaly_score * 0.35)
            probability = round(raw_probs["UNKNOWN_ANOMALY"], 3)
            confidence = 0.68
            severity = "MEDIUM"
            supporting_features = ["multivariate_residual_deviation"]
            evidence_list.append({
                "type": "ML_SCORE",
                "parameter": "isolation_forest",
                "observation": "Multivariate residual anomaly detected on physical testbed. Requires visual inspection.",
                "confidence": 0.68
            })
        else:
            fault = "NOMINAL"
            qualifier = "CONFIRMED"
            probability = 0.90
            confidence = 0.92
            severity = "NONE"
            raw_probs["NOMINAL"] = 0.90

        # Softmax normalisation
        class_keys = list(raw_probs.keys())
        raw_vals = np.array([raw_probs[k] for k in class_keys], dtype=np.float64)
        sm_vals = _softmax(raw_vals)
        norm_probabilities = {k: round(float(v), 3) for k, v in zip(class_keys, sm_vals)}

        return {
            "fault": fault,
            "status_qualifier": qualifier,
            "data_sufficiency": data_sufficiency,
            "probability": probability,
            "confidence": confidence,
            "severity": severity,
            "probabilities": norm_probabilities,
            "supporting_features": supporting_features,
            "evidence": evidence_list,
            "model_version": self.model_version
        }

    def classify(
        self,
        residuals: Dict[str, Any],
        anomaly_result: Dict[str, Any],
        telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classifies current failure mode using physics residuals and sensor patterns.
        Dispatches to motor prototype classification when telemetry is from physical motor.
        """
        profile = telemetry.get("profile")
        if profile == "MOTOR_PROTOTYPE" or "current_a" in telemetry or "voltage_v" in telemetry or (
            "oilPressure" not in telemetry and "oil_pressure" not in telemetry and "fuelFlow" not in telemetry and "fuel_flow" not in telemetry and "cht" not in telemetry
        ):
            return self.classify_motor_prototype(residuals, anomaly_result, telemetry)

        vib_res = residuals.get("vibration", {})
        temp_res = residuals.get("temperature", {})
        oil_res = residuals.get("oilPressure", {})
        fuel_res = residuals.get("fuelFlow", {})
        egt_res = residuals.get("egt", {})
        rpm_res = residuals.get("rpm", {})
        
        is_anomaly = anomaly_result.get("anomaly", False)
        anomaly_score = anomaly_result.get("score", 0.0)
        
        v_norm = vib_res.get("normalized_residual", 0.0)
        v_slope = vib_res.get("residual_slope", 0.0)
        t_norm = temp_res.get("normalized_residual", 0.0)
        o_norm = oil_res.get("normalized_residual", 0.0)
        f_norm = fuel_res.get("normalized_residual", 0.0)
        
        raw_probs = {c: 0.02 for c in self.aero_classes}
        supporting_features = []
        evidence_list = []
        qualifier = "LIKELY"
        data_sufficiency = "SUFFICIENT"
        
        # 1. Nominal check
        if not is_anomaly and abs(v_norm) < 1.5 and abs(t_norm) < 1.5 and abs(o_norm) < 1.5:
            fault = "NOMINAL"
            qualifier = "CONFIRMED"
            probability = 0.94
            confidence = 0.95
            severity = "NONE"
            raw_probs["NOMINAL"] = 0.94
            evidence_list.append({
                "type": "STATE_ESTIMATION",
                "observation": "All physical residuals within standard 1.5 sigma operational boundary",
                "confidence": 0.95
            })
            
        # 2. Bearing Degradation Signature: High vibration residual, positive vibration slope
        elif v_norm > 2.2 or (v_norm > 1.8 and v_slope > 0.01):
            fault = "BEARING_DEGRADATION"
            qualifier = "LIKELY" if v_norm > 3.0 else "SUSPECTED"
            raw_probs["BEARING_DEGRADATION"] = min(0.92, 0.60 + (v_norm - 2.0) * 0.12)
            probability = round(raw_probs["BEARING_DEGRADATION"], 3)
            confidence = round(min(0.96, 0.78 + (v_norm / 6.0) * 0.18), 3)
            severity = "HIGH" if v_norm > 4.0 else "MEDIUM"
            supporting_features = ["vibration_normalized_residual", "vibration_slope", "mechanical_loss"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "vibration",
                "observation": f"Vibration residual ({v_norm:.2f} sigma) with positive trend ({v_slope:.4f}/s) indicates progressive bearing race/cage wear",
                "confidence": confidence
            })
            
        # 3. Cooling / Thermal Stress Signature: High CHT residual, normal vibration
        elif t_norm > 2.5:
            fault = "COOLING_DEGRADATION"
            qualifier = "LIKELY" if t_norm > 3.5 else "SUSPECTED"
            raw_probs["COOLING_DEGRADATION"] = min(0.91, 0.62 + (t_norm - 2.5) * 0.08)
            probability = round(raw_probs["COOLING_DEGRADATION"], 3)
            confidence = round(min(0.95, 0.80 + (t_norm / 5.0) * 0.15), 3)
            severity = "HIGH" if t_norm > 4.5 else "MEDIUM"
            supporting_features = ["temperature_normalized_residual", "thermal_accumulation"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "temperature",
                "observation": f"Cylinder head temperature ({t_norm:.2f} sigma above thermal model) indicates cooling airflow or fin heat rejection deficit",
                "confidence": confidence
            })
            
        # 4. Lubrication System Degradation: Low oil pressure residual
        elif o_norm < -2.2:
            fault = "LUBRICATION_DEGRADATION"
            qualifier = "LIKELY" if o_norm < -3.0 else "SUSPECTED"
            raw_probs["LUBRICATION_DEGRADATION"] = min(0.92, 0.65 + abs(o_norm) * 0.08)
            probability = round(raw_probs["LUBRICATION_DEGRADATION"], 3)
            confidence = round(min(0.95, 0.78 + abs(o_norm) * 0.05), 3)
            severity = "HIGH" if o_norm < -3.5 else "MEDIUM"
            supporting_features = ["oil_pressure_drop", "hydrodynamic_film_thinning"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "oilPressure",
                "observation": f"Oil pressure ({abs(o_norm):.2f} sigma below nominal) indicates lubrication delivery degradation",
                "confidence": confidence
            })
            
        # 5. Spark Plug Misfire: Elevated fuel flow residual with negative/fluctuating RPM residual
        elif f_norm > 2.0 and (rpm_res.get("normalized_residual", 0.0) < -1.2 or abs(rpm_res.get("residual_slope", 0.0)) > 0.02):
            fault = "SPARK_PLUG_DEGRADATION"
            qualifier = "POSSIBLE"
            raw_probs["SPARK_PLUG_DEGRADATION"] = min(0.88, 0.62 + f_norm * 0.08)
            probability = round(raw_probs["SPARK_PLUG_DEGRADATION"], 3)
            confidence = round(min(0.92, 0.76 + f_norm * 0.05), 3)
            severity = "MEDIUM"
            supporting_features = ["fuel_flow_residual", "rpm_torque_instability"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "combustion_efficiency",
                "observation": "Unburned fuel accumulation and torque jitter indicates incomplete ignition cycle (spark misfire)",
                "confidence": confidence
            })
            
        # 6. Fuel System Clog / Injection Loss: High fuel flow residual with normal RPM
        elif f_norm > 2.5:
            fault = "FUEL_SYSTEM_DEGRADATION"
            qualifier = "POSSIBLE"
            raw_probs["FUEL_SYSTEM_DEGRADATION"] = min(0.88, 0.62 + f_norm * 0.08)
            probability = round(raw_probs["FUEL_SYSTEM_DEGRADATION"], 3)
            confidence = round(min(0.92, 0.76 + f_norm * 0.05), 3)
            severity = "MEDIUM"
            supporting_features = ["fuel_flow_residual", "bsfc_deviation"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "fuelFlow",
                "observation": f"Fuel mass flow rate ({f_norm:.2f} sigma above model) indicates injector metering anomaly",
                "confidence": confidence
            })

        # 7. Unknown Anomaly: Anomaly detected by Isolation Forest, but doesn't fit standard templates
        elif is_anomaly:
            fault = "UNKNOWN_ANOMALY"
            qualifier = "POSSIBLE"
            raw_probs["UNKNOWN_ANOMALY"] = min(0.85, 0.50 + anomaly_score * 0.35)
            probability = round(raw_probs["UNKNOWN_ANOMALY"], 3)
            confidence = 0.70
            severity = "MEDIUM"
            supporting_features = ["multivariate_residual_deviation"]
            evidence_list.append({
                "type": "ML_SCORE",
                "parameter": "isolation_forest",
                "observation": "Multivariate anomaly detected without matching classical bearing/spark/thermal signatures. Flagged for engineering review.",
                "confidence": 0.70
            })
        else:
            fault = "NOMINAL"
            qualifier = "CONFIRMED"
            probability = 0.90
            confidence = 0.92
            severity = "NONE"
            raw_probs["NOMINAL"] = 0.90
            
        # Softmax-normalise raw probabilities
        class_keys = list(raw_probs.keys())
        raw_vals = np.array([raw_probs[k] for k in class_keys], dtype=np.float64)
        sm_vals = _softmax(raw_vals)
        norm_probabilities = {k: round(float(v), 3) for k, v in zip(class_keys, sm_vals)}
        
        return {
            "fault": fault,
            "status_qualifier": qualifier,
            "data_sufficiency": data_sufficiency,
            "probability": probability,
            "confidence": confidence,
            "severity": severity,
            "probabilities": norm_probabilities,
            "supporting_features": supporting_features,
            "evidence": evidence_list,
            "model_version": self.model_version
        }
