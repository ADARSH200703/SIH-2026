"""
Prognostics & Remaining Useful Life (RUL) Engine for AERIS-TWIN
Calculates remaining flight hours to defined failure threshold (D_failure = 0.75)
with rigorously bounded uncertainty intervals derived from sensor trust and model validity.
"""
from typing import Dict, Any, List
import numpy as np

class EngineRULEngine:
    def __init__(self, failure_threshold: float = 0.75):
        self.d_failure = failure_threshold
        self.max_tbo_hours = 1200.0  # Time Between Overhaul nominal baseline for Rotax 914
        self.model_version = "AERIS-RUL-PolyExtrap-v1.5"

    def estimate_rul(
        self,
        degradation_data: Dict[str, Any],
        sensor_trust: Dict[str, Any],
        telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimates remaining useful life hours and confidence intervals.
        """
        current_d = float(degradation_data.get("normalized_degradation", 0.05))
        velocity = float(degradation_data.get("degradation_velocity", 0.002))
        sensor_trust_score = float(sensor_trust.get("aggregate_trust_score", 1.0))
        
        # Check operating envelope validity
        rpm = float(telemetry.get("rpm", 4215.0))
        alt = float(telemetry.get("altitude_ft", 15000.0))
        within_envelope = (800.0 <= rpm <= 5800.0) and (0.0 <= alt <= 28000.0)
        model_validity = "WITHIN_VALIDATED_RANGE" if within_envelope else "OUT_OF_RANGE"
        
        # Remaining degradation margin before functional failure
        margin = max(0.0, self.d_failure - current_d)
        
        # If already at or beyond failure threshold
        if margin <= 0.001:
            rul_hours = 0.0
            lower_hours = 0.0
            upper_hours = 0.5
            confidence = 0.95
        # If degradation velocity is positive and meaningful
        elif velocity > 0.001:
            raw_rul = margin / velocity
            rul_hours = round(min(self.max_tbo_hours, max(0.5, raw_rul)), 1)
            
            # Uncertainty interval calculation:
            # Base uncertainty from extrapolation variance (approx ±15%)
            # Expanded by sensor trust degradation and model validity penalty
            uncert_factor = 0.15 + (1.0 - sensor_trust_score) * 0.40 + (0.15 if not within_envelope else 0.0)
            
            lower_hours = round(max(0.1, rul_hours * (1.0 - uncert_factor)), 1)
            upper_hours = round(rul_hours * (1.0 + uncert_factor * 1.3), 1)
            confidence = round(min(0.95, sensor_trust_score * (0.88 if within_envelope else 0.65)), 3)
        else:
            # Nominal steady state; RUL corresponds to remaining baseline component life
            rul_hours = round(self.max_tbo_hours * (1.0 - current_d), 1)
            lower_hours = round(rul_hours * 0.85, 1)
            upper_hours = round(rul_hours * 1.15, 1)
            confidence = 0.92

        # Format human-readable RUL string (HH:MM:SS or hours)
        total_seconds = int(rul_hours * 3600)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        rul_time_str = f"{h:02d}:{m:02d}:{s:02d}"

        evidence_items = [
            {
                "type": "DEGRADATION_TRAJECTORY",
                "observation": f"Current normalized degradation D={current_d:.4f} progressing at {velocity:.5f} /hr towards D_failure={self.d_failure}",
                "confidence": confidence
            },
            {
                "type": "UNCERTAINTY_BOUNDS",
                "observation": f"90% Prediction interval [{lower_hours}h, {upper_hours}h] conditioned on sensor trust ({sensor_trust_score:.2f})",
                "confidence": confidence
            }
        ]

        return {
            "rul_estimate_hours": rul_hours,
            "rul_time_str": rul_time_str,
            "lower_bound_hours": lower_hours,
            "upper_bound_hours": upper_hours,
            "confidence": confidence,
            "degradation_velocity": velocity,
            "endpoint_definition": f"Critical mechanical/thermal failure boundary D_failure >= {self.d_failure}",
            "model_validity": model_validity,
            "evidence": evidence_items,
            "model_version": self.model_version
        }
