"""
bench_tester.py
CFP Bench Tester - Windows Desktop OBD2 Emulator

Emulates a vehicle ECU over USB CAN (DSD TECH SH-C31A / gs_usb).
OBDLink MX+ plugs into OBD2 pigtail, reads Pi like a real car.
Use --simulate flag to run without hardware.

Usage:
    python bench_tester.py              # real hardware
    python bench_tester.py --simulate   # no hardware needed
"""

import sys
import os
import time
import math
import threading
import argparse
import tkinter as tk
from tkinter import ttk, font
from dataclasses import dataclass, field
from typing import Optional

# -- Argument parsing --------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--simulate", action="store_true")
args = parser.parse_args()
SIMULATE = args.simulate

# -- CAN IDs -----------------------------------------------------------------
CAN_REQUEST_ID   = 0x7DF
CAN_RESPONSE_ID  = 0x7E8
CAN_FLOW_CTRL_ID = 0x7E0

# -- Colors ------------------------------------------------------------------
BG          = "#0A0A0A"
CARD_BG     = "#1A1A1A"
CRIMSON     = "#EA1823"
CRIMSON_DK  = "#BA0D20"
BLUE        = "#3489E6"
CYAN        = "#4ACCFE"
GREEN       = "#32C864"
GRAY        = "#AAAAAA"
DARK_GRAY   = "#333333"
WHITE       = "#FFFFFF"
ORANGE      = "#F0A020"

# -- Scenario Data -----------------------------------------------------------
SCENARIOS = [
    {
        "label":    "S1",
        "vehicle":  "2012 Ford F-150",
        "vin":      "1FTFW1ET1CFA84056",
        "customer": "Marcus Webb",
        "dtcs":     ["P0420", "P0171"],
        "rpm":      790, "coolant_c": 83, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 22, "iat_c": 28, "o2_raw": 0x44,
        "stft_pct": 2.3, "ltft_pct": 1.6, "maf_gps": 2.8,
        "map_kpa": 36, "timing_deg": 14, "banks": 2,
    },
    {
        "label":    "S2",
        "vehicle":  "2009 Chevrolet Silverado 1500",
        "vin":      "1GCEK29079E143364",
        "customer": "James Kowalski",
        "dtcs":     ["P0302", "P0316"],
        "rpm":      750, "coolant_c": 80, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 20, "iat_c": 26, "o2_raw": 0x3C,
        "stft_pct": 4.7, "ltft_pct": 3.1, "maf_gps": 3.2,
        "map_kpa": 34, "timing_deg": 12, "banks": 2,
    },
    {
        "label":    "S3",
        "vehicle":  "2010 Honda Civic",
        "vin":      "19XFA1F51AE028415",
        "customer": "Sarah Chen",
        "dtcs":     ["P0171", "P0174"],
        "rpm":      800, "coolant_c": 79, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 24, "iat_c": 27, "o2_raw": 0x50,
        "stft_pct": 9.4, "ltft_pct": 8.6, "maf_gps": 2.2,
        "map_kpa": 32, "timing_deg": 16, "banks": 1,
    },
    {
        "label":    "S4",
        "vehicle":  "2010 Nissan Altima",
        "vin":      "1N4AL2AP6AN555869",
        "customer": "Derek Owens",
        "dtcs":     [],
        "rpm":      850, "coolant_c": 85, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 18, "iat_c": 25, "o2_raw": 0x48,
        "stft_pct": 0.8, "ltft_pct": 1.6, "maf_gps": 3.5,
        "map_kpa": 38, "timing_deg": 15, "banks": 1,
    },
    {
        "label":    "S5",
        "vehicle":  "2010 Toyota Camry",
        "vin":      "4T4BF3EK8AR074927",
        "customer": "Amy Torres",
        "dtcs":     [],
        "rpm":      768, "coolant_c": 82, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 20, "iat_c": 24, "o2_raw": 0x40,
        "stft_pct": 1.6, "ltft_pct": 2.3, "maf_gps": 3.0,
        "map_kpa": 37, "timing_deg": 14, "banks": 1,
    },
]

