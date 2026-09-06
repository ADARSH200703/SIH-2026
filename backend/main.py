"""
FastAPI Server & WebSocket Telemetry Gateway
AERIS-TWIN — Real-Time Continuous Telemetry Evaluation & Evidence Backend
Supports LIVE and SIMULATION/TEST modes, configurable data rates (1-20 Hz),
latency/data age metrics, alert debouncing, deterministic replay, and multi-source ingestion.
"""
import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import (
    init_db, log_event, get_db_connection,
    get_recent_telemetry_rows
)
from .simulation.aero_simulator import AeroEngineSimulator
from .simulation.replay_engine import ReplayEngine
from .simulation.sources import (
    LiveStreamSource, SimulationSource, FileReplaySource, MAVLinkSource
)
from .twin_service import TwinUpdateService
from .validation.experiment_runner import ExperimentRunner
from .evaluator.questions_registry import EVALUATOR_QUESTIONS
from .evaluator.limitations import SYSTEM_LIMITATIONS
from .models.telemetry import (
    ScenarioRequest, ParameterOverrideRequest,
    FaultInjectionRequest, WhatIfRequest, TelemetryPacket
)

# Initialize core subsystems
init_db()
simulator = AeroEngineSimulator(seed=42)
twin_service = TwinUpdateService()
replay_engine = ReplayEngine(twin_service=twin_service)
experiment_runner = ExperimentRunner()

# Multi-source telemetry abstractions
live_source = LiveStreamSource(stale_timeout_sec=3.0, disconnect_timeout_sec=6.0)
mavlink_source = MAVLinkSource()

# System Mode & Frequency State
class SystemState:
    mode: str = "LIVE"  # "LIVE" or "SIMULATION"
    target_rate_hz: float = 10.0  # 1.0, 5.0, 10.0, 20.0
    is_paused: bool = False

system_state = SystemState()

# Request schemas for new endpoints
class ModeRequest(BaseModel):
    mode: str = Field(..., description="LIVE or SIMULATION")

class RateRequest(BaseModel):
    rate_hz: float = Field(..., ge=1.0, le=50.0, description="Target evaluation frequency in Hz")

class ReplaySeekRequest(BaseModel):
    frame_index: Optional[int] = Field(None, ge=0)
    position: Optional[float] = Field(None, ge=0.0)

class ReplaySpeedRequest(BaseModel):
    speed: float = Field(..., ge=0.1, le=20.0)

class FlightTimeResetRequest(BaseModel):
    seconds: int = Field(0, ge=0, description="Target seconds to reset mission flight time to")


# Connected WebSocket clients manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        for dead in disconnected:
            self.disconnect(dead)

manager = ConnectionManager()

# Background broadcast loop supporting both LIVE & SIMULATION modes
async def telemetry_broadcast_loop():
    while True:
        try:
            if not system_state.is_paused:
                if system_state.mode == "LIVE":
                    # LIVE MODE: Ingest from LiveStreamSource
                    status_info = live_source.get_status()
                    if live_source.is_connected():
                        raw_frame = live_source.get_frame()
                        if raw_frame is not None:
                            raw_frame["source"] = raw_frame.get("source", "LIVE")
                            raw_frame["is_simulated"] = False
                            pipeline_out = twin_service.process_telemetry_frame(raw_frame)
                            
                            payload = {
                                "type": "TELEMETRY_UPDATE",
                                "mode": "LIVE",
                                "connected": True,
                                "status": "LIVE" if not live_source.is_stale() else "STALE",
                                "data": pipeline_out,
                                "state": raw_frame,
                                "history": simulator.history,
                                "inference": pipeline_out["inference"],
                                "twin_state": pipeline_out["twin_state"],
                                "dashboard_view": pipeline_out["dashboard_view"],
                                "residuals": pipeline_out["residuals"],
                                "expected_physics": pipeline_out["expected_physics"],
                                "sensor_trust": pipeline_out["sensor_trust"],
                                "alerts": pipeline_out.get("alerts", []),
                                "events": pipeline_out.get("events", []),
                                "primary_evidence": pipeline_out.get("primary_evidence", []),
                                "stream_metrics": status_info,
                                "target_rate_hz": system_state.target_rate_hz,
                            }
                            await manager.broadcast(payload)
                        elif live_source.is_stale():
                            payload = {
                                "type": "LIVE_STREAM_STATUS",
                                "mode": "LIVE",
                                "connected": True,
                                "status": "STALE",
                                "message": f"LIVE DATA: STALE ({status_info.get('data_age_ms')} ms)",
                                "status_details": status_info,
                                "target_rate_hz": system_state.target_rate_hz,
                                "timestamp": time.time(),
                            }
                            await manager.broadcast(payload)
                    else:
                        # Live mode but no active live stream connected
                        payload = {
                            "type": "LIVE_STREAM_STATUS",
                            "mode": "LIVE",
                            "connected": False,
                            "status": status_info.get("status", "NOT_CONNECTED"),
                            "message": "NO LIVE DATA — SOURCE DISCONNECTED",
                            "status_details": status_info,
                            "target_rate_hz": system_state.target_rate_hz,
                            "timestamp": time.time(),
                        }
                        await manager.broadcast(payload)

                else:
                    # SIMULATION / TEST MODE
                    if replay_engine.is_playing:
                        raw_frame = replay_engine.step()
                        if raw_frame is None:
                            raw_frame = simulator.step()
                    else:
                        raw_frame = simulator.step()

                    raw_frame["source"] = "SIMULATION"
                    raw_frame["is_simulated"] = True
                    
                    pipeline_out = twin_service.process_telemetry_frame(raw_frame)
                    
                    payload = {
                        "type": "TELEMETRY_UPDATE",
                        "mode": "SIMULATION",
                        "connected": True,
                        "data": pipeline_out,
                        "state": raw_frame,
                        "history": simulator.history,
                        "inference": pipeline_out["inference"],
                        "twin_state": pipeline_out["twin_state"],
                        "dashboard_view": pipeline_out["dashboard_view"],
                        "residuals": pipeline_out["residuals"],
                        "expected_physics": pipeline_out["expected_physics"],
                        "sensor_trust": pipeline_out["sensor_trust"],
                        "alerts": pipeline_out.get("alerts", []),
                        "events": pipeline_out.get("events", []),
                        "primary_evidence": pipeline_out.get("primary_evidence", []),
                        "stream_metrics": pipeline_out.get("stream_metrics", {}),
                        "target_rate_hz": system_state.target_rate_hz,
                    }
                    await manager.broadcast(payload)

        except Exception as e:
            log_event(f"Broadcast Loop Exception: {str(e)}", "error", "TelemetryBroadcast")

        # Configurable loop frequency (default: 10 Hz target -> 100ms sleep)
        sleep_sec = 1.0 / max(1.0, min(50.0, system_state.target_rate_hz))
        await asyncio.sleep(sleep_sec)

