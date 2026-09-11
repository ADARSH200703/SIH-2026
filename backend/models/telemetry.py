"""
Normalized Telemetry Data Models & Schemas
Supports MAVLink, Simulator, Replay, and REST/WebSocket ingest
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import time

# Profile Constants
PROFILE_AERO_ENGINE = "AERO_ENGINE"
PROFILE_MOTOR_PROTOTYPE = "MOTOR_PROTOTYPE"

class MotorPrototypePacket(BaseModel):
    """
    Physical DC Motor Testbed Telemetry Packet
    Hardware: 3x18650 Battery -> ACS712 Current Sensor -> L298N Motor Driver -> DC Geared Motor -> ESP32
    """
    device_id: str = Field(default="AERIS-ESP32-001", description="Physical ESP32 device identifier")
    profile: str = Field(default=PROFILE_MOTOR_PROTOTYPE, description="Telemetry profile (MOTOR_PROTOTYPE)")
    sequence_number: int = Field(default=0, description="Monotonically increasing sequence number")
    timestamp: float = Field(default_factory=time.time, description="Unix epoch timestamp in seconds")
    
    # Real physical measurements
    rpm: Optional[float] = Field(default=None, description="DC motor shaft rotational speed (RPM)")
    current_a: Optional[float] = Field(default=None, description="ACS712 current measurement in Amperes")
    voltage_v: Optional[float] = Field(default=None, description="Battery/bus voltage in Volts")
    power_w: Optional[float] = Field(default=None, description="Electrical power in Watts (voltage_v * current_a)")
    temperature_c: Optional[float] = Field(default=None, description="Motor casing / driver temperature in °C")
    vibration: Optional[float] = Field(default=None, description="Vibration metric (e.g. mm/s or raw accelerometer RMS)")
    motor_load_pct: Optional[float] = Field(default=None, description="Motor mechanical load percentage (0-100%)")
    
    # Metadata & connectivity
    wifi_rssi: Optional[int] = Field(default=None, description="ESP32 Wi-Fi Received Signal Strength Indication (dBm)")
    firmware_version: Optional[str] = Field(default="v1.4.2-motor", description="ESP32 firmware version")
    source: str = Field(default="PHYSICAL_SENSOR", description="PHYSICAL_SENSOR, ESP32, REST")
    api_key: Optional[str] = Field(default=None, description="Optional device authentication API key")
    raw_packet: Optional[Dict[str, Any]] = None

class TelemetryPacket(BaseModel):
    profile: str = Field(default=PROFILE_AERO_ENGINE, description="AERO_ENGINE or MOTOR_PROTOTYPE")
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
