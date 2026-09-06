"""
Residual Engine for AERIS-TWIN
Calculates raw residuals, normalized z-scores, rolling statistics,
and temporal trends for all engine physical parameters.
"""
from typing import Dict, Any, List
from collections import deque
import numpy as np

class ResidualEngine:
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        
        # Nominal parameter standard deviations for normalization (sigma_baseline)
        self.nominal_sigmas = {
            "vibration": 0.25,     # mm/s
            "temperature": 2.5,    # °C (CHT)
            "oilPressure": 0.20,   # Bar
            "oilTemperature": 2.0, # °C
            "fuelFlow": 0.35,      # L/h
            "egt": 15.0,           # °C
            "rpm": 45.0,           # RPM
            "engineLoad": 3.0      # %
        }
        
        # Parameter historical buffers for rolling statistics
        self.history: Dict[str, deque] = {
            param: deque(maxlen=window_size) for param in self.nominal_sigmas
        }

    def compute_residuals(self, measured: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates residual = measured - expected, normalized residual, and rolling trends.
        """
        # Mapping between telemetry keys and expected state keys
        param_mapping = [
            ("vibration", measured.get("vibration", 1.6), expected.get("expected_vibration_mms", 1.6)),
            ("temperature", measured.get("temperature", 78.4), expected.get("expected_cht_c", 78.4)),
            ("oilPressure", measured.get("oilPressure", 4.3), expected.get("expected_oil_pressure_bar", 4.3)),
            ("oilTemperature", measured.get("oil_temperature_c", 82.1), expected.get("expected_oil_temperature_c", 82.1)),
            ("fuelFlow", measured.get("fuelFlow", 5.2), expected.get("expected_fuel_flow", 5.2)),
            ("egt", measured.get("egt_c", 645.0), expected.get("expected_egt_c", 645.0)),
            ("rpm", measured.get("rpm", 4215.0), expected.get("expected_rpm", 4215.0)),
            ("engineLoad", measured.get("engineLoad", 62.0), expected.get("expected_load_pct", 62.0))
        ]
        
        residuals_dict = {}
        
        for param, meas_val, exp_val in param_mapping:
            raw_residual = round(meas_val - exp_val, 4)
            sigma = self.nominal_sigmas.get(param, 1.0)
            norm_residual = round(raw_residual / sigma, 3)
            
            # Update rolling buffer
            buf = self.history[param]
            buf.append(raw_residual)
            
            # Compute rolling statistics
            buf_arr = np.array(buf)
            r_mean = float(np.mean(buf_arr))
            r_std = float(np.std(buf_arr)) if len(buf_arr) > 1 else 0.01
            r_var = float(np.var(buf_arr)) if len(buf_arr) > 1 else 0.001
            
            # Compute residual slope (linear regression over recent window)
            if len(buf_arr) >= 5:
                x = np.arange(len(buf_arr))
                slope, _ = np.polyfit(x, buf_arr, 1)
            else:
                slope = 0.0
                
            # Trend determination
            if slope > 0.015:
                trend = "INCREASING"
            elif slope < -0.015:
                trend = "DECREASING"
            else:
                trend = "STABLE"
                
            residuals_dict[param] = {
                "parameter": param,
                "measured": round(float(meas_val), 2),
                "expected": round(float(exp_val), 2),
                "residual": raw_residual,
                "normalized_residual": norm_residual,
                "rolling_mean": round(r_mean, 4),
                "rolling_std": round(r_std, 4),
                "residual_variance": round(r_var, 5),
                "residual_slope": round(float(slope), 5),
                "trend": trend
            }
            
        return residuals_dict
