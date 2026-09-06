"""
Telemetry Sources Abstraction for AERIS-TWIN
Defines unified interface for:
- LiveStreamSource: Real-time telemetry from external REST/WebSocket clients
- FileReplaySource: Deterministic playback of recorded mission telemetry
- SimulationSource: Physics-grounded engine simulator with fault injection
- MAVLinkSource: Adapter for MAVLink protocol packets
"""
import abc
import time
import math
import random
from typing import Dict, Any, Optional, List
from collections import deque


class TelemetrySource(abc.ABC):
    """Abstract base class for all normalized telemetry sources."""

    @abc.abstractmethod
    def get_source_type(self) -> str:
        """Returns the source identifier (e.g. LIVE, SIMULATION, REPLAY, MAVLINK)."""
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the source is actively providing data."""
        pass

    @abc.abstractmethod
    def get_frame(self) -> Optional[Dict[str, Any]]:
        """Retrieves or produces the next normalized telemetry frame."""
        pass

    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns source-specific status metrics."""
        pass


class LiveStreamSource(TelemetrySource):
    """
    Ingests continuous telemetry from external live streams (REST / WebSocket / IoT Gateway).
    If no packet has arrived within timeout, reports NOT CONNECTED rather than synthesizing fake data.
    """

    def __init__(self, stale_timeout_sec: float = 3.0, disconnect_timeout_sec: float = 6.0):
        self.stale_timeout_sec = stale_timeout_sec
        self.disconnect_timeout_sec = disconnect_timeout_sec

        self._buffer: deque = deque(maxlen=200)
        self.last_received_time: Optional[float] = None
        self.last_packet_timestamp: Optional[float] = None
        self.last_sequence_num: int = -1
        self.total_received: int = 0
        self.total_dropped: int = 0
        self.last_frame: Optional[Dict[str, Any]] = None

    def get_source_type(self) -> str:
        return "LIVE"

    def push_frame(self, raw_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Called when an external live telemetry frame is received."""
        now = time.time()
        self.last_received_time = now
        self.total_received += 1

        seq = raw_frame.get("sequence_number", self.last_sequence_num + 1)
        if self.last_sequence_num >= 0 and seq > (self.last_sequence_num + 1):
            dropped = seq - (self.last_sequence_num + 1)
            self.total_dropped += dropped
        self.last_sequence_num = seq

        ts = raw_frame.get("timestamp", now)
        self.last_packet_timestamp = ts

        # Tag normalized frame
        raw_frame["_ingest_time"] = now
        raw_frame["source"] = "LIVE"
        self.last_frame = raw_frame
        self._buffer.append(raw_frame)
        return raw_frame

    def is_connected(self) -> bool:
        if self.last_received_time is None:
            return False
        age = time.time() - self.last_received_time
        return age <= self.disconnect_timeout_sec

    def is_stale(self) -> bool:
        if self.last_received_time is None:
            return True
        age = time.time() - self.last_received_time
        return age > self.stale_timeout_sec

    def get_frame(self) -> Optional[Dict[str, Any]]:
        if self._buffer:
            return self._buffer.popleft()
        return None

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        if self.last_received_time is None:
            age_sec = None
            status = "NOT CONNECTED"
        else:
            age_sec = round(now - self.last_received_time, 3)
            if age_sec > self.disconnect_timeout_sec:
                status = "DISCONNECTED"
            elif age_sec > self.stale_timeout_sec:
                status = "STALE"
            else:
                status = "CONNECTED"

        total_expected = self.total_received + self.total_dropped
        loss_rate = round((self.total_dropped / max(1, total_expected)) * 100.0, 2)

        return {
            "source": "LIVE",
            "status": status,
            "connected": self.is_connected(),
            "packet_age_seconds": age_sec,
            "data_age_ms": round(age_sec * 1000.0, 1) if age_sec is not None else None,
            "total_received": self.total_received,
            "total_dropped": self.total_dropped,
            "packet_loss_pct": loss_rate,
            "last_sequence": self.last_sequence_num,
            "last_packet_time": self.last_received_time,
        }


class SimulationSource(TelemetrySource):
    """
    Generates deterministic, physics-informed synthetic telemetry for Rotax 914 aero piston engine.
    Supports scenario selection and progressive fault injection for testing.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

        self.tick = 0
        self.flight_time_seconds = 9918  # T+ 02:45:18 initial
        self.active_scenario = "cruise"
        self.is_running = True
        self.speed_multiplier = 1.0

        # Nominal Rotax 914 Baselines
        self.base_rpm = 4215.0
        self.base_cht = 78.4
        self.base_oil_p = 4.3
        self.base_vib = 1.6
        self.base_fuel = 5.2
        self.base_load = 62.0
        self.base_altitude = 15000.0
        self.base_ambient_temp = -14.5

        # Active injected faults
        self.injected_faults: List[Dict[str, Any]] = []

        # Current state
        self.state = self._compute_initial_state()

    def get_source_type(self) -> str:
        return "SIMULATION"

    def is_connected(self) -> bool:
        return True

    def _compute_initial_state(self) -> Dict[str, Any]:
        return {
            "engine_id": "UAV-ENG-ROT-914-01",
            "uav_id": "MALE-UAV-TAPAS-04",
            "mission_id": "MSN-2026-SURV-082",
            "timestamp": time.time(),
            "sequence_number": self.tick,
            "rpm": self.base_rpm,
            "temperature": self.base_cht,
            "oilPressure": self.base_oil_p,
            "vibration": self.base_vib,
            "fuelFlow": self.base_fuel,
            "engineLoad": self.base_load,
            "altitude_ft": self.base_altitude,
            "airspeed_kts": 85.0,
            "throttle": 68.0,
            "map_kpa": 96.4,
            "egt_c": 645.0,
            "oil_temperature_c": 82.1,
            "ambient_temperature_c": self.base_ambient_temp,
            "flight_phase": "CRUISE",
            "flight_time_seconds": self.flight_time_seconds,
            "activeScenario": self.active_scenario,
            "engineHealth": 92,
            "missionReliability": 92,
            "status": "NORMAL",
            "source": "SIMULATION",
            "is_simulated": True,
        }

    def set_scenario(self, scenario: str):
        self.active_scenario = scenario

    def inject_fault(self, fault: str, severity: float = 0.5, start_time: float = 0.0, progression_rate: float = 0.002) -> Dict[str, Any]:
        fault_record = {
            "id": f"FAULT-{len(self.injected_faults)+1}",
            "fault": fault,
            "severity": severity,
            "start_time": start_time or self.flight_time_seconds,
            "progression_rate": progression_rate,
            "injected_at": time.time(),
            "active": True,
        }
        self.injected_faults.append(fault_record)
        return fault_record

    def clear_faults(self):
        self.injected_faults.clear()
        self.active_scenario = "cruise"

    def execute_mitigation(self):
        self.active_scenario = "cruise"
        self.injected_faults.clear()

    def get_frame(self) -> Optional[Dict[str, Any]]:
        self.tick += 1
        self.flight_time_seconds += 1
        now = time.time()

        # Gaussian sensor noise
        n_rpm = random.gauss(0, 12.0)
        n_cht = random.gauss(0, 0.25)
        n_oil = random.gauss(0, 0.03)
        n_vib = random.gauss(0, 0.05)
        n_fuel = random.gauss(0, 0.04)
        n_load = random.gauss(0, 0.4)

        rpm = self.base_rpm + n_rpm
        cht = self.base_cht + n_cht
        oil_p = self.base_oil_p + n_oil
        vib = self.base_vib + n_vib
        fuel = self.base_fuel + n_fuel
        load = self.base_load + n_load
        egt = 645.0 + random.gauss(0, 2.5)

        # Apply scenario dynamics
        if self.active_scenario == "lubrication_degradation":
            # Pressure drops, oil temp climbs, vibration slightly rises
            drop = min(2.4, self.tick * 0.035)
            oil_p = max(1.8, self.base_oil_p - drop + n_oil)
            cht += min(14.0, drop * 5.0)
            vib += min(0.8, drop * 0.35)

        elif self.active_scenario == "vibration_bearing":
            # Progressive bearing race wear
            growth = min(4.8, self.tick * 0.065)
            vib = self.base_vib + growth + n_vib
            oil_p -= min(0.6, growth * 0.1)

        elif self.active_scenario == "thermal_overheat":
            # Cooling deficiency, CHT & EGT surge
            surge = min(32.0, self.tick * 0.45)
            cht = self.base_cht + surge + n_cht
            egt += surge * 1.4

        elif self.active_scenario == "spark_misfire":
            # Rough running, power loss, cyclic RPM wobble
            wobble = math.sin(self.tick * 0.8) * 140.0
            rpm = self.base_rpm - 280.0 + wobble + n_rpm
            vib += 1.4 + abs(math.sin(self.tick * 0.8) * 0.6)
            fuel += 0.85
            load += 8.0

        elif self.active_scenario == "high_altitude_climb":
            # Heavy climb load, lower ambient temp
            rpm = 4950.0 + n_rpm
            load = 88.0 + n_load
            cht += 6.5
            fuel = 7.4 + n_fuel

        # Apply custom injected faults
        for f in self.injected_faults:
            if not f.get("active", True):
                continue
            f_type = f.get("fault", "")
            sev = f.get("severity", 0.5)
            rate = f.get("progression_rate", 0.002)
            elapsed = max(0.0, self.flight_time_seconds - f.get("start_time", 0.0))
            current_sev = min(1.0, sev + elapsed * rate)

            if "BEARING" in f_type:
                vib += current_sev * 4.5
            elif "COOLING" in f_type or "THERMAL" in f_type or "EGT" in f_type:
                cht += current_sev * 28.0
                egt += current_sev * 65.0
            elif "OIL" in f_type or "LUBRICATION" in f_type:
                oil_p = max(1.2, oil_p - current_sev * 2.2)
            elif "FUEL" in f_type:
                fuel += current_sev * 3.5
            elif "SPARK" in f_type:
                rpm -= current_sev * 350.0
                vib += current_sev * 2.0

        self.state = {
            "engine_id": "UAV-ENG-ROT-914-01",
            "uav_id": "MALE-UAV-TAPAS-04",
            "mission_id": "MSN-2026-SURV-082",
            "timestamp": now,
            "sequence_number": self.tick,
            "rpm": round(rpm, 1),
            "temperature": round(cht, 1),
            "oilPressure": round(oil_p, 2),
            "vibration": round(vib, 2),
            "fuelFlow": round(fuel, 2),
            "engineLoad": round(load, 1),
            "egt_c": round(egt, 1),
            "altitude_ft": self.base_altitude,
            "airspeed_kts": 85.0,
            "throttle": 68.0,
            "map_kpa": 96.4,
            "oil_temperature_c": round(82.1 + (cht - 78.4) * 0.6, 1),
            "ambient_temperature_c": self.base_ambient_temp,
            "flight_phase": "CRUISE",
            "flight_time_seconds": self.flight_time_seconds,
            "activeScenario": self.active_scenario,
            "source": "SIMULATION",
            "is_simulated": True,
        }
        return self.state

    def get_status(self) -> Dict[str, Any]:
        return {
            "source": "SIMULATION",
            "status": "RUNNING",
            "connected": True,
            "scenario": self.active_scenario,
            "tick": self.tick,
            "flight_time_seconds": self.flight_time_seconds,
            "active_faults_count": len(self.injected_faults),
        }

    def reset_flight_time(self, seconds: int = 0):
        """Resets the simulation flight time counter."""
        self.flight_time_seconds = max(0, seconds)
        return {"status": "flight_time_reset", "flight_time_seconds": self.flight_time_seconds}



class FileReplaySource(TelemetrySource):
    """
    Deterministic playback of recorded mission telemetry frames from file/memory/SQLite.
    Supports pause, resume, seek, and speed multiplier (0.5x to 10x).
    """

    def __init__(self, frames: Optional[List[Dict[str, Any]]] = None):
        self.frames: List[Dict[str, Any]] = frames or []
        self.cursor: int = 0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.loop: bool = True

    def load_frames(self, frames: List[Dict[str, Any]]):
        self.frames = frames
        self.cursor = 0

    def get_source_type(self) -> str:
        return "REPLAY"

    def is_connected(self) -> bool:
        return len(self.frames) > 0

    def play(self):
        self.is_playing = True

    def pause(self):
        self.is_playing = False

    def seek(self, frame_index: int):
        if self.frames:
            self.cursor = max(0, min(len(self.frames) - 1, frame_index))

    def set_speed(self, speed: float):
        self.playback_speed = max(0.1, min(20.0, speed))

    def get_frame(self) -> Optional[Dict[str, Any]]:
        if not self.frames:
            return None
        if not self.is_playing:
            # Return current paused frame with updated timestamp tag
            frame = dict(self.frames[self.cursor])
            frame["_is_replay_paused"] = True
            frame["source"] = "REPLAY"
            return frame

        frame = dict(self.frames[self.cursor])
        self.cursor += 1
        if self.cursor >= len(self.frames):
            if self.loop:
                self.cursor = 0
            else:
                self.cursor = len(self.frames) - 1
                self.is_playing = False

        frame["source"] = "REPLAY"
        frame["_replay_cursor"] = self.cursor
        frame["_replay_total"] = len(self.frames)
        return frame

    def get_status(self) -> Dict[str, Any]:
        return {
            "source": "REPLAY",
            "status": "PLAYING" if self.is_playing else "PAUSED",
            "connected": len(self.frames) > 0,
            "cursor": self.cursor,
            "total_frames": len(self.frames),
            "progress_pct": round((self.cursor / max(1, len(self.frames))) * 100.0, 1),
            "playback_speed": self.playback_speed,
        }


class MAVLinkSource(TelemetrySource):
    """
    Decodes MAVLink packet streams into normalized TelemetryPacket format.
    """

    def __init__(self):
        self.last_packet_time: Optional[float] = None
        self.total_packets: int = 0
        self.connected = False

    def get_source_type(self) -> str:
        return "MAVLINK"

    def is_connected(self) -> bool:
        if self.last_packet_time is None:
            return False
        return (time.time() - self.last_packet_time) <= 5.0

    def ingest_mavlink_msg(self, msg_type: str, msg_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Maps MAVLink messages (e.g. HIGHRES_IMU, SYS_STATUS, ESC_STATUS) to normalized telemetry."""
        now = time.time()
        self.last_packet_time = now
        self.total_packets += 1
        self.connected = True

        # Normalized mapping
        frame = {
            "engine_id": "UAV-ENG-ROT-914-01",
            "timestamp": now,
            "sequence_number": msg_payload.get("seq", self.total_packets),
            "rpm": float(msg_payload.get("rpm", msg_payload.get("esc_rpm", 4215.0))),
            "temperature": float(msg_payload.get("temperature", msg_payload.get("temperature_cht", 78.4))),
            "oilPressure": float(msg_payload.get("press_abs", msg_payload.get("oil_press", 4.3))),
            "vibration": float(msg_payload.get("zacc", msg_payload.get("vibration_rms", 1.6))),
            "fuelFlow": float(msg_payload.get("fuel_flow", 5.2)),
            "engineLoad": float(msg_payload.get("load", 62.0)),
            "source": "MAVLINK",
            "raw_msg_type": msg_type,
        }
        return frame

    def get_frame(self) -> Optional[Dict[str, Any]]:
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "source": "MAVLINK",
            "status": "CONNECTED" if self.is_connected() else "NOT CONNECTED",
            "connected": self.is_connected(),
            "total_packets": self.total_packets,
        }