# Drive cycle patterns - (rpm, throttle_pct, speed_kph, load_pct)
DRIVE_CYCLES = {
    "IDLE":    {"rpm": 780,  "throttle_pct": 0,  "speed_kph": 0,   "engine_load_pct": 15,
                "stft_pct": 2.3,  "ltft_pct": 1.6, "maf_gps": 3.0,
                "map_kpa": 35,  "timing_deg": 14},
    "CITY":    {"rpm": 1800, "throttle_pct": 25, "speed_kph": 40,  "engine_load_pct": 45,
                "stft_pct": 0.8,  "ltft_pct": 1.6, "maf_gps": 7.5,
                "map_kpa": 55,  "timing_deg": 18},
    "HIGHWAY": {"rpm": 2200, "throttle_pct": 35, "speed_kph": 100, "engine_load_pct": 55,
                "stft_pct": 0.0,  "ltft_pct": 1.6, "maf_gps": 12.0,
                "map_kpa": 65,  "timing_deg": 20},
    "WOT":     {"rpm": 4500, "throttle_pct": 98, "speed_kph": 150, "engine_load_pct": 95,
                "stft_pct": -1.6, "ltft_pct": 1.6, "maf_gps": 35.0,
                "map_kpa": 98,  "timing_deg": 24},
    "DECEL":   {"rpm": 900,  "throttle_pct": 0,  "speed_kph": 20,  "engine_load_pct": 8,
                "stft_pct": 5.5,  "ltft_pct": 1.6, "maf_gps": 1.5,
                "map_kpa": 25,  "timing_deg": 10},
}

# -- Live State --------------------------------------------------------------
state = {
    "scenario_idx":     0,
    "active_dtcs":      list(SCENARIOS[0]["dtcs"]),
    "rpm":              SCENARIOS[0]["rpm"],
    "coolant_c":        SCENARIOS[0]["coolant_c"],
    "throttle_pct":     SCENARIOS[0]["throttle_pct"],
    "speed_kph":        SCENARIOS[0]["speed_kph"],
    "engine_load_pct":  SCENARIOS[0]["engine_load_pct"],
    "iat_c":            SCENARIOS[0]["iat_c"],
    "o2_raw":           SCENARIOS[0]["o2_raw"],
    "stft_pct":         SCENARIOS[0]["stft_pct"],
    "ltft_pct":         SCENARIOS[0]["ltft_pct"],
    "maf_gps":          SCENARIOS[0]["maf_gps"],
    "map_kpa":          SCENARIOS[0]["map_kpa"],
    "timing_deg":       SCENARIOS[0]["timing_deg"],
    "connected":        False,
    "request_count":    0,
    "last_pid":         "",
    "dynamic_mode":     False,
    "dynamic_pattern":  "IDLE",
}
state_lock = threading.Lock()
isotp_pending = {}

# -- OBD2 Encoding -----------------------------------------------------------

def encode_dtc(dtc: str) -> list:
    prefix_map = {"P": 0x00, "C": 0x40, "B": 0x80, "U": 0xC0}
    prefix = prefix_map.get(dtc[0].upper(), 0x00)
    byte1  = prefix | (int(dtc[1]) << 4) | int(dtc[2], 16)
    byte2  = int(dtc[3:5], 16)
    return [byte1 & 0xFF, byte2 & 0xFF]

def supported_pid_set(banks: int) -> set:
    """Set of supported Mode-01 PID ints for the current scenario.
    Bank-2 PIDs (08/09/3D) only present on V8 (banks>=2)."""
    base = {0x01, 0x04, 0x05, 0x06, 0x07, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            0x10, 0x11, 0x14, 0x15, 0x1F, 0x21,
            0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x33, 0x3C,
            0x42, 0x43, 0x44, 0x45, 0x46, 0x4C, 0x5C, 0x5E,
            0x20, 0x40}  # 0x20/0x40 = continuation flags to next bitmask block
    if banks >= 2:
        base |= {0x08, 0x09, 0x3D}
    return base


