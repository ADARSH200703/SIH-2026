"""
Physical DC Motor Testbed Digital Twin Physics Model
System: 3x18650 Battery Pack -> ACS712 Current Transducer -> L298N Dual H-Bridge -> DC Geared Motor -> ESP32

Electro-mechanical Principles:
1. Armature Voltage Equation: V_in = I * R_a + K_e * omega_m + V_diode_drop
2. Mechanical Torque & Load: T_em = K_t * I_a = T_load + B * omega_m + J * (d_omega/dt)
3. Battery Internal Resistance / Bus Sag: V_bus = V_open_circuit - I_load * R_battery_internal
4. Joule Heating & Thermal Equilibrium: P_loss = I^2 * R_a + P_iron, T_motor_ss = T_amb + P_loss * R_th
5. Baseline Dynamic Vibration: Vib_baseline proportional to rotational eccentricity frequency harmonics.
"""
import math
from typing import Dict, Any, Optional

class MotorPrototypePhysicsModel:
    def __init__(self):
        # Physical Testbed Constants
        self.r_armature_ohms = 1.85           # DC Motor Armature Resistance (Ohms)
        self.k_back_emf = 0.0042              # Back-EMF constant (V / RPM)
        self.k_torque = 0.040                 # Torque constant (N*m / A)
        self.r_battery_internal = 0.22        # 3S 18650 Internal Resistance (Ohms)
        self.v_nominal_battery_ocv = 12.0     # Nominal Open-Circuit Battery Voltage (V)
        self.i_no_load_a = 0.38               # No-load current (A)
        self.i_stall_a = 6.80                 # Stall current (A)
        self.r_thermal_deg_per_w = 4.2        # Thermal resistance (°C / W)
        self.ambient_temp_c = 25.0            # Nominal ambient room temperature (°C)
        self.nominal_vibration_mms = 0.85     # Baseline vibration at 1800 RPM (mm/s)

    def compute_expected_state(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates expected physical parameters from operating context:
        ExpectedState = f(load, voltage, rpm, ambient_temp)
        """
        load_pct = telemetry.get("motor_load_pct")
        if load_pct is None:
            load_pct = telemetry.get("motor_load", telemetry.get("load", 45.0))
        load_pct = max(0.0, min(100.0, float(load_pct)))
        load_frac = load_pct / 100.0

        # 1. Expected Shaft Speed (RPM)
        # Higher load leads to armature speed reduction along linear DC torque-speed curve
        exp_rpm = round(max(0.0, 2100.0 - (load_frac * 650.0)), 1)
        actual_rpm = telemetry.get("rpm")
        eval_rpm = float(actual_rpm) if actual_rpm is not None else exp_rpm

        # 2. Expected Armature Current (A)
        # I_exp = I_no_load + load_frac * (I_rated - I_no_load)
        exp_current_a = round(self.i_no_load_a + load_frac * (2.80 - self.i_no_load_a), 3)

        # 3. Expected Terminal Voltage (V)
        # Battery voltage under load sag
        meas_current = telemetry.get("current_a")
        eval_current = float(meas_current) if meas_current is not None else exp_current_a
        exp_voltage_v = round(max(8.5, self.v_nominal_battery_ocv - eval_current * self.r_battery_internal), 2)

        # 4. Expected Electrical Power (W)
        exp_power_w = round(exp_voltage_v * exp_current_a, 2)

        # 5. Expected Steady-State Motor Temperature (°C)
        # Thermal dissipation from copper losses (I^2 * R) + driver drop
        p_loss_w = (eval_current ** 2) * self.r_armature_ohms + (eval_current * 1.4) # 1.4V L298N BJT V_ce sat drop
        exp_temperature_c = round(min(90.0, self.ambient_temp_c + (p_loss_w * 0.85)), 1)

        # 6. Expected Mechanical Vibration (mm/s)
        # Harmonic eccentricity scaling with speed and mechanical load
        exp_vibration_mms = round(self.nominal_vibration_mms + (eval_rpm / 2000.0) * 0.25 + (load_frac * 0.35), 2)

        return {
            "rpm": exp_rpm,
            "current_a": exp_current_a,
            "voltage_v": exp_voltage_v,
            "power_w": exp_power_w,
            "temperature_c": exp_temperature_c,
            "vibration": exp_vibration_mms,
            "motor_load_pct": load_pct
        }

    def compute_residuals(self, measured: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates deterministic residuals: Residual = Measured - Expected
        Includes deviation percentage and normalized residual score.
        """
        residuals = {}
        channels = [
            ("current_a", "A", 0.35),       # (key, unit, std_dev)
            ("voltage_v", "V", 0.25),
            ("power_w", "W", 3.0),
            ("rpm", "RPM", 80.0),
            ("temperature_c", "°C", 3.5),
            ("vibration", "mm/s", 0.20),
            ("motor_load_pct", "%", 5.0)
        ]

        for key, unit, sigma_nominal in channels:
            m_val = measured.get(key)
            e_val = expected.get(key)
            if m_val is not None and e_val is not None:
                try:
                    m_f = float(m_val)
                    e_f = float(e_val)
                    raw_diff = m_f - e_f
                    norm_sigma = raw_diff / max(0.001, sigma_nominal)
                    pct_dev = ((m_f - e_f) / max(0.01, abs(e_f))) * 100.0 if e_f != 0 else 0.0

                    residuals[key] = {
                        "measured": round(m_f, 3),
                        "expected": round(e_f, 3),
                        "raw_residual": round(raw_diff, 3),
                        "normalized_residual": round(norm_sigma, 2),
                        "percentage_deviation": round(pct_dev, 1),
                        "unit": unit,
                        "status": "NORMAL" if abs(norm_sigma) < 2.0 else ("WARNING" if abs(norm_sigma) < 3.5 else "CRITICAL")
                    }
                except (ValueError, TypeError):
                    pass

        return residuals
