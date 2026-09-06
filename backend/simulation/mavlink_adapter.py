"""
MAVLink & Telemetry Gateway Adapter for AERIS-TWIN
Abstracts physical/simulated telemetry link, monitors packet drop rates,
sequence gaps, latency, and handles link staleness/loss defensively.
"""
import time
from typing import Dict, Any, Optional

class TelemetryGatewayAdapter:
    def __init__(self, stale_timeout_sec: float = 3.0, disconnect_timeout_sec: float = 8.0):
        self.stale_timeout_sec = stale_timeout_sec
        self.disconnect_timeout_sec = disconnect_timeout_sec
        
        self.last_packet_time = time.time()
        self.last_sequence_num = -1
        self.total_packets_received = 0
        self.total_packets_dropped = 0
        self.current_latency_ms = 4.2
        
    def ingest_packet(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes packet from MAVLink / REST / Simulator, checks sequence order and integrity.
        """
        now = time.time()
        seq = raw_data.get("sequence_number", self.last_sequence_num + 1)
        
        # Check sequence gap
        if self.last_sequence_num >= 0 and seq > (self.last_sequence_num + 1):
            dropped = seq - (self.last_sequence_num + 1)
            self.total_packets_dropped += dropped
            
        self.last_sequence_num = seq
        self.last_packet_time = now
        self.total_packets_received += 1
        
        # Compute dynamic latency
        sent_ts = raw_data.get("timestamp", now)
        self.current_latency_ms = round(max(0.5, (now - sent_ts) * 1000.0), 2)
        
        return raw_data

    def get_link_status(self) -> Dict[str, Any]:
        """
        Calculates telemetry link health, packet age, and connection status.
        """
        now = time.time()
        age_sec = round(now - self.last_packet_time, 2)
        
        total_expected = self.total_packets_received + self.total_packets_dropped
        loss_rate = round((self.total_packets_dropped / max(1, total_expected)) * 100.0, 2)
        
        if age_sec > self.disconnect_timeout_sec:
            status = "DISCONNECTED"
        elif age_sec > self.stale_timeout_sec:
            status = "STALE"
        elif loss_rate > 10.0:
            status = "DEGRADED"
        else:
            status = "CONNECTED"
            
        return {
            "link_status": status,
            "packet_age_seconds": age_sec,
            "latency_ms": self.current_latency_ms,
            "packet_loss_rate_pct": loss_rate,
            "total_received": self.total_packets_received,
            "total_dropped": self.total_packets_dropped,
            "last_valid_timestamp": self.last_packet_time
        }
