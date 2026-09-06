"""
Evidence & Audit Data Structures for AERIS-TWIN
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time

class EvidenceItem(BaseModel):
    type: str = Field(..., description="PHYSICS_RESIDUAL, TREND, SENSOR_CONSISTENCY, ML_SCORE, DEGRADATION_RATE, DOMAIN_LIMIT")
    parameter: Optional[str] = None
    observation: str
    confidence: float = 1.0
    timestamp: float = Field(default_factory=time.time)
    details: Optional[Dict[str, Any]] = None

class PredictionAuditRecord(BaseModel):
    engine_id: str
    mission_id: str
    timestamp: float = Field(default_factory=time.time)
    input_telemetry_ref: str
    model_version: str = "AERIS-ML-v2.4-Hybrid"
    physics_model_version: str = "AERIS-MV-AeroPiston-v1.8"
    dataset_version: str = "UAV-ROT914-SIM-CORPUS-2026.1"
    prediction_type: str
    prediction_value: Any
    confidence: float
    uncertainty_range: Optional[Dict[str, float]] = None
    evidence: List[EvidenceItem]
