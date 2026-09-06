"""
Mission Risk Engine for AERIS-TWIN
Differentiates Engine Health (current physical condition) from Mission Risk (probabilistic mission abort risk).
Calculates MissionRisk = f(engine_state, degradation, fault_probability, RUL, mission_profile).
"""
from typing import Dict, Any, List
import numpy as np

class MissionRiskEngine:
    def __init__(self):
        pass

    def evaluate_risk(
        self,
        degradation_data: Dict[str, Any],
        fault_data: Dict[str, Any],
        rul_data: Dict[str, Any],
        telemetry: Dict[str, Any],
        planned_duration_hours: float = 6.0
    ) -> Dict[str, Any]:
        """
        Calculates mission risk index [0.0 - 1.0] and completion probability.
        """
        current_d = float(degradation_data.get("normalized_degradation", 0.05))
        d_velocity = float(degradation_data.get("degradation_velocity", 0.002))
        fault_prob = float(fault_data.get("probability", 0.05))
        fault_class = fault_data.get("fault", "NOMINAL")
        rul_hours = float(rul_data.get("rul_estimate_hours", 1200.0))
        rul_lower = float(rul_data.get("lower_bound_hours", 1000.0))
        
        # Flight environmental severity factors
        alt_ft = float(telemetry.get("altitude_ft", 15000.0))
        ambient_temp = float(telemetry.get("ambient_temperature_c", -14.5))
        engine_load = float(telemetry.get("engine_load", 62.0))
        
        # 1. RUL-to-Mission Margin Risk
        # If RUL lower bound is close to or less than planned mission duration
        if rul_lower < planned_duration_hours:
            rul_risk = 1.0
        elif rul_hours < (planned_duration_hours * 1.5):
            rul_risk = 0.75
        elif rul_hours < (planned_duration_hours * 3.0):
            rul_risk = 0.40
        else:
            rul_risk = 0.05
            
        # 2. Fault Severity Weight
        fault_weights = {
            "NOMINAL": 0.05,
            "SPARK_PLUG_DEGRADATION": 0.45,
            "COOLING_DEGRADATION": 0.65,
            "BEARING_DEGRADATION": 0.85,
            "FUEL_SYSTEM_DEGRADATION": 0.75,
            "UNKNOWN_ANOMALY": 0.55
        }
        fault_risk = fault_weights.get(fault_class, 0.5) * fault_prob
        
        # 3. Environmental Stress Factor
        alt_stress = max(0.0, (alt_ft - 18000.0) / 12000.0) * 0.15
        temp_stress = max(0.0, (ambient_temp - 25.0) / 25.0) * 0.20
        load_stress = max(0.0, (engine_load - 75.0) / 25.0) * 0.25
        env_stress = alt_stress + temp_stress + load_stress
        
        # 4. Degradation Velocity Risk
        vel_risk = min(0.35, max(0.0, d_velocity * 12.0))
        
        # Composite Mission Risk Index [0.0 - 1.0]
        composite_risk = float(np.clip(
            (current_d * 0.25) +
            (fault_risk * 0.35) +
            (rul_risk * 0.25) +
            (vel_risk * 0.10) +
            (env_stress * 0.05),
            0.02, 0.99
        ))
        
        # Completion Probability
        completion_prob = round(float(np.clip(1.0 - composite_risk * 1.05, 0.01, 0.99)), 3)
        risk_index = round(composite_risk, 3)
        
        if risk_index >= 0.65:
            risk_level = "CRITICAL"
        elif risk_index >= 0.40:
            risk_level = "HIGH"
        elif risk_index >= 0.20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        # Format mission reliability percentage for UI (e.g. 92%)
        mission_reliability_pct = int(completion_prob * 100.0)

        risk_factors = [
            {"factor": "RUL Margin Risk", "score": round(rul_risk, 3), "detail": f"RUL lower bound {rul_lower}h vs mission length {planned_duration_hours}h"},
            {"factor": "Active Fault Risk", "score": round(fault_risk, 3), "detail": f"Class {fault_class} (P={fault_prob})"},
            {"factor": "Degradation Velocity", "score": round(vel_risk, 3), "detail": f"Rate {d_velocity:.5f} /hr"},
            {"factor": "Environmental Stress", "score": round(env_stress, 3), "detail": f"Alt {alt_ft:.0f}ft, Load {engine_load:.1f}%"}
        ]

        return {
            "risk_index": risk_index,
            "risk_level": risk_level,
            "completion_probability": completion_prob,
            "mission_reliability_pct": mission_reliability_pct,
            "planned_duration_hours": planned_duration_hours,
            "risk_factors": risk_factors,
            "confidence": round(min(0.95, fault_data.get("confidence", 0.9) * 0.95), 3)
        }