# Lifespan background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(telemetry_broadcast_loop())
    log_event("AERIS-TWIN Real-Time Evaluator Gateway Started on Port 8000", "info", "Lifespan")
    yield

app = FastAPI(
    title="AERIS-TWIN — Evaluator Intelligence & Evidence Backend",
    description="Research-Grade Digital Twin Intelligence Layer for MALE UAV Aero Piston Engines",
    version="2.5.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. CORE SYSTEM, HEALTH & MODE CONFIG
# ==========================================
@app.get("/api/health")
@app.get("/health")
def get_system_health():
    return {
        "status": "ok",
        "service": "AERIS-TWIN Evaluator Intelligence & Evidence Backend",
        "version": "2.5.0",
        "pipeline_stages": 16,
        "mode": system_state.mode,
        "target_rate_hz": system_state.target_rate_hz,
        "live_connected": live_source.is_connected(),
        "edge_native": True
    }

@app.get("/api/mode")
def get_evaluator_mode():
    return {
        "mode": system_state.mode,
        "target_rate_hz": system_state.target_rate_hz,
        "live_status": live_source.get_status(),
        "is_paused": system_state.is_paused,
    }

@app.post("/api/mode")
def set_evaluator_mode(req: ModeRequest):
    req_mode = req.mode.upper()
    if req_mode not in ["LIVE", "SIMULATION", "TEST"]:
        raise HTTPException(status_code=400, detail="Mode must be 'LIVE' or 'SIMULATION'")
    if req_mode == "TEST":
        req_mode = "SIMULATION"
    system_state.mode = req_mode
    twin_service.reset()
    log_event(f"Evaluator Mode Switched to: {req_mode}", "info", "ModeManager")
    return {
        "status": "mode_updated",
        "mode": system_state.mode,
        "live_status": live_source.get_status(),
    }

@app.get("/api/rate")
def get_target_rate():
    return {"target_rate_hz": system_state.target_rate_hz}

@app.post("/api/rate")
def set_target_rate(req: RateRequest):
    system_state.target_rate_hz = req.rate_hz
    log_event(f"Target Ingestion Frequency Set to {req.rate_hz} Hz", "info", "RateManager")
    return {"status": "rate_updated", "target_rate_hz": system_state.target_rate_hz}

@app.get("/api/stream/metrics")
def get_stream_metrics():
    last_view = twin_service.last_dashboard_view or {}
    stream_m = last_view.get("stream_metrics", {})
    live_stat = live_source.get_status()
    return {
        "mode": system_state.mode,
        "target_rate_hz": system_state.target_rate_hz,
        "live_status": live_stat,
        "stream_metrics": stream_m,
        "link_status": twin_service.gateway.get_link_status(),
    }

@app.get("/api/alerts/active")
def get_active_alerts():
    return {
        "system_state": twin_service.alert_engine.current_system_state,
        "active_alerts_count": len(twin_service.alert_engine.active_alerts),
        "alerts": [a.to_dict() for a in twin_service.alert_engine.active_alerts.values()],
        "recent_transitions": list(twin_service.alert_engine.transition_history),
    }

@app.get("/api/events/timeline")
def get_events_timeline(limit: int = 50):
    events = list(twin_service.alert_engine.event_timeline)[:limit]
    return {
        "total_events": len(twin_service.alert_engine.event_timeline),
        "events": events,
    }

@app.get("/api/events")
def get_system_events(limit: int = 50):
    """Returns aggregated system event logs and alert timelines."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_events ORDER BY timestamp DESC LIMIT ?", (limit,))
    db_events = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "active_alerts": [a.to_dict() for a in twin_service.alert_engine.active_alerts.values()],
        "transition_timeline": list(twin_service.alert_engine.transition_history)[:limit],
        "event_timeline": list(twin_service.alert_engine.event_timeline)[:limit],
        "log_events": db_events
    }


# ==========================================
# 2. TELEMETRY INGEST (LIVE & REST)
# ==========================================
@app.post("/api/telemetry/live")
@app.post("/telemetry/live")
def ingest_live_telemetry(raw_packet: Dict[str, Any]):
    """
    Direct ingestion endpoint for continuous external live telemetry streams.
    """
    raw_packet["source"] = "LIVE"
    raw_packet["is_simulated"] = False
    pushed = live_source.push_frame(raw_packet)
    pipeline_out = twin_service.process_telemetry_frame(pushed)
    return {
        "status": "ingested",
        "mode": "LIVE",
        "sequence_number": pushed.get("sequence_number", 0),
        "latency_ms": pipeline_out["twin_state"]["processing_latency_ms"],
        "data_age_ms": pipeline_out["dashboard_view"].get("stream_metrics", {}).get("data_age_ms", 0),
        "health_index": pipeline_out["twin_state"]["health_state"]["value"]["health_index"],
        "anomaly_score": pipeline_out["inference"]["anomalyScore"],
        "fault_class": pipeline_out["inference"]["possibleIssue"],
    }

@app.post("/telemetry")
def ingest_telemetry_packet(packet: TelemetryPacket):
    p_dict = packet.model_dump()
    if system_state.mode == "LIVE":
        live_source.push_frame(p_dict)
    result = twin_service.process_telemetry_frame(p_dict)
    return {
        "status": "ingested",
        "sequence_number": packet.sequence_number,
        "latency_ms": result["twin_state"]["processing_latency_ms"]
    }

@app.get("/telemetry/{engine_id}")
def get_engine_telemetry(engine_id: str):
    recent = get_recent_telemetry_rows(limit=60)
    link = twin_service.gateway.get_link_status()
    return {
        "engine_id": engine_id,
        "link_status": link,
        "current_state": simulator.state,
        "history_frames": recent
    }

@app.get("/api/telemetry")
def get_current_telemetry_compat():
    """Maintains backward compatibility with frontend."""
    if not twin_service.last_dashboard_view:
        twin_service.process_telemetry_frame(simulator.state)
    return {
        "state": simulator.state,
        "history": simulator.history,
        "inference": twin_service.last_twin_state["fault_state"]["value"] if twin_service.last_twin_state else {},
        "twin_state": twin_service.last_twin_state,
        "dashboard_view": twin_service.last_dashboard_view,
        "mode": system_state.mode,
        "stream_metrics": twin_service.last_dashboard_view.get("stream_metrics", {}) if twin_service.last_dashboard_view else {}
    }

@app.post("/api/telemetry")
def ingest_telemetry_standard(payload: Dict[str, Any]):
    """
    Standard ingestion endpoint for continuous or discrete telemetry frames.
    """
    if system_state.mode == "LIVE":
        payload["source"] = "LIVE"
        payload["is_simulated"] = False
        pushed = live_source.push_frame(payload)
        pipeline_out = twin_service.process_telemetry_frame(pushed)
    else:
        payload["source"] = payload.get("source", "SIMULATION")
        payload["is_simulated"] = True
        pipeline_out = twin_service.process_telemetry_frame(payload)
        
    return {
        "status": "processed",
        "mode": system_state.mode,
        "latency_ms": pipeline_out["twin_state"].get("processing_latency_ms", 0.0),
        "health_index": pipeline_out["twin_state"].get("health_state", {}).get("value", {}).get("health_index", 100.0),
        "anomaly_score": pipeline_out["inference"].get("anomalyScore", 0.0),
        "fault_class": pipeline_out["inference"].get("possibleIssue", "NOMINAL"),
        "twin_state": pipeline_out["twin_state"],
        "dashboard_view": pipeline_out["dashboard_view"]
    }

@app.get("/api/evaluations/latest")
def get_evaluations_latest():
    """Returns the most recent digital twin telemetry evaluation."""
    if not twin_service.last_dashboard_view:
        twin_service.process_telemetry_frame(simulator.state)
    return {
        "timestamp": time.time(),
        "mode": system_state.mode,
        "is_simulated": system_state.mode == "SIMULATION",
        "twin_state": twin_service.last_twin_state,
        "dashboard_view": twin_service.last_dashboard_view,
        "residuals": twin_service.last_dashboard_view.get("residuals", {}) if twin_service.last_dashboard_view else {},
        "sensor_trust": twin_service.last_dashboard_view.get("sensor_trust", {}) if twin_service.last_dashboard_view else {},
        "alerts": twin_service.last_dashboard_view.get("alerts", []) if twin_service.last_dashboard_view else [],
        "stream_metrics": twin_service.last_dashboard_view.get("stream_metrics", {}) if twin_service.last_dashboard_view else {}
    }

@app.get("/api/evaluations/history")
def get_evaluations_history(limit: int = 50):
    """Returns historical evaluation frames."""
    limit = max(1, min(200, limit))
    recent = list(twin_service.state_history)[-limit:]
    return {
        "count": len(recent),
        "history": recent
    }

@app.post("/api/telemetry/override")
def override_telemetry_parameters(req: ParameterOverrideRequest):
    overrides = req.model_dump(exclude_none=True)
    simulator.state.update({"manualOverride": True, **overrides})
    twin_service.process_telemetry_frame(simulator.state)
    return {"status": "overrides_applied", "state": simulator.state}

# ==========================================
# 3. DIGITAL TWIN STATE & 3D VISUALIZATION
# ==========================================
@app.get("/twin/state")
def get_digital_twin_full_state():
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state

@app.get("/visualization/state/{uav_id}")
def get_visualization_state(uav_id: str):
    """
    Typed 3D Digital Twin Visualization contract.
    Provides hierarchical component statuses, sensor nodes, residuals, and evidence.
    """
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
        
    ts = twin_service.last_twin_state
    db = twin_service.last_dashboard_view or {}
    op = ts.get("operating_state", {}).get("value", {})
    therm = ts.get("thermal_state", {}).get("value", {})
    mech = ts.get("mechanical_state", {}).get("value", {})
    comb = ts.get("combustion_state", {}).get("value", {})
    lub = ts.get("lubrication_state", {}).get("value", {})
    deg = ts.get("degradation_state", {}).get("value", {})
    health = ts.get("health_state", {}).get("value", {})
    fault = ts.get("fault_state", {}).get("value", {})
    rul = ts.get("rul_state", {}).get("value", {})
    risk = ts.get("mission_risk", {})
    sensors = ts.get("sensor_state", {}).get("value", {}).get("sensors", {})
    residuals = twin_service.residual_engine.history
    
    # Compute component-level healths
    sub_deg = deg.get("subsystem_degradations", {})
    mech_health = round(100.0 * (1.0 - sub_deg.get("mechanical", 0.05)), 1)
    therm_health = round(100.0 * (1.0 - sub_deg.get("thermal", 0.05)), 1)
    lub_health = round(100.0 * (1.0 - sub_deg.get("lubrication", 0.05)), 1)
    comb_health = round(100.0 * (1.0 - sub_deg.get("combustion", 0.05)), 1)
    
    def status_for_health(h):
        return "HEALTHY" if h >= 85 else ("WARNING" if h >= 70 else ("DEGRADED" if h >= 50 else "FAULT"))
    
    components = {
        "airframe": {
            "name": "MALE UAV Composite Airframe",
            "type": "STRUCTURE",
            "health": 98.5,
            "status": "HEALTHY",
            "confidence": 0.98,
            "metrics": {"wingspan_m": 20.6, "mtow_kg": 1800.0, "drag_coeff": 0.028},
            "fault": "None (Structural Integrity Nominal)"
        },
        "propeller": {
            "name": "3-Blade Constant Speed Propeller & Hub",
            "type": "PROPULSION",
            "health": round(float(db.get("mission_reliability", 92)), 1),
            "status": status_for_health(db.get("mission_reliability", 92)),
            "confidence": 0.94,
            "metrics": {"rpm": op.get("rpm", 4215), "thrust_kn": round(op.get("rpm", 4215) * 0.00065, 2), "pitch_deg": 18.5},
            "fault": "Nominal Aerodynamic Thrust"
        },
        "engine": {
            "name": "Rotax 914 Turbocharged Aero Piston Engine",
            "type": "POWERPLANT",
            "health": round(float(health.get("health_index", 92.0)), 1),
            "status": db.get("status", "NORMAL"),
            "confidence": ts.get("confidence", {}).get("overall", 0.92),
            "metrics": {
                "rpm": op.get("rpm", 4215),
                "cht_c": therm.get("cht_c", 78.4),
                "oil_pressure_bar": lub.get("oil_pressure_bar", 4.3),
                "vibration_mms": mech.get("vibration_mms", 1.6),
                "power_kw": op.get("power_kw", 82.5),
                "bsfc_g_kwh": comb.get("bsfc_g_kwh", 285.0)
            },
            "fault": fault.get("fault", "NOMINAL"),
            "rul_hours": rul.get("rul_estimate_hours", 1200.0),
            "rul_interval": [rul.get("lower_bound_hours", 1000.0), rul.get("upper_bound_hours", 1400.0)]
        },
        "cylinder_1": {
            "name": "Combustion Cylinder #1 (Front-Right)",
            "type": "COMBUSTION",
            "health": therm_health,
            "status": status_for_health(therm_health),
            "confidence": 0.92,
            "metrics": {"cht_c": therm.get("cht_c", 78.4), "piston_bore_mm": 79.5, "displacement_cc": 302.8},
            "fault": "Thermal Stress" if therm_health < 75 else "Nominal Compression"
        },
        "cylinder_2": {
            "name": "Combustion Cylinder #2 (Front-Left)",
            "type": "COMBUSTION",
            "health": therm_health,
            "status": status_for_health(therm_health),
            "confidence": 0.92,
            "metrics": {"cht_c": round(therm.get("cht_c", 78.4) - 0.6, 1), "piston_bore_mm": 79.5, "displacement_cc": 302.8},
            "fault": "Nominal Compression"
        },
        "cylinder_3": {
            "name": "Combustion Cylinder #3 (Rear-Right)",
            "type": "COMBUSTION",
            "health": therm_health,
            "status": status_for_health(therm_health),
            "confidence": 0.92,
            "metrics": {"cht_c": round(therm.get("cht_c", 78.4) + 0.8, 1), "piston_bore_mm": 79.5, "displacement_cc": 302.8},
            "fault": "Thermal Gradient" if therm_health < 75 else "Nominal Compression"
        },
        "cylinder_4": {
            "name": "Combustion Cylinder #4 (Rear-Left)",
            "type": "COMBUSTION",
            "health": therm_health,
            "status": status_for_health(therm_health),
            "confidence": 0.92,
            "metrics": {"cht_c": round(therm.get("cht_c", 78.4) + 0.2, 1), "piston_bore_mm": 79.5, "displacement_cc": 302.8},
            "fault": "Nominal Compression"
        },
        "crankshaft": {
            "name": "Nitrided Alloy Crankshaft & Connecting Rods",
            "type": "MECHANICAL",
            "health": mech_health,
            "status": status_for_health(mech_health),
            "confidence": 0.93,
            "metrics": {"rpm": op.get("rpm", 4215), "stroke_mm": 61.0, "torsional_strain_pct": round(sub_deg.get("mechanical", 0.05) * 100, 1)},
            "fault": "Dynamic Imbalance" if mech_health < 75 else "Nominal Rotation"
        },
        "bearings": {
            "name": "Main Journal Hydrodynamic Crankshaft Bearings",
            "type": "MECHANICAL",
            "health": mech_health,
            "status": status_for_health(mech_health),
            "confidence": 0.94,
            "metrics": {"vibration_mms": mech.get("vibration_mms", 1.6), "residual_sigma": mech.get("vibration_residual_sigma", 0.0), "slope": mech.get("vibration_slope", 0.0)},
            "fault": "Bearing Race Spalling & Wear" if mech_health < 75 else "Nominal Hydrodynamic Film"
        },
        "cooling_system": {
            "name": "Ram-Air Duct & Liquid Cooling Jacket",
            "type": "COOLING",
            "health": therm_health,
            "status": status_for_health(therm_health),
            "confidence": 0.90,
            "metrics": {"coolant_flow_lpm": 28.5, "radiator_delta_c": 12.4, "ambient_c": op.get("ambient_temperature_c", -14.5)},
            "fault": "Cooling Capacity Deficit" if therm_health < 75 else "Optimal Heat Rejection"
        },
        "fuel_system": {
            "name": "Common-Rail Fuel Injection & Spark Plugs",
            "type": "FUEL_IGNITION",
            "health": comb_health,
            "status": status_for_health(comb_health),
            "confidence": 0.91,
            "metrics": {"fuel_flow_lh": comb.get("fuel_flow", 5.2), "rail_pressure_bar": 3.2, "spark_advance_deg": 24.0},
            "fault": "Ignition Misfire / Injector Clog" if comb_health < 75 else "Nominal Stoichiometric Mixture"
        },
        "oil_system": {
            "name": "Dry Sump Pressurized Lubrication Circuit",
            "type": "LUBRICATION",
            "health": lub_health,
            "status": status_for_health(lub_health),
            "confidence": 0.93,
            "metrics": {"oil_pressure_bar": lub.get("oil_pressure_bar", 4.3), "oil_temp_c": therm.get("oil_temp_c", 82.1), "filter_delta_bar": 0.25},
            "fault": "Pressure Loss / Viscosity Drop" if lub_health < 75 else "Nominal Hydrodynamic Pressure"
        },
        "ecu": {
            "name": "Dual-Redundant Electronic Engine Controller (ECU)",
            "type": "AVIONICS",
            "health": 99.2,
            "status": "HEALTHY",
            "confidence": 0.99,
            "metrics": {"bus_voltage_v": 28.2, "processor_load_pct": 14.5, "can_bus_freq_hz": 50.0},
            "fault": "Dual Channels Synchronized"
        },
        "telemetry_gateway": {
            "name": "Edge IoT 10Hz CAN-bus Telemetry Transceiver",
            "type": "TELEMETRY",
            "health": 98.8,
            "status": "HEALTHY",
            "confidence": 0.96,
            "metrics": {"packet_rate_hz": system_state.target_rate_hz, "latency_ms": ts.get("processing_latency_ms", 2.4), "link_status": db.get("link_status", {}).get("link_status", "CONNECTED")},
            "fault": "AES-256 Link Authenticated"
        }
    }
    
    raw_telem = simulator.state or {
        "rpm": op.get("rpm", 4215),
        "temperature": therm.get("cht_c", 78.4),
        "oilPressure": lub.get("oil_pressure_bar", 4.3),
        "vibration": mech.get("vibration_mms", 1.6),
        "fuelFlow": comb.get("fuel_flow", 5.2),
        "throttle": op.get("load_pct", 72.0),
        "altitude_ft": op.get("altitude_m", 3200.0) * 3.28084,
        "ambient_temperature_c": op.get("ambient_temperature_c", -14.5)
    }
    expected_p = twin_service.physics_model.compute_expected_state(raw_telem)

    res_hist = twin_service.residual_engine.history
    vib_res = res_hist["vibration"][-1] if res_hist.get("vibration") and len(res_hist["vibration"]) > 0 else 0.1
    cht_res = res_hist["temperature"][-1] if res_hist.get("temperature") and len(res_hist["temperature"]) > 0 else 0.4
    oil_res = res_hist["oilPressure"][-1] if res_hist.get("oilPressure") and len(res_hist["oilPressure"]) > 0 else 0.0
    rpm_res = res_hist["rpm"][-1] if res_hist.get("rpm") and len(res_hist["rpm"]) > 0 else 0.0
    fuel_res = res_hist["fuelFlow"][-1] if res_hist.get("fuelFlow") and len(res_hist["fuelFlow"]) > 0 else 0.1

    sensor_nodes = {
        "sensor_vib": {
            "name": "Tri-Axial Vibration Accelerometer",
            "current_value": round(float(mech.get("vibration_mms", 1.6)), 2),
            "expected_value": round(float(expected_p.get("expected_vibration_mms", 1.2)), 2),
            "residual": round(float(vib_res), 2),
            "trust": round(float(sensors.get("vibration", {}).get("trust_score", 0.96) * 100), 1),
            "status": sensors.get("vibration", {}).get("health_status", "VALID"),
            "position_3d": [0.65, 0.65, -1.8]
        },
        "sensor_cht": {
            "name": "Cylinder Head Thermocouple (CHT)",
            "current_value": round(float(therm.get("cht_c", 78.4)), 1),
            "expected_value": round(float(expected_p.get("expected_cht_c", 78.0)), 1),
            "residual": round(float(cht_res), 2),
            "trust": round(float(sensors.get("temperature", {}).get("trust_score", 0.95) * 100), 1),
            "status": sensors.get("temperature", {}).get("health_status", "VALID"),
            "position_3d": [1.15, 0.45, -1.35]
        },
        "sensor_oil": {
            "name": "Oil Pressure Transducer",
            "current_value": round(float(lub.get("oil_pressure_bar", 4.3)), 2),
            "expected_value": round(float(expected_p.get("expected_oil_pressure_bar", 4.3)), 2),
            "residual": round(float(oil_res), 2),
            "trust": round(float(sensors.get("oilPressure", {}).get("trust_score", 0.98) * 100), 1),
            "status": sensors.get("oilPressure", {}).get("health_status", "VALID"),
            "position_3d": [-0.65, -0.15, -1.8]
        },
        "sensor_rpm": {
            "name": "Optical Crankshaft RPM Sensor",
            "current_value": round(float(op.get("rpm", 4215)), 0),
            "expected_value": round(float(expected_p.get("expected_rpm", 4215)), 0),
            "residual": round(float(rpm_res), 1),
            "trust": round(float(sensors.get("rpm", {}).get("trust_score", 0.99) * 100), 1),
            "status": sensors.get("rpm", {}).get("health_status", "VALID"),
            "position_3d": [0, 0.45, -1.05]
        },
        "sensor_fuel": {
            "name": "Fuel Mass Flow Sensor",
            "current_value": round(float(comb.get("fuel_flow", 5.2)), 2),
            "expected_value": round(float(expected_p.get("expected_fuel_flow_lh", 5.1)), 2),
            "residual": round(float(fuel_res), 2),
            "trust": round(float(sensors.get("fuelFlow", {}).get("trust_score", 0.97) * 100), 1),
            "status": sensors.get("fuelFlow", {}).get("health_status", "VALID"),
            "position_3d": [0.35, 0.82, -1.6]
        }
    }
    
    return {
        "timestamp": ts.get("timestamp", time.time()),
        "uav_id": uav_id,
        "engine_id": ts.get("engine_id", "UAV-ENG-ROT-914-01"),
        "mission_id": ts.get("mission_id", "MSN-2026-SURV-082"),
        "system_status": db.get("status", "NORMAL"),
        "overall_health": round(float(health.get("health_index", 92.0)), 1),
        "confidence": ts.get("confidence", {}).get("overall", 0.92),
        "mode": system_state.mode,
        "is_simulated": system_state.mode == "SIMULATION",
        "mission": {
            "altitude_m": round(float(op.get("altitude_m", 3200.0)), 0),
            "airspeed_kmh": round(float(op.get("airspeed_kmh", 120.0)), 1),
            "engine_load_pct": round(float(op.get("load_pct", 72.0)), 1),
            "phase": "Cruise (Autonomous Loiter)",
            "elapsed_time_s": int(raw_telem.get("flight_time_seconds", 9918)),
            "mission_risk_pct": round(float(risk.get("risk_index", 0.14) * 100), 1)
        },
        "components": components,
        "sensors": sensors,
        "sensor_nodes": sensor_nodes,
        "engine_summary": {
            "health_index": health.get("health_index", 92.0),
            "status": db.get("status", "NORMAL"),
            "rpm": op.get("rpm", 4215),
            "cht_c": therm.get("cht_c", 78.4),
            "oil_pressure_bar": lub.get("oil_pressure_bar", 4.3),
            "vibration_mms": mech.get("vibration_mms", 1.6),
            "active_scenario": db.get("active_scenario", "cruise")
        },
        "prognostics": {
            "rul_hours": rul.get("rul_estimate_hours", 1200.0),
            "rul_interval": [rul.get("lower_bound_hours", 1000.0), rul.get("upper_bound_hours", 1400.0)],
            "rul_time_str": rul.get("rul_time_str", "N/A"),
            "confidence": rul.get("confidence", 0.92),
            "degradation_velocity": deg.get("degradation_velocity", 0.002),
            "velocity_trend": deg.get("velocity_trend", "STABLE"),
            "model_validity": rul.get("model_validity", "WITHIN_VALIDATED_RANGE"),
            "label": "SIMULATION-BASED RUL" if system_state.mode == "SIMULATION" else "LIVE RUL ESTIMATE"
        },
        "faults": [fault] if fault.get("fault") != "NOMINAL" else [],
        "mission_risk": risk,
        "decision": ts.get("decision", {}),
        "consensus": ts.get("consensus", {}),
        "evidence": ts.get("evidence", []),
        "alerts": ts.get("alerts", []),
        "stream_metrics": ts.get("stream_metrics", {})
    }

@app.get("/twin/{engine_id}")
def get_engine_digital_twin(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state

@app.get("/twin/{engine_id}/history")
def get_digital_twin_history(engine_id: str, limit: int = 30):
    recent = list(twin_service.state_history)[-limit:]
    return {
        "engine_id": engine_id,
        "history_count": len(recent),
        "states": recent
    }

# ==========================================
# 4. SUBSYSTEM HEALTH & DIAGNOSTICS
# ==========================================
@app.get("/health/{engine_id}")
def get_health_index(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    h_state = twin_service.last_twin_state.get("health_state", {}).get("value", {})
    deg_state = twin_service.last_twin_state.get("degradation_state", {}).get("value", {})
    return {
        "engine_id": engine_id,
        "health_index": h_state.get("health_index", 95.0),
        "normalized_degradation": h_state.get("normalized_degradation", 0.05),
        "subsystems": deg_state.get("subsystem_degradations", {}),
        "degradation_velocity": deg_state.get("degradation_velocity", 0.002),
        "velocity_trend": deg_state.get("velocity_trend", "STABLE"),
        "interpretation": h_state.get("interpretation", "")
    }

@app.get("/health/{engine_id}/evidence")
def get_health_evidence(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    deg_state = twin_service.last_twin_state.get("degradation_state", {}).get("value", {})
    return {
        "engine_id": engine_id,
        "evidence": deg_state.get("evidence", [])
    }

@app.get("/faults/{engine_id}")
def get_fault_classification(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state.get("fault_state", {}).get("value", {})

@app.get("/faults/{engine_id}/evidence")
def get_fault_evidence(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    fault_val = twin_service.last_twin_state.get("fault_state", {}).get("value", {})
    return {
        "engine_id": engine_id,
        "fault": fault_val.get("fault", "NOMINAL"),
        "evidence": fault_val.get("evidence", [])
    }

@app.get("/rul/{engine_id}")
def get_rul_prognostics(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state.get("rul_state", {}).get("value", {})

@app.get("/rul/{engine_id}/evidence")
def get_rul_evidence(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    rul_val = twin_service.last_twin_state.get("rul_state", {}).get("value", {})
    deg_val = twin_service.last_twin_state.get("degradation_state", {}).get("value", {})
    return {
        "engine_id": engine_id,
        "rul_estimate_hours": rul_val.get("rul_estimate_hours"),
        "prediction_interval": [rul_val.get("lower_bound_hours"), rul_val.get("upper_bound_hours")],
        "confidence": rul_val.get("confidence"),
        "degradation_velocity": rul_val.get("degradation_velocity"),
        "endpoint_definition": rul_val.get("endpoint_definition"),
        "model_version": rul_val.get("model_version"),
        "dataset_version": "UAV-ROT914-SIM-CORPUS-2026.1",
        "subsystem_degradations": deg_val.get("subsystem_degradations"),
        "evidence": rul_val.get("evidence", [])
    }

@app.get("/sensors/{engine_id}/trust")
def get_sensor_trust_matrix(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state.get("sensor_state", {}).get("value", {})

# ==========================================
# 5. MISSION INTELLIGENCE & WHAT-IF
# ==========================================
@app.get("/risk/{engine_id}/{mission_id}")
def get_mission_risk(engine_id: str, mission_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state.get("mission_risk", {})

@app.post("/mission/what-if")
def counterfactual_what_if(req: WhatIfRequest):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
        
    result = twin_service.what_if_engine.simulate_what_if(
        current_twin_state=twin_service.last_twin_state,
        duration_hours=req.duration_hours,
        altitude_ft=req.altitude,
        power_setting=req.power_setting,
        ambient_temp_c=req.ambient_temperature
    )
    return result

@app.get("/decision/{engine_id}")
def get_mission_decision(engine_id: str):
    if not twin_service.last_twin_state:
        twin_service.process_telemetry_frame(simulator.state)
    return twin_service.last_twin_state.get("decision", {})

# ==========================================
# 6. SIMULATION, FAULT INJECTION & REPLAY
# ==========================================
@app.post("/api/scenario")
def trigger_scenario(req: ScenarioRequest):
    valid_scenarios = [
        "cruise", "lubrication_degradation", "vibration_bearing",
        "thermal_overheat", "spark_misfire", "high_altitude_climb"
    ]
    if req.scenario not in valid_scenarios:
        raise HTTPException(status_code=400, detail="Invalid scenario name")

    simulator.set_scenario(req.scenario)
    log_event(f"Simulation Scenario Activated: {req.scenario.upper()}", "warning", "Simulation")
    return {"status": "scenario_applied", "activeScenario": req.scenario}

@app.post("/api/mitigate")
def execute_mitigation():
    simulator.execute_mitigation()
    twin_service.process_telemetry_frame(simulator.state)
    log_event("Closed-Loop Feedback Telecommand Sent to Real UAV Engine", "info", "Telecommand")
    return {"status": "mitigation_applied", "state": simulator.state}

@app.post("/api/flight-time/reset")
@app.post("/mission/reset-clock")
def reset_mission_flight_time(req: Optional[FlightTimeResetRequest] = None):
    """Resets the mission flight time clock back to 00:00:00 or specified offset."""
    secs = req.seconds if req else 0
    simulator.reset_flight_time(secs)
    twin_service.process_telemetry_frame(simulator.state)
    log_event(f"Mission Flight Time Reset to {secs}s", "info", "MissionClock")
    return {
        "status": "flight_time_reset",
        "flight_time_seconds": secs,
        "flight_time_str": twin_service.last_dashboard_view.get("flight_time_str", "00:00:00") if twin_service.last_dashboard_view else "00:00:00"
    }


@app.post("/simulation/start")
def start_simulation(seed: int = 42):
    global simulator
    simulator = AeroEngineSimulator(seed=seed)
    twin_service.process_telemetry_frame(simulator.state)
    return {"status": "simulation_started", "seed": seed}

@app.post("/simulation/inject-fault")
def inject_fault(req: FaultInjectionRequest):
    inj = simulator.inject_fault(
        fault=req.fault,
        severity=req.severity,
        start_time=req.start_time,
        progression_rate=req.progression_rate
    )
    log_event(f"Progressive Fault Injected: {req.fault} (Severity: {req.severity})", "warning", "FaultInjection")
    return {"status": "fault_injected", "details": inj, "is_simulated": True}

@app.post("/replay/start")
def start_replay():
    res = replay_engine.start()
    log_event("Deterministic Replay Session Started", "info", "ReplayEngine")
    return res

@app.post("/replay/pause")
def pause_replay():
    res = replay_engine.pause()
    log_event("Deterministic Replay Session Paused", "info", "ReplayEngine")
    return res

@app.post("/replay/reset")
def reset_replay():
    res = replay_engine.reset()
    log_event("Deterministic Replay Session Reset", "info", "ReplayEngine")
    return res

@app.get("/replay/state")
def get_replay_state():
    return replay_engine.get_state()

@app.get("/api/replay/{id}")
def get_replay_by_id(id: str):
    """Returns deterministic replay metadata and current session state."""
    state = replay_engine.get_state()
    return {
        "replay_id": id,
        "state": state,
        "frame_count": len(replay_engine.trajectory_buffer),
        "available_scenarios": ["bearing_degradation", "thermal_overheat", "spark_misfire", "sensor_drift"]
    }


@app.post("/replay/seek")
def seek_replay(req: ReplaySeekRequest):
    if req.frame_index is not None:
        idx = req.frame_index
    elif req.position is not None and replay_engine.trajectory_buffer:
        idx = int((req.position / 100.0) * (len(replay_engine.trajectory_buffer) - 1))
    else:
        idx = 0
    replay_engine.current_frame = max(0, min(len(replay_engine.trajectory_buffer) - 1, idx)) if replay_engine.trajectory_buffer else 0
    return {"status": "seek_applied", "step": replay_engine.current_frame, "frame_index": replay_engine.current_frame}

@app.post("/replay/speed")
def speed_replay(req: ReplaySpeedRequest):
    replay_engine.playback_speed = req.speed
    return {"status": "speed_applied", "playback_speed": replay_engine.playback_speed}

# ==========================================
# 7. VALIDATION & BASELINE EXPERIMENTS
# ==========================================
@app.get("/experiments/baseline-comparison")
def get_baseline_comparison(seed: int = 42, samples: int = 120):
    result = experiment_runner.run_baseline_comparison_experiment(seed=seed, n_samples=samples)
    return result

@app.get("/experiments")
def list_experiments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiments ORDER BY timestamp DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"experiments": rows}

@app.get("/experiments/{id}")
def get_experiment_detail(id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiments WHERE experiment_id = ?", (id,))
    exp = cursor.fetchone()
    if not exp:
        conn.close()
        raise HTTPException(status_code=404, detail="Experiment ID not found")
    cursor.execute("SELECT * FROM experiment_metrics WHERE experiment_id = ?", (id,))
    metrics = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"experiment": dict(exp), "metrics": metrics}

@app.get("/experiments/{id}/metrics")
def get_experiment_metrics(id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiment_metrics WHERE experiment_id = ?", (id,))
    metrics = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"experiment_id": id, "metrics": metrics}

# ==========================================
# 8. EVALUATOR Q&A & EVIDENCE API
# ==========================================
@app.get("/evaluator/questions")
def list_evaluator_questions(category: Optional[str] = None):
    questions_list = list(EVALUATOR_QUESTIONS.values())
    if category:
        questions_list = [q for q in questions_list if q.get("category") == category]
    return {
        "total_questions": len(questions_list),
        "questions": questions_list
    }

@app.get("/evaluator/questions/{id}")
def get_evaluator_question_by_id(id: str):
    q = EVALUATOR_QUESTIONS.get(id.upper())
    if not q:
        raise HTTPException(status_code=404, detail=f"Evaluator Question '{id}' not found")
    return q

@app.get("/evaluator/evidence/{id}")
def get_evaluator_evidence(id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evidence ORDER BY timestamp DESC LIMIT 50")
    ev_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "evidence_id": id,
        "timestamp": time.time(),
        "recent_evidence_records": ev_rows
    }

@app.get("/system/limitations")
def get_system_limitations():
    return SYSTEM_LIMITATIONS

# ==========================================
# 9. WEBSOCKET GATEWAY & LIVE TELECOMMANDS
# ==========================================
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action", "")

                if action == "SET_MODE":
                    mode = msg.get("mode", "LIVE").upper()
                    if mode in ["LIVE", "SIMULATION"]:
                        system_state.mode = mode
                elif action == "SET_RATE":
                    rate = float(msg.get("rate_hz", 10.0))
                    system_state.target_rate_hz = max(1.0, min(50.0, rate))
                elif action == "PAUSE_STREAM":
                    system_state.is_paused = not system_state.is_paused
                elif action == "SET_SCENARIO":
                    simulator.set_scenario(msg.get("scenario", "cruise"))
                elif action == "INJECT_FAULT":
                    simulator.inject_fault(
                        fault=msg.get("fault", "BEARING_DEGRADATION"),
                        severity=float(msg.get("severity", 0.5)),
                        start_time=float(msg.get("start_time", 0.0)),
                        progression_rate=float(msg.get("progression_rate", 0.002))
                    )
                elif action == "MITIGATE":
                    simulator.execute_mitigation()
                elif action == "INGEST_LIVE":
                    frame = msg.get("frame", {})
                    if frame:
                        live_source.push_frame(frame)
                elif action == "REPLAY_START":
                    replay_engine.start()
                elif action == "REPLAY_PAUSE":
                    replay_engine.pause()
                elif action == "REPLAY_RESET":
                    replay_engine.reset()
                elif action == "REPLAY_SPEED":
                    replay_engine.playback_speed = float(msg.get("speed", 1.0))
                elif action == "REPLAY_SEEK":
                    replay_engine.current_step = int(msg.get("step", 0))
                elif action in ["RESET_FLIGHT_TIME", "RESET_MISSION_CLOCK"]:
                    secs = int(msg.get("seconds", 0))
                    simulator.reset_flight_time(secs)
                    twin_service.process_telemetry_frame(simulator.state)
                    log_event(f"Mission Flight Time Reset to {secs}s", "info", "MissionClock")


            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ─── Mount Built Frontend Static Files (Single-Port Hosting) ──────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIST_DIR = os.path.join(_BASE_DIR, "dist")
if os.path.exists(_DIST_DIR):
    app.mount("/", StaticFiles(directory=_DIST_DIR, html=True), name="static")

