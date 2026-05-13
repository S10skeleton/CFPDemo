"""
obd_emulator.py
CFP Demo Car — CAN Bus OBD2 Emulator

The Pi IS the car. MCP2515 wired to OBD2 female port via CAN H/L.
OBDLink MX+ plugs into that port and reads the Pi like a real ECU.
Pi never touches Bluetooth — MX+ handles that to the phone.

CAN Bus protocol:
  MX+ sends requests on arbitration ID 0x7DF (OBD2 functional address)
  Pi responds on arbitration ID 0x7E8 (ECU 1 response address)
  MX+ sends flow control on 0x7E0 after multi-frame first frame

Simulation mode: Interactive console — type OBD PIDs, see hex responses.
Production mode: Real python-can on socketcan can0 interface.
"""

import os
import sys
import time
from config import get_scenario, get_scenario_count
from state import get_scenario_index, set_connected

SIMULATE = os.environ.get("CFP_SIMULATE", "0") == "1"

# —— CAN IDs ——————————————————————————————————————————————————————————————————
CAN_REQUEST_ID   = 0x7DF   # OBD2 functional broadcast — MX+ sends here
CAN_RESPONSE_ID  = 0x7E8   # ECU 1 response — Pi sends here
CAN_FLOW_CTRL_ID = 0x7E0   # Flow control — MX+ sends after first frame

# —— ISO-TP Multi-frame State ————————————————————————————————————————————————
_isotp_pending = {}   # stores remaining bytes for consecutive frame sending

# —— ISO-TP Helpers ——————————————————————————————————————————————————————————

def _isotp_send_first_frame(bus, data: list) -> bool:
    """
    Send ISO-TP first frame for multi-byte responses.
    Returns True if multi-frame was needed (caller waits for flow control).
    Returns False if single frame was sufficient (already sent).
    """
    import can

    if len(data) <= 7:
        # Single frame — fits in one CAN message
        frame = [len(data)] + data
        while len(frame) < 8:
            frame.append(0x00)
        bus.send(can.Message(
            arbitration_id=CAN_RESPONSE_ID,
            data=bytes(frame[:8]),
            is_extended_id=False
        ))
        _isotp_pending.clear()
        return False
    else:
        # Multi-frame — send first frame, save rest
        total_len = len(data)
        ff = [0x10, total_len & 0xFF] + data[:6]
        bus.send(can.Message(
            arbitration_id=CAN_RESPONSE_ID,
            data=bytes(ff[:8]),
            is_extended_id=False
        ))
        _isotp_pending['remaining'] = data[6:]
        _isotp_pending['seq']       = 1
        print(f"[OBD] Multi-frame first frame sent, {len(data[6:])} bytes remaining")
        return True


def _isotp_send_consecutive_frames(bus):
    """
    Send ISO-TP consecutive frames after receiving flow control (0x30).
    Called when 0x7E0 flow control frame received from MX+.
    """
    import can

    remaining = _isotp_pending.get('remaining', [])
    seq       = _isotp_pending.get('seq', 1)

    if not remaining:
        return

    print(f"[OBD] Sending {len(remaining)} remaining bytes in consecutive frames")

    while remaining:
        chunk = remaining[:7]
        remaining = remaining[7:]

        cf = [0x20 | (seq & 0x0F)] + chunk
        while len(cf) < 8:
            cf.append(0x00)

        bus.send(can.Message(
            arbitration_id=CAN_RESPONSE_ID,
            data=bytes(cf[:8]),
            is_extended_id=False
        ))
        print(f"[OBD] CF{seq}: {[hex(b) for b in cf]}")
        seq += 1
        time.sleep(0.0005)   # 0.5ms between frames — stable for MX+

    _isotp_pending.clear()
    print("[OBD] Multi-frame complete")


# —— OBD2 Mode/PID Response Builder ——————————————————————————————————————————

def build_response_data(mode: int, pid: int, scenario: dict) -> list:
    """
    Build the raw OBD2 response data bytes for a given mode/PID.
    Returns a list of bytes to be sent via ISO-TP.
    """
    if mode == 0x01:
        return _mode01(pid, scenario)

    elif mode == 0x02:
        return _mode02(pid, scenario)

    elif mode == 0x09:
        return _mode09_data(pid, scenario)

    elif mode == 0x03:
        return _mode03(scenario)

    elif mode == 0x04:
        # Clear DTCs — acknowledge
        return [0x01, 0x44]

    # Default: negative response (service not supported)
    return [0x03, 0x7F, mode, 0x12]


