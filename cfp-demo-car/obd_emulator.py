"""
obd_emulator.py
CFP Demo Car — CAN Bus OBD2 Emulator

The Pi IS the car. MCP2515 wired to OBD2 female port via CAN H/L.
OBDLink MX+ plugs into that port and reads the Pi like a real ECU.
Pi never touches Bluetooth — MX+ handles that to the phone.

CAN Bus protocol:
  MX+ sends requests on arbitration ID 0x7DF (OBD2 functional address)
  Pi responds on arbitration ID 0x7E8 (ECU 1 response address)

Simulation mode: Interactive console — type OBD PIDs, see hex responses.
Production mode: Real python-can on socketcan can1 interface.
"""

import os
import sys
import time
import threading
from config import get_scenario, get_scenario_count
from state import (
    get_scenario_index, set_connected,
    set_sms_sent, read_state, write_state
)
from twilio_trigger import fire_sms

SIMULATE = os.environ.get("CFP_SIMULATE", "0") == "1"

# —— CAN IDs ——————————————————————————————————————————————————————————————————
CAN_REQUEST_ID  = 0x7DF   # OBD2 functional broadcast — MX+ sends here
CAN_RESPONSE_ID = 0x7E8   # ECU 1 response — Pi sends here

# —— OBD2 Mode/PID Response Builder ——————————————————————————————————————————

