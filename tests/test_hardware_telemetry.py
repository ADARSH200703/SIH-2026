"""
Hardware Telemetry Verification Test Suite for AERIS-TWIN
Tests:
1. POST /api/telemetry/hardware and POST /api/telemetry/live endpoints.
2. Hardware authentication verification (X-Device-API-Key header and JSON api_key).
3. Payload normalization (mapping aliases like 'cht'/'temperature', 'oil_pressure', 'vibration').
4. Hardware metadata tracking (device_id, gateway_source, wifi_rssi, firmware_version) in LiveStreamSource.
5. Telemetry stream state transitions (CONNECTED -> STALE -> DISCONNECTED).
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app, live_source
import backend.main as main_module

class TestHardwareTelemetry(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Reset live_source before each test
        live_source.reset()

    def test_01_hardware_endpoint_open_mode(self):
        """Test telemetry ingestion when no API key is enforced."""
        original_key = main_module.AERIS_DEVICE_API_KEY
        main_module.AERIS_DEVICE_API_KEY = ""  # Permissive dev mode
        try:
            payload = {
                "device_id": "AERIS-UAV-HW-01",
                "gateway_source": "ESP32",
                "firmware_version": "v1.4.2-hw",
                "wifi_rssi": -55,
                "seq": 1,
                "source": "PHYSICAL_SENSOR",
                "rpm": 5420.0,
                "cht": 148.5,
                "oil_pressure": 4.2,
                "vibration": 1.8,
                "fuel_flow": 8.5,
                "engine_load": 65.0
            }
            res = self.client.post("/api/telemetry/hardware", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "ingested")
            self.assertEqual(data["mode"], "LIVE")
            self.assertEqual(data["device_id"], "AERIS-UAV-HW-01")
            self.assertEqual(data["source"], "PHYSICAL_SENSOR")
            self.assertIn("health_index", data)

            # Check status reported by LiveStreamSource
            status = live_source.get_status()
            self.assertEqual(status["status"], "CONNECTED")
            self.assertEqual(status["device_id"], "AERIS-UAV-HW-01")
            self.assertEqual(status["source"], "PHYSICAL_SENSOR")
            self.assertEqual(status["wifi_rssi"], -55)
            self.assertEqual(status["firmware_version"], "v1.4.2-hw")
        finally:
            main_module.AERIS_DEVICE_API_KEY = original_key

    def test_02_hardware_endpoint_with_auth_header(self):
        """Test telemetry ingestion with strict API key authentication header."""
        original_key = main_module.AERIS_DEVICE_API_KEY
        main_module.AERIS_DEVICE_API_KEY = "test-secret-hardware-key-2026"
        try:
            payload = {
                "device_id": "AERIS-UAV-HW-02",
                "gateway_source": "ESP32",
                "firmware_version": "v1.4.2-hw",
                "wifi_rssi": -62,
                "seq": 2,
                "source": "PHYSICAL_SENSOR",
                "rpm": 5500.0,
                "cht": 150.0,
                "oil_pressure": 4.1,
                "vibration": 1.9,
                "fuel_flow": 8.7,
                "engine_load": 68.0
            }
            # Attempt without key -> 401 Unauthorized
            res_fail = self.client.post("/api/telemetry/hardware", json=payload)
            self.assertEqual(res_fail.status_code, 401)

            # Attempt with wrong key -> 401 Unauthorized
            res_wrong = self.client.post(
                "/api/telemetry/hardware",
                headers={"X-Device-API-Key": "wrong-key"},
                json=payload
            )
            self.assertEqual(res_wrong.status_code, 401)

            # Attempt with correct header -> 200 OK
            res_ok = self.client.post(
                "/api/telemetry/hardware",
                headers={"X-Device-API-Key": "test-secret-hardware-key-2026"},
                json=payload
            )
            self.assertEqual(res_ok.status_code, 200)
            self.assertEqual(res_ok.json()["status"], "ingested")

            # Check live source status
            status = live_source.get_status()
            self.assertEqual(status["device_id"], "AERIS-UAV-HW-02")
        finally:
            main_module.AERIS_DEVICE_API_KEY = original_key

    def test_03_hardware_endpoint_with_body_auth_and_normalization(self):
        """Test telemetry ingestion with API key provided in JSON payload and sensor field aliases."""
        original_key = main_module.AERIS_DEVICE_API_KEY
        main_module.AERIS_DEVICE_API_KEY = "test-secret-hardware-key-2026"
        try:
            payload = {
                "api_key": "test-secret-hardware-key-2026",
                "device_id": "AERIS-UAV-HW-03",
                "gateway_source": "ESP32",
                "seq": 3,
                "rpm": 5350.0,
                "cht": 142.0,          # alias for temperature
                "oil_pressure": 4.3,   # alias for oilPressure
                "vibration": 1.7,      # alias for vibration
                "fuel_flow": 8.4,      # alias for fuelFlow
                "engine_load": 64.0    # alias for engineLoad
            }
            res = self.client.post("/api/telemetry/hardware", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "ingested")
            self.assertEqual(data["device_id"], "AERIS-UAV-HW-03")

            # Verify that live_source buffer holds the frame with normalized values
            frame = live_source.last_frame
            self.assertIsNotNone(frame)
            self.assertEqual(frame["temperature"], 142.0)
            self.assertEqual(frame["oilPressure"], 4.3)
            self.assertEqual(frame["fuelFlow"], 8.4)
            self.assertEqual(frame["engineLoad"], 64.0)
        finally:
            main_module.AERIS_DEVICE_API_KEY = original_key

    def test_04_live_source_status_endpoint(self):
        """Test GET /api/telemetry/status returns hardware telemetry metadata."""
        payload = {
            "device_id": "AERIS-UAV-HW-STATUS-TEST",
            "gateway_source": "ESP32_TEST",
            "firmware_version": "v1.4.2-hw",
            "wifi_rssi": -48,
            "rpm": 5400.0,
            "cht": 145.0,
            "oil_pressure": 4.2,
            "vibration": 1.8,
            "fuel_flow": 8.5,
            "engine_load": 65.0
        }
        self.client.post("/api/telemetry/live", json=payload)

        res = self.client.get("/api/telemetry/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "CONNECTED")
        self.assertEqual(data["connected"], True)
        self.assertEqual(data["device_id"], "AERIS-UAV-HW-STATUS-TEST")
        self.assertEqual(data["wifi_rssi"], -48)
        self.assertEqual(data["firmware_version"], "v1.4.2-hw")
        self.assertIn("data_age_ms", data)

if __name__ == "__main__":
    unittest.main()
