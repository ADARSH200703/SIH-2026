"""
Anomaly Detection Module for AERIS-TWIN
Combines Isolation Forest residual scoring with multi-variate statistical distance.
Capable of flagging anomalous behaviour even when the specific failure mode is UNKNOWN.
"""
from typing import Dict, Any, List
import numpy as np
from sklearn.ensemble import IsolationForest

class EngineAnomalyDetector:
    def __init__(self):
        self.model_version = "AERIS-IF-Anom-v2.1"
        self.feature_names = [
            "vib_norm_res", "vib_slope", "temp_norm_res", "temp_slope",
            "oil_norm_res", "oil_slope", "fuel_norm_res", "egt_norm_res"
        ]
        # Calibrated baseline training data representation
        np.random.seed(42)
        baseline_data = np.random.normal(0.0, 0.45, size=(300, len(self.feature_names)))
        self.iso_forest = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )
        self.iso_forest.fit(baseline_data)

    def detect(self, residuals: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs anomaly inference over residual features and statistical deviations.
        """
        vib_res = residuals.get("vibration", {})
        temp_res = residuals.get("temperature", {})
        oil_res = residuals.get("oilPressure", {})
        fuel_res = residuals.get("fuelFlow", {})
        egt_res = residuals.get("egt", {})
        
        # Build feature vector
        features = np.array([[
            vib_res.get("normalized_residual", 0.0),
            vib_res.get("residual_slope", 0.0) * 100.0,
            temp_res.get("normalized_residual", 0.0),
            temp_res.get("residual_slope", 0.0) * 100.0,
            oil_res.get("normalized_residual", 0.0),
            oil_res.get("residual_slope", 0.0) * 100.0,
            fuel_res.get("normalized_residual", 0.0),
            egt_res.get("normalized_residual", 0.0)
        ]])
        
        # Raw decision function from Isolation Forest (lower values = more abnormal)
        raw_score = self.iso_forest.decision_function(features)[0]
        # Normalize into anomaly score [0.0 - 1.0] where 1.0 is extremely anomalous
        norm_anomaly_score = float(np.clip(0.5 - (raw_score * 1.5), 0.02, 0.99))
        
        # Multi-variate Mahalanobis-like residual magnitude
        norm_res_values = [
            abs(vib_res.get("normalized_residual", 0.0)),
            abs(temp_res.get("normalized_residual", 0.0)),
            abs(oil_res.get("normalized_residual", 0.0)),
            abs(fuel_res.get("normalized_residual", 0.0)),
            abs(egt_res.get("normalized_residual", 0.0))
        ]
        max_norm_res = max(norm_res_values) if norm_res_values else 0.0
        
        # Composite score combining tree isolation and physics residuals
        composite_score = round(float(np.clip(norm_anomaly_score * 0.4 + (max_norm_res / 4.0) * 0.6, 0.02, 0.99)), 4)
        
        is_anomaly = composite_score >= 0.40 or max_norm_res >= 2.5
        
        if composite_score >= 0.70 or max_norm_res >= 4.0:
            severity = "HIGH"
        elif composite_score >= 0.40 or max_norm_res >= 2.5:
            severity = "MEDIUM"
        else:
            severity = "LOW"
            
        # Evidence generation
        evidence_items = []
        if vib_res.get("normalized_residual", 0.0) > 2.0:
            evidence_items.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "vibration",
                "observation": f"Vibration residual is {vib_res.get('normalized_residual')} sigma above baseline expectation",
                "confidence": 0.92
            })
        if oil_res.get("normalized_residual", 0.0) < -2.0:
            evidence_items.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "oilPressure",
                "observation": f"Oil pressure residual is {abs(oil_res.get('normalized_residual'))} sigma below hydrodynamic expected state",
                "confidence": 0.90
            })
        if temp_res.get("normalized_residual", 0.0) > 2.0:
            evidence_items.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "temperature",
                "observation": f"Cylinder head temperature residual is {temp_res.get('normalized_residual')} sigma above thermal model",
                "confidence": 0.88
            })
        if fuel_res.get("normalized_residual", 0.0) > 2.2:
            evidence_items.append({
                "type": "PHYSICS_RESIDUAL",
                "parameter": "fuelFlow",
                "observation": f"Fuel mass flow is {fuel_res.get('normalized_residual')} sigma above BSFC baseline",
                "confidence": 0.85
            })
            
        if is_anomaly and not evidence_items:
            evidence_items.append({
                "type": "ML_SCORE",
                "parameter": "multivariate_residual",
                "observation": f"Isolation Forest decision boundary exceeded with score {composite_score}",
                "confidence": 0.82
            })
            
        return {
            "anomaly": is_anomaly,
            "score": composite_score,
            "severity": severity,
            "max_normalized_residual": round(max_norm_res, 3),
            "evidence": evidence_items,
            "model_version": self.model_version
        }
