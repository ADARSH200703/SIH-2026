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
import sys
import time
import httpx


def generate_frame(seq: int, scenario: str = "nominal", elapsed_s: float = 0.0, custom_params: dict = None) -> dict:
    now = time.time()
    
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
    if custom_params:
        if "rpm" in custom_params and custom_params["rpm"] is not None:
            rpm = custom_params["rpm"]
        if "cht" in custom_params and custom_params["cht"] is not None:
            temperature = custom_params["cht"]
        if "oil" in custom_params and custom_params["oil"] is not None:
            oil_pressure = custom_params["oil"]
        if "vib" in custom_params and custom_params["vib"] is not None:
            vibration = custom_params["vib"]
        if "fuel" in custom_params and custom_params["fuel"] is not None:
            fuel_flow = custom_params["fuel"]
        if "load" in custom_params and custom_params["load"] is not None:
            engine_load = custom_params["load"]

    return {
        "engine_id": "UAV-ENG-ROT-914-01",
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
        "source": "LIVE_PRODUCER",
        "is_simulated": False
    }


def run_producer(args):
    url = f"{args.host.rstrip('/')}/api/telemetry/live"
    print(f"[*] AERIS-TWIN Telemetry Producer starting...")
    print(f"[*] Target Endpoint: {url}")
    print(f"[*] Mode: {'SINGLE-FRAME' if args.single else f'CONTINUOUS @ {args.rate} Hz'}")
    print(f"[*] Scenario: {args.scenario}")

    custom_params = {
        "rpm": args.rpm,
        "cht": args.cht,
        "oil": args.oil,
        "vib": args.vib,
        "fuel": args.fuel,
        "load": args.load
    }

    client = httpx.Client(timeout=4.0)
    seq = 1
    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            packet = generate_frame(seq, args.scenario, elapsed, custom_params)
            
            t0 = time.perf_counter()
            resp = client.post(url, json=packet)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code == 200:
                res_data = resp.json()
                print(f"[+] Frame #{seq:04d} transmitted | Latency: {latency_ms:.1f}ms | Health: {res_data.get('health_index', '--')}% | Fault: {res_data.get('fault_class', 'NOMINAL')}")
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
    parser = argparse.ArgumentParser(description="AERIS-TWIN Development Telemetry Producer")
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--rate", type=float, default=10.0, help="Transmission rate in Hz (default: 10.0)")
    parser.add_argument("--scenario", default="nominal", choices=["nominal", "bearing_wear", "thermal_overheat", "lubrication_loss", "spark_misfire"], help="Fault trajectory scenario")
    parser.add_argument("--single", action="store_true", help="Send exactly one frame and exit")
    parser.add_argument("--count", type=int, default=None, help="Stop after sending N frames")
    parser.add_argument("--rpm", type=float, default=None, help="Override RPM value")
    parser.add_argument("--cht", type=float, default=None, help="Override CHT (°C) value")
    parser.add_argument("--oil", type=float, default=None, help="Override Oil Pressure (Bar) value")
    parser.add_argument("--vib", type=float, default=None, help="Override Vibration (mm/s) value")
    parser.add_argument("--fuel", type=float, default=None, help="Override Fuel Flow (L/h) value")
    parser.add_argument("--load", type=float, default=None, help="Override Engine Load (%) value")

    args = parser.parse_args()
    run_producer(args)
