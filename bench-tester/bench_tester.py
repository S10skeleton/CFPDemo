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
    },
    {
        "label":    "S2",
        "vehicle":  "2009 Chevrolet Silverado 1500",
        "vin":      "1GCEK29079E143364",
        "customer": "James Kowalski",
        "dtcs":     ["P0302", "P0316"],
        "rpm":      750, "coolant_c": 80, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 20, "iat_c": 26, "o2_raw": 0x3C,
    },
    {
        "label":    "S3",
        "vehicle":  "2010 Honda Civic",
        "vin":      "19XFA1F51AE028415",
        "customer": "Sarah Chen",
        "dtcs":     ["P0171", "P0174"],
        "rpm":      800, "coolant_c": 79, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 24, "iat_c": 27, "o2_raw": 0x50,
    },
    {
        "label":    "S4",
        "vehicle":  "2010 Nissan Altima",
        "vin":      "1N4AL2AP6AN555869",
        "customer": "Derek Owens",
        "dtcs":     [],
        "rpm":      850, "coolant_c": 85, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 18, "iat_c": 25, "o2_raw": 0x48,
    },
    {
        "label":    "S5",
        "vehicle":  "2010 Toyota Camry",
        "vin":      "4T4BF3EK8AR074927",
        "customer": "Amy Torres",
        "dtcs":     [],
        "rpm":      768, "coolant_c": 82, "throttle_pct": 0,
        "speed_kph": 0, "engine_load_pct": 20, "iat_c": 24, "o2_raw": 0x40,
    },
]

# Drive cycle patterns - (rpm, throttle_pct, speed_kph, load_pct)
DRIVE_CYCLES = {
    "IDLE":    {"rpm": 780,  "throttle_pct": 0,  "speed_kph": 0,   "engine_load_pct": 15},
    "CITY":    {"rpm": 1800, "throttle_pct": 25, "speed_kph": 40,  "engine_load_pct": 45},
    "HIGHWAY": {"rpm": 2200, "throttle_pct": 35, "speed_kph": 100, "engine_load_pct": 55},
    "WOT":     {"rpm": 4500, "throttle_pct": 98, "speed_kph": 150, "engine_load_pct": 95},
    "DECEL":   {"rpm": 900,  "throttle_pct": 0,  "speed_kph": 20,  "engine_load_pct": 8},
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

def build_response(mode: int, pid: int) -> list:
    with state_lock:
        s = state.copy()
        dtcs = list(s["active_dtcs"])

    if mode == 0x01:
        if pid == 0x00:
            return [0x06, 0x41, 0x00, 0xBE, 0x3F, 0xA8, 0x13, 0x00]
        elif pid == 0x01:
            mil  = 0x81 if dtcs else 0x01
            return [0x06, 0x41, 0x01, mil, len(dtcs), 0x07, 0xFF, 0x00]
        elif pid == 0x04:
            return [0x03, 0x41, 0x04, int(s["engine_load_pct"] * 255 / 100) & 0xFF]
        elif pid == 0x05:
            return [0x03, 0x41, 0x05, (s["coolant_c"] + 40) & 0xFF]
        elif pid == 0x0C:
            raw = int(s["rpm"] * 4)
            return [0x04, 0x41, 0x0C, (raw >> 8) & 0xFF, raw & 0xFF]
        elif pid == 0x0D:
            return [0x03, 0x41, 0x0D, s["speed_kph"] & 0xFF]
        elif pid == 0x0F:
            return [0x03, 0x41, 0x0F, (s["iat_c"] + 40) & 0xFF]
        elif pid == 0x11:
            return [0x03, 0x41, 0x11, int(s["throttle_pct"] * 255 / 100) & 0xFF]
        elif pid == 0x14:
            return [0x04, 0x41, 0x14, s["o2_raw"], 0xFF]
        elif pid == 0x1F:
            return [0x04, 0x41, 0x1F, 0x00, 0x3C]
        elif pid == 0x21:
            return [0x04, 0x41, 0x21, 0x00, 0x0A if dtcs else 0x00]
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
