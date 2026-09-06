"""
Fault Classification Module for AERIS-TWIN
Implements multi-class degradation classification backed by physics residuals and ML signatures.
Handles UNKNOWN fault scenarios defensibly when an anomaly occurs without known matching fault signatures.
"""
from typing import Dict, Any, List
import numpy as np
from scipy.special import softmax as _softmax

class EngineFaultClassifier:
    def __init__(self):
        self.model_version = "AERIS-GBM-Fault-v2.4"
        self.classes = [
            "NOMINAL",
            "BEARING_DEGRADATION",
            "COOLING_DEGRADATION",
            "LUBRICATION_DEGRADATION",
            "SPARK_PLUG_DEGRADATION",
            "FUEL_SYSTEM_DEGRADATION",
            "UNKNOWN_ANOMALY"
        ]

    def classify(self, residuals: Dict[str, Any], anomaly_result: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies current engine failure mode using physics residuals and sensor patterns.
        """
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
        
        raw_probs = {c: 0.02 for c in self.classes}
        supporting_features = []
        evidence_list = []
        
        # 1. Nominal check
        if not is_anomaly and abs(v_norm) < 1.5 and abs(t_norm) < 1.5 and abs(o_norm) < 1.5:
            fault = "NOMINAL"
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
            raw_probs["BEARING_DEGRADATION"] = min(0.92, 0.60 + (v_norm - 2.0) * 0.12)
            probability = round(raw_probs["BEARING_DEGRADATION"], 3)
            confidence = round(min(0.96, 0.78 + (v_norm / 6.0) * 0.18), 3)
            severity = "HIGH" if v_norm > 4.0 else "MEDIUM"
            supporting_features = ["vibration_normalized_residual", "vibration_slope", "mechanical_loss"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "vibration",
                "observation": f"Vibration residual ({v_norm} sigma) with positive trend ({v_slope:.4f}/s) indicates progressive bearing race/cage wear",
                "confidence": confidence
            })
            
        # 3. Cooling / Thermal Stress Signature: High CHT residual, normal vibration
        elif t_norm > 2.5:
            fault = "COOLING_DEGRADATION"
            raw_probs["COOLING_DEGRADATION"] = min(0.91, 0.62 + (t_norm - 2.5) * 0.08)
            probability = round(raw_probs["COOLING_DEGRADATION"], 3)
            confidence = round(min(0.95, 0.80 + (t_norm / 5.0) * 0.15), 3)
            severity = "HIGH" if t_norm > 4.5 else "MEDIUM"
            supporting_features = ["temperature_normalized_residual", "thermal_accumulation"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "temperature",
                "observation": f"Cylinder head temperature ({t_norm} sigma above thermal model) indicates cooling airflow or fin heat rejection deficit",
                "confidence": confidence
            })
            
        # 4. Lubrication System Degradation: Low oil pressure residual
        elif o_norm < -2.2:
            fault = "LUBRICATION_DEGRADATION"
            raw_probs["LUBRICATION_DEGRADATION"] = min(0.92, 0.65 + abs(o_norm) * 0.08)
            probability = round(raw_probs["LUBRICATION_DEGRADATION"], 3)
            confidence = round(min(0.95, 0.78 + abs(o_norm) * 0.05), 3)
            severity = "HIGH" if o_norm < -3.5 else "MEDIUM"
            supporting_features = ["oil_pressure_drop", "hydrodynamic_film_thinning"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "oilPressure",
                "observation": f"Oil pressure ({abs(o_norm)} sigma below nominal) indicates lubrication delivery degradation",
                "confidence": confidence
            })
            
        # 5. Spark Plug Misfire: Elevated fuel flow residual with negative/fluctuating RPM residual
        elif f_norm > 2.0 and (rpm_res.get("normalized_residual", 0.0) < -1.2 or abs(rpm_res.get("residual_slope", 0.0)) > 0.02):
            fault = "SPARK_PLUG_DEGRADATION"
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
            raw_probs["FUEL_SYSTEM_DEGRADATION"] = min(0.88, 0.62 + f_norm * 0.08)
            probability = round(raw_probs["FUEL_SYSTEM_DEGRADATION"], 3)
            confidence = round(min(0.92, 0.76 + f_norm * 0.05), 3)
            severity = "MEDIUM"
            supporting_features = ["fuel_flow_residual", "bsfc_deviation"]
            evidence_list.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "fuelFlow",
                "observation": f"Fuel mass flow rate ({f_norm} sigma above model) indicates injector metering anomaly",
                "confidence": confidence
            })

        # 7. Unknown Anomaly: Anomaly detected by Isolation Forest, but doesn't fit standard templates
        elif is_anomaly:
            fault = "UNKNOWN_ANOMALY"
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
            probability = 0.90
            confidence = 0.92
            severity = "NONE"
            raw_probs["NOMINAL"] = 0.90
            
        # Softmax-normalise raw probabilities (numerically stable, sums to 1.0)
        class_keys = list(raw_probs.keys())
        raw_vals = np.array([raw_probs[k] for k in class_keys], dtype=np.float64)
        sm_vals = _softmax(raw_vals)
        norm_probabilities = {k: round(float(v), 3) for k, v in zip(class_keys, sm_vals)}
        
        return {
            "fault": fault,
            "probability": probability,
            "confidence": confidence,
            "severity": severity,
            "probabilities": norm_probabilities,
            "supporting_features": supporting_features,
            "evidence": evidence_list,
            "model_version": self.model_version
        }
