"""
Counterfactual What-If Simulation Engine for AERIS-TWIN
Evaluates hypothetical mission profiles (altitude, power derating, ambient temp, duration)
projected from current Digital Twin state.
"""
from typing import Dict, Any, List
import numpy as np

class WhatIfSimulationEngine:
    def __init__(self, physics_model, risk_engine):
        self.physics_model = physics_model
        self.risk_engine = risk_engine

    def simulate_what_if(
        self,
        current_twin_state: Dict[str, Any],
        duration_hours: float,
        altitude_ft: float,
        power_setting: float,
        ambient_temp_c: float
    ) -> Dict[str, Any]:
        """
        Simulates engine dynamics and degradation accumulation under counterfactual flight conditions.
        """
        # Extract baseline current state
        deg_state = current_twin_state.get("degradation_state", {}).get("value", {})
        current_d = float(deg_state.get("normalized_degradation", 0.05))
        base_vel = float(deg_state.get("degradation_velocity", 0.002))
        
        fault_state = current_twin_state.get("fault_state", {}).get("value", {})
        fault_class = fault_state.get("fault", "NOMINAL")
        fault_prob = float(fault_state.get("probability", 0.05))
        
        # 1. Physics reaction under counterfactual condition
        power_frac = power_setting / 100.0 if power_setting > 1.2 else power_setting
        hypothetical_telemetry = {
            "rpm": 3800.0 + power_frac * 1200.0,
            "throttle": power_frac * 100.0,
            "altitude_ft": altitude_ft,
            "ambient_temperature_c": ambient_temp_c,
            "engine_load": power_frac * 90.0,
            "flight_phase": "CRUISE"
        }
        
        expected_physics = self.physics_model.compute_expected_state(hypothetical_telemetry)
        
        # 2. Projected degradation velocity under new load & thermal stress
        # Higher power setting & higher ambient temp accelerate wear exponentially
        power_factor = float(np.exp((power_frac - 0.70) * 2.2))
        temp_factor = 1.0 + max(0.0, (ambient_temp_c - 20.0) * 0.02)
        alt_factor = 1.0 + max(0.0, (altitude_ft - 15000.0) / 25000.0)
        
        projected_velocity = round(base_vel * power_factor * temp_factor * alt_factor, 5)
        
        # 3. Projected degradation accumulation over proposed mission duration
        delta_d = round(projected_velocity * duration_hours, 4)
        projected_end_d = round(min(0.98, current_d + delta_d), 4)
        
        # 4. Projected RUL at end of simulated mission
        d_failure = 0.75
        remaining_margin = max(0.0, d_failure - projected_end_d)
        projected_rul_hours = round(remaining_margin / max(0.0005, projected_velocity), 1) if projected_velocity > 0 else 1000.0
        
        # 5. Risk evaluation under counterfactual mission
        projected_degradation = {
            "normalized_degradation": projected_end_d,
            "degradation_velocity": projected_velocity
        }
        projected_rul = {
            "rul_estimate_hours": projected_rul_hours,
            "lower_bound_hours": round(projected_rul_hours * 0.8, 1)
        }
        
        projected_risk = self.risk_engine.evaluate_risk(
            degradation_data=projected_degradation,
            fault_data=fault_state,
            rul_data=projected_rul,
            telemetry=hypothetical_telemetry,
            planned_duration_hours=duration_hours
        )
        
        # 6. Build Comparative Scenarios:
        # Scenario A: Proposed Parameter Setting
        # Scenario B: Conservative Power Derate (-15% throttle)
        derated_telemetry = dict(hypothetical_telemetry, throttle=max(45.0, hypothetical_telemetry["throttle"] - 15.0), power_setting=max(0.5, power_frac - 0.15))
        derated_vel = round(base_vel * float(np.exp((derated_telemetry["power_setting"] - 0.70) * 2.2)) * temp_factor, 5)
        derated_end_d = round(min(0.98, current_d + derated_vel * duration_hours), 4)
        derated_rul = round(max(0.0, d_failure - derated_end_d) / max(0.0005, derated_vel), 1)
        derated_risk = self.risk_engine.evaluate_risk(
            degradation_data={"normalized_degradation": derated_end_d, "degradation_velocity": derated_vel},
            fault_data=fault_state,
            rul_data={"rul_estimate_hours": derated_rul, "lower_bound_hours": round(derated_rul * 0.8, 1)},
            telemetry=derated_telemetry,
            planned_duration_hours=duration_hours
        )

        return {
            "proposed_parameters": {
                "duration_hours": duration_hours,
                "altitude_ft": altitude_ft,
                "power_setting": power_setting,
                "ambient_temperature_c": ambient_temp_c
            },
            "projected_state": {
                "initial_degradation": current_d,
                "projected_final_degradation": projected_end_d,
                "projected_degradation_velocity": projected_velocity,
                "projected_rul_hours": projected_rul_hours,
                "expected_cht_c": expected_physics["expected_cht_c"],
                "expected_oil_pressure_bar": expected_physics["expected_oil_pressure_bar"],
                "expected_fuel_flow": expected_physics["expected_fuel_flow"]
            },
            "projected_risk": projected_risk,
            "scenario_comparisons": [
                {
                    "name": "Proposed Profile",
                    "power_setting": power_setting,
                    "risk_index": projected_risk["risk_index"],
                    "completion_probability": projected_risk["completion_probability"],
                    "final_degradation": projected_end_d
                },
                {
                    "name": "Power Derating Option (-15% Power)",
                    "power_setting": round(derated_telemetry["power_setting"], 2),
                    "risk_index": derated_risk["risk_index"],
                    "completion_probability": derated_risk["completion_probability"],
                    "final_degradation": derated_end_d
                }
            ],
            "confidence": 0.88,
            "model_assumptions": "Quasi-steady power law degradation scaling; ISA troposphere thermal dissipation model."
        }
