"""
Real-Time Alert Debouncing & State Transition Engine for AERIS-TWIN
Prevents alert fatigue/flooding by maintaining active alert state machines,
tracking condition onset/duration, updating evidence, and emitting discrete transition events.
"""
import time
from typing import Dict, Any, List, Optional
from collections import deque


class AlertState:
    """Represents a single persistent, debounced alert condition."""

    def __init__(self, key: str, severity: str, title: str, initial_evidence: List[str], timestamp: float):
        self.key = key
        self.severity = severity  # "warning" or "critical"
        self.title = title
        self.evidence = list(initial_evidence)
        self.first_detected_ts = timestamp
        self.last_updated_ts = timestamp
        self.occurrence_count = 1
        self.is_active = True

    def update(self, evidence: List[str], timestamp: float):
        self.last_updated_ts = timestamp
        self.evidence = list(evidence)
        self.occurrence_count += 1

    def to_dict(self) -> Dict[str, Any]:
        duration_sec = round(self.last_updated_ts - self.first_detected_ts, 1)
        h = int(duration_sec // 3600)
        m = int((duration_sec % 3600) // 60)
        s = int(duration_sec % 60)
        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

        t_str = time.strftime("%H:%M:%S", time.localtime(self.first_detected_ts))

        return {
            "key": self.key,
            "severity": self.severity,
            "title": self.title,
            "evidence": self.evidence,
            "first_detected": t_str,
            "first_detected_ts": self.first_detected_ts,
            "last_updated_ts": self.last_updated_ts,
            "duration_seconds": duration_sec,
            "duration_str": dur_str,
            "occurrences": self.occurrence_count,
            "is_active": self.is_active,
        }


class RealtimeAlertEngine:
    """
    Manages active alerts, alert debouncing, and timestamped state-transition events.
    """

    def __init__(self, max_timeline_events: int = 200):
        self.active_alerts: Dict[str, AlertState] = {}
        self.current_system_state: str = "NORMAL"  # NORMAL, ANOMALY, HIGH_RISK, CRITICAL
        self.event_timeline: deque = deque(maxlen=max_timeline_events)
        self.transition_history: deque = deque(maxlen=100)

        # Initial nominal event
        self._record_event("Evaluator Initialized — State: NOMINAL", "info", time.time())

    def _format_time(self, ts: float) -> str:
        return time.strftime("%H:%M:%S", time.localtime(ts))

    def _record_event(self, text: str, event_type: str, timestamp: float, details: Optional[Dict[str, Any]] = None):
        event = {
            "id": f"EVT-{int(timestamp*1000)}-{len(self.event_timeline)+1}",
            "time": self._format_time(timestamp),
            "timestamp": timestamp,
            "text": text,
            "type": event_type,  # info, warning, critical, success
            "details": details or {},
        }
        self.event_timeline.appendleft(event)
        return event

    def evaluate_state_transitions(
        self,
        health_index: float,
        anomaly_result: Dict[str, Any],
        fault_result: Dict[str, Any],
        risk_result: Dict[str, Any],
        sensor_trust: Dict[str, Any],
        residuals: Dict[str, Any],
        telemetry: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes alert evaluation, updates active alert records without duplicate spam,
        and generates state transition events.
        """
        timestamp = telemetry.get("timestamp", time.time())

        # Determine target state
        is_anomaly = anomaly_result.get("anomaly", False)
        risk_level = risk_result.get("risk_level", "LOW")
        fault_name = fault_result.get("fault", "NOMINAL")
        sensor_trust_score = sensor_trust.get("aggregate_trust_score", 1.0)

        if health_index < 50 or risk_level == "CRITICAL" or fault_result.get("severity") == "CRITICAL":
            new_system_state = "CRITICAL"
        elif health_index < 75 or risk_level == "HIGH" or is_anomaly:
            new_system_state = "HIGH_RISK" if risk_level == "HIGH" else "ANOMALY"
        else:
            new_system_state = "NORMAL"

        # Check for State Transition
        if new_system_state != self.current_system_state:
            prev = self.current_system_state
            self.current_system_state = new_system_state

            trans_text = f"State Transition: {prev} → {new_system_state}"
            severity = "critical" if new_system_state == "CRITICAL" else ("warning" if new_system_state in ["HIGH_RISK", "ANOMALY"] else "success")
            self._record_event(trans_text, severity, timestamp, {
                "previous_state": prev,
                "new_state": new_system_state,
                "health_index": health_index,
                "fault": fault_name,
            })
            self.transition_history.append({
                "from_state": prev,
                "to_state": new_system_state,
                "timestamp": timestamp,
                "health_index": health_index,
            })

        # Evaluate condition rules for debounced alerts
        active_keys_this_tick = set()

        # 1. Vibration / Bearing Alert
        vib_res = residuals.get("vibration", {}).get("normalized_residual", 0.0)
        vib_val = telemetry.get("vibration", 1.6)
        if vib_res > 2.5 or vib_val > 3.2 or fault_name == "BEARING_DEGRADATION":
            key = "BEARING_VIBRATION"
            active_keys_this_tick.add(key)
            sev = "critical" if vib_val > 3.8 or vib_res > 3.5 else "warning"
            ev = [
                f"Vibration residual: +{vib_res:.2f}σ above expected physics baseline",
                f"Casing acceleration: {vib_val:.2f} mm/s (Threshold: 2.4 mm/s)",
                f"Predicted mode: {fault_name.replace('_', ' ').title()}",
            ]
            self._upsert_alert(key, sev, "Excessive Engine Casing Vibration / Bearing Stress", ev, timestamp)

        # 2. Thermal / CHT Overheat Alert
        cht_val = telemetry.get("temperature", 78.4)
        cht_res = residuals.get("temperature", {}).get("normalized_residual", 0.0)
        if cht_val > 88.0 or cht_res > 2.5 or fault_name == "COOLING_DEGRADATION":
            key = "THERMAL_OVERHEAT"
            active_keys_this_tick.add(key)
            sev = "critical" if cht_val > 94.0 else "warning"
            ev = [
                f"Cylinder head temperature: {cht_val:.1f}°C (Limit: 85°C)",
                f"Thermal residual: +{cht_res:.2f}σ relative to ISA thermodynamic baseline",
            ]
            self._upsert_alert(key, sev, "Cylinder Head Thermal Stress / Overheat", ev, timestamp)

        # 3. Oil Pressure / Lubrication Deficit Alert
        oil_val = telemetry.get("oilPressure", 4.3)
        oil_res = residuals.get("oilPressure", {}).get("normalized_residual", 0.0)
        if oil_val < 3.2 or oil_res < -2.0 or fault_name == "FUEL_SYSTEM_DEGRADATION":
            key = "LUBRICATION_DEFICIT"
            active_keys_this_tick.add(key)
            sev = "critical" if oil_val < 2.5 else "warning"
            ev = [
                f"Oil pressure: {oil_val:.2f} Bar (Nominal minimum: 3.5 Bar)",
                f"Hydrodynamic film pressure deficit: {oil_res:.2f}σ",
            ]
            self._upsert_alert(key, sev, "Lubrication Oil Pressure Deficit", ev, timestamp)

        # 4. Sensor Trust Degradation Alert
        if sensor_trust_score < 0.85:
            key = "SENSOR_TRUST_DEGRADED"
            active_keys_this_tick.add(key)
            ev = [
                f"Aggregate sensor trust dropped to {int(sensor_trust_score*100)}%",
                f"Degraded channels: {', '.join([k for k, v in sensor_trust.get('sensors', {}).items() if v.get('trust_score', 1.0) < 0.8]) or 'Multiple'}",
            ]
            self._upsert_alert(key, "warning", "Sensor Quality / Data Stream Health Degraded", ev, timestamp)

        # Clear alerts that are no longer active
        keys_to_remove = [k for k in self.active_alerts if k not in active_keys_this_tick]
        for k in keys_to_remove:
            cleared_alert = self.active_alerts.pop(k)
            self._record_event(f"Alert Cleared: {cleared_alert.title}", "success", timestamp)

        # Build output structures
        active_list = [a.to_dict() for a in self.active_alerts.values()]

        return {
            "system_state": self.current_system_state,
            "active_alerts_count": len(active_list),
            "alerts": active_list,
            "recent_events": list(self.event_timeline)[:25],
        }

    def _upsert_alert(self, key: str, severity: str, title: str, evidence: List[str], timestamp: float):
        if key in self.active_alerts:
            # Update existing without emitting duplicate event
            self.active_alerts[key].update(evidence, timestamp)
            self.active_alerts[key].severity = severity
        else:
            # Trigger new alert event on state entry
            alert = AlertState(key, severity, title, evidence, timestamp)
            self.active_alerts[key] = alert
            self._record_event(f"Alert Triggered [{severity.upper()}]: {title}", severity, timestamp, {
                "key": key,
                "evidence": evidence,
            })
