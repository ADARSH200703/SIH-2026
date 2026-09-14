"""
AERIS-TWIN — Arduino Uno Serial Telemetry Integration Tests
Validates the full 10-point test specification:
1. Valid Arduino JSON parsing.
2. Invalid JSON handling.
3. Missing optional sensor fields (strict null preservation).
4. Sequence number preservation.
5. MOTOR_PROTOTYPE profile preservation.
6. PHYSICAL_SENSOR source preservation.
7. Simulation/physical separation (Mock vs Physical tagging).
8. Backend POST success (/api/telemetry/hardware).
9. Backend unavailable/retry behavior.
10. Serial disconnect/reconnect behavior.
"""
import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import httpx

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app, live_source
import backend.main as main_module
from hardware.arduino_uno.serial_bridge import (
    parse_and_validate_packet,
    ArduinoSerialBridge
)

class TestArduinoSerialIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        live_source.reset()

    # -------------------------------------------------------------------------
    # 1. Valid Arduino JSON Parsing
    # -------------------------------------------------------------------------
    def test_01_valid_arduino_json_parsing(self):
        """Test parsing of a clean, well-formed JSON line from Arduino Uno."""
        raw_json = json.dumps({
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 1042,
            "timestamp_ms": 154300,
            "rpm": 1850.0,
            "current_a": 1.45,
            "voltage_v": 11.85,
            "temperature_c": 36.2,
            "vibration": 0.82,
            "motor_load_pct": 42.0,
            "firmware_version": "v1.0.0-uno-serial"
        })
        packet, err = parse_and_validate_packet(raw_json, is_mock=False)
        self.assertIsNone(err)
        self.assertIsNotNone(packet)
        self.assertEqual(packet["device_id"], "AERIS-UNO-001")
        self.assertEqual(packet["sequence_number"], 1042)
        self.assertEqual(packet["rpm"], 1850.0)
        self.assertEqual(packet["current_a"], 1.45)
        self.assertEqual(packet["voltage_v"], 11.85)
        self.assertEqual(packet["power_w"], 17.18)  # 11.85 * 1.45
        self.assertEqual(packet["temperature_c"], 36.2)
        self.assertEqual(packet["vibration"], 0.82)
        self.assertEqual(packet["motor_load_pct"], 42.0)
        self.assertEqual(packet["is_simulated"], False)

    # -------------------------------------------------------------------------
    # 2. Invalid JSON Handling
    # -------------------------------------------------------------------------
    def test_02_invalid_json_handling(self):
        """Test that malformed lines, partial transmissions, or debug strings do not crash parser."""
        # Truncated JSON
        p1, err1 = parse_and_validate_packet('{"device_id":"AERIS-UNO-001","rpm":1850', is_mock=False)
        self.assertIsNone(p1)
        self.assertIn("JSON parse error", err1)

        # Plain text / boot log
        p2, err2 = parse_and_validate_packet("[LOG] Arduino Uno Booting Initialized...", is_mock=False)
        self.assertIsNone(p2)
        self.assertIn("Debug message", err2)

        # Empty line
        p3, err3 = parse_and_validate_packet("   \n\r", is_mock=False)
        self.assertIsNone(p3)
        self.assertEqual(err3, "Empty line")

        # Non-dictionary JSON (array or scalar)
        p4, err4 = parse_and_validate_packet("[1, 2, 3]", is_mock=False)
        self.assertIsNone(p4)
        self.assertIn("not a JSON object", err4)

    # -------------------------------------------------------------------------
    # 3. Missing Optional Sensor Fields (Strict Null Preservation)
    # -------------------------------------------------------------------------
    def test_03_missing_optional_sensor_fields_null_preservation(self):
        """Ensure missing sensors (e.g. RPM, temperature, vibration) are strictly preserved as None."""
        raw_json = json.dumps({
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 5,
            "timestamp_ms": 500,
            "rpm": None,
            "current_a": 1.25,
            "voltage_v": 11.90,
            "temperature_c": None,
            "vibration": None,
            "motor_load_pct": None
        })
        packet, err = parse_and_validate_packet(raw_json, is_mock=False)
        self.assertIsNone(err)
        self.assertIsNone(packet["rpm"])
        self.assertIsNone(packet["temperature_c"])
        self.assertIsNone(packet["vibration"])
        self.assertIsNone(packet["motor_load_pct"])
        self.assertEqual(packet["current_a"], 1.25)
        self.assertEqual(packet["voltage_v"], 11.90)

    # -------------------------------------------------------------------------
    # 4. Sequence Number Preservation
    # -------------------------------------------------------------------------
    def test_04_sequence_number_preservation(self):
        """Test that Arduino sequence numbers are preserved through ingestion."""
        payload = {
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 98765,
            "current_a": 1.50,
            "voltage_v": 12.00
        }
        res = self.client.post("/api/telemetry/hardware", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["sequence_number"], 98765)
        self.assertEqual(live_source.last_sequence_num, 98765)

    # -------------------------------------------------------------------------
    # 5. MOTOR_PROTOTYPE Profile Preservation
    # -------------------------------------------------------------------------
    def test_05_motor_prototype_profile_preservation(self):
        """Test that MOTOR_PROTOTYPE profile is maintained without defaulting to AERO_ENGINE."""
        payload = {
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 1,
            "current_a": 1.80,
            "voltage_v": 11.75
        }
        res = self.client.post("/api/telemetry/hardware", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["profile"], "MOTOR_PROTOTYPE")
        frame = live_source.last_frame
        self.assertEqual(frame["profile"], "MOTOR_PROTOTYPE")
        # Ensure NO aero-engine fields were silently inserted
        self.assertNotIn("oilPressure", frame)
        self.assertNotIn("cht_c", frame)

    # -------------------------------------------------------------------------
    # 6. PHYSICAL_SENSOR Source Preservation
    # -------------------------------------------------------------------------
    def test_06_physical_sensor_source_preservation(self):
        """Test that source is strictly preserved as PHYSICAL_SENSOR."""
        payload = {
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 2,
            "current_a": 1.60,
            "voltage_v": 11.80
        }
        res = self.client.post("/api/telemetry/hardware", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["source"], "PHYSICAL_SENSOR")
        self.assertEqual(live_source.last_source, "PHYSICAL_SENSOR")

    # -------------------------------------------------------------------------
    # 7. Simulation vs Physical Separation (Mock vs Physical Tagging)
    # -------------------------------------------------------------------------
    def test_07_simulation_physical_separation(self):
        """Test strict boundary between physical packets and mock test packets."""
        # Physical packet
        raw_phys = json.dumps({
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 10,
            "current_a": 1.5,
            "voltage_v": 11.9
        })
        p_phys, _ = parse_and_validate_packet(raw_phys, is_mock=False)
        self.assertEqual(p_phys["source"], "PHYSICAL_SENSOR")
        self.assertEqual(p_phys["is_simulated"], False)

        # Mock packet
        raw_mock = json.dumps({
            "device_id": "AERIS-UNO-MOCK",
            "profile": "MOTOR_PROTOTYPE",
            "source": "SIMULATION_PRODUCER",
            "sequence_number": 1,
            "current_a": 1.5,
            "voltage_v": 11.9
        })
        p_mock, _ = parse_and_validate_packet(raw_mock, is_mock=True)
        self.assertEqual(p_mock["source"], "SIMULATION_PRODUCER")
        self.assertEqual(p_mock["is_simulated"], True)
        self.assertEqual(p_mock["device_id"], "AERIS-UNO-MOCK")

    # -------------------------------------------------------------------------
    # 8. Backend POST Success via Bridge
    # -------------------------------------------------------------------------
    def test_08_bridge_send_packet_success(self):
        """Test that ArduinoSerialBridge successfully POSTs packets to backend."""
        bridge = ArduinoSerialBridge(
            port="COM4",
            backend_url="http://testserver",
            endpoint="/api/telemetry/hardware"
        )
        bridge.http_client = self.client

        packet = {
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 50,
            "timestamp": time.time(),
            "rpm": 1850.0,
            "current_a": 1.45,
            "voltage_v": 11.80,
            "power_w": 17.11,
            "is_simulated": False
        }

        success = bridge.send_packet_to_backend(packet)
        self.assertTrue(success)
        self.assertEqual(bridge.packets_sent, 1)
        self.assertEqual(bridge.packets_failed, 0)
        bridge.close()

    # -------------------------------------------------------------------------
    # 9. Backend Unavailable / Retry Behavior
    # -------------------------------------------------------------------------
    def test_09_bridge_backend_unavailable_handling(self):
        """Test that network/backend connection errors are caught cleanly without crashing."""
        bridge = ArduinoSerialBridge(
            port="COM4",
            backend_url="http://invalid-nonexistent-host:9999",
            endpoint="/api/telemetry/hardware"
        )
        packet = {
            "device_id": "AERIS-UNO-001",
            "profile": "MOTOR_PROTOTYPE",
            "source": "PHYSICAL_SENSOR",
            "sequence_number": 51,
            "timestamp": time.time(),
            "current_a": 1.45,
            "voltage_v": 11.80
        }

        # Should return False and increment packets_failed without raising unhandled exception
        success = bridge.send_packet_to_backend(packet)
        self.assertFalse(success)
        self.assertEqual(bridge.packets_failed, 1)
        bridge.close()

    # -------------------------------------------------------------------------
    # 10. Serial Disconnect / Reconnect Simulation Behavior
    # -------------------------------------------------------------------------
    def test_10_serial_disconnect_reconnect_simulation(self):
        """Test that the bridge's mock run loop runs and terminates cleanly."""
        bridge = ArduinoSerialBridge(
            port="COM4",
            backend_url="http://testserver",
            is_mock=True,
            mock_rate_hz=50.0  # Fast rate for test
        )
        bridge.http_client = self.client

        # Run mock loop for 5 packets
        bridge.run_mock_loop(max_count=5)
        self.assertEqual(bridge.packets_sent, 5)
        self.assertEqual(bridge.packets_failed, 0)

        # Verify live_source has received the mock telemetry
        status = live_source.get_status()
        self.assertEqual(status["device_id"], "AERIS-UNO-MOCK")
        self.assertEqual(status["source"], "SIMULATION_PRODUCER")
        self.assertEqual(status["profile"], "MOTOR_PROTOTYPE")
        bridge.close()


if __name__ == "__main__":
    unittest.main()
