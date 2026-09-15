"""
AERIS-TWIN — Arduino Uno USB Serial to Cloud / Local Telemetry Bridge
Transmits real-time physical telemetry from an Arduino Uno over USB Serial (115200 baud)
to the cloud-hosted Vercel website or local FastAPI backend via HTTP POST (/api/telemetry).

Architecture:
  Arduino Uno (ATmega328P)
        ↓ USB Serial (115200 Baud, Newline-Delimited JSON)
  serial_bridge.py (Laptop / Host)
        ↓ HTTP POST (requests.post)
  Live Vercel Backend / Local FastAPI (https://aeris-uav-digital-twin.vercel.app/api/telemetry)
        ↓
  Cockpit Dashboard UI

Usage:
  # Stream live Arduino Uno telemetry directly to your Vercel cloud app:
  python hardware/arduino_uno/serial_bridge.py

  # Stream with auto-detected COM port (or specify manually):
  python hardware/arduino_uno/serial_bridge.py --port COM6

  # Stream to local backend for testing:
  python hardware/arduino_uno/serial_bridge.py --url http://127.0.0.1:8000/api/telemetry

  # Diagnostic / Debug mode with raw packet tracing:
  python hardware/arduino_uno/serial_bridge.py --debug
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

import requests
import serial
import serial.tools.list_ports

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
    print("\n[BRIDGE] Termination signal received. Closing serial port and shutting down gracefully...")
    g_running = False


signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)


def find_arduino_port() -> Optional[str]:
    """Auto-detects connected Arduino / USB serial COM port on the host system."""
    try:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return None
        # 1. Prioritize devices with Arduino / FTDI / CH340 / USB Serial signatures
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in ["arduino", "ch340", "ftdi", "usb serial", "cp210", "uart", "vid:pid"]):
                return p.device
        # 2. Fall back to the first available COM port
        return ports[0].device
    except Exception:
        return None


def parse_and_validate_packet(line_str: str, is_mock: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parses a single newline-delimited JSON line from Arduino Serial.
    Enforces strict physical data integrity:
    - Arduino 'rpm_throttle' (PWM mapped 0-100) -> 'throttle_pct' and 'motor_load_pct'
    - Real RPM is NOT fabricated (remains None/null when no physical RPM tachometer exists)
    - Unmeasured transducers (ACS712 current, voltage, power) strictly remain None/null
    - Arduino 'vibration_g' -> 'vibration'
    - Arduino 'temp_c' -> 'temperature_c'
    - Arduino 'humidity' -> 'humidity'
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
    raw_seq = data.get("sequence_number", data.get("seq"))
    if raw_seq is not None:
        try:
            packet["sequence_number"] = int(raw_seq)
        except (ValueError, TypeError):
            packet["sequence_number"] = None
    else:
        packet["sequence_number"] = None

    packet["timestamp"] = now_epoch
    if "timestamp_ms" in data:
        packet["timestamp_ms"] = data["timestamp_ms"]
        packet["device_timestamp_ms"] = data["timestamp_ms"]

    # 3. Real Physical Measurements
    # RPM — Only extract if a real RPM pulse sensor is present. Never map rpm_throttle (PWM) to RPM!
    rpm_val = data.get("rpm", data.get("motor_rpm"))
    if rpm_val is not None:
        try:
            packet["rpm"] = float(rpm_val)
        except (ValueError, TypeError):
            packet["rpm"] = None
    else:
        packet["rpm"] = None

    # Current (A) — Null when unmeasured
    curr = data.get("current_a", data.get("current", data.get("amps", data.get("current_amps"))))
    if curr is not None:
        try:
            packet["current_a"] = float(curr)
        except (ValueError, TypeError):
            packet["current_a"] = None
    else:
        packet["current_a"] = None

    # Voltage (V) — Null when unmeasured
    volt = data.get("voltage_v", data.get("voltage", data.get("volts", data.get("v_bat"))))
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
        packet["power_w"] = round(packet["voltage_v"] * packet["current_a"], 2)
    else:
        packet["power_w"] = None

    # Temperature (°C) — DHT22 / NTC sensor channel
    temp = data.get("temperature_c", data.get("temperature", data.get("temp", data.get("temp_c", data.get("cht")))))
    if temp is not None:
        try:
            packet["temperature_c"] = float(temp)
            packet["temp_c"] = float(temp)
        except (ValueError, TypeError):
            packet["temperature_c"] = None
            packet["temp_c"] = None
    else:
        packet["temperature_c"] = None
        packet["temp_c"] = None

    # Vibration (g or mm/s) — MPU6050 / Piezo transducer channel
    vib = data.get("vibration", data.get("vibration_mms", data.get("vibration_g", data.get("vib"))))
    if vib is not None:
        try:
            packet["vibration"] = float(vib)
            packet["vibration_g"] = float(vib)
        except (ValueError, TypeError):
            packet["vibration"] = None
            packet["vibration_g"] = None
    else:
        packet["vibration"] = None
        packet["vibration_g"] = None

    # Throttle / Motor PWM Load (%) — Arduino sends rpm_throttle representing PWM (0-255 -> 0-100%)
    load = data.get("motor_load_pct", data.get("throttle_pct", data.get("rpm_throttle", data.get("motor_load", data.get("load", data.get("engine_load", data.get("throttle")))))))
    if load is not None:
        try:
            load_num = max(0.0, min(100.0, float(load)))
            packet["motor_load_pct"] = load_num
            packet["throttle_pct"] = load_num
            packet["rpm_throttle"] = load_num
        except (ValueError, TypeError):
            packet["motor_load_pct"] = None
            packet["throttle_pct"] = None
            packet["rpm_throttle"] = None
    else:
        packet["motor_load_pct"] = None
        packet["throttle_pct"] = None
        packet["rpm_throttle"] = None

    # Humidity (%) — DHT22 relative humidity
    if "humidity" in data and data["humidity"] is not None:
        try:
            packet["humidity"] = max(0.0, min(100.0, float(data["humidity"])))
        except (ValueError, TypeError):
            pass

    # Firmware version
    if "firmware_version" in data:
        packet["firmware_version"] = str(data["firmware_version"])
    else:
        packet["firmware_version"] = "v1.0.0-uno-serial" if not is_mock else "v1.0.0-mock"

    return packet, None


class ArduinoSerialBridge:
    """
    Manages serial communication with the Arduino Uno and sends HTTP POST requests
    to the cloud-hosted Vercel website or local FastAPI backend using the requests library.
    """

    def __init__(
        self,
        port: str = "COM6",
        baud_rate: int = 115200,
        target_url: str = "https://aeris-uav-digital-twin.vercel.app/api/telemetry",
        api_key: Optional[str] = None,
        is_mock: bool = False,
        mock_rate_hz: float = 10.0,
        post_delay_sec: float = 0.05,
        debug: bool = False,
        verbose: bool = False
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.target_url = target_url
        self.api_key = api_key or os.getenv("AERIS_DEVICE_API_KEY", "").strip()
        self.is_mock = is_mock
        self.mock_rate_hz = max(1.0, min(50.0, mock_rate_hz))
        self.post_delay_sec = max(0.01, min(1.0, post_delay_sec))
        self.debug = debug
        self.verbose = verbose

        # Persistent requests session
        self.session = requests.Session()

        self.packets_sent = 0
        self.packets_failed = 0
        self.last_seq = 0

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    def send_packet_to_backend(self, packet: Dict[str, Any], raw_line: Optional[str] = None) -> bool:
        """Packages telemetry JSON and transmits via requests.post to cloud/local endpoint."""
        if packet.get("sequence_number") is None:
            self.last_seq += 1
            packet["sequence_number"] = self.last_seq
        else:
            self.last_seq = packet["sequence_number"]
        seq = packet["sequence_number"]

        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": packet.get("device_id", "AERIS-UNO-001"),
        }
        if self.api_key:
            headers["X-Device-API-Key"] = self.api_key
            packet["api_key"] = self.api_key

        if self.debug:
            print(f"\n[{seq}] SERIAL RX: {raw_line or json.dumps(packet)}")
            print(f"[{seq}] POST URL:  {self.target_url}")

        try:
            t0 = time.perf_counter()
            resp = self.session.post(
                self.target_url,
                json=packet,
                headers=headers,
                timeout=5.0
            )
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)

            if self.debug:
                print(f"[{seq}] HTTP STATUS: {resp.status_code} ({latency_ms} ms)")

            if resp.status_code in (200, 201):
                self.packets_sent += 1
                dev_id = packet.get("device_id", "AERIS-UNO-001")
                if not self.debug:
                    print(f"[BRIDGE] [seq={seq}] -> POST {self.target_url} [HTTP {resp.status_code}] ({latency_ms} ms)")
                return True
            else:
                self.packets_failed += 1
                print(f"[BRIDGE ERROR] HTTP {resp.status_code} from {self.target_url}: {resp.text[:120]}")
                return False

        except requests.exceptions.Timeout:
            self.packets_failed += 1
            print(f"[BRIDGE TIMEOUT] Request to {self.target_url} timed out (>5.0s)")
            return False
        except requests.exceptions.ConnectionError as exc:
            self.packets_failed += 1
            print(f"[BRIDGE CONNECTION ERROR] Could not reach {self.target_url} ({exc})")
            return False
        except requests.exceptions.RequestException as exc:
            self.packets_failed += 1
            print(f"[BRIDGE REQUEST ERROR] {exc}")
            return False

    def run_serial_loop(self, max_count: Optional[int] = None):
        """
        Connects to Arduino Uno serial port and streams real physical telemetry.
        Includes clean port closure and graceful exit on KeyboardInterrupt.
        """
        print("=" * 65)
        print("  AERIS-TWIN ARDUINO SERIAL TO CLOUD BRIDGE")
        print("=" * 65)
        print(f"  Target Serial Port:  {self.port} @ {self.baud_rate} Baud")
        print(f"  Target Cloud URL:    {self.target_url}")
        print(f"  Transmission Delay:  {int(self.post_delay_sec * 1000)} ms between frames")
        print("=" * 65)
        print("Press Ctrl+C at any time to disconnect cleanly.\n")

        consecutive_errors = 0
        count = 0

        while g_running:
            ser = None
            try:
                print(f"[ARDUINO] Opening serial port '{self.port}' @ {self.baud_rate} baud...")
                ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=1.0,
                    rtscts=False,
                    dsrdtr=False
                )
                print(f"[ARDUINO] Successfully connected to {self.port}.")
                print(f"[ARDUINO] Streaming physical telemetry frames to cloud...")
                consecutive_errors = 0

                # Flush boot reset garbage
                time.sleep(1.5)
                ser.reset_input_buffer()

                while g_running:
                    try:
                        raw_bytes = ser.readline()
                    except serial.SerialException as exc:
                        print(f"[ARDUINO] Serial read error (disconnected?): {exc}")
                        break

                    if not raw_bytes:
                        continue

                    try:
                        line_str = raw_bytes.decode("utf-8", errors="replace").strip()
                    except Exception:
                        continue

                    packet, err = parse_and_validate_packet(line_str, is_mock=False)
                    if packet:
                        self.send_packet_to_backend(packet, raw_line=line_str)
                        count += 1

                        # Small sleep to prevent overwhelming the server
                        time.sleep(self.post_delay_sec)

                        if max_count and count >= max_count:
                            print(f"[BRIDGE] Reached target count ({max_count}). Exiting.")
                            return
                    elif self.debug and err:
                        print(f"[BRIDGE DEBUG] Skipped line: {err}")

            except (serial.SerialException, FileNotFoundError, PermissionError) as exc:
                consecutive_errors += 1
                if consecutive_errors == 1 or consecutive_errors % 5 == 0:
                    print(f"[ARDUINO] Could not access '{self.port}' ({exc}). Retrying in 2.0s...")
                time.sleep(2.0)
            except KeyboardInterrupt:
                print("\n[BRIDGE] KeyboardInterrupt caught. Disconnecting...")
                break
            except Exception as exc:
                print(f"[BRIDGE] Unexpected error: {exc}")
                time.sleep(2.0)
            finally:
                if ser and ser.is_open:
                    try:
                        ser.close()
                        print(f"[ARDUINO] Serial port {self.port} closed cleanly.")
                    except Exception:
                        pass


def main():
    detected_port = find_arduino_port()
    default_port = os.getenv("AERIS_SERIAL_PORT") or os.getenv("SERIAL_PORT") or detected_port or "COM6"
    default_baud = int(os.getenv("AERIS_SERIAL_BAUD") or os.getenv("BAUD_RATE") or "115200")
    default_url = (
        os.getenv("AERIS_BACKEND_URL")
        or os.getenv("VERCEL_URL")
        or "https://aeris-uav-digital-twin.vercel.app/api/telemetry"
    )
    default_key = os.getenv("AERIS_DEVICE_API_KEY") or ""

    parser = argparse.ArgumentParser(description="AERIS-TWIN Arduino Uno USB Serial to Cloud Bridge")
    parser.add_argument("--port", "-p", default=default_port, help=f"Arduino USB COM port (default: {default_port})")
    parser.add_argument("--baud", "-b", type=int, default=default_baud, help=f"Serial baud rate (default: {default_baud})")
    parser.add_argument("--url", "-u", default=default_url, help=f"Target telemetry endpoint URL (default: {default_url})")
    parser.add_argument("--api-key", "-k", default=default_key, help="Device API authentication key")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable structured diagnostic debug mode (RX, POST, STATUS)")
    parser.add_argument("--delay", type=float, default=0.05, help="Small delay in seconds between HTTP POST requests (default: 0.05s)")
    parser.add_argument("--count", "-c", type=int, default=None, help="Maximum number of packets to transmit before exiting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    chosen_port = args.port
    if not chosen_port or chosen_port == "None":
        chosen_port = find_arduino_port() or "COM6"

    bridge = ArduinoSerialBridge(
        port=chosen_port,
        baud_rate=args.baud,
        target_url=args.url,
        api_key=args.api_key,
        post_delay_sec=args.delay,
        debug=args.debug,
        verbose=args.verbose
    )

    try:
        bridge.run_serial_loop(max_count=args.count)
    except KeyboardInterrupt:
        print("\n[BRIDGE] Interrupted by user.")
    finally:
        bridge.close()
        print(f"[BRIDGE] Finished. Total Sent: {bridge.packets_sent} | Failed: {bridge.packets_failed}")


if __name__ == "__main__":
    main()