def build_supported_bitmask(base_pid: int, banks: int) -> list:
    """Build the 0100/0120/0140 supported-PID response for a 0x20-wide block.
    Byte A bit7 = base+1 ... byte D bit0 = base+32 (SAE J1979)."""
    sup = supported_pid_set(banks)
    data = [0, 0, 0, 0]
    for i in range(1, 33):
        if (base_pid + i) in sup:
            data[(i - 1) // 8] |= (1 << (7 - ((i - 1) % 8)))
    return [0x06, 0x41, base_pid] + data + [0x00]


def build_response(mode: int, pid: int) -> list:
    with state_lock:
        s = state.copy()
        dtcs = list(s["active_dtcs"])
    banks = SCENARIOS[s["scenario_idx"]].get("banks", 1)

    if mode == 0x01:
        if pid == 0x00:
            return build_supported_bitmask(0x00, banks)
        elif pid == 0x01:
            mil  = 0x81 if dtcs else 0x01
            return [0x06, 0x41, 0x01, mil, len(dtcs), 0x07, 0xFF, 0x00]
        elif pid == 0x04:
            return [0x03, 0x41, 0x04, int(s["engine_load_pct"] * 255 / 100) & 0xFF]
        elif pid == 0x05:
            return [0x03, 0x41, 0x05, (s["coolant_c"] + 40) & 0xFF]
        elif pid == 0x06:
            # Short Fuel Trim B1: A = (pct/100 * 128) + 128, range -100% to +99.2%
            raw = max(0, min(255, round((s["stft_pct"] / 100.0 * 128) + 128)))
            return [0x03, 0x41, 0x06, raw]
        elif pid == 0x07:
            # Long Fuel Trim B1: same formula as STFT
            raw = max(0, min(255, round((s["ltft_pct"] / 100.0 * 128) + 128)))
            return [0x03, 0x41, 0x07, raw]
        elif pid == 0x0C:
            raw = int(s["rpm"] * 4)
            return [0x04, 0x41, 0x0C, (raw >> 8) & 0xFF, raw & 0xFF]
        elif pid == 0x0D:
            return [0x03, 0x41, 0x0D, s["speed_kph"] & 0xFF]
        elif pid == 0x0F:
            return [0x03, 0x41, 0x0F, (s["iat_c"] + 40) & 0xFF]
        elif pid == 0x0B:
            # Intake Manifold Absolute Pressure: A = kPa (0-255)
            return [0x03, 0x41, 0x0B, max(0, min(255, s["map_kpa"])) & 0xFF]
        elif pid == 0x0E:
            # Timing Advance: A = (degrees + 64) * 2, range -64 to +63.5 deg
            raw = max(0, min(255, int((s["timing_deg"] + 64) * 2)))
            return [0x03, 0x41, 0x0E, raw]
        elif pid == 0x10:
            # Mass Air Flow: (A*256+B)/100 g/s
            raw = max(0, min(0xFFFF, int(s["maf_gps"] * 100)))
            return [0x04, 0x41, 0x10, (raw >> 8) & 0xFF, raw & 0xFF]
        elif pid == 0x11:
            return [0x03, 0x41, 0x11, int(s["throttle_pct"] * 255 / 100) & 0xFF]
        elif pid == 0x14:
            return [0x04, 0x41, 0x14, s["o2_raw"], 0xFF]
        elif pid == 0x1F:
            return [0x04, 0x41, 0x1F, 0x00, 0x3C]
        elif pid == 0x20:
            return build_supported_bitmask(0x20, banks)
        elif pid == 0x21:
            return [0x04, 0x41, 0x21, 0x00, 0x0A if dtcs else 0x00]
        elif pid == 0x31:
            # Distance since codes last cleared (km): report 0 km
            return [0x04, 0x41, 0x31, 0x00, 0x00]
        elif pid == 0x40:
            return build_supported_bitmask(0x40, banks)
        elif pid == 0x42:
            # Control Module Voltage: (A*256+B)/1000 V — fixed at 14.4V (charging)
            raw = 14400  # 14.4V * 1000
            return [0x04, 0x41, 0x42, (raw >> 8) & 0xFF, raw & 0xFF]
        elif pid == 0x08:
            if banks < 2:
                return [0x03, 0x7F, 0x01, 0x12]
            raw = max(0, min(255, round(((s["stft_pct"] + 0.8) / 100.0 * 128) + 128)))
            return [0x03, 0x41, 0x08, raw]
        elif pid == 0x09:
            if banks < 2:
                return [0x03, 0x7F, 0x01, 0x12]
            raw = max(0, min(255, round(((s["ltft_pct"] + 0.5) / 100.0 * 128) + 128)))
            return [0x03, 0x41, 0x09, raw]
        elif pid == 0x0A:
            # Fuel system pressure (gauge): A*3 kPa -> ~350 kPa port injection
            return [0x03, 0x41, 0x0A, max(0, min(255, round(350 / 3)))]
        elif pid == 0x15:
            # O2 B1S2 (downstream). Healthy cat -> steady ~0.65V. P0420 -> mirrors
            # upstream (a dead cat lets the upstream swing pass through).
            a = s["o2_raw"] if "P0420" in dtcs else max(0, min(255, round(0.65 * 200)))
            return [0x04, 0x41, 0x15, a & 0xFF, 0xFF]
        elif pid == 0x2C:
            # Commanded EGR: closed at idle and WOT, open mid-cruise
            load = s["engine_load_pct"]
            egr = 0.0 if (load < 30 or load > 80) else (load - 25) * 0.5
            return [0x03, 0x41, 0x2C, max(0, min(255, round(egr * 255 / 100)))]
        elif pid == 0x2D:
            # EGR error: ~0% (tracking well). A=128 -> 0
            return [0x03, 0x41, 0x2D, 128]
        elif pid == 0x2E:
            # Evap purge: ~0% at idle
            return [0x03, 0x41, 0x2E, 0]
        elif pid == 0x2F:
            # Fuel level: 64%
            return [0x03, 0x41, 0x2F, max(0, min(255, round(64 * 255 / 100)))]
        elif pid == 0x30:
            # Warm-ups since codes cleared
            return [0x03, 0x41, 0x30, 40]
        elif pid == 0x33:
            # Barometric pressure: ~83 kPa (Colorado elevation)
            return [0x03, 0x41, 0x33, 83]
        elif pid == 0x3C:
            # Catalyst temp B1S1: (256A+B)/10 - 40, hotter under load
            t = max(0, min(0xFFFF, round((450 + s["engine_load_pct"] * 3 + 40) * 10)))
            return [0x04, 0x41, 0x3C, (t >> 8) & 0xFF, t & 0xFF]
        elif pid == 0x3D:
            if banks < 2:
                return [0x03, 0x7F, 0x01, 0x12]
            t = max(0, min(0xFFFF, round((445 + s["engine_load_pct"] * 3 + 40) * 10)))
            return [0x04, 0x41, 0x3D, (t >> 8) & 0xFF, t & 0xFF]
        elif pid == 0x43:
            # Absolute load: (256A+B)*100/255
            v = max(0, min(0xFFFF, round(s["engine_load_pct"] * 255 / 100)))
            return [0x04, 0x41, 0x43, (v >> 8) & 0xFF, v & 0xFF]
        elif pid == 0x44:
            # Commanded equivalence ratio (lambda): (256A+B)/32768.
            # 1.0 in closed loop, ~0.88 power enrichment near WOT
            lam = 0.88 if s["throttle_pct"] >= 80 else 1.0
            raw = max(0, min(0xFFFF, round(lam * 32768)))
            return [0x04, 0x41, 0x44, (raw >> 8) & 0xFF, raw & 0xFF]
        elif pid == 0x45:
            # Relative throttle position
            return [0x03, 0x41, 0x45, int(s["throttle_pct"] * 255 / 100) & 0xFF]
        elif pid == 0x46:
            # Ambient air temp: 22C
            return [0x03, 0x41, 0x46, (22 + 40) & 0xFF]
        elif pid == 0x4C:
            # Commanded throttle actuator
            return [0x03, 0x41, 0x4C, int(s["throttle_pct"] * 255 / 100) & 0xFF]
        elif pid == 0x5C:
            # Engine oil temp: A-40, ~coolant + 7C
            return [0x03, 0x41, 0x5C, (s["coolant_c"] + 7 + 40) & 0xFF]
        elif pid == 0x5E:
            # Engine fuel rate: (256A+B)/20 L/h, tracks MAF (~0.5x)
            raw = max(0, min(0xFFFF, round(s["maf_gps"] * 0.5 * 20)))
            return [0x04, 0x41, 0x5E, (raw >> 8) & 0xFF, raw & 0xFF]
        return [0x03, 0x7F, 0x01, 0x12]

    elif mode == 0x02:
        m01 = build_response(0x01, pid)
        if len(m01) >= 3 and m01[1] == 0x41:
            result = [m01[0] + 1, 0x42, pid, 0x00] + m01[3:]
            return result
        return [0x03, 0x7F, 0x02, 0x12]

    elif mode == 0x09:
        if pid == 0x00:
            return [0x04, 0x49, 0x00, 0x54, 0x40, 0x00, 0x00, 0x00]
        elif pid == 0x02:
            scenario = SCENARIOS[state["scenario_idx"]]
            vin = scenario["vin"]
            return [0x49, 0x02, 0x01] + [ord(c) for c in vin[:17]]
        return [0x03, 0x7F, 0x09, 0x12]

    elif mode == 0x03:
        if not dtcs:
            return [0x02, 0x43, 0x00]
        frame = [0x02 + len(dtcs) * 2, 0x43]
        for dtc in dtcs[:3]:
            frame.extend(encode_dtc(dtc))
        return frame

    elif mode == 0x04:
        with state_lock:
            state["active_dtcs"] = []
        return [0x01, 0x44]

    elif mode == 0x07:
        # Pending DTCs — always return "no pending codes" for bench tester
        return [0x02, 0x47, 0x00]

    elif mode == 0x0A:
        # Permanent DTCs — always return "no permanent codes" for bench tester
        return [0x02, 0x4A, 0x00]

    return [0x03, 0x7F, mode, 0x12]

def isotp_send(bus, data: list):
    """Send ISO-TP response - handles single and multi-frame."""
    import can as can_lib
    if len(data) <= 7:
        frame = [len(data)] + data
        while len(frame) < 8:
            frame.append(0x00)
        bus.send(can_lib.Message(
            arbitration_id=CAN_RESPONSE_ID,
            data=bytes(frame[:8]),
            is_extended_id=False
        ))
        isotp_pending.clear()
    else:
        ff = [0x10, len(data) & 0xFF] + data[:6]
        bus.send(can_lib.Message(
            arbitration_id=CAN_RESPONSE_ID,
            data=bytes(ff[:8]),
            is_extended_id=False
        ))
        isotp_pending["remaining"] = data[6:]
        isotp_pending["seq"] = 1

def isotp_continue(bus):
    """Send consecutive frames after flow control."""
    import can as can_lib
    remaining = isotp_pending.get("remaining", [])
    seq       = isotp_pending.get("seq", 1)
    while remaining:
        chunk = remaining[:7]
        remaining = remaining[7:]
        cf = [0x20 | (seq & 0x0F)] + chunk
        while len(cf) < 8:
            cf.append(0x00)
        bus.send(can_lib.Message(
            arbitration_id=CAN_RESPONSE_ID,
            data=bytes(cf[:8]),
            is_extended_id=False
        ))
        seq += 1
        time.sleep(0.0005)
    isotp_pending.clear()

# -- Dynamic PID Thread ------------------------------------------------------

def dynamic_pid_thread():
    """Updates PIDs smoothly when dynamic mode is active."""
    start = time.time()
    while True:
        time.sleep(0.1)
        with state_lock:
            if not state["dynamic_mode"]:
                continue
            pattern = DRIVE_CYCLES[state["dynamic_pattern"]]
            t = time.time() - start
            state["rpm"]             = int(pattern["rpm"] + 50 * math.sin(t * 0.7))
            state["throttle_pct"]    = max(0, min(100, pattern["throttle_pct"] + int(5 * math.sin(t * 1.2))))
            state["speed_kph"]       = max(0, int(pattern["speed_kph"] + 3 * math.sin(t * 0.4)))
            state["engine_load_pct"] = max(0, min(100, pattern["engine_load_pct"] + int(3 * math.sin(t * 0.9))))
            state["maf_gps"]         = max(0.5, pattern["maf_gps"] + 0.8 * math.sin(t * 0.8))
            state["map_kpa"]         = max(15, min(105, int(pattern["map_kpa"] + 2 * math.sin(t * 0.6))))
            # Upstream O2 swings 0.1-0.9V in closed loop (~1 Hz). Downstream (0x15)
            # mirrors this on P0420 vehicles; stays steady on a healthy cat.
            state["o2_raw"]          = max(20, min(180, int(100 + 80 * math.sin(t * 5.0))))

# -- CAN Bus Thread ----------------------------------------------------------

def can_thread(log_callback, status_callback):
    """Main CAN bus loop - listens for MX+ requests and responds."""
    if SIMULATE:
        status_callback("SIMULATE MODE - no hardware", CYAN)
        while True:
            time.sleep(1)
        return

    try:
        import can as can_lib
    except ImportError:
        status_callback("ERROR: pip install python-can", CRIMSON)
        return

    status_callback("Connecting to CAN adapter...", ORANGE)

    try:
        bus = can_lib.Bus(interface="slcan", channel="COM3", bitrate=500000)
    except Exception as e:
        status_callback(f"ERROR: {e}", CRIMSON)
        log_callback(f"Could not open gs_usb: {e}\nCheck USB CAN adapter is plugged in.")
        return

    status_callback("CAN READY - waiting for MX+", GREEN)
    log_callback("CAN bus open at 500kbps. Plug in MX+...")

    last_msg_time = None
    connected     = False

    try:
        while True:
            if connected and last_msg_time:
                if time.time() - last_msg_time > 5.0:
                    connected = False
                    status_callback("CAN READY - waiting for MX+", GREEN)
                    log_callback("MX+ disconnected.")

            msg = bus.recv(timeout=0.1)
            if msg is None:
                continue

            last_msg_time = time.time()

            if msg.arbitration_id == CAN_FLOW_CTRL_ID:
                if msg.data[0] == 0x30 and isotp_pending:
                    isotp_continue(bus)
                continue

            if msg.arbitration_id != CAN_REQUEST_ID:
                continue

            if not connected:
                connected = True
                status_callback("MX+ CONNECTED", CYAN)
                log_callback("MX+ connected!")

            data   = msg.data
            length = data[0]
            mode   = data[1]
            pid    = data[2] if length > 1 else 0x00

            with state_lock:
                state["request_count"] += 1
                state["last_pid"] = f"Mode {hex(mode)} PID {hex(pid)}"

            response = build_response(mode, pid)
            isotp_send(bus, response)
            log_callback(f"-> {hex(mode)}/{hex(pid)}  -> {[hex(b) for b in response[:6]]}")

    except Exception as e:
        status_callback(f"CAN ERROR: {e}", CRIMSON)
        log_callback(f"CAN error: {e}")
    finally:
        try:
            bus.shutdown()
        except:
            pass

# -- GUI ---------------------------------------------------------------------

class BenchTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CFP Bench Tester")
        self.root.configure(bg=BG)
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        self.root.minsize(800, 600)

        self.font_header = font.Font(family="Consolas", size=14, weight="bold")
        self.font_label  = font.Font(family="Consolas", size=11, weight="bold")
        self.font_body   = font.Font(family="Consolas", size=10)
        self.font_small  = font.Font(family="Consolas", size=9)
        self.font_mono   = font.Font(family="Consolas", size=9)

        self.scenario_var     = tk.IntVar(value=0)
        self.rpm_var          = tk.IntVar(value=790)
        self.coolant_var      = tk.IntVar(value=83)
        self.throttle_var     = tk.IntVar(value=0)
        self.speed_var        = tk.IntVar(value=0)
        self.load_var         = tk.IntVar(value=22)
        self.dynamic_var      = tk.BooleanVar(value=False)
        self.dtc_entry_var    = tk.StringVar(value="P0300")
        self.status_text      = tk.StringVar(value="Starting...")
        self.req_count_var    = tk.StringVar(value="Requests: 0")

        self._build_ui()
        self._start_threads()
        self._update_loop()

    def _build_ui(self):
        header = tk.Frame(self.root, bg=CRIMSON, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="CRIMSONFORGE  BENCH TESTER",
                 font=self.font_header, bg=CRIMSON, fg=WHITE).pack(side="left", padx=12, pady=8)
        self.status_label = tk.Label(header, textvariable=self.status_text,
                                     font=self.font_label, bg=CRIMSON, fg=WHITE)
        self.status_label.pack(side="right", padx=12)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        left  = tk.Frame(main, bg=BG)
        right = tk.Frame(main, bg=BG)
        left.pack(side="left",  fill="both", expand=True, padx=(0, 4))
        right.pack(side="right", fill="both", expand=True, padx=(4, 0))

        self._section(left, "SCENARIO")
        for i, sc in enumerate(SCENARIOS):
            color = CRIMSON if sc["dtcs"] else CYAN
            text  = f"{sc['label']}  {sc['vehicle']}"
            dtc_text = "  " + " | ".join(sc["dtcs"]) if sc["dtcs"] else "  CLEAN"
            row = tk.Frame(left, bg=CARD_BG, pady=4)
            row.pack(fill="x", pady=2)
            rb = tk.Radiobutton(row, text=text, variable=self.scenario_var,
                                value=i, command=self._on_scenario_change,
                                font=self.font_label, bg=CARD_BG, fg=WHITE,
                                selectcolor=CRIMSON_DK, activebackground=CARD_BG,
                                activeforeground=WHITE)
            rb.pack(side="left", padx=8)
            tk.Label(row, text=dtc_text, font=self.font_small,
                     bg=CARD_BG, fg=color).pack(side="right", padx=8)

        self._section(left, "LIVE PIDs")
        self._slider(left, "RPM", self.rpm_var, 400, 6000, "rpm")
        self._slider(left, "COOLANT C", self.coolant_var, 20, 110, "coolant_c")
        self._slider(left, "THROTTLE %", self.throttle_var, 0, 100, "throttle_pct")
        self._slider(left, "SPEED km/h", self.speed_var, 0, 200, "speed_kph")
        self._slider(left, "LOAD %", self.load_var, 0, 100, "engine_load_pct")

        self._section(left, "DRIVE CYCLE")
        cycle_frame = tk.Frame(left, bg=BG)
        cycle_frame.pack(fill="x", pady=4)

        dyn_cb = tk.Checkbutton(cycle_frame, text="DYNAMIC MODE",
                                variable=self.dynamic_var,
                                command=self._on_dynamic_toggle,
                                font=self.font_label, bg=BG, fg=CYAN,
                                selectcolor=DARK_GRAY, activebackground=BG)
        dyn_cb.pack(side="left", padx=4)

        btn_frame = tk.Frame(left, bg=BG)
        btn_frame.pack(fill="x", pady=2)
        for cycle_name in DRIVE_CYCLES:
            tk.Button(btn_frame, text=cycle_name,
                      command=lambda c=cycle_name: self._set_drive_cycle(c),
                      font=self.font_small, bg=DARK_GRAY, fg=WHITE,
                      activebackground=BLUE, relief="flat",
                      padx=6, pady=4).pack(side="left", padx=2)

        self._section(right, "DTCs")
        self.dtc_frame = tk.Frame(right, bg=BG)
        self.dtc_frame.pack(fill="x")
        self._refresh_dtc_display()

        add_frame = tk.Frame(right, bg=BG)
        add_frame.pack(fill="x", pady=4)
        tk.Entry(add_frame, textvariable=self.dtc_entry_var,
                 font=self.font_label, bg=DARK_GRAY, fg=WHITE,
                 insertbackground=WHITE, width=8).pack(side="left", padx=4)
        tk.Button(add_frame, text="+ INJECT",
                  command=self._inject_dtc,
                  font=self.font_label, bg=CRIMSON_DK, fg=WHITE,
                  activebackground=CRIMSON, relief="flat",
                  padx=8, pady=4).pack(side="left", padx=4)
        tk.Button(add_frame, text="CLEAR ALL",
                  command=self._clear_dtcs,
                  font=self.font_label, bg=DARK_GRAY, fg=CYAN,
                  activebackground=DARK_GRAY, relief="flat",
                  padx=8, pady=4).pack(side="left", padx=4)

        quick_frame = tk.Frame(right, bg=BG)
        quick_frame.pack(fill="x", pady=2)
        common_codes = ["P0300", "P0420", "P0171", "P0174", "P0302", "P0441"]
        for code in common_codes:
            tk.Button(quick_frame, text=code,
                      command=lambda c=code: self._quick_inject(c),
                      font=self.font_small, bg=DARK_GRAY, fg=CRIMSON,
                      activebackground=CRIMSON_DK, relief="flat",
                      padx=4, pady=3).pack(side="left", padx=1, pady=2)

        self._section(right, "CAN MONITOR")
        self.req_label = tk.Label(right, textvariable=self.req_count_var,
                                  font=self.font_label, bg=BG, fg=CYAN)
        self.req_label.pack(anchor="w", padx=4)

        log_frame = tk.Frame(right, bg=CARD_BG)
        log_frame.pack(fill="both", expand=True, pady=4)
        self.log_box = tk.Text(log_frame, font=self.font_mono,
                               bg=CARD_BG, fg=GREEN, insertbackground=GREEN,
                               height=12, wrap="word", state="disabled")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)

        tk.Button(right, text="CLEAR LOG",
                  command=self._clear_log,
                  font=self.font_small, bg=DARK_GRAY, fg=GRAY,
                  relief="flat", padx=6, pady=3).pack(anchor="e", padx=4)

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(8, 2))
        tk.Label(f, text=title, font=self.font_label,
                 bg=BG, fg=CRIMSON).pack(side="left", padx=4)
        tk.Frame(f, bg=DARK_GRAY, height=1).pack(
            side="left", fill="x", expand=True, padx=4)

    def _slider(self, parent, label, var, from_, to_, state_key):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=f"{label:12}", font=self.font_small,
                 bg=BG, fg=GRAY, width=12, anchor="w").pack(side="left", padx=4)
        val_label = tk.Label(row, text=str(var.get()), font=self.font_label,
                             bg=BG, fg=WHITE, width=5, anchor="e")
        val_label.pack(side="right", padx=8)

        def on_change(v, lbl=val_label, key=state_key, variable=var):
            val = int(float(v))
            lbl.config(text=str(val))
            with state_lock:
                state[key] = val

        tk.Scale(row, from_=from_, to=to_, orient="horizontal",
                 variable=var, command=on_change,
                 bg=BG, fg=WHITE, troughcolor=DARK_GRAY,
                 highlightthickness=0, showvalue=False,
                 length=200).pack(side="left", fill="x", expand=True)

    def _on_scenario_change(self):
        idx = self.scenario_var.get()
        sc  = SCENARIOS[idx]
        with state_lock:
            state["scenario_idx"]    = idx
            state["active_dtcs"]     = list(sc["dtcs"])
            state["rpm"]             = sc["rpm"]
            state["coolant_c"]       = sc["coolant_c"]
            state["throttle_pct"]    = sc["throttle_pct"]
            state["speed_kph"]       = sc["speed_kph"]
            state["engine_load_pct"] = sc["engine_load_pct"]
            state["stft_pct"]        = sc["stft_pct"]
            state["ltft_pct"]        = sc["ltft_pct"]
            state["maf_gps"]         = sc["maf_gps"]
            state["map_kpa"]         = sc["map_kpa"]
            state["timing_deg"]      = sc["timing_deg"]
        self.rpm_var.set(sc["rpm"])
        self.coolant_var.set(sc["coolant_c"])
        self.throttle_var.set(sc["throttle_pct"])
        self.speed_var.set(sc["speed_kph"])
        self.load_var.set(sc["engine_load_pct"])
        self._refresh_dtc_display()
        self._log(f"Scenario -> {sc['vehicle']} | VIN: {sc['vin']}")

    def _on_dynamic_toggle(self):
        with state_lock:
            state["dynamic_mode"] = self.dynamic_var.get()
        status = "ON" if self.dynamic_var.get() else "OFF"
        self._log(f"Dynamic mode: {status}")

    def _set_drive_cycle(self, cycle_name):
        pattern = DRIVE_CYCLES[cycle_name]
        with state_lock:
            state.update(pattern)
            state["dynamic_pattern"] = cycle_name
        self.rpm_var.set(pattern["rpm"])
        self.throttle_var.set(pattern["throttle_pct"])
        self.speed_var.set(pattern["speed_kph"])
        self.load_var.set(pattern["engine_load_pct"])
        self._log(f"Drive cycle: {cycle_name}")

    def _inject_dtc(self):
        code = self.dtc_entry_var.get().upper().strip()
        if len(code) == 5 and code[0] in "PCBU":
            with state_lock:
                if code not in state["active_dtcs"]:
                    state["active_dtcs"].append(code)
            self._refresh_dtc_display()
            self._log(f"DTC injected: {code}")

    def _quick_inject(self, code):
        self.dtc_entry_var.set(code)
        self._inject_dtc()

    def _clear_dtcs(self):
        with state_lock:
            state["active_dtcs"] = []
        self._refresh_dtc_display()
        self._log("All DTCs cleared")

    def _refresh_dtc_display(self):
        for w in self.dtc_frame.winfo_children():
            w.destroy()
        with state_lock:
            dtcs = list(state["active_dtcs"])
        if not dtcs:
            tk.Label(self.dtc_frame, text="No active DTCs",
                     font=self.font_small, bg=BG, fg=GRAY).pack(anchor="w", padx=4)
        else:
            row = tk.Frame(self.dtc_frame, bg=BG)
            row.pack(fill="x")
            for dtc in dtcs:
                btn = tk.Button(row, text=f"x {dtc}",
                                command=lambda d=dtc: self._remove_dtc(d),
                                font=self.font_label, bg=CRIMSON_DK, fg=WHITE,
                                activebackground=DARK_GRAY, relief="flat",
                                padx=6, pady=3)
                btn.pack(side="left", padx=2, pady=2)

    def _remove_dtc(self, code):
        with state_lock:
            if code in state["active_dtcs"]:
                state["active_dtcs"].remove(code)
        self._refresh_dtc_display()
        self._log(f"DTC removed: {code}")

    def _log(self, msg):
        """Thread-safe log append."""
        def _do():
            self.log_box.config(state="normal")
            ts = time.strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}] {msg}\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
            lines = int(self.log_box.index("end-1c").split(".")[0])
            if lines > 200:
                self.log_box.config(state="normal")
                self.log_box.delete("1.0", "50.0")
                self.log_box.config(state="disabled")
        self.root.after(0, _do)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _set_status(self, text, color=WHITE):
        def _do():
            self.status_text.set(text)
            self.status_label.config(fg=color)
        self.root.after(0, _do)

    def _start_threads(self):
        t1 = threading.Thread(target=dynamic_pid_thread, daemon=True)
        t1.start()

        t2 = threading.Thread(
            target=can_thread,
            args=(self._log, self._set_status),
            daemon=True
        )
        t2.start()

        if SIMULATE:
            self._log("SIMULATION MODE - hardware not required")
            self._log("CAN responses will be calculated but not transmitted")

    def _update_loop(self):
        """Update UI elements from state every 500ms."""
        with state_lock:
            count    = state["request_count"]
            last_pid = state["last_pid"]

        self.req_count_var.set(f"Requests: {count}  |  Last: {last_pid}")
        self.root.after(500, self._update_loop)

# -- Entry Point -------------------------------------------------------------

def main():
    root = tk.Tk()
    app  = BenchTesterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
