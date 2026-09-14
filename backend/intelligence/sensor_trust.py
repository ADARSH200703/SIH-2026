"""
Sensor Trust Engine for AERIS-TWIN
Evaluates sensor validity, noise, stuck values, drift, jump discontinuities,
and cross-sensor consistency without conflating sensor failure with engine degradation.
Profile-aware: Supports both AERO_ENGINE and MOTOR_PROTOTYPE transducer arrays.
Strict Scientific Integrity: Zero silent fallback or injection of fake measurements.
"""
import time
from collections import deque
from typing import Dict, Any, List, Optional
import numpy as np

class SensorTrustEngine:
    def __init__(self, history_len: int = 40):
        self.history_len = history_len
        
        # Hard physical transducer boundaries
        self.aero_sensor_limits = {
            "rpm": (500.0, 6200.0),
            "temperature": (0.0, 130.0),        # CHT (°C)
            "oilPressure": (0.2, 7.5),          # Bar
            "vibration": (0.0, 12.0),           # mm/s
            "fuelFlow": (0.0, 15.0),            # L/h
            "engineLoad": (0.0, 100.0),         # %
            "egt": (200.0, 950.0),              # EGT (°C)
            "oilTemperature": (10.0, 140.0)     # Oil Temp (°C)
        }
        
        self.aero_max_step_jumps = {
            "rpm": 500.0,
            "temperature": 15.0,
            "oilPressure": 1.5,
            "vibration": 3.0,
            "fuelFlow": 3.5,
            "engineLoad": 25.0,
            "egt": 60.0,
            "oilTemperature": 10.0
        }

        self.motor_sensor_limits = {
            "current_a": (0.0, 10.0),           # Amperes
            "voltage_v": (6.0, 14.5),           # Volts (3S 18650 pack)
            "power_w": (0.0, 120.0),            # Watts
            "temperature_c": (0.0, 100.0),      # Motor / driver casing temp (°C)
            "vibration": (0.0, 10.0),           # mm/s or RMS
            "rpm": (0.0, 4500.0),               # DC shaft RPM
            "motor_load_pct": (0.0, 100.0)      # %
        }

        self.motor_max_step_jumps = {
            "current_a": 4.0,
            "voltage_v": 3.0,
            "power_w": 40.0,
            "temperature_c": 15.0,
            "vibration": 3.0,
            "rpm": 800.0,
            "motor_load_pct": 35.0
        }

        # Sensor value historical windows (combined key pool)
        all_keys = set(self.aero_sensor_limits.keys()) | set(self.motor_sensor_limits.keys())
        self.history: Dict[str, deque] = {
            s: deque(maxlen=history_len) for s in all_keys
        }
        self.last_valid_timestamps: Dict[str, float] = {
            s: time.time() for s in all_keys
        }
        self.last_valid_values: Dict[str, float] = {}
        self.last_frame_timestamp: Optional[float] = None

    def reset(self):
        """Clears historical buffers, resets timestamps, and restores valid trust."""
        for s in self.history:
            self.history[s].clear()
        all_keys = set(self.aero_sensor_limits.keys()) | set(self.motor_sensor_limits.keys())
        self.last_valid_timestamps = {s: time.time() for s in all_keys}
        self.last_valid_values.clear()
        self.last_frame_timestamp = None

    def evaluate_sensors(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates trust for each sensor channel based on the active telemetry profile.
        Never fabricates measurements for missing channels.
        """
        current_time = telemetry.get("timestamp", time.time())
        profile = telemetry.get("profile")
        if profile == "MOTOR_PROTOTYPE" or "current_a" in telemetry or "voltage_v" in telemetry or (
            "oilPressure" not in telemetry and "oil_pressure" not in telemetry and "fuelFlow" not in telemetry and "fuel_flow" not in telemetry and "cht" not in telemetry
        ):
            active_profile = "MOTOR_PROTOTYPE"
            sensor_limits = self.motor_sensor_limits
            max_step_jumps = self.motor_max_step_jumps
            criticality_weights = {
                "current_a": 1.5,
                "voltage_v": 1.4,
                "temperature_c": 1.3,
                "vibration": 1.2,
                "power_w": 1.0,
                "rpm": 1.0,
                "motor_load_pct": 0.8
            }
            alt_keys = {
                "temperature_c": "temperature",
                "motor_load_pct": "motor_load",
            }
        else:
            active_profile = "AERO_ENGINE"
            sensor_limits = self.aero_sensor_limits
            max_step_jumps = self.aero_max_step_jumps
            criticality_weights = {
                "oilPressure": 1.5,
                "vibration": 1.4,
                "temperature": 1.3,
                "rpm": 1.2,
                "fuelFlow": 1.0,
                "egt": 1.0,
                "oilTemperature": 1.0,
                "engineLoad": 0.8
            }
            alt_keys = {
                "temperature":    "cht_c",
                "oilPressure":    "oil_pressure_bar",
                "vibration":      "vibration_mms",
                "egt":            "egt_c",
                "oilTemperature": "oil_temperature_c",
                "fuelFlow":       "fuel_flow",
            }

        results = {}
        total_trust_weighted = 0.0
        weights_sum = 0.0

        for sensor, bounds in sensor_limits.items():
            val = telemetry.get(sensor)
            if val is None:
                val = telemetry.get(alt_keys.get(sensor, ""))

            # Handle Missing Channels Honestly
            if val is None:
                # Optional channels that might not be physically installed
                is_optional = (
                    (active_profile == "MOTOR_PROTOTYPE" and sensor in ("rpm", "voltage_v", "temperature_c", "vibration", "power_w", "motor_load_pct")) or
                    (active_profile == "AERO_ENGINE" and sensor in ("egt", "oilTemperature", "engineLoad"))
                )
                if is_optional:
                    status = "NOT_INSTALLED"
                    reason = f"Transducer channel '{sensor}' not physically present or unattached"
                    trust_score = 1.0  # Do not penalize aggregate trust for uninstalled optional channels
                    weight = 0.0
                else:
                    status = "MISSING"
                    reason = f"Telemetry stream missing required parameter reading for '{sensor}'"
                    trust_score = 0.0
                    weight = criticality_weights.get(sensor, 1.0)
                
                results[sensor] = {
                    "sensor": sensor,
                    "value": None,
                    "status": status,
                    "trust_score": round(trust_score, 3),
                    "confidence": round(trust_score, 3),
                    "reason": reason,
                    "last_valid_timestamp": self.last_valid_timestamps.get(sensor, current_time)
                }
                if weight > 0.0:
                    total_trust_weighted += trust_score * weight
                    weights_sum += weight
                continue

            # Process Available Measurement
            try:
                val = float(val)
            except (ValueError, TypeError):
                results[sensor] = {
                    "sensor": sensor,
                    "value": None,
                    "status": "MALFORMED",
                    "trust_score": 0.0,
                    "confidence": 0.0,
                    "reason": f"Non-numeric value received for transducer '{sensor}'",
                    "last_valid_timestamp": self.last_valid_timestamps.get(sensor, current_time)
                }
                w = criticality_weights.get(sensor, 1.0)
                total_trust_weighted += 0.0
                weights_sum += w
                continue

            buf = self.history[sensor]
            min_b, max_b = bounds
            status = "VALID"
            reason = "Transducer operating within valid physical envelope and nominal signal dynamics"
            trust_score = 1.0

            # 1. Out of Range Check
            if val < min_b or val > max_b:
                status = "OUT_OF_RANGE"
                reason = f"Value {val} exceeds physical transducer boundaries [{min_b}, {max_b}]"
                trust_score = 0.15

            # 2. Jump Discontinuity Check
            elif len(buf) > 0 and abs(val - buf[-1]) > max_step_jumps[sensor]:
                status = "JUMP"
                reason = f"Step discontinuity: delta {abs(val - buf[-1]):.2f} exceeds dynamic threshold {max_step_jumps[sensor]}"
                trust_score = 0.35

            # 3. Stuck Transducer (Zero variance over window)
            elif len(buf) >= 15 and np.var(list(buf)[-15:] + [val]) < 1e-6:
                status = "STUCK"
                reason = "Zero statistical variance detected over 15 consecutive samples (sensor frozen)"
                trust_score = 0.20

            # 4. Excessive Noise / Flutter Check
            elif len(buf) >= 10 and np.mean(np.abs(np.diff(list(buf)[-10:] + [val]))) > (max_step_jumps[sensor] * 0.45):
                status = "NOISY"
                reason = "High-frequency signal flutter exceeds acceptable transducer noise baseline"
                trust_score = 0.55

            # 5. Calibration Drift Check
            elif len(buf) >= 20:
                recent = np.array(list(buf)[-20:] + [val])
                poly = np.polyfit(np.arange(len(recent)), recent, 1)
                slope = poly[0]
                if abs(slope) > (max_step_jumps[sensor] * 0.05) and np.std(recent - (poly[0] * np.arange(len(recent)) + poly[1])) < 0.1:
                    status = "DRIFTING"
                    reason = f"Monotonic calibration drift detected (slope: {slope:+.4f}/sample)"
                    trust_score = 0.45

            if trust_score > 0.4:
                self.last_valid_timestamps[sensor] = current_time
                self.last_valid_values[sensor] = val

            buf.append(val)

            w = criticality_weights.get(sensor, 1.0)
            total_trust_weighted += trust_score * w
            weights_sum += w

            results[sensor] = {
                "sensor": sensor,
                "value": round(val, 3),
                "status": status,
                "trust_score": round(trust_score, 3),
                "confidence": round(trust_score, 3),
                "reason": reason,
                "last_valid_timestamp": self.last_valid_timestamps.get(sensor, current_time)
            }

        # Profile-specific cross-sensor consistency
        if active_profile == "AERO_ENGINE":
            cht_info = results.get("temperature")
            egt_info = results.get("egt")
            if cht_info and egt_info and cht_info["value"] is not None and egt_info["value"] is not None:
                if cht_info["value"] > 105.0 and egt_info["value"] < 400.0:
                    cht_info["status"] = "INCONSISTENT"
                    cht_info["trust_score"] = min(cht_info["trust_score"], 0.4)
                    cht_info["reason"] = "Thermal inconsistency: CHT is elevated while EGT is near ambient"
        elif active_profile == "MOTOR_PROTOTYPE":
            curr_info = results.get("current_a")
            pwr_info = results.get("power_w")
            volt_info = results.get("voltage_v")
            if curr_info and pwr_info and volt_info:
                if curr_info["value"] is not None and volt_info["value"] is not None and pwr_info["value"] is not None:
                    exp_pwr = curr_info["value"] * volt_info["value"]
                    if abs(pwr_info["value"] - exp_pwr) > 5.0:
                        pwr_info["status"] = "INCONSISTENT"
                        pwr_info["trust_score"] = min(pwr_info["trust_score"], 0.5)
                        pwr_info["reason"] = f"Electrical inconsistency: Power {pwr_info['value']}W != V*I ({exp_pwr:.1f}W)"

        # Timestamp Monotonicity & Clock Skew Validation
        raw_ts = telemetry.get("timestamp", current_time)
        ts_valid = True
        ts_reason = "Valid monotonic epoch timestamp"
        ts_age_ms = max(0.0, round((time.time() - raw_ts) * 1000.0, 1)) if raw_ts else 0.0

        if raw_ts is None:
            ts_valid = False
            ts_reason = "Missing packet timestamp"
        elif self.last_frame_timestamp is not None and raw_ts < self.last_frame_timestamp:
            ts_valid = False
            ts_reason = f"Out-of-order / non-monotonic timestamp: delta {raw_ts - self.last_frame_timestamp:.3f}s"
        elif raw_ts > (time.time() + 60.0):
            ts_valid = False
            ts_reason = "Future timestamp detected (clock skew > 60s)"

        self.last_frame_timestamp = raw_ts

        aggregate_trust = round(total_trust_weighted / max(0.01, weights_sum), 3)
        return {
            "profile": active_profile,
            "sensors": results,
            "aggregate_trust_score": aggregate_trust,
            "all_sensors_valid": all(s["status"] in ("VALID", "NOT_INSTALLED") for s in results.values()),
            "timestamp_validation": {
                "valid": ts_valid,
                "reason": ts_reason,
                "data_age_ms": ts_age_ms,
                "packet_timestamp": raw_ts,
            }
        }
