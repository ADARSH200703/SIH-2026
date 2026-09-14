"""
AERIS-TWIN — Arduino Uno USB Serial Telemetry Bridge
Transmits real-time physical telemetry from an Arduino Uno over USB Serial (115200 baud)
to the AERIS-TWIN FastAPI backend (/api/telemetry/hardware) and WebSocket gateway.

Architecture:
  Arduino Uno (ATmega328P)
        ↓ USB Serial (115200 Baud, Newline-Delimited JSON)
  serial_bridge.py (Laptop / Host)
        ↓ HTTP POST /api/telemetry/hardware
  AERIS-TWIN Backend
        ↓ WebSocket /ws/telemetry
  Cockpit Dashboard UI

Usage:
  # Normal operation with physical Arduino Uno connected:
  python hardware/arduino_uno/serial_bridge.py --port COM4

  # Diagnostic / Debug mode with detailed request-response tracing:
  python hardware/arduino_uno/serial_bridge.py --port COM4 --debug

  # Custom baud rate and backend endpoint:
  python hardware/arduino_uno/serial_bridge.py --port COM4 --baud 115200 --url http://127.0.0.1:8000

  # Authenticated ingestion with device API key:
  python hardware/arduino_uno/serial_bridge.py --port COM4 --api-key aeris-device-secret-key-2026

  # Mock / Software testing mode without physical hardware:
  python hardware/arduino_uno/serial_bridge.py --mock --count 50
"""
import argparse
import json
import logging
import math
import os
import signal
import sys
import time
from typing import Dict, Any, Optional, Tuple

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger("AerisSerialBridge")

# Global termination flag for clean signal handling
g_running = True

def handle_exit_signal(sig, frame):
    global g_running
    print("\n[BRIDGE] Termination signal received. Shutting down gracefully...")
    g_running = False

signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)


