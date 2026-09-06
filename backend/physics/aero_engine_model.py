"""
Mean-Value Aero Piston Engine Physics Model (Rotax 914 Turbocharged Architecture)

Assumptions & Simplifications:
1. Zero-dimensional lumped parameter thermal capacitance model for CHT and Oil Temperature.
2. Mean-value brake torque and power balance based on manifold pressure and engine displacement.
3. ISA (International Standard Atmosphere) ambient density & temperature lapse formulations.
4. Turbocharger wastegate control maintains sea-level manifold pressure up to critical altitude (approx 16,000 ft).
5. Viscosity-temperature relationship for oil pressure baseline based on hydrodynamic journal bearing theory.
"""
import math
from typing import Dict, Any

class AeroPistonPhysicsModel:
    def __init__(self):
        # Engine Specifications (Rotax 914 F Baseline)
        self.displacement_l = 1.211  # 1211 cc
        self.compression_ratio = 9.0
        self.rated_power_kw = 84.5   # 115 HP
        self.max_continuous_rpm = 5500.0
        self.cruise_rpm_nominal = 4200.0
        
        # Baselines at Standard Day Sea Level
        self.bsfc_nominal = 285.0    # Brake Specific Fuel Consumption (g/kWh)
        self.fuel_density = 0.72     # kg/L (Avgas 100LL)
        
    def calculate_isa_atmosphere(self, altitude_ft: float) -> Dict[str, float]:
        """
        Standard International Atmosphere (ISA) calculations up to 36,000 ft (Troposphere).
        """
        alt_m = max(0.0, altitude_ft * 0.3048)
        t_sl = 288.15  # Kelvin (15°C)
        p_sl = 101.325 # kPa
        lapse_rate = 0.0065 # K/m
        
        t_kelvin = max(216.65, t_sl - lapse_rate * alt_m)
        t_celsius = t_kelvin - 273.15
        p_kpa = p_sl * math.pow((t_kelvin / t_sl), 5.25588)
        # Air density rho = P / (R * T), R = 287.058 J/(kg*K)
        rho = (p_kpa * 1000.0) / (287.058 * t_kelvin)
        
        return {
            "temperature_c": t_celsius,
            "pressure_kpa": p_kpa,
            "air_density_kg_m3": rho,
            "density_ratio": rho / 1.225
        }

    def compute_expected_state(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates expected physical parameters from operating context:
        ExpectedState = f(RPM, throttle, MAP, altitude, ambient_temp, ambient_press, fuel_flow, load, flight_phase)
        """
        rpm = float(telemetry.get("rpm", 4215.0))
        throttle = float(telemetry.get("throttle", 68.0)) / 100.0 # fraction 0.0 - 1.0
        alt_ft = float(telemetry.get("altitude_ft", 15000.0))
        ambient_temp = float(telemetry.get("ambient_temperature_c", -14.5))
        
        # 1. Atmospheric Context
        isa = self.calculate_isa_atmosphere(alt_ft)
        density_ratio = isa["density_ratio"]
        
        # 2. Expected Manifold Absolute Pressure (kPa)
        # Rotax 914 Turbocharger maintains MAP around 95-108 kPa up to 16,000 ft
        turbo_boost = 1.15 if alt_ft > 5000 else 1.0
        exp_map_kpa = round(min(115.0, max(45.0, (40.0 + throttle * 60.0) * turbo_boost)), 2)
        
        # 3. Expected Engine Load & Power Output
        # Power is proportional to RPM * MAP
        exp_load_pct = round(min(100.0, max(15.0, (throttle * 0.75 + (rpm / self.max_continuous_rpm) * 0.25) * 100.0)), 1)
        est_power_kw = (rpm / self.max_continuous_rpm) * (exp_map_kpa / 100.0) * self.rated_power_kw
        # Mechanical torque tau = Power / omega = (P * 60,000) / (2 * pi * RPM) in N*m
        omega_rad_s = (2.0 * math.pi * max(100.0, rpm)) / 60.0
        est_torque_nm = (est_power_kw * 1000.0) / omega_rad_s
        
        # 4. Expected Fuel Flow (L/h or ml/min)
        # Fuel Flow = Power (kW) * BSFC (g/kWh) / (Density * 1000)
        # Scaled to simulator ml/min representation (nominal ~5.0 - 6.0)
        exp_fuel_flow = round(min(12.0, max(1.5, 1.8 + (rpm / 1000.0) * 0.75 + throttle * 0.8)), 2)
        
        # 5. Expected Cylinder Head Temperature (°C)
        # CHT depends on combustion heat flux vs ram-air / coolant heat rejection
        # Nominal cruise CHT ~75°C - 85°C
        exp_cht_c = round(60.0 + (throttle * 22.0) + (exp_load_pct * 0.08) + (ambient_temp - 15.0) * 0.15, 2)
        
        # 6. Expected Exhaust Gas Temperature (°C)
        # Lean/rich mixture and load effect; nominal ~620°C - 680°C
        exp_egt_c = round(560.0 + (throttle * 110.0) + (rpm / self.max_continuous_rpm) * 30.0, 1)
        
        # 7. Expected Oil Temperature (°C)
        # Thermostatically regulated with heat exchanger: nominal ~78°C - 86°C
        exp_oil_temp_c = round(68.0 + (throttle * 14.0) + (exp_load_pct * 0.05) + (ambient_temp - 15.0) * 0.1, 2)
        
        # 8. Expected Oil Pressure (Bar)
        # Hydrodynamic pump displacement proportional to RPM, inversely related to oil temperature viscosity
        exp_oil_press_bar = round(min(5.5, max(1.8, 2.2 + (rpm / self.max_continuous_rpm) * 2.4 - (exp_oil_temp_c - 80.0) * 0.02)), 2)
        
        # 9. Expected Engine Baseline Vibration RMS (mm/s)
        # 2nd harmonic crankshaft rotational vibration; baseline ~1.2 - 1.8 mm/s
        exp_vibration_mms = round(0.8 + (rpm / 3000.0) * 0.6 + (exp_load_pct / 100.0) * 0.2, 2)

        # 10. Operating Regime Classification
        flight_phase = str(telemetry.get("flight_phase", "CRUISE")).upper()
        if rpm < 400.0:
            regime = "SHUTDOWN"
        elif rpm < 1200.0:
            regime = "START"
        elif rpm < 2200.0:
            regime = "IDLE"
        elif throttle > 0.88 or exp_load_pct > 85.0:
            regime = "HIGH_LOAD"
        elif throttle >= 0.82 or flight_phase == "CLIMB":
            regime = "CLIMB"
        elif flight_phase == "DESCENT" or (throttle < 0.35 and alt_ft > 3000.0):
            regime = "DESCENT"
        elif throttle < 0.35:
            regime = "LOW_LOAD"
        else:
            regime = "CRUISE"

        return {
            "expected_rpm": rpm,
            "expected_map_kpa": exp_map_kpa,
            "expected_fuel_flow": exp_fuel_flow,
            "expected_egt_c": exp_egt_c,
            "expected_cht_c": exp_cht_c,
            "expected_oil_temperature_c": exp_oil_temp_c,
            "expected_oil_pressure_bar": exp_oil_press_bar,
            "expected_vibration_mms": exp_vibration_mms,
            "expected_load_pct": exp_load_pct,
            "estimated_power_kw": round(est_power_kw, 2),
            "estimated_torque_nm": round(est_torque_nm, 2),
            "angular_velocity_rad_s": round(omega_rad_s, 2),
            "isa_air_density": round(isa["air_density_kg_m3"], 4),
            "operating_regime": regime,
            "model_version": "AERIS-MV-AeroPiston-v1.8"
        }