def _mode01(pid: int, scenario: dict) -> list:
    """Mode 01 — Current live data PIDs."""

    if pid == 0x00:
        # Supported PIDs 01-20
        return [0x06, 0x41, 0x00, 0xBE, 0x3F, 0xA8, 0x13, 0x00]

    elif pid == 0x01:
        # Monitor status / MIL
        has_fault = scenario.get("has_fault", False)
        mil_byte  = 0x81 if has_fault else 0x01
        dtc_count = len(scenario.get("dtcs", []))
        return [0x06, 0x41, 0x01, mil_byte, dtc_count, 0x07, 0xFF, 0x00]

    elif pid == 0x04:
        # Engine load %
        load = scenario.get("engine_load_pct", 25)
        a    = int(load * 255 / 100)
        return [0x03, 0x41, 0x04, a & 0xFF]

    elif pid == 0x05:
        # Coolant temp — Temp(C) = A - 40
        temp_c = scenario.get("coolant_c", 83)
        return [0x03, 0x41, 0x05, (temp_c + 40) & 0xFF]

    elif pid == 0x0C:
        # Engine RPM — RPM = (A*256 + B) / 4
        rpm_raw = int(scenario.get("rpm_value", 790) * 4)
        a = (rpm_raw >> 8) & 0xFF
        b = rpm_raw & 0xFF
        return [0x04, 0x41, 0x0C, a, b]

    elif pid == 0x0D:
        # Vehicle speed km/h
        speed = scenario.get("speed_kph", 0)
        return [0x03, 0x41, 0x0D, speed & 0xFF]

    elif pid == 0x0F:
        # Intake air temperature
        iat_c = scenario.get("iat_c", 25)
        return [0x03, 0x41, 0x0F, (iat_c + 40) & 0xFF]

    elif pid == 0x11:
        # Throttle position %
        throttle = scenario.get("throttle_pct", 0)
        a        = int(throttle * 255 / 100)
        return [0x03, 0x41, 0x11, a & 0xFF]

    elif pid == 0x14:
        # O2 sensor Bank 1 Sensor 1
        o2_raw = scenario.get("o2_raw", 0x44)
        return [0x04, 0x41, 0x14, o2_raw, 0xFF]

    elif pid == 0x1F:
        # Runtime since engine start (seconds)
        return [0x04, 0x41, 0x1F, 0x00, 0x3C]   # 60 seconds

    elif pid == 0x21:
        # Distance with MIL on
        has_fault = scenario.get("has_fault", False)
        return [0x04, 0x41, 0x21, 0x00, 0x0A if has_fault else 0x00]

    # Unsupported PID — negative response
    return [0x03, 0x7F, 0x01, 0x12]


def _mode02(pid: int, scenario: dict) -> list:
    """
    Mode 02 — Freeze frame data.
    Returns same sensor values as Mode 01 but with Mode 02 response byte
    and frame number byte. MX+ sends frame_number in data[3] — we always
    use frame 0.
    """
    if pid == 0x04:
        load = scenario.get("engine_load_pct", 25)
        a    = int(load * 255 / 100)
        return [0x04, 0x42, 0x04, 0x00, a & 0xFF]

    elif pid == 0x05:
        temp_c = scenario.get("coolant_c", 83)
        return [0x04, 0x42, 0x05, 0x00, (temp_c + 40) & 0xFF]

    elif pid == 0x06:
        # Short term fuel trim Bank 1 — 0% trim = 0x80
        return [0x04, 0x42, 0x06, 0x00, 0x80]

    elif pid == 0x07:
        # Long term fuel trim Bank 1
        has_fault = scenario.get("has_fault", False)
        trim = 0x70 if has_fault else 0x80
        return [0x04, 0x42, 0x07, 0x00, trim]

    elif pid == 0x0B:
        # MAP sensor kPa
        return [0x04, 0x42, 0x0B, 0x00, 0x60]

    elif pid == 0x0C:
        rpm_raw = int(scenario.get("rpm_value", 790) * 4)
        a = (rpm_raw >> 8) & 0xFF
        b = rpm_raw & 0xFF
        return [0x05, 0x42, 0x0C, 0x00, a, b]

    elif pid == 0x0D:
        speed = scenario.get("speed_kph", 0)
        return [0x04, 0x42, 0x0D, 0x00, speed & 0xFF]

    elif pid == 0x0F:
        iat_c = scenario.get("iat_c", 25)
        return [0x04, 0x42, 0x0F, 0x00, (iat_c + 40) & 0xFF]

    elif pid == 0x10:
        # MAF air flow rate g/s — ~8 g/s
        return [0x05, 0x42, 0x10, 0x00, 0x00, 0x50]

    elif pid == 0x11:
        throttle = scenario.get("throttle_pct", 0)
        a        = int(throttle * 255 / 100)
        return [0x04, 0x42, 0x11, 0x00, a & 0xFF]

    # Unsupported freeze frame PID
    return [0x03, 0x7F, 0x02, 0x12]


def _mode09_data(pid: int, scenario: dict) -> list:
    """
    Mode 09 — Vehicle information.
    Returns raw data bytes for ISO-TP sending.
    """
    if pid == 0x00:
        # Supported Mode 09 PIDs
        return [0x04, 0x49, 0x00, 0x54, 0x40, 0x00, 0x00, 0x00]

    elif pid == 0x02:
        # VIN — 20 bytes total: 49 02 01 + 17 VIN chars
        vin       = scenario.get("vin", "00000000000000000")
        vin_bytes = [ord(c) for c in vin[:17]]
        return [0x49, 0x02, 0x01] + vin_bytes

    elif pid == 0x04:
        # Calibration ID (8 chars)
        cal = "CFP10001"
        return [0x49, 0x04, 0x01] + [ord(c) for c in cal]

    return [0x03, 0x7F, 0x09, 0x12]


