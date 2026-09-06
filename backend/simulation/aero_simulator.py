"""
Aero Piston Engine Physics Simulator for AERIS-TWIN
Deterministic seed-based telemetry generator with progressive degradation dynamics
and interactive fault injection.
"""
import random
import math
import time
from typing import Dict, Any, List, Optional

class AeroEngineSimulator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        
        # Engine operating baseline
        self.state = {
            "engine_id": "UAV-ENG-ROT-914-01",
            "uav_id": "MALE-UAV-TAPAS-04",
            "mission_id": "MSN-2026-SURV-082",
            "timestamp": time.time(),
            "sequence_number": 0,
            "flight_time_seconds": 9918,
            
            # Kinematics & Thermodynamics
            "rpm": 4215.0,
            "throttle": 68.0,
            "temperature": 78.4,       # CHT (°C)
            "oilPressure": 4.3,        # Bar
            "vibration": 1.6,          # mm/s
            "fuelFlow": 5.2,           # L/h
            "engineLoad": 62.0,        # %
            "egt_c": 645.0,            # EGT (°C)
            "oil_temperature_c": 82.1, # Oil Temp (°C)
            
            # Environmental Flight Profile
            "altitude_ft": 15000.0,
            "airspeed_kts": 85.0,
            "ambient_temperature_c": -14.5,
            "ambient_pressure_kpa": 57.2,
            "power_setting": 0.72,
            "flight_phase": "CRUISE",
            
            # Scenario & Controls
            "activeScenario": "cruise",
            "manualOverride": False,
            "isRunning": True,
            "source": "SIMULATOR"
        }
        
        # Active fault injection states
        self.active_injections: List[Dict[str, Any]] = []
        
        # 60-sample historical window for UI charts
        self.history = {
            "labels": [],
            "rpm": [],
            "temperature": [],
            "oilPressure": [],
            "vibration": []
        }
        self._init_history()

    def _init_history(self):
        for i in range(59, -1, -1):
            self.history["labels"].append(f"{(-i * 5 / 60):.1f}")
            self.history["rpm"].append(4215.0 + math.sin(i * 0.4) * 20 + self.rng.uniform(-3, 3))
            self.history["temperature"].append(78.0 + math.cos(i * 0.2) * 1.2 + self.rng.uniform(-0.1, 0.1))
            self.history["oilPressure"].append(4.3 + math.sin(i * 0.3) * 0.08 + self.rng.uniform(-0.01, 0.01))
            self.history["vibration"].append(1.6 + math.cos(i * 0.5) * 0.1 + self.rng.uniform(-0.02, 0.02))

    def inject_fault(self, fault: str, severity: float = 0.5, start_time: float = 0.0, progression_rate: float = 0.002) -> Dict[str, Any]:
        """
        Registers a progressive fault injection profile.
        """
        injection = {
            "fault": fault,
            "severity": severity,
            "current_severity": 0.05,
            "start_time_offset": start_time,
            "progression_rate": progression_rate,
            "injected_at": time.time(),
            "active": True
        }
        self.active_injections.append(injection)
        return injection

    def set_scenario(self, scenario: str):
        self.state["activeScenario"] = scenario
        self.state["manualOverride"] = False
        
        # Map scenario to standard fault injection
        if scenario == "vibration_bearing":
            self.inject_fault("BEARING_DEGRADATION", severity=0.7, progression_rate=0.015)
        elif scenario == "lubrication_degradation":
            self.inject_fault("LUBRICATION_DEGRADATION", severity=0.6, progression_rate=0.012)
        elif scenario == "thermal_overheat":
            self.inject_fault("COOLING_DEGRADATION", severity=0.8, progression_rate=0.018)
        elif scenario == "spark_misfire":
            self.inject_fault("SPARK_PLUG_DEGRADATION", severity=0.65, progression_rate=0.010)

    def execute_mitigation(self):
        """
        Closes feedback loop: resets fault injections and returns engine to optimal cruise trim.
        """
        self.active_injections.clear()
        self.state["activeScenario"] = "cruise"
        self.state["manualOverride"] = False
        self.state["vibration"] = 1.65
        self.state["temperature"] = 78.5
        self.state["oilPressure"] = 4.28
        self.state["fuelFlow"] = 5.2

    def step(self) -> Dict[str, Any]:
        """
        Advances the simulator by 1 time step.
        """
        if not self.state["isRunning"]:
            return self.state

        self.state["timestamp"] = time.time()
        self.state["sequence_number"] += 1
        self.state["flight_time_seconds"] += 1

        # Baseline cruise targets
        target_rpm = 4215.0
        target_temp = 78.4
        target_oil = 4.30
        target_vib = 1.60
        target_fuel = 5.20
        target_load = 62.0

        # Apply progressive active fault injections
        for inj in self.active_injections:
            if not inj.get("active", True):
                continue
            # Progressive growth
            inj["current_severity"] = min(inj["severity"], inj["current_severity"] + inj["progression_rate"])
            sev = inj["current_severity"]
            fault_type = inj["fault"]
            
            if fault_type in ["BEARING_DEGRADATION", "vibration_bearing"]:
                target_vib += sev * 4.2
                target_oil -= sev * 0.4
                target_temp += sev * 3.5
            elif fault_type in ["LUBRICATION_DEGRADATION", "lubrication_degradation"]:
                target_oil -= sev * 2.2
                target_temp += sev * 9.0
                target_vib += sev * 1.5
            elif fault_type in ["COOLING_DEGRADATION", "thermal_overheat"]:
                target_temp += sev * 24.0
                target_oil -= sev * 0.8
                target_load += sev * 20.0
            elif fault_type in ["SPARK_PLUG_DEGRADATION", "spark_misfire"]:
                target_fuel += sev * 2.5
                target_rpm -= sev * 350.0 + self.rng.uniform(-100, 100)
                target_vib += sev * 1.8
            elif fault_type == "SENSOR_DRIFT_VIBRATION":
                # Only affects reported vibration sensor without changing physics load
                self.state["vibration"] += 0.05

        # Smooth relaxation towards targets with Gaussian perturbation
        if not self.state["manualOverride"]:
            self.state["rpm"] += (target_rpm - self.state["rpm"]) * 0.12 + self.rng.uniform(-4.0, 4.0)
            self.state["temperature"] += (target_temp - self.state["temperature"]) * 0.08 + self.rng.uniform(-0.1, 0.1)
            self.state["oilPressure"] += (target_oil - self.state["oilPressure"]) * 0.08 + self.rng.uniform(-0.015, 0.015)
            self.state["vibration"] += (target_vib - self.state["vibration"]) * 0.12 + self.rng.uniform(-0.03, 0.03)
            self.state["fuelFlow"] += (target_fuel - self.state["fuelFlow"]) * 0.08 + self.rng.uniform(-0.02, 0.02)
            self.state["engineLoad"] += (target_load - self.state["engineLoad"]) * 0.08 + self.rng.uniform(-0.15, 0.15)
        else:
            self.state["rpm"] += self.rng.uniform(-2.0, 2.0)
            self.state["temperature"] += self.rng.uniform(-0.05, 0.05)
            self.state["oilPressure"] += self.rng.uniform(-0.01, 0.01)
            self.state["vibration"] += self.rng.uniform(-0.02, 0.02)

        # Physical clamping bounds
        self.state["rpm"] = max(800.0, min(6200.0, self.state["rpm"]))
        self.state["temperature"] = max(15.0, min(125.0, self.state["temperature"]))
        self.state["oilPressure"] = max(0.5, min(7.5, self.state["oilPressure"]))
        self.state["vibration"] = max(0.2, min(10.0, self.state["vibration"]))
        self.state["fuelFlow"] = max(0.0, min(15.0, self.state["fuelFlow"]))
        self.state["engineLoad"] = max(0.0, min(100.0, self.state["engineLoad"]))

        self._push_history()
        return self.state

    def _push_history(self):
        size = 60
        self.history["labels"] = [f"{(-(size - 1 - i) * 5 / 60):.1f}" for i in range(size)]
        for k in ("rpm", "temperature", "oilPressure", "vibration"):
            if len(self.history[k]) >= size:
                self.history[k].pop(0)
            self.history[k].append(round(self.state[k], 2))

    def reset_flight_time(self, seconds: int = 0):
        """Resets or adjusts the mission flight time counter."""
        self.state["flight_time_seconds"] = max(0, seconds)
        return {"status": "flight_time_reset", "flight_time_seconds": self.state["flight_time_seconds"]}

