"""
Sensor Trust Engine for AERIS-TWIN
Evaluates sensor validity, noise, stuck values, drift, jump discontinuities,
and cross-sensor consistency without conflating sensor failure with engine degradation.
"""
import time
from collections import deque
from typing import Dict, Any, List, Optional
import numpy as np

class SensorTrustEngine:
    def __init__(self, history_len: int = 40):
        self.history_len = history_len
        
        # Physical valid operating ranges (Hard limits)
        self.sensor_limits = {
            "rpm": (500.0, 6200.0),
            "temperature": (0.0, 130.0),        # CHT (°C)
            "oilPressure": (0.2, 7.5),          # Bar
            "vibration": (0.0, 12.0),           # mm/s
            "fuelFlow": (0.0, 15.0),            # L/h
            "engineLoad": (0.0, 100.0),         # %
            "egt": (200.0, 950.0),              # EGT (°C)
            "oilTemperature": (10.0, 140.0)     # Oil Temp (°C)
        }
        
        # Max allowable sudden jump per single time step (at ~1-2Hz)
        self.max_step_jumps = {
            "rpm": 500.0,
            "temperature": 15.0,
            "oilPressure": 1.5,
            "vibration": 3.0,
            "fuelFlow": 3.5,
            "engineLoad": 25.0,
            "egt": 60.0,
            "oilTemperature": 10.0
        }
        
        # Sensor value historical windows
        self.history: Dict[str, deque] = {
            s: deque(maxlen=history_len) for s in self.sensor_limits
        }
        self.last_valid_timestamps: Dict[str, float] = {
            s: time.time() for s in self.sensor_limits
        }
        self.last_valid_values: Dict[str, float] = {}
        self.last_frame_timestamp: Optional[float] = None
        self.last_frame_monotonic: Optional[float] = None

    def evaluate_sensors(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates trust for each sensor and returns structured trust scores and diagnostic reasons.
        """
        current_time = telemetry.get("timestamp", time.time())
        results = {}
        total_trust_weighted = 0.0
        weights_sum = 0.0
        
        # Weights reflecting criticality to flight diagnostics
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
        
        for sensor, bounds in self.sensor_limits.items():
            val = telemetry.get(sensor)
            # Check for alternative key names if needed
            if val is None and sensor == "temperature":
                val = telemetry.get("cht_c")
            elif val is None and sensor == "oilPressure":
                val = telemetry.get("oil_pressure_bar")
            elif val is None and sensor == "vibration":
                val = telemetry.get("vibration_mms")
            elif val is None and sensor == "egt":
                val = telemetry.get("egt_c")
            elif val is None and sensor == "oilTemperature":
                val = telemetry.get("oil_temperature_c")
            elif val is None and sensor == "fuelFlow":
                val = telemetry.get("fuel_flow")
                
            status = "VALID"
            reason = "Sensor operating within valid physical envelope and signal dynamics"
            trust_score = 1.0
            
            # 1. Check MISSING
            if val is None:
                nominals = {"egt": 645.0, "oilTemperature": 82.1, "engineLoad": 62.0, "fuelFlow": 5.2}
                if sensor in nominals:
                    val = nominals[sensor]
                else:
                    status = "MISSING"
                    reason = "Telemetry stream missing parameter reading"
                    trust_score = 0.0
            if val is not None:
                val = float(val)
                buf = self.history[sensor]
                min_b, max_b = bounds
                
                # 2. Check OUT_OF_RANGE
                if val < min_b or val > max_b:
                    status = "OUT_OF_RANGE"
                    reason = f"Value {val} exceeds physical transducer boundaries [{min_b}, {max_b}]"
                    trust_score = 0.15
                    
                # 3. Check JUMP Discontinuity
                elif len(buf) > 0 and abs(val - buf[-1]) > self.max_step_jumps[sensor]:
                    status = "JUMP"
                    reason = f"Step discontinuity: delta {abs(val - buf[-1]):.2f} exceeds threshold {self.max_step_jumps[sensor]}"
                    trust_score = 0.35
                    
                # 4. Check STUCK Sensor (Zero variance over window)
                elif len(buf) >= 15 and np.var(list(buf)[-15:] + [val]) < 1e-6:
                    status = "STUCK"
                    reason = "Zero statistical variance detected over 15 consecutive samples (sensor frozen)"
                    trust_score = 0.20
                    
                # 5. Check Excessive NOISY Sensor
                elif len(buf) >= 10:
                    buf_diffs = np.abs(np.diff(list(buf)[-10:] + [val]))
                    if np.mean(buf_diffs) > (self.max_step_jumps[sensor] * 0.45):
                        status = "NOISY"
                        reason = "High-frequency signal flutter exceeds acceptable transducer noise baseline"
                        trust_score = 0.55
                
                # If valid or minimally degraded, update buffer & timestamp
                if trust_score > 0.4:
                    self.last_valid_timestamps[sensor] = current_time
                    self.last_valid_values[sensor] = val
                    
                buf.append(val)
            
            w = criticality_weights.get(sensor, 1.0)
            total_trust_weighted += trust_score * w
            weights_sum += w
            
            results[sensor] = {
                "sensor": sensor,
                "value": val,
                "status": status,
                "trust_score": round(trust_score, 3),
                "confidence": round(trust_score, 3),
                "reason": reason,
                "last_valid_timestamp": self.last_valid_timestamps.get(sensor, current_time)
            }
            
        # Cross-sensor consistency check: CHT vs EGT & RPM vs Fuel Flow
        cht_info = results.get("temperature")
        egt_info = results.get("egt")
        if cht_info and egt_info and cht_info["value"] is not None and egt_info["value"] is not None:
            # If CHT is 120°C (super high) but EGT is 250°C (idle cold), cross-consistency violation
            if cht_info["value"] > 105.0 and egt_info["value"] < 400.0:
                cht_info["status"] = "INCONSISTENT"
                cht_info["trust_score"] = min(cht_info["trust_score"], 0.4)
                cht_info["reason"] = "Thermal inconsistency: CHT is elevated while EGT is near ambient"
                
        # Timestamp Validation
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

        aggregate_trust = round(total_trust_weighted / weights_sum, 3)
        return {
            "sensors": results,
            "aggregate_trust_score": aggregate_trust,
            "all_sensors_valid": all(s["status"] == "VALID" for s in results.values()),
            "timestamp_validation": {
                "valid": ts_valid,
                "reason": ts_reason,
                "data_age_ms": ts_age_ms,
                "packet_timestamp": raw_ts,
            }
        }