def _mode03(scenario: dict) -> list:
    """Mode 03 — Stored DTCs."""
    dtcs = scenario.get("dtcs", [])

    if not dtcs:
        return [0x02, 0x43, 0x00]

    frame = [0x02 + len(dtcs) * 2, 0x43]
    for dtc in dtcs[:3]:
        frame.extend(_encode_dtc(dtc))
    return frame


def _encode_dtc(dtc: str) -> list:
    """Encode DTC string (e.g. 'P0420') into two OBD2 bytes."""
    prefix_map = {"P": 0x00, "C": 0x40, "B": 0x80, "U": 0xC0}
    prefix     = prefix_map.get(dtc[0].upper(), 0x00)
    byte1      = prefix | (int(dtc[1]) << 4) | int(dtc[2], 16)
    byte2      = int(dtc[3:5], 16)
    return [byte1 & 0xFF, byte2 & 0xFF]


# —— Connection Detection ————————————————————————————————————————————————————

def on_scanner_connect(scenario: dict):
    print(f"[OBD] Scanner connected — {scenario['vehicle']}")
    set_connected(True)

def on_scanner_disconnect():
    print("[OBD] Scanner disconnected (timeout)")
    set_connected(False)


# —— Production: CAN Bus Loop ————————————————————————————————————————————————

def run_can_loop():
    """
    Production mode: Listen on CAN bus, respond to OBD2 requests.
    Handles both single-frame and ISO-TP multi-frame responses.
    """
    try:
        import can
    except ImportError:
        print("[OBD] ERROR: python-can not installed.")
        sys.exit(1)

    print("[OBD] Starting CAN bus listener on can0...")

    try:
        bus = can.interface.Bus(channel="can0", interface="socketcan")
    except Exception as e:
        print(f"[OBD] ERROR: Could not open can0 — {e}")
        print("[OBD] Check: sudo ip link set can0 up type can bitrate 500000")
        sys.exit(1)

    print("[OBD] CAN bus ready. Waiting for OBD2 requests...")

    connected          = False
    last_msg_time      = None
    disconnect_timeout = 5.0

    try:
        while True:
            if connected and last_msg_time:
                if time.time() - last_msg_time > disconnect_timeout:
                    on_scanner_disconnect()
                    connected = False

            scenario = get_scenario(get_scenario_index())
            msg      = bus.recv(timeout=0.1)

            if msg is None:
                continue

            last_msg_time = time.time()

            # Flow control from MX+ → send consecutive frames
            if msg.arbitration_id == CAN_FLOW_CTRL_ID:
                if msg.data[0] == 0x30 and _isotp_pending:
                    print("[OBD] Flow control received → sending consecutive frames")
                    _isotp_send_consecutive_frames(bus)
                continue

            # Only process OBD2 functional requests
            if msg.arbitration_id != CAN_REQUEST_ID:
                continue

            if not connected:
                connected = True
                on_scanner_connect(scenario)

            data   = msg.data
            length = data[0]
            mode   = data[1]
            pid    = data[2] if length > 1 else 0x00

            print(f"[OBD] Request: mode={hex(mode)} pid={hex(pid)}")

            response_data = build_response_data(mode, pid, scenario)
            _isotp_send_first_frame(bus, response_data)
            print(f"[OBD] Response sent: {[hex(b) for b in response_data[:8]]}")

    except KeyboardInterrupt:
        print("[OBD] Stopped.")
    finally:
        bus.shutdown()


# —— Simulation: Interactive Console —————————————————————————————————————————

def run_simulation_console():
    """
    Simulation mode — interactive OBD2 console for development.
    Commands: connect, disconnect, 01 0C, 02 05, 03, 09 02,
              scenario <0-4>, exit
    """
    print("\n[OBD SIM] CAN Bus Simulator")
    print("[OBD SIM] Commands: connect, disconnect, 01 0C, 02 05, 03, 09 02, scenario <N>, exit\n")

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

            parts = raw.split()
            if parts:
                try:
                    mode = int(parts[0], 16)
                    pid  = int(parts[1], 16) if len(parts) > 1 else 0x00
                    scenario = get_scenario(get_scenario_index())
                    response = build_response_data(mode, pid, scenario)
                    print(f"[OBD SIM] Response: {[hex(b) for b in response]}")
                    if mode == 0x09 and pid == 0x02:
                        vin_bytes = response[3:]
                        vin = ''.join(chr(b) for b in vin_bytes if b)
                        print(f"[OBD SIM] VIN decoded: {vin}")
                except ValueError:
                    print("[OBD SIM] Unknown command.")

        except (KeyboardInterrupt, EOFError):
            break

    print("[OBD SIM] Exiting.")


# —— Entry Point —————————————————————————————————————————————————————————————

def run_emulator(simulate: bool = False):
    if simulate:
        run_simulation_console()
    else:
        run_can_loop()

if __name__ == "__main__":
    run_emulator(simulate=SIMULATE)
