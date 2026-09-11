"""
AERIS-TWIN — Development Telemetry Producer & Stream Transmitter
Transmits real, deterministic, or simulated telemetry packets to the AERIS backend
ingestion pipeline via HTTP POST (/api/telemetry/live) or WebSocket.

Usage Examples:
  # Send 1 single deterministic frame with known values:
  python dev_telemetry_sender.py --single --rpm 3850 --cht 78.4 --oil 4.2 --vib 1.6 --fuel 5.2 --load 65

  # Stream continuous live telemetry at 10 Hz:
  python dev_telemetry_sender.py --rate 10 --scenario nominal

  # Stream a progressive bearing wear fault trajectory:
  python dev_telemetry_sender.py --rate 10 --scenario bearing_wear --count 200
"""
import argparse
import json
import math
import os
import sys
import time
import httpx



def generate_frame(seq: int, scenario: str = "nominal", elapsed_s: float = 0.0, custom_params: dict = None) -> dict:
    now = time.time()
    custom_params = custom_params or {}
    profile = custom_params.get("profile", "MOTOR_PROTOTYPE")

    if profile == "MOTOR_PROTOTYPE":
        # Base nominal physical prototype (3x18650 Battery -> ACS712 -> L298N -> DC Geared Motor -> ESP32)
        voltage_v = 11.80 - min(1.8, elapsed_s * 0.005) + math.sin(elapsed_s * 0.2) * 0.05
        current_a = 2.65 + math.sin(elapsed_s * 0.5) * 0.15
        rpm = 1850.0 + math.sin(elapsed_s * 0.4) * 35.0
        temperature_c = 38.5 + min(12.0, elapsed_s * 0.02) + math.sin(elapsed_s * 0.1) * 0.4
        vibration = 0.85 + math.sin(elapsed_s * 0.3) * 0.08
        motor_load_pct = 45.0 + math.sin(elapsed_s * 0.2) * 5.0

        # Prototype Scenarios
        if scenario == "bearing_wear":
            prog = min(1.0, elapsed_s / 15.0)
            vibration += 1.8 * prog + (prog ** 2) * 2.5
            current_a += 1.2 * prog
        elif scenario == "thermal_overheat":
            prog = min(1.0, elapsed_s / 12.0)
            temperature_c += 25.0 * prog
        elif scenario == "lubrication_loss" or scenario == "motor_stall":
            prog = min(1.0, elapsed_s / 10.0)
            current_a += 3.5 * prog
            rpm = max(0.0, rpm - 1400.0 * prog)
            voltage_v -= 1.2 * prog

        # Apply overrides
        if custom_params.get("rpm") is not None:
            rpm = custom_params["rpm"]
        if custom_params.get("current_a") is not None:
            current_a = custom_params["current_a"]
        if custom_params.get("voltage_v") is not None:
            voltage_v = custom_params["voltage_v"]
        if custom_params.get("temperature_c") is not None:
            temperature_c = custom_params["temperature_c"]
        if custom_params.get("vibration") is not None:
            vibration = custom_params["vibration"]
        if custom_params.get("motor_load_pct") is not None:
            motor_load_pct = custom_params["motor_load_pct"]

        power_w = custom_params.get("power_w")
        if power_w is None and voltage_v is not None and current_a is not None:
            power_w = round(voltage_v * current_a, 2)

        return {
            "device_id": custom_params.get("device_id", "AERIS-ESP32-001"),
            "profile": "MOTOR_PROTOTYPE",
            "sequence_number": seq,
            "timestamp": now,
            "rpm": round(rpm, 1) if rpm is not None else None,
            "current_a": round(current_a, 3) if current_a is not None else None,
            "voltage_v": round(voltage_v, 2) if voltage_v is not None else None,
            "power_w": round(power_w, 2) if power_w is not None else None,
            "temperature_c": round(temperature_c, 1) if temperature_c is not None else None,
            "vibration": round(vibration, 3) if vibration is not None else None,
            "motor_load_pct": round(motor_load_pct, 1) if motor_load_pct is not None else None,
            "source": custom_params.get("source", "PHYSICAL_SENSOR"),
            "wifi_rssi": -58,
            "firmware_version": "v1.4.2-motor",
            "is_simulated": False
        }

    # Base nominal frame (Rotax 914 Turbocharged Aero Piston Engine)
    rpm = 4215.0 + math.sin(elapsed_s * 0.4) * 15.0
    temperature = 78.4 + math.cos(elapsed_s * 0.2) * 0.8
    oil_pressure = 4.30 + math.sin(elapsed_s * 0.3) * 0.05
    vibration = 1.55 + math.cos(elapsed_s * 0.5) * 0.08
    fuel_flow = 5.20 + math.sin(elapsed_s * 0.1) * 0.04
    engine_load = 62.0 + math.sin(elapsed_s * 0.2) * 1.5
    egt_c = 645.0 + math.sin(elapsed_s * 0.2) * 3.0
    altitude_ft = 12500.0
    ambient_temp_c = -8.0

    # Scenarios
    if scenario == "bearing_wear":
        prog = min(1.0, elapsed_s / 15.0)
        vibration += 1.2 * prog + (prog ** 2) * 3.5
        temperature += 6.0 * prog
    elif scenario == "thermal_overheat":
        prog = min(1.0, elapsed_s / 12.0)
        temperature += 15.0 * prog + (prog ** 2) * 18.0
        oil_pressure -= 0.6 * prog
    elif scenario == "lubrication_loss":
        prog = min(1.0, elapsed_s / 10.0)
        oil_pressure = max(1.2, oil_pressure - 2.2 * prog)
        temperature += 8.0 * prog
    elif scenario == "spark_misfire":
        fuel_flow += 1.6
        rpm -= 250.0 + (math.sin(elapsed_s * 10.0) * 120.0)

    # Apply any custom overrides
    if custom_params.get("rpm") is not None:
        rpm = custom_params["rpm"]
    if custom_params.get("cht") is not None:
        temperature = custom_params["cht"]
    if custom_params.get("oil") is not None:
        oil_pressure = custom_params["oil"]
    if custom_params.get("vib") is not None:
        vibration = custom_params["vib"]
    if custom_params.get("fuel") is not None:
        fuel_flow = custom_params["fuel"]
    if custom_params.get("load") is not None:
        engine_load = custom_params["load"]

    return {
        "engine_id": "UAV-ENG-ROT-914-01",
        "profile": "AERO_ENGINE",
        "timestamp": now,
        "sequence_number": seq,
        "rpm": round(rpm, 1),
        "temperature": round(temperature, 2),
        "oilPressure": round(oil_pressure, 2),
        "vibration": round(vibration, 3),
        "fuelFlow": round(fuel_flow, 2),
        "engineLoad": round(engine_load, 1),
        "egt_c": round(egt_c, 1),
        "altitude_ft": round(altitude_ft, 1),
        "ambient_temperature_c": round(ambient_temp_c, 1),
        "source": custom_params.get("source", "LIVE_PRODUCER"),
        "device_id": custom_params.get("device_id", "AERIS-PROTOTYPE-01"),
        "is_simulated": False
    }


