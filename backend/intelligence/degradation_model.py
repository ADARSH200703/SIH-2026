"""
Degradation & Health Index Engine for AERIS-TWIN
Calculates normalized multi-subsystem degradation D in [0, 1],
Health Index = 100 * (1 - D), and real-time degradation velocity dD/dt.
"""
from typing import Dict, Any, List
from collections import deque
import numpy as np

class EngineDegradationModel:
    def __init__(self, history_size: int = 60):
        self.history_size = history_size
        self.degradation_history = deque(maxlen=history_size)
        self.timestamp_history = deque(maxlen=history_size)
        
        # Subsystem degradation weights summing to 1.0
        self.weights = {
            "mechanical": 0.35,   # Vibration, bearing friction
            "thermal": 0.25,      # CHT thermal stress, cooling capacity
            "lubrication": 0.25,  # Oil pressure, hydrodynamic film thickness
            "combustion": 0.15    # Fuel consumption, spark efficiency
        }

    def reset(self):
        """Clears rolling degradation and timestamp buffers."""
        self.degradation_history.clear()
        self.timestamp_history.clear()


    def compute_degradation(
        self,
        residuals: Dict[str, Any],
        telemetry: Dict[str, Any],
        sensor_trust: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Computes normalized physical degradation D in [0, 1], Health Index, and velocity.
        """
        timestamp = telemetry.get("timestamp", 0.0)
        
        # 1. Mechanical Degradation (based on vibration residual and casing acceleration)
        v_norm = max(0.0, residuals.get("vibration", {}).get("normalized_residual", 0.0))
        d_mech = float(np.clip(v_norm / 5.5, 0.0, 1.0))
        
        # 2. Thermal Degradation (based on CHT residual and high temperature soak)
        t_norm = max(0.0, residuals.get("temperature", {}).get("normalized_residual", 0.0))
        d_therm = float(np.clip(t_norm / 5.0, 0.0, 1.0))
        
        # 3. Lubrication Degradation (based on oil pressure deficit)
        o_norm = max(0.0, -residuals.get("oilPressure", {}).get("normalized_residual", 0.0))
        d_lub = float(np.clip(o_norm / 4.5, 0.0, 1.0))
        
        # 4. Combustion Degradation (based on fuel flow & EGT residuals)
        f_norm = max(0.0, residuals.get("fuelFlow", {}).get("normalized_residual", 0.0))
        d_comb = float(np.clip(f_norm / 4.0, 0.0, 1.0))
        
        # Weighted composite degradation D in [0, 1]
        raw_d = (
            self.weights["mechanical"] * d_mech +
            self.weights["thermal"] * d_therm +
            self.weights["lubrication"] * d_lub +
            self.weights["combustion"] * d_comb
        )
        
        # If sensor trust is degraded on a specific channel, damp that channel's influence
        # to prevent sensor failure from falsifying mechanical engine wear
        aggregate_trust = sensor_trust.get("aggregate_trust_score", 1.0)
        total_d = round(float(np.clip(raw_d * aggregate_trust + (1.0 - aggregate_trust) * 0.05, 0.02, 0.98)), 4)
        
        # Health Index = 100 * (1 - D)
        health_index = round(100.0 * (1.0 - total_d), 2)
        
        # Update rolling buffers
        self.degradation_history.append(total_d)
        self.timestamp_history.append(timestamp)
        
        # Compute degradation velocity (dD/dt in fraction/hour)
        if len(self.degradation_history) >= 5:
            d_arr = np.array(self.degradation_history)
            t_arr = np.array(self.timestamp_history)
            raw_dt = float(t_arr[-1] - t_arr[0])
            dt_sec = raw_dt if (0.5 <= raw_dt <= 7200.0) else float(len(d_arr))
            # Velocity per hour (3600 seconds)
            delta_d = float(d_arr[-1] - d_arr[0])
            velocity_per_hour = round(max(0.0001, (delta_d / max(1.0, dt_sec)) * 3600.0) if delta_d > 0 else 0.001, 5)
        else:
            velocity_per_hour = 0.002
            
        if velocity_per_hour > 0.025:
            velocity_trend = "RAPID_ACCELERATION"
        elif velocity_per_hour > 0.005:
            velocity_trend = "INCREASING"
        elif velocity_per_hour < -0.005:
            velocity_trend = "RECOVERING"
        else:
            velocity_trend = "STABLE"
            
        evidence_items = []
        if d_mech > 0.3:
            evidence_items.append({
                "type": "DEGRADATION_COMPONENT",
                "parameter": "mechanical",
                "observation": f"Mechanical subsystem contributes {d_mech:.2f} normalized degradation",
                "confidence": 0.92
            })
        if d_lub > 0.3:
            evidence_items.append({
                "type": "DEGRADATION_COMPONENT",
                "parameter": "lubrication",
                "observation": f"Lubrication subsystem contributes {d_lub:.2f} normalized degradation",
                "confidence": 0.90
            })
        if d_therm > 0.3:
            evidence_items.append({
                "type": "DEGRADATION_COMPONENT",
                "parameter": "thermal",
                "observation": f"Thermal subsystem contributes {d_therm:.2f} normalized degradation",
                "confidence": 0.88
            })

        return {
            "health_index": health_index,
            "normalized_degradation": total_d,
            "subsystem_degradations": {
                "mechanical": round(d_mech, 3),
                "thermal": round(d_therm, 3),
                "lubrication": round(d_lub, 3),
                "combustion": round(d_comb, 3)
            },
            "degradation_velocity": velocity_per_hour,
            "velocity_unit": "degradation_fraction/hour",
            "velocity_trend": velocity_trend,
            "interpretation": "Estimated condition relative to the defined healthy reference and degradation failure boundary (D_failure = 0.75).",
            "confidence": round(min(0.96, aggregate_trust * 0.95), 3),
            "evidence": evidence_items
        }