def build_response(mode: int, pid: int, scenario: dict) -> list[int]:
    """
    Build the OBD2 CAN response bytes for a given mode/PID request.
    Returns list of up to 8 bytes (CAN frame data).
    Format: [length, mode+0x40, pid, data...]
    """

    if mode == 0x01:
        return _mode01(pid, scenario)

    elif mode == 0x09:
        return _mode09(pid, scenario)

    elif mode == 0x03:
        return _mode03(scenario)

    elif mode == 0x04:
        return [0x01, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # Default: no data
    return [0x03, 0x7F, mode, 0x12, 0x00, 0x00, 0x00, 0x00]

def _mode01(pid: int, scenario: dict) -> list[int]:
    """Mode 01 — Live sensor data PIDs."""

    if pid == 0x00:
        # Supported PIDs 01-20
        return [0x06, 0x41, 0x00, 0xBE, 0x3F, 0xA8, 0x13, 0x00]

    elif pid == 0x0C:
        # Engine RPM — formula: RPM = (A*256 + B) / 4
        rpm_raw = int(scenario.get("rpm_value", 790) * 4)
        a = (rpm_raw >> 8) & 0xFF
        b = rpm_raw & 0xFF
        return [0x04, 0x41, 0x0C, a, b, 0x00, 0x00, 0x00]

    elif pid == 0x05:
        # Coolant temp — formula: Temp(C) = A - 40
        temp_c = scenario.get("coolant_c", 83)
        a = temp_c + 40
        return [0x03, 0x41, 0x05, a & 0xFF, 0x00, 0x00, 0x00, 0x00]

    elif pid == 0x11:
        # Throttle position — formula: Throttle% = A * 100 / 255
        throttle = scenario.get("throttle_pct", 0)
        a = int(throttle * 255 / 100)
        return [0x03, 0x41, 0x11, a & 0xFF, 0x00, 0x00, 0x00, 0x00]

    elif pid == 0x0D:
        # Vehicle speed km/h
        speed = scenario.get("speed_kph", 0)
        return [0x03, 0x41, 0x0D, speed & 0xFF, 0x00, 0x00, 0x00, 0x00]

    elif pid == 0x04:
        # Engine load %
        load = scenario.get("engine_load_pct", 25)
        a = int(load * 255 / 100)
        return [0x03, 0x41, 0x04, a & 0xFF, 0x00, 0x00, 0x00, 0x00]

    elif pid == 0x0F:
        # Intake air temperature
        iat_c = scenario.get("iat_c", 25)
        return [0x03, 0x41, 0x0F, (iat_c + 40) & 0xFF, 0x00, 0x00, 0x00, 0x00]

    elif pid == 0x14:
        # O2 sensor Bank 1 Sensor 1
        o2_raw = scenario.get("o2_raw", 0x44)
        return [0x04, 0x41, 0x14, o2_raw, 0xFF, 0x00, 0x00, 0x00]

    elif pid == 0x01:
        # Monitor status / MIL
        has_fault = scenario.get("has_fault", False)
        mil_byte = 0x81 if has_fault else 0x01  # 0x80 bit = MIL on
        dtc_count = len(scenario.get("dtcs", []))
        return [0x06, 0x41, 0x01, mil_byte, dtc_count, 0x07, 0xFF, 0x00]

    # Unsupported PID
    return [0x03, 0x7F, 0x01, 0x12, 0x00, 0x00, 0x00, 0x00]

def _mode09(pid: int, scenario: dict) -> list[int]:
    """Mode 09 — Vehicle information."""

    if pid == 0x02:
        # VIN — multi-frame response (simplified single-frame for emulator)
        vin = scenario.get("vin", "00000000000000000")
        vin_bytes = [ord(c) for c in vin[:17]]
        frame = [0x10, 0x14, 0x49, 0x02, 0x01] + vin_bytes[:3]
        return frame[:8]

    elif pid == 0x00:
        # Supported mode 09 PIDs
        return [0x04, 0x49, 0x00, 0x54, 0x40, 0x00, 0x00, 0x00]

    return [0x03, 0x7F, 0x09, 0x12, 0x00, 0x00, 0x00, 0x00]

def _mode03(scenario: dict) -> list[int]:
    """Mode 03 — Stored DTCs."""
    dtcs = scenario.get("dtcs", [])

    if not dtcs:
        return [0x02, 0x43, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # Encode first two DTCs into response frame
    frame = [0x02 + len(dtcs) * 2, 0x43]
    for dtc in dtcs[:3]:
        encoded = _encode_dtc(dtc)
        frame.extend(encoded)
    # Pad to 8 bytes
    while len(frame) < 8:
        frame.append(0x00)
    return frame[:8]

def _encode_dtc(dtc: str) -> list[int]:
    """
    Encode DTC string (e.g. 'P0420') into two OBD2 bytes.
    High nibble of byte 1: P=0, C=4, B=8, U=C
    """
    prefix_map = {"P": 0x00, "C": 0x40, "B": 0x80, "U": 0xC0}
    prefix_byte = prefix_map.get(dtc[0].upper(), 0x00)
    byte1 = prefix_byte | (int(dtc[1]) << 4) | int(dtc[2], 16)
    byte2 = int(dtc[3:5], 16)
    return [byte1 & 0xFF, byte2 & 0xFF]

# —— Connection Detection ————————————————————————————————————————————————————

def on_scanner_connect(scenario: dict):
    """Called when first valid OBD request received — scanner is live."""
    print(f"[OBD] Scanner connected — {scenario['vehicle']}")
    set_connected(True)
    set_sms_sent(False)
    fire_sms(scenario)
    set_sms_sent(True)

def on_scanner_disconnect():
    """Called when no messages received for timeout period."""
    print("[OBD] Scanner disconnected (timeout)")
    set_connected(False)
    set_sms_sent(False)

# —— Production: CAN Bus Loop ————————————————————————————————————————————————

def run_can_loop():
    """
    Production mode: Listen on CAN bus, respond to OBD2 requests.
    Requires: MCP2515 wired to SPI1, can1 interface up.
    """
    try:
        import can
    except ImportError:
        print("[OBD] ERROR: python-can not installed. Run: pip install python-can")
        sys.exit(1)

    print("[OBD] Starting CAN bus listener on can1...")

    try:
        bus = can.interface.Bus(channel="can1", bustype="socketcan")
    except Exception as e:
        print(f"[OBD] ERROR: Could not open can1 — {e}")
        print("[OBD] Check: sudo ip link set can1 up type can bitrate 500000")
        sys.exit(1)

    print("[OBD] CAN bus ready. Waiting for OBD2 requests...")

    connected        = False
    last_msg_time    = None
    disconnect_timeout = 5.0   # seconds without message = disconnected

    try:
        while True:
            # Check for disconnect timeout
            if connected and last_msg_time:
                if time.time() - last_msg_time > disconnect_timeout:
                    on_scanner_disconnect()
                    connected = False

            # Read scenario fresh each loop (user may have changed it)
            scenario = get_scenario(get_scenario_index())

            # Non-blocking receive with 0.1s timeout
            msg = bus.recv(timeout=0.1)
            if msg is None:
                continue

            last_msg_time = time.time()

            # Only process OBD2 functional request ID
            if msg.arbitration_id != CAN_REQUEST_ID:
                continue

            # First message = scanner just connected
            if not connected:
                connected = True
                on_scanner_connect(scenario)

            # Parse OBD2 request
            data   = msg.data
            length = data[0]
            mode   = data[1]
            pid    = data[2] if length > 1 else 0x00

            print(f"[OBD] Request: mode={hex(mode)} pid={hex(pid)}")

            # Build and send response
            response_data = build_response(mode, pid, scenario)
            response = can.Message(
                arbitration_id=CAN_RESPONSE_ID,
                data=bytes(response_data),
                is_extended_id=False
            )
            bus.send(response)
            print(f"[OBD] Response: {[hex(b) for b in response_data]}")

    except KeyboardInterrupt:
        print("[OBD] Stopped.")
    finally:
        bus.shutdown()

# —— Simulation: Interactive Console —————————————————————————————————————————

def run_simulation_console():
    """
    Simulation mode — interactive OBD2 console for development.
    Mimics what the MX+ would send/receive over CAN.

    Commands:
        connect             Simulate MX+ connecting
        disconnect          Simulate MX+ disconnecting
        01 0C               Mode 01, PID 0C (RPM)
        03                  Mode 03 (read DTCs)
        09 02               Mode 09 PID 02 (VIN)
        scenario <0-4>      Switch active scenario
        exit                Quit
    """
    print("\n[OBD SIM] CAN Bus Simulator")
    print("[OBD SIM] Commands: connect, disconnect, 01 0C, 03, 09 02, scenario <N>, exit\n")

    while True:
        try:
            raw = input("[OBD SIM] > ").strip().lower()
            if not raw:
                continue

            if raw == "exit":
                break

            if raw == "connect":
                scenario = get_scenario(get_scenario_index())
                on_scanner_connect(scenario)
                continue

            if raw == "disconnect":
                on_scanner_disconnect()
                continue

            if raw.startswith("scenario"):
                parts = raw.split()
                if len(parts) == 2 and parts[1].isdigit():
                    idx = int(parts[1]) % get_scenario_count()
                    from state import set_scenario_index
                    set_scenario_index(idx)
                    print(f"[OBD SIM] Scenario -> {get_scenario(idx)['vehicle']}")
                continue

            # Parse as OBD2 hex command
            parts = raw.split()
            if len(parts) >= 1:
                try:
                    mode = int(parts[0], 16)
                    pid  = int(parts[1], 16) if len(parts) > 1 else 0x00
                    scenario = get_scenario(get_scenario_index())
                    response = build_response(mode, pid, scenario)
                    print(f"[OBD SIM] Response: {[hex(b) for b in response]}")
                except ValueError:
                    print("[OBD SIM] Unknown command. Try: 01 0C  or  03  or  connect")

        except KeyboardInterrupt:
            break

    print("[OBD SIM] Exiting.")

# —— Entry Point —————————————————————————————————————————————————————————————

def run_emulator(simulate: bool = False):
    if simulate:
        run_simulation_console()
    else:
        run_can_loop()

if __name__ == "__main__":
    os.environ["CFP_SIMULATE"] = "1"
    run_simulation_console()