def run_producer(args):
    endpoint = args.endpoint.lstrip('/')
    url = f"{args.host.rstrip('/')}/{endpoint}"
    print(f"[*] AERIS-TWIN Telemetry Producer starting...")
    print(f"[*] Target Endpoint: {url}")
    print(f"[*] Profile: {args.profile} | Device ID: {args.device_id} | Source: {args.source}")
    print(f"[*] Mode: {'SINGLE-FRAME' if args.single else f'CONTINUOUS @ {args.rate} Hz'}")
    print(f"[*] Scenario: {args.scenario}")
    if args.api_key:
        print(f"[*] Device Authentication: API Key configured ({args.api_key[:4]}***)")

    custom_params = {
        "profile": args.profile,
        "rpm": args.rpm,
        "current_a": args.current,
        "voltage_v": args.voltage,
        "power_w": args.power,
        "temperature_c": args.temp_c,
        "motor_load_pct": args.motor_load,
        "vibration": args.vibration,
        "fuel": args.fuel,
        "load": args.load,
        "source": args.source,
        "device_id": args.device_id
    }

    if getattr(args, "dry_run", False):
        packet = generate_frame(1, args.scenario, 0.0, custom_params)
        if args.api_key:
            packet["api_key"] = args.api_key
        print("[*] DRY RUN MODE: Generated sample telemetry payload:")
        import json
        print(json.dumps(packet, indent=2))
        return

    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-Device-API-Key"] = args.api_key

    client = httpx.Client(timeout=4.0, headers=headers)
    seq = 1
    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            packet = generate_frame(seq, args.scenario, elapsed, custom_params)
            if args.api_key:
                packet["api_key"] = args.api_key
            
            t0 = time.perf_counter()
            resp = client.post(url, json=packet)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code == 200:
                res_data = resp.json()
                print(f"[+] Frame #{seq:04d} transmitted | Latency: {latency_ms:.1f}ms | Profile: {res_data.get('profile', args.profile)} | Source: {res_data.get('source', args.source)} | Health: {res_data.get('health_index', '--')}% | Fault: {res_data.get('fault_class', 'NOMINAL')}")
            else:
                print(f"[-] Frame #{seq:04d} failed: HTTP {resp.status_code} - {resp.text}")

            if args.single or (args.count and seq >= args.count):
                print(f"[*] Transmission completed. Total frames sent: {seq}")
                break

            seq += 1
            sleep_sec = max(0.01, (1.0 / max(0.5, args.rate)) - (latency_ms / 1000.0))
            time.sleep(sleep_sec)

    except KeyboardInterrupt:
        print(f"\n[*] Producer stopped by user. Total frames sent: {seq}")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AERIS-TWIN Development & Hardware Telemetry Producer")
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--endpoint", default="api/telemetry/hardware", choices=["api/telemetry/hardware", "api/telemetry/live", "api/telemetry"], help="Target REST endpoint")
    parser.add_argument("--profile", default="MOTOR_PROTOTYPE", choices=["MOTOR_PROTOTYPE", "AERO_ENGINE"], help="Telemetry Profile")
    parser.add_argument("--rate", type=float, default=10.0, help="Transmission rate in Hz (default: 10.0)")
    parser.add_argument("--scenario", default="nominal", choices=["nominal", "bearing_wear", "thermal_overheat", "lubrication_loss", "spark_misfire", "motor_stall"], help="Fault trajectory scenario")
    parser.add_argument("--single", action="store_true", help="Send exactly one frame and exit")
    parser.add_argument("--count", type=int, default=None, help="Stop after sending N frames")
    parser.add_argument("--dry-run", action="store_true", help="Print sample packet and exit without sending HTTP request")
    parser.add_argument("--device-id", default="AERIS-ESP32-001", help="Hardware Device Identifier")
    parser.add_argument("--source", default="PHYSICAL_SENSOR", help="Telemetry source tag (e.g. PHYSICAL_SENSOR, ESP32, LIVE_PRODUCER)")
    parser.add_argument("--api-key", default=os.getenv("AERIS_DEVICE_API_KEY", None), help="Device API authentication key")
    
    # Motor Prototype Parameters
    parser.add_argument("--rpm", type=float, default=None, help="Override RPM value")
    parser.add_argument("--current", "--current-a", type=float, default=None, dest="current", help="Override Motor Current (A)")
    parser.add_argument("--voltage", "--voltage-v", type=float, default=None, dest="voltage", help="Override Bus Voltage (V)")
    parser.add_argument("--power", "--power-w", type=float, default=None, dest="power", help="Override Motor Power (W)")
    parser.add_argument("--temp-c", type=float, default=None, dest="temp_c", help="Override Motor Temperature (°C)")
    parser.add_argument("--motor-load", type=float, default=None, dest="motor_load", help="Override Motor Load (%)")

    # Aero Engine Parameters
    parser.add_argument("--cht", type=float, default=None, help="Override CHT (°C) value (AERO_ENGINE)")
    parser.add_argument("--oil", type=float, default=None, help="Override Oil Pressure (Bar) value (AERO_ENGINE)")
    parser.add_argument("--vib", "--vibration", type=float, default=None, dest="vibration", help="Override Vibration (mm/s) value")
    parser.add_argument("--fuel", type=float, default=None, help="Override Fuel Flow (L/h) value (AERO_ENGINE)")
    parser.add_argument("--load", type=float, default=None, help="Override Engine Load (%) value")

    args = parser.parse_args()
    run_producer(args)
