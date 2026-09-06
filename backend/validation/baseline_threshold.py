"""
Threshold Baseline Engine for AERIS-TWIN Evaluator Comparison
Implements traditional single-parameter threshold alarms (the industry standard baseline)
to measure exact empirical performance advantages of AERIS-TWIN Digital Twin monitoring.
"""
from typing import Dict, Any, List

class ThresholdBaselineEngine:
    def __init__(self):
        # Traditional fixed aerospace threshold limits
        self.thresholds = {
            "vibration_warning": 3.2,     # mm/s
            "vibration_alarm": 4.5,       # mm/s
            "cht_warning": 88.0,          # °C
            "cht_alarm": 98.0,            # °C
            "oil_press_warning": 3.2,     # Bar
            "oil_press_alarm": 2.2,       # Bar
            "rpm_max_warning": 5400.0,    # RPM
            "rpm_max_alarm": 5800.0       # RPM
        }

    def evaluate_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates telemetry using traditional static thresholds.
        """
        vib = float(telemetry.get("vibration", 1.6))
        cht = float(telemetry.get("temperature", 78.4))
        oil = float(telemetry.get("oilPressure", 4.3))
        rpm = float(telemetry.get("rpm", 4215.0))
        
        alarm_triggered = False
        warning_triggered = False
        triggered_rules = []
        
        # Check Alarms
        if vib >= self.thresholds["vibration_alarm"]:
            alarm_triggered = True
            triggered_rules.append(f"Vibration ({vib} mm/s) >= Alarm Limit ({self.thresholds['vibration_alarm']} mm/s)")
        elif vib >= self.thresholds["vibration_warning"]:
            warning_triggered = True
            triggered_rules.append(f"Vibration ({vib} mm/s) >= Warning Limit ({self.thresholds['vibration_warning']} mm/s)")
            
        if cht >= self.thresholds["cht_alarm"]:
            alarm_triggered = True
            triggered_rules.append(f"CHT ({cht} °C) >= Alarm Limit ({self.thresholds['cht_alarm']} °C)")
        elif cht >= self.thresholds["cht_warning"]:
            warning_triggered = True
            triggered_rules.append(f"CHT ({cht} °C) >= Warning Limit ({self.thresholds['cht_warning']} °C)")
            
        if oil <= self.thresholds["oil_press_alarm"]:
            alarm_triggered = True
            triggered_rules.append(f"Oil Pressure ({oil} Bar) <= Alarm Limit ({self.thresholds['oil_press_alarm']} Bar)")
        elif oil <= self.thresholds["oil_press_warning"]:
            warning_triggered = True
            triggered_rules.append(f"Oil Pressure ({oil} Bar) <= Warning Limit ({self.thresholds['oil_press_warning']} Bar)")
            
        if rpm >= self.thresholds["rpm_max_alarm"]:
            alarm_triggered = True
            triggered_rules.append(f"RPM ({rpm}) >= Overspeed Alarm ({self.thresholds['rpm_max_alarm']})")
        elif rpm >= self.thresholds["rpm_max_warning"]:
            warning_triggered = True
            triggered_rules.append(f"RPM ({rpm}) >= Caution Limit ({self.thresholds['rpm_max_warning']})")
            
        status = "ALARM" if alarm_triggered else ("WARNING" if warning_triggered else "NORMAL")
        
        return {
            "system": "TRADITIONAL_THRESHOLD_MONITORING",
            "anomaly_detected": alarm_triggered or warning_triggered,
            "status": status,
            "triggered_rules": triggered_rules,
            "has_fault_classification": False,
            "has_rul_estimation": False,
            "has_consensus": False,
            "has_counterfactual_simulation": False
        }
