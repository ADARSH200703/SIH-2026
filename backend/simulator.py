"""
Aero Piston Engine Physics Simulator (Python Backend)
Data-driven scenario table mirrors the JS engineSimulator.js implementation.
"""
import random
import math
from typing import Optional

# Scenario target parameters — identical to JS SCENARIOS lookup
SCENARIOS = {
    "cruise":                  dict(rpm=4215.0, temperature=78.4, oilPressure=4.3, vibration=1.6, fuelFlow=5.2, engineLoad=62.0),
    "lubrication_degradation": dict(rpm=4180.0, temperature=86.8, oilPressure=2.6, vibration=2.7, fuelFlow=5.6, engineLoad=68.0),
    "vibration_bearing":       dict(rpm=4260.0, temperature=81.2, oilPressure=3.9, vibration=4.6, fuelFlow=5.4, engineLoad=65.0),
    "thermal_overheat":        dict(rpm=4450.0, temperature=97.5, oilPressure=3.2, vibration=3.1, fuelFlow=6.4, engineLoad=88.0),
    "spark_misfire":           dict(rpm=3920.0, temperature=82.0, oilPressure=4.1, vibration=3.5, fuelFlow=6.9, engineLoad=74.0),
    "high_altitude_climb":     dict(rpm=4850.0, temperature=84.6, oilPressure=4.5, vibration=2.2, fuelFlow=7.6, engineLoad=94.0),
}

# Physical bounds: (min, max) per parameter
CLAMPS = {
    "rpm":         (800.0,  6500.0),
    "temperature": (20.0,   130.0),
    "oilPressure": (0.5,    8.0),
    "vibration":   (0.2,    10.0),
    "fuelFlow":    (0.0,    15.0),
    "engineLoad":  (0.0,    100.0),
}

# Lerp smoothing and noise amplitudes per parameter
LERP  = dict(rpm=0.15, temperature=0.1, oilPressure=0.1, vibration=0.15, fuelFlow=0.1, engineLoad=0.1)
NOISE = dict(rpm=7.0,  temperature=0.15, oilPressure=0.02, vibration=0.04, fuelFlow=0.03, engineLoad=0.2)

# Mitigation recovery values
MITIGATIONS = {
    "lubrication_degradation": dict(oilPressure=4.1, temperature=79.5, vibration=1.7),
    "thermal_overheat":        dict(engineLoad=55.0, temperature=80.2),
    "vibration_bearing":       dict(rpm=3850.0, vibration=2.0),
    "spark_misfire":           dict(rpm=4150.0, fuelFlow=5.3),
}

def _clamp(v: float, bounds: tuple) -> float:
    return max(bounds[0], min(bounds[1], v))

def _noise(amp: float) -> float:
    return random.uniform(-amp, amp)


class BackendEngineSimulator:
    def __init__(self):
        self.state = {
            "rpm": 4215.0, "temperature": 78.4, "oilPressure": 4.3,
            "vibration": 1.6, "fuelFlow": 5.2, "engineLoad": 62.0,
            "flightTimeSeconds": 9918,
            "engineHealth": 87, "missionReliability": 92,
            "status": "NORMAL",
            "activeScenario": "cruise",
            "manualOverride": False, "isRunning": True,
        }
        self.history = {"labels": [], "rpm": [], "temperature": [], "oilPressure": [], "vibration": []}
        self._init_history()

    def _init_history(self):
        for i in range(59, -1, -1):
            self.history["labels"].append(f"{(-i * 5 / 60):.1f}")
            self.history["rpm"].append(4215.0 + math.sin(i * 0.4) * 25 + _noise(5))
            self.history["temperature"].append(78.0 + math.cos(i * 0.2) * 1.5 + _noise(0.2))
            self.history["oilPressure"].append(4.3 + math.sin(i * 0.3) * 0.1 + _noise(0.02))
            self.history["vibration"].append(1.6 + math.cos(i * 0.5) * 0.15 + _noise(0.04))

    def set_scenario(self, scenario: str):
        if scenario in SCENARIOS:
            self.state["activeScenario"] = scenario
            self.state["manualOverride"] = False

    def execute_mitigation(self):
        fix = MITIGATIONS.get(self.state["activeScenario"], {})
        self.state.update(fix)
        self.state["activeScenario"] = "cruise"
        self._recalculate_health()

    def step(self) -> dict:
        if not self.state["isRunning"]:
            return self.state

        self.state["flightTimeSeconds"] += 1
        scenario = self.state["activeScenario"]
        target = dict(SCENARIOS.get(scenario, SCENARIOS["cruise"]))

        # Add misfire RPM jitter
        if scenario == "spark_misfire":
            target["rpm"] += _noise(150)

        if not self.state["manualOverride"]:
            for param in LERP:
                self.state[param] += (target[param] - self.state[param]) * LERP[param] + _noise(NOISE[param])
        else:
            # Light noise only on manual overrides
            self.state["rpm"]         += _noise(3)
            self.state["temperature"] += _noise(0.05)
            self.state["oilPressure"] += _noise(0.01)
            self.state["vibration"]   += _noise(0.02)

        # Clamp to physical limits
        for param, bounds in CLAMPS.items():
            self.state[param] = _clamp(self.state[param], bounds)

        self._recalculate_health()
        self._push_history()
        return self.state

    def _push_history(self):
        SIZE = 60
        self.history["labels"] = [f"{(-(SIZE - 1 - i) * 5 / 60):.1f}" for i in range(SIZE)]
        for key in ("rpm", "temperature", "oilPressure", "vibration"):
            self.history[key].pop(0)
            self.history[key].append(self.state[key])

    def _recalculate_health(self):
        oil, temp, vib = self.state["oilPressure"], self.state["temperature"], self.state["vibration"]
        penalty = 0
        if oil  < 3.0:  penalty += 28
        elif oil  < 3.8: penalty += 12
        if temp > 92:   penalty += 32
        elif temp > 84:  penalty += 14
        if vib  > 4.0:  penalty += 35
        elif vib  > 2.4: penalty += 16
        if self.state["rpm"] > 5500: penalty += 18

        self.state["engineHealth"]       = max(15, min(99, int(96 - penalty)))
        self.state["missionReliability"] = max(20, min(99, int(self.state["engineHealth"] * 1.05 - vib * 2)))

        h = self.state["engineHealth"]
        self.state["status"] = (
            "NORMAL"   if h >= 80 and oil >= 3.6 and temp <= 85 and vib <= 2.5 else
            "WARNING"  if h >= 50 and oil >= 2.5 and temp <= 93 and vib <= 3.8 else
            "CRITICAL"
        )

    def get_formatted_flight_time(self) -> str:
        s = int(self.state["flightTimeSeconds"])
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