def parse_and_validate_packet(line_str: str, is_mock: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parses a single newline-delimited JSON line from Arduino Serial.
    Enforces strict data integrity:
    - Never fabricates missing measurements (leaves them as None / null).
    - Preserves sequence numbers and device identity.
    - Tags physical data as PHYSICAL_SENSOR with is_simulated=False.
    - Tags mock data as SIMULATION_PRODUCER with is_simulated=True.
    """
    raw_str = line_str.strip()
    if not raw_str:
        return None, "Empty line"

    # Safely skip non-JSON debug prefixes if present
    if raw_str.startswith("[LOG]") or raw_str.startswith("[DEBUG]") or raw_str.startswith("//"):
        return None, f"Debug message: {raw_str}"

    try:
        data = json.loads(raw_str)
    except json.JSONDecodeError as err:
        return None, f"JSON parse error: {err} (raw: {raw_str[:60]})"

    if not isinstance(data, dict):
        return None, "Packet is not a JSON object"

    now_epoch = time.time()
    packet: Dict[str, Any] = {}

    # 1. Device Identity & Profile
    if is_mock:
        packet["device_id"] = data.get("device_id", "AERIS-UNO-MOCK")
        packet["profile"] = "MOTOR_PROTOTYPE"
        packet["source"] = "SIMULATION_PRODUCER"
        packet["is_simulated"] = True
    else:
        packet["device_id"] = data.get("device_id", "AERIS-UNO-001")
        packet["profile"] = "MOTOR_PROTOTYPE"
        packet["source"] = "PHYSICAL_SENSOR"
        packet["is_simulated"] = False

    # 2. Sequence Number & Timestamps
    packet["sequence_number"] = int(data.get("sequence_number", data.get("seq", 0)))
    packet["timestamp"] = now_epoch
    if "timestamp_ms" in data:
        packet["device_timestamp_ms"] = data["timestamp_ms"]

    # 3. Real Physical Measurements (Only preserve real data; never invent fake defaults)
    # RPM
    if data.get("rpm") is not None:
        try:
            packet["rpm"] = float(data["rpm"])
        except (ValueError, TypeError):
            packet["rpm"] = None
    else:
        packet["rpm"] = None

    # Current (A)
    curr = data.get("current_a", data.get("current"))
    if curr is not None:
        try:
            packet["current_a"] = float(curr)
        except (ValueError, TypeError):
            packet["current_a"] = None
    else:
        packet["current_a"] = None

    # Voltage (V)
    volt = data.get("voltage_v", data.get("voltage"))
    if volt is not None:
        try:
            packet["voltage_v"] = float(volt)
        except (ValueError, TypeError):
            packet["voltage_v"] = None
    else:
        packet["voltage_v"] = None

    # Electrical Power (W)
    if data.get("power_w") is not None:
        try:
            packet["power_w"] = float(data["power_w"])
        except (ValueError, TypeError):
            packet["power_w"] = None
    elif packet["voltage_v"] is not None and packet["current_a"] is not None:
        # P = V x I computed electrically
        packet["power_w"] = round(packet["voltage_v"] * packet["current_a"], 2)
    else:
        packet["power_w"] = None

    # Temperature (°C)
    temp = data.get("temperature_c", data.get("temperature", data.get("temp")))
    if temp is not None:
        try:
            packet["temperature_c"] = float(temp)
        except (ValueError, TypeError):
            packet["temperature_c"] = None
    else:
        packet["temperature_c"] = None

    # Vibration (mm/s or RMS)
    vib = data.get("vibration", data.get("vibration_mms"))
    if vib is not None:
        try:
            packet["vibration"] = float(vib)
        except (ValueError, TypeError):
            packet["vibration"] = None
    else:
        packet["vibration"] = None

    # Motor Load (%)
    load = data.get("motor_load_pct", data.get("motor_load", data.get("load")))
    if load is not None:
        try:
            packet["motor_load_pct"] = float(load)
        except (ValueError, TypeError):
            packet["motor_load_pct"] = None
    else:
        packet["motor_load_pct"] = None

    # Firmware & connectivity metadata
    if "firmware_version" in data:
        packet["firmware_version"] = str(data["firmware_version"])
    else:
        packet["firmware_version"] = "v1.0.0-uno-serial" if not is_mock else "v1.0.0-mock"

    return packet, None


class ArduinoSerialBridge:
    """
    Manages serial communication with the Arduino Uno and HTTP POST transmission
    to the AERIS-TWIN FastAPI backend.
    """

    def __init__(
        self,
        port: str = "COM4",
        baud_rate: int = 115200,
        backend_url: str = "http://127.0.0.1:8000",
        endpoint: str = "/api/telemetry/hardware",
        api_key: Optional[str] = None,
        is_mock: bool = False,
        mock_rate_hz: float = 10.0,
        debug: bool = False,
        verbose: bool = False
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.backend_url = backend_url.rstrip("/")
        self.endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        self.api_key = api_key or os.getenv("AERIS_DEVICE_API_KEY", "").strip()
        self.is_mock = is_mock
        self.mock_rate_hz = max(1.0, min(50.0, mock_rate_hz))
        self.debug = debug
        self.verbose = verbose

        self.full_post_url = f"{self.backend_url}{self.endpoint}"
        self.http_client = httpx.Client(timeout=2.0)

        self.packets_sent = 0
        self.packets_failed = 0
        self.last_seq = 0

    def close(self):
        try:
            self.http_client.close()
        except Exception:
            pass

    def send_packet_to_backend(self, packet: Dict[str, Any], raw_line: Optional[str] = None) -> bool:
        """Transmits normalized telemetry packet to FastAPI /api/telemetry/hardware."""
        seq = packet.get("sequence_number", self.packets_sent + 1)
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": packet.get("device_id", "AERIS-UNO-001"),
        }
        if self.api_key:
            headers["X-Device-API-Key"] = self.api_key
            packet["api_key"] = self.api_key

        if self.debug:
            print(f"\n[{seq}] SERIAL RX")
            print(raw_line or json.dumps(packet))
            print(f"\n[{seq}] HTTP POST")
            print(self.full_post_url)

        try:
            t0 = time.perf_counter()
            resp = self.http_client.post(self.full_post_url, json=packet, headers=headers)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            if self.debug:
                print(f"\n[{seq}] HTTP STATUS")
                print(resp.status_code)

            if resp.status_code in (200, 201):
                self.packets_sent += 1
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass

                dev_status = data.get("status", "CONNECTED")

                if self.debug:
                    print(f"\n[{seq}] BACKEND")
                    print(dev_status)
                else:
                    dev_id = packet.get("device_id", "AERIS-UNO-001")
                    print(f"[ARDUINO] Received packet (seq={seq})")
                    print(f"[BACKEND] POST {self.full_post_url}")
                    print(f"[BACKEND] HTTP {resp.status_code}")
                    print(f"[BACKEND] Device {dev_id} {dev_status}")

                return True
            else:
                self.packets_failed += 1
                if self.debug:
                    print(f"\n[{seq}] BACKEND ERROR")
                    print(f"HTTP {resp.status_code}: {resp.text}")

                if resp.status_code in (401, 403):
                    print(f"[BACKEND] ERROR: HTTP {resp.status_code} (Authentication Failed)")
                elif resp.status_code == 422:
                    print(f"[BACKEND] ERROR: HTTP 422 (Validation Error)")
                    print(f"[BACKEND] Response: {resp.text}")
                else:
                    print(f"[BACKEND] ERROR: HTTP {resp.status_code} - {resp.text}")
                return False

        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            self.packets_failed += 1
            if self.debug:
                print(f"\n[{seq}] HTTP STATUS")
                print("CONNECTION_FAILED")
                print(f"\n[{seq}] BACKEND")
                print(f"ERROR: connection refused ({exc})")
            else:
                print(f"[BACKEND] ERROR: connection refused ({self.full_post_url})")
            return False
        except httpx.RequestError as exc:
            self.packets_failed += 1
            if self.debug:
                print(f"\n[{seq}] BACKEND ERROR")
                print(f"Request error: {exc}")
            else:
                print(f"[BACKEND] ERROR: {exc}")
            return False

    def run_mock_loop(self, max_count: Optional[int] = None):
        """
        Executes software test mode without physical serial hardware.
        Strictly tags packets with source='SIMULATION_PRODUCER' and is_simulated=True.
        """
        print(f"[BRIDGE] Starting MOCK mode at {self.mock_rate_hz} Hz -> {self.full_post_url}")
        print("[BRIDGE] Mock packets are strictly tagged: source='SIMULATION_PRODUCER', is_simulated=True")

        seq = 0
        t_start = time.time()
        interval = 1.0 / self.mock_rate_hz

        while g_running:
            seq += 1
            elapsed = time.time() - t_start

            mock_voltage = round(11.85 - min(1.2, elapsed * 0.005) + math.sin(elapsed * 0.3) * 0.05, 2)
            mock_current = round(1.42 + math.sin(elapsed * 0.5) * 0.15, 3)
            mock_rpm = round(1850.0 + math.sin(elapsed * 0.4) * 30.0, 1)

            mock_json_line = json.dumps({
                "device_id": "AERIS-UNO-MOCK",
                "profile": "MOTOR_PROTOTYPE",
                "source": "SIMULATION_PRODUCER",
                "sequence_number": seq,
                "timestamp_ms": int(elapsed * 1000),
                "rpm": mock_rpm,
                "current_a": mock_current,
                "voltage_v": mock_voltage,
                "temperature_c": None,
                "vibration": None,
                "motor_load_pct": None,
                "firmware_version": "v1.0.0-mock"
            })

            packet, err = parse_and_validate_packet(mock_json_line, is_mock=True)
            if packet:
                self.send_packet_to_backend(packet, raw_line=mock_json_line)

            if max_count and seq >= max_count:
                print(f"[BRIDGE] Reached requested max packet count ({max_count}). Exiting mock mode.")
                break

            time.sleep(interval)

    def run_serial_loop(self, max_count: Optional[int] = None):
        """
        Connects to Arduino Uno COM port and streams physical telemetry.
        Includes automatic retry / reconnect logic if COM port is unplugged.
        """
        try:
            import serial
        except ImportError:
            print("[BRIDGE] ERROR: pyserial module is not installed! Run 'pip install pyserial' to connect to Arduino hardware.")
            return

        print(f"[ARDUINO] Target Serial Port: {self.port} @ {self.baud_rate} Baud")
        print(f"[BACKEND] Target URL: {self.full_post_url}")

        consecutive_errors = 0
        count = 0

        while g_running:
            ser = None
            try:
                print(f"[ARDUINO] Attempting to open serial port '{self.port}' @ {self.baud_rate} baud...")
                ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=1.0,
                    rtscts=False,
                    dsrdtr=False
                )
                print(f"[ARDUINO] Serial connected: {self.port}")
                print(f"[ARDUINO] Listening for Arduino telemetry stream...")
                consecutive_errors = 0

                # Flush initial boot / reset garbage
                time.sleep(1.5)
                ser.reset_input_buffer()

                while g_running:
                    try:
                        raw_bytes = ser.readline()
                    except serial.SerialException as exc:
                        print(f"[ARDUINO] Serial read error (device disconnected?): {exc}")
                        break

                    if not raw_bytes:
                        continue

                    try:
                        line_str = raw_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        continue

                    packet, err = parse_and_validate_packet(line_str, is_mock=False)
                    if packet:
                        self.send_packet_to_backend(packet, raw_line=line_str.strip())
                        count += 1
                        if max_count and count >= max_count:
                            print(f"[BRIDGE] Reached target count {max_count}. Exiting.")
                            return
                    elif self.debug and err:
                        print(f"[BRIDGE] Skipped non-packet line: {err}")

            except (serial.SerialException, FileNotFoundError, PermissionError) as exc:
                consecutive_errors += 1
                if consecutive_errors == 1 or consecutive_errors % 5 == 0:
                    print(f"[ARDUINO] Could not open '{self.port}' ({exc}). Retrying in 2.0s (Ctrl+C to abort)...")
                time.sleep(2.0)
            except Exception as exc:
                print(f"[BRIDGE] Unexpected error: {exc}")
                time.sleep(2.0)
            finally:
                if ser and ser.is_open:
                    try:
                        ser.close()
                    except Exception:
                        pass


def main():
    default_port = os.getenv("AERIS_SERIAL_PORT") or os.getenv("SERIAL_PORT") or "COM4"
    default_baud = int(os.getenv("AERIS_SERIAL_BAUD") or os.getenv("BAUD_RATE") or "115200")
    default_url = os.getenv("AERIS_BACKEND_URL") or os.getenv("BACKEND_URL") or "http://127.0.0.1:8000"
    default_key = os.getenv("AERIS_DEVICE_API_KEY") or ""

    parser = argparse.ArgumentParser(description="AERIS-TWIN Arduino Uno USB Serial Telemetry Bridge")
    parser.add_argument("--port", "-p", default=default_port, help=f"Arduino USB COM port (default: {default_port})")
    parser.add_argument("--baud", "-b", type=int, default=default_baud, help=f"Serial baud rate (default: {default_baud})")
    parser.add_argument("--url", "-u", default=default_url, help=f"FastAPI backend URL (default: {default_url})")
    parser.add_argument("--endpoint", default="/api/telemetry/hardware", help="Backend telemetry endpoint (default: /api/telemetry/hardware)")
    parser.add_argument("--api-key", "-k", default=default_key, help="Device API authentication key")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable structured diagnostic debug mode (RX, POST, STATUS, BACKEND)")
    parser.add_argument("--mock", "-m", action="store_true", help="Run in mock simulation mode without physical hardware")
    parser.add_argument("--rate", "-r", type=float, default=10.0, help="Mock telemetry rate in Hz (default: 10.0)")
    parser.add_argument("--count", "-c", type=int, default=None, help="Maximum number of packets to transmit before exiting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    bridge = ArduinoSerialBridge(
        port=args.port,
        baud_rate=args.baud,
        backend_url=args.url,
        endpoint=args.endpoint,
        api_key=args.api_key,
        is_mock=args.mock,
        mock_rate_hz=args.rate,
        debug=args.debug,
        verbose=args.verbose
    )

    try:
        if args.mock:
            bridge.run_mock_loop(max_count=args.count)
        else:
            bridge.run_serial_loop(max_count=args.count)
    finally:
        bridge.close()
        print(f"[BRIDGE] Closed. Total Sent: {bridge.packets_sent} | Failed: {bridge.packets_failed}")


if __name__ == "__main__":
    main()
