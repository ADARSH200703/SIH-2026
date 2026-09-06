"""
Normalized Telemetry Data Models & Schemas
Supports MAVLink, Simulator, Replay, and REST/WebSocket ingest
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import time

class TelemetryPacket(BaseModel):
    engine_id: str = Field(default="UAV-ENG-ROT-914-01", description="Unique identifier for engine")
    uav_id: str = Field(default="MALE-UAV-TAPAS-04", description="Host UAV airframe identifier")
    mission_id: str = Field(default="MSN-2026-SURV-082", description="Active mission identifier")
    timestamp: float = Field(default_factory=time.time, description="Unix epoch timestamp in seconds")
    sequence_number: int = Field(default=0, description="Monotonically increasing sequence number")
    
    # Kinematic & Thermodynamic States
    rpm: float = Field(default=4215.0, description="Crankshaft rotational speed (RPM)")
    throttle: float = Field(default=68.0, description="Throttle lever position percentage (0-100%)")
    map_kpa: float = Field(default=96.4, description="Manifold Absolute Pressure (kPa)")
    fuel_flow: float = Field(default=5.2, description="Fuel mass flow rate (L/h or ml/min normalized)")
    egt_c: float = Field(default=645.0, description="Exhaust Gas Temperature (°C)")
    cht_c: float = Field(default=78.4, description="Cylinder Head Temperature (°C)")
    oil_pressure_bar: float = Field(default=4.3, description="Lubrication circuit oil pressure (Bar)")
    oil_temperature_c: float = Field(default=82.1, description="Engine lubrication oil temperature (°C)")
    vibration_mms: float = Field(default=1.6, description="Tri-axial engine casing vibration RMS (mm/s)")
    engine_load: float = Field(default=62.0, description="Engine load percentage (0-100%)")
    
    # Flight Dynamics & Environmental Context
    altitude_ft: float = Field(default=15000.0, description="Pressure altitude in feet")
    airspeed_kts: float = Field(default=85.0, description="Indicated airspeed in knots")
    ambient_temperature_c: float = Field(default=-14.5, description="Outside Ambient Air Temperature (°C)")
    ambient_pressure_kpa: float = Field(default=57.2, description="Ambient atmospheric pressure (kPa)")
    power_setting: float = Field(default=0.72, description="Power setting fraction (0.0 - 1.0)")
    flight_phase: str = Field(default="CRUISE", description="TAKEOFF, CLIMB, CRUISE, DESCENT, LOITER, EMERGENCY")
    
    # Metadata
    source: str = Field(default="SIMULATOR", description="SIMULATOR, REPLAY, MAVLINK, REST")
    raw_packet: Optional[Dict[str, Any]] = None

class ScenarioRequest(BaseModel):
    scenario: str

class ParameterOverrideRequest(BaseModel):
    rpm: Optional[float] = None
    temperature: Optional[float] = None
    oilPressure: Optional[float] = None
    vibration: Optional[float] = None
    fuelFlow: Optional[float] = None
    engineLoad: Optional[float] = None
    altitude: Optional[float] = None
    throttle: Optional[float] = None

class FaultInjectionRequest(BaseModel):
    fault: str = Field(..., description="BEARING_DEGRADATION, SPARK_PLUG_DEGRADATION, FUEL_SYSTEM_DEGRADATION, COOLING_DEGRADATION, SENSOR_DRIFT_VIBRATION, SENSOR_STUCK_TEMP, PACKET_LOSS")
    severity: float = Field(default=0.5, ge=0.0, le=1.0, description="Initial/target fault severity")
    start_time: float = Field(default=0.0, description="Flight second offset to begin fault injection")
    progression_rate: float = Field(default=0.002, description="Degradation growth rate per second")

class WhatIfRequest(BaseModel):
    duration_hours: float = Field(default=4.0, description="Proposed mission duration in hours")
    altitude: float = Field(default=18000.0, description="Proposed cruise altitude in feet")
    power_setting: float = Field(default=0.75, description="Proposed power setting fraction (0.5 - 1.0)")
    ambient_temperature: float = Field(default=35.0, description="Worst-case ambient temperature (°C)")
