"""
Mission Decision Engine for AERIS-TWIN
Rule + Risk based actionable recommendation layer.
Advisory decision support only — never autonomously commands aircraft control surfaces or throttles.
"""
from typing import Dict, Any, List

class MissionDecisionEngine:
    def __init__(self):
        self.decisions_vocab = [
            "PROCEED",
            "PROCEED_WITH_POWER_DERATING",
            "SHORTEN_MISSION",
            "MODIFY_MISSION_PROFILE",
            "INSPECTION_RECOMMENDED",
            "ENGINE_CHANGE_RECOMMENDED",
            "MISSION_NOT_RECOMMENDED"
        ]

    def recommend(
        self,
        health_data: Dict[str, Any],
        fault_data: Dict[str, Any],
        rul_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        consensus_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates actionable mission advisory recommendation with before/after risk quantification.
        """
        health_index = float(health_data.get("health_index", 95.0))
        d_vel = float(health_data.get("degradation_velocity", 0.002))
        fault_class = fault_data.get("fault", "NOMINAL")
        fault_prob = float(fault_data.get("probability", 0.05))
        risk_before = float(risk_data.get("risk_index", 0.10))
        rul_lower = float(rul_data.get("lower_bound_hours", 1000.0))
        mission_dur = float(risk_data.get("planned_duration_hours", 6.0))
        consensus_status = consensus_data.get("consensus_status", "HIGH_CONSENSUS")
        
        evidence_items = []
        
        # 1. Critical Imminent Failure: RUL lower bound less than mission or extreme health degradation
        if health_index < 40.0 or rul_lower < (mission_dur * 0.5) or (fault_class == "BEARING_DEGRADATION" and fault_prob > 0.85):
            decision = "MISSION_NOT_RECOMMENDED"
            reason = "Critical degradation detected. Remaining useful life lower bound is insufficient for safe mission completion."
            risk_after = round(risk_before * 0.95, 3) # aborting avoids in-flight failure
            actions = [
                "Abort active sortie; initiate RTB (Return To Base) immediately",
                "Execute gentle continuous descent at minimum safe power setting",
                "Flag engine for comprehensive workshop teardown and non-destructive inspection"
            ]
            evidence_items.append({
                "type": "SAFETY_LIMIT",
                "observation": f"Health index {health_index}% and fault {fault_class} (P={fault_prob}) violate MALE UAV airworthiness thresholds",
                "confidence": 0.95
            })
            
        # 2. Severe Bearing or Lubrication Degradation: Derate & Shorten
        elif fault_class in ["BEARING_DEGRADATION", "FUEL_SYSTEM_DEGRADATION"] or health_index < 65.0:
            decision = "PROCEED_WITH_POWER_DERATING"
            reason = "Progressive bearing/lubrication stress detected. Derating throttle by 15-20% stabilizes thermal/mechanical wear rate."
            # Calculated risk reduction from derating
            risk_after = round(max(0.15, risk_before * 0.58), 3)
            actions = [
                "Cap maximum engine throttle demand at 65%",
                "Avoid high-g maneuvering and aggressive climb profiles",
                "Re-route mission towards nearest secondary recovery waypoint",
                "Schedule post-flight bearing and oil filter debris inspection"
            ]
            evidence_items.append({
                "type": "RISK_MITIGATION",
                "observation": f"Power derating reduces projected degradation velocity from {d_vel:.4f}/hr to ~{d_vel*0.4:.4f}/hr",
                "confidence": 0.90
            })
            
        # 3. High Thermal Accumulation / Cooling Degradation: Modify Profile
        elif fault_class == "COOLING_DEGRADATION" or health_index < 78.0:
            decision = "MODIFY_MISSION_PROFILE"
            reason = "Cylinder head thermal stress elevated. Altering flight altitude or increasing airspeed optimizes ram-air cooling heat rejection."
            risk_after = round(max(0.12, risk_before * 0.65), 3)
            actions = [
                "Descend to lower altitude for denser, cooler ram air",
                "Open cowl cooling flaps to 100% manual override",
                "Enrich air-fuel mixture to provide in-cylinder evaporative cooling"
            ]
            evidence_items.append({
                "type": "THERMAL_MANAGEMENT",
                "observation": "Thermodynamic heat balance recovered by ram air increase",
                "confidence": 0.88
            })
            
        # 4. Sensor Corruption Detected: Inspection Recommended
        elif "SENSOR_CORRUPTION" in consensus_status or consensus_data.get("sensor_evidence", {}).get("aggregate_trust", 1.0) < 0.6:
            decision = "INSPECTION_RECOMMENDED"
            reason = "Telemetry sensor trust degraded. Physical engine likely sound, but sensor channel requires harness/transducer inspection."
            risk_after = round(risk_before * 0.85, 3)
            actions = [
                "Cross-reference telemetry against secondary analog avionics bus",
                "Continue standard mission under conservative flight envelope",
                "Perform pre-flight transducer calibration before subsequent sorties"
            ]
            evidence_items.append({
                "type": "SENSOR_MAINTENANCE",
                "observation": "Degraded sensor trust score isolated from physical engine wear",
                "confidence": 0.85
            })
            
        # 5. Nominal Flight
        else:
            decision = "PROCEED"
            reason = "All mechanical, thermal, combustion, and lubrication parameters within nominal operating envelope."
            risk_after = risk_before
            actions = [
                "Continue standard planned mission profile",
                "Maintain continuous 10Hz digital twin telemetry synchronization"
            ]
            evidence_items.append({
                "type": "NOMINAL_STATE",
                "observation": f"Health index {health_index}%, RUL {rul_data.get('rul_estimate_hours')}h exceeds mission duration",
                "confidence": 0.95
            })

        return {
            "decision": decision,
            "reason": reason,
            "risk_before": risk_before,
            "risk_after": risk_after,
            "risk_reduction_pct": round(max(0.0, (risk_before - risk_after) / max(0.01, risk_before) * 100.0), 1),
            "recommended_actions": actions,
            "evidence": evidence_items,
            "confidence": round(min(0.96, fault_data.get("confidence", 0.9) * 0.95), 3),
            "safety_disclaimer": "AERIS-TWIN is a decision-support advisory system. Final flight commands remain with the certified UAV Mission Commander."
        }
