"""
Digital Twin State & Dashboard View Models
Differentiates the computational Digital Twin source of truth from the presentation DashboardView.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time

class SubState(BaseModel):
    value: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="STATE_ESTIMATOR")

class DigitalTwinState(BaseModel):
    engine_id: str = "UAV-ENG-ROT-914-01"
    uav_id: str = "MALE-UAV-TAPAS-04"
    mission_id: str = "MSN-2026-SURV-082"
    timestamp: float = Field(default_factory=time.time)
    sequence_number: int = 0
    processing_latency_ms: float = 2.4
    
    # Structural Sub-States
    operating_state: SubState
    thermal_state: SubState
    mechanical_state: SubState
    combustion_state: SubState
    lubrication_state: SubState
    degradation_state: SubState
    sensor_state: SubState
    health_state: SubState
    fault_state: SubState
    rul_state: SubState
    
    # Consensus & Confidence Matrix
    confidence: Dict[str, float] = Field(default_factory=lambda: {
        "overall": 0.92,
        "sensor_trust": 0.95,
        "physics_agreement": 0.90,
        "ai_certainty": 0.88
    })
    
    # Dynamic Traceable Evidence
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

class DashboardView(BaseModel):
    """
    Presentation Transformation Layer — converts internal mathematical
    DigitalTwinState into UI widgets and real-time graphs.
    """
    engine_id: str
    rpm: float
    temperature: float
    oil_pressure: float
    vibration: float
    fuel_flow: float
    engine_load: float
    flight_time_str: str
    flight_time_seconds: int
    
    # Health & Mission Indicators
    engine_health: int
    mission_reliability: int
    status: str  # NORMAL, WARNING, CRITICAL
    
    # Diagnostics & Prognostics
    active_scenario: str
    anomaly_detected: bool
    anomaly_score: float
    fault_class: str
    fault_probability: float
    confidence_pct: int
    rul_time_str: str
    rul_estimate_hours: float
    rul_lower_bound_hours: float
    rul_upper_bound_hours: float
    degradation_velocity: float
    degradation_velocity_trend: str
    mission_risk_index: float
    consensus_status: str
    recommended_decision: str
    recommended_actions: List[str]
    
    # Live Chart History
    history: Dict[str, List[Any]]
