"""
Twin Consensus Engine for AERIS-TWIN
Evaluates independent evidence from Physics Model, Sensor Trust, and AI/ML Classifiers.
Detects consensus vs conflicts and dynamically adjusts Twin confidence and diagnostic transparency.
"""
from typing import Dict, Any, List

class TwinConsensusEngine:
    def __init__(self):
        pass

    def evaluate_consensus(
        self,
        physics_residuals: Dict[str, Any],
        sensor_trust: Dict[str, Any],
        anomaly_result: Dict[str, Any],
        fault_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes Physics, Sensor Trust, and AI perspectives.
        """
        # 1. Physics Perspective
        max_norm_res = max([abs(r.get("normalized_residual", 0.0)) for r in physics_residuals.values()] or [0.0])
        physics_sees_anomaly = max_norm_res >= 2.2
        physics_confidence = round(min(0.98, max(0.60, 1.0 - (max_norm_res / 10.0))), 3) if not physics_sees_anomaly else 0.90
        
        # 2. Sensor Perspective
        sensor_trust_score = sensor_trust.get("aggregate_trust_score", 1.0)
        sensors_valid = sensor_trust.get("all_sensors_valid", True)
        
        # 3. AI / ML Perspective
        ai_sees_anomaly = anomaly_result.get("anomaly", False)
        ai_confidence = fault_result.get("confidence", 0.85)
        
        evidence_items = []
        
        # Consensus Matrix Logic
        if physics_sees_anomaly and sensors_valid and ai_sees_anomaly:
            status = "HIGH_CONSENSUS"
            explanation = "Physics residuals, valid sensor dynamics, and AI models all corroborate progressive anomaly."
            overall_confidence = round(min(0.96, (physics_confidence + sensor_trust_score + ai_confidence) / 3.0), 3)
            evidence_items.append({
                "type": "CONSENSUS",
                "observation": f"Tripartite agreement (Physics res={max_norm_res}σ, Sensors valid={sensors_valid}, AI score={anomaly_result.get('score')})",
                "confidence": overall_confidence
            })
            
        elif not physics_sees_anomaly and not ai_sees_anomaly and sensors_valid:
            status = "HIGH_CONSENSUS_NOMINAL"
            explanation = "All subsystems independently confirm normal operating regime within design boundaries."
            overall_confidence = 0.95
            evidence_items.append({
                "type": "CONSENSUS",
                "observation": "Physics, sensor integrity, and AI models confirm nominal steady-state operation.",
                "confidence": 0.95
            })
            
        elif not sensors_valid:
            status = "SENSOR_CORRUPTION_DETECTED"
            explanation = "Sensor trust degradation detected. Telemetry may contain sensor artifacts rather than true physical engine failure."
            # Penalize confidence significantly
            overall_confidence = round(sensor_trust_score * 0.75, 3)
            evidence_items.append({
                "type": "SENSOR_CONFLICT",
                "observation": f"Sensor trust degraded ({sensor_trust_score:.2f}). Isolating sensor channel to prevent false degradation attribution.",
                "confidence": overall_confidence
            })
            
        elif ai_sees_anomaly and not physics_sees_anomaly and sensors_valid:
            status = "AI_PHYSICS_DISAGREEMENT"
            explanation = "AI flags anomaly but mean-value physics model shows expected thermodynamics. Potential subtle multi-harmonic anomaly or model envelope edge."
            overall_confidence = round(ai_confidence * 0.70, 3)
            evidence_items.append({
                "type": "AI_CONFLICT",
                "observation": "AI anomaly detected without strong physics residual corroboration; confidence downgraded.",
                "confidence": overall_confidence
            })
            
        elif physics_sees_anomaly and not ai_sees_anomaly:
            status = "PHYSICS_LEAD_ANOMALY"
            explanation = "Physics residuals deviating before statistical ML boundary trigger (Early warning phase)."
            overall_confidence = 0.80
            evidence_items.append({
                "type": "PHYSICS_LEAD",
                "observation": f"Early physics residual deviation ({max_norm_res}σ) prior to ML classification threshold.",
                "confidence": 0.80
            })
        else:
            status = "MODERATE_CONSENSUS"
            explanation = "Subsystem evidence within acceptable tracking tolerance."
            overall_confidence = 0.85

        return {
            "consensus_status": status,
            "explanation": explanation,
            "overall_confidence": overall_confidence,
            "physics_evidence": {
                "sees_anomaly": physics_sees_anomaly,
                "max_residual_sigma": round(max_norm_res, 2),
                "confidence": physics_confidence
            },
            "sensor_evidence": {
                "aggregate_trust": sensor_trust_score,
                "all_valid": sensors_valid
            },
            "ai_evidence": {
                "sees_anomaly": ai_sees_anomaly,
                "fault_class": fault_result.get("fault", "NOMINAL"),
                "confidence": ai_confidence
            },
            "evidence": evidence_items
        }
