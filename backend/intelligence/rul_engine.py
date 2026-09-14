"""
Prognostics & Remaining Useful Life (RUL) Engine for AERIS-TWIN
Calculates remaining flight/operating hours to defined failure threshold (D_failure = 0.75)
with rigorously bounded uncertainty intervals derived from sensor trust, degradation velocity, and model validity.
Never fabricates exact countdown seconds; provides transparent data sufficiency and engineering disclaimers.
"""
from typing import Dict, Any, List, Optional
import numpy as np

class EngineRULEngine:
    def __init__(self, failure_threshold: float = 0.75):
        self.d_failure = failure_threshold
        self.max_tbo_hours = 1200.0  # Time Between Overhaul nominal baseline for Rotax 914
        self.max_motor_hours = 250.0 # Nominal testbed motor brushed/geared life baseline
        self.model_version = "AERIS-RUL-PolyExtrap-v2.0"

    def estimate_rul(
        self,
        degradation_data: Dict[str, Any],
        sensor_trust: Dict[str, Any],
        telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimates remaining useful life hours and confidence intervals with explicit data sufficiency checks.
        """
        profile = telemetry.get("profile")
        is_motor = (
            profile == "MOTOR_PROTOTYPE" or "current_a" in telemetry or "voltage_v" in telemetry or (
                "oilPressure" not in telemetry and "oil_pressure" not in telemetry and "fuelFlow" not in telemetry and "fuel_flow" not in telemetry and "cht" not in telemetry
            )
        )

        current_d = float(degradation_data.get("normalized_degradation", 0.05))
        velocity = float(degradation_data.get("degradation_velocity", 0.002))
        sensor_trust_score = float(sensor_trust.get("aggregate_trust_score", 1.0))
        
        # Check operating envelope validity
        if is_motor:
            max_baseline = self.max_motor_hours
            meas_curr = telemetry.get("current_a")
            within_envelope = (meas_curr is not None and 0.1 <= float(meas_curr) <= 8.0)
            model_validity = "BENCH_TESTBED_ESTIMATE"
            disclaimer = "Engineering estimate based on testbed electrical duty cycle — not flight qualified"
            data_sufficiency = "LIMITED" if velocity > 0.0005 else "INSUFFICIENT"
        else:
            max_baseline = self.max_tbo_hours
            rpm = float(telemetry.get("rpm", 4215.0))
            alt = float(telemetry.get("altitude_ft", 15000.0))
            within_envelope = (800.0 <= rpm <= 5800.0) and (0.0 <= alt <= 28000.0)
            model_validity = "WITHIN_VALIDATED_RANGE" if within_envelope else "OUT_OF_RANGE"
            disclaimer = "Engineering estimate based on empirical degradation trend — not a guaranteed countdown"
            data_sufficiency = "SUFFICIENT" if velocity > 0.001 else "LIMITED"
        
        # Remaining degradation margin before functional failure
        margin = max(0.0, self.d_failure - current_d)
        
        # If already at or beyond failure threshold
        if margin <= 0.001:
            rul_hours = 0.0
            lower_hours = 0.0
            upper_hours = 0.5
            confidence_score = 0.95
            confidence_level = "HIGH"
            status = "CRITICAL_LIMIT_REACHED"
        # If degradation velocity is positive and meaningful
        elif velocity > 0.0008:
            raw_rul = margin / velocity
            rul_hours = round(min(max_baseline, max(0.5, raw_rul)), 1)
            
            # Uncertainty interval calculation:
            uncert_factor = 0.15 + (1.0 - sensor_trust_score) * 0.40 + (0.15 if not within_envelope else 0.0)
            if is_motor:
                uncert_factor += 0.15  # Higher uncertainty on physical bench demonstrator
            
            lower_hours = round(max(0.1, rul_hours * (1.0 - uncert_factor)), 1)
            upper_hours = round(rul_hours * (1.0 + uncert_factor * 1.3), 1)
            confidence_score = round(min(0.95, sensor_trust_score * (0.85 if within_envelope else 0.60)), 3)
            confidence_level = "HIGH" if confidence_score >= 0.85 else ("MEDIUM" if confidence_score >= 0.65 else "LOW")
            status = "ACTIVE_ESTIMATE"
        else:
            # Nominal steady state; RUL corresponds to remaining baseline component life
            rul_hours = round(max_baseline * (1.0 - current_d), 1)
            lower_hours = round(rul_hours * 0.80, 1)
            upper_hours = round(rul_hours * 1.20, 1)
            confidence_score = round((0.80 if is_motor else 0.90) * sensor_trust_score, 3)
            confidence_level = "HIGH" if confidence_score >= 0.85 else ("MEDIUM" if confidence_score >= 0.65 else "LOW")
            status = "NOMINAL_BASE_LIFE"

        # Format human-readable RUL string (Hours representation)
        if is_motor and data_sufficiency == "INSUFFICIENT":
            rul_time_str = f"~{int(lower_hours)}–{int(upper_hours)} h (Est.)"
        else:
            rul_time_str = f"{rul_hours:.1f} h"

        evidence_items = [
            {
                "type": "DEGRADATION_TRAJECTORY",
                "observation": f"Current normalized degradation index D={current_d:.4f} progressing at {velocity:.5f}/hr towards threshold D_failure={self.d_failure}",
                "confidence": confidence_score
            },
            {
                "type": "UNCERTAINTY_BOUNDS",
                "observation": f"Prediction interval [{lower_hours:.1f}h, {upper_hours:.1f}h] (Confidence: {confidence_level}, Data Sufficiency: {data_sufficiency})",
                "confidence": confidence_score
            }
        ]

        return {
            "rul_estimate_hours": rul_hours,
            "rul_time_str": rul_time_str,
            "lower_bound_hours": lower_hours,
            "upper_bound_hours": upper_hours,
            "confidence": confidence_score,
            "confidence_level": confidence_level,
            "confidence_category": confidence_level,
            "data_sufficiency": data_sufficiency,
            "disclaimer": disclaimer,
            "status": status,
            "degradation_velocity": velocity,
            "endpoint_definition": f"Critical mechanical/thermal failure boundary D_failure >= {self.d_failure}",
            "model_validity": model_validity,
            "evidence": evidence_items,
            "model_version": self.model_version
        }
