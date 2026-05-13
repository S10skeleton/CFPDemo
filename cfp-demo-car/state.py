"""
state.py
Shared state broker — reads and writes state.json.
Used by both obd_emulator.py and ui_app.py to communicate
active scenario index and connection status.
"""

import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

DEFAULT_STATE = {
    "scenario_index":    0,
    "connected":         False,
    "last_vin":          "",
}

def read_state() -> dict:
    """Read current state from state.json. Returns defaults if missing."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_STATE.copy()

def write_state(updates: dict) -> None:
    """Merge updates into current state and write to state.json."""
    current = read_state()
    current.update(updates)
    with open(STATE_FILE, "w") as f:
        json.dump(current, f, indent=2)

def reset_state() -> None:
    """Reset state to defaults."""
    write_state(DEFAULT_STATE.copy())

def get_scenario_index() -> int:
    return read_state().get("scenario_index", 0)

def set_scenario_index(index: int) -> None:
    write_state({"scenario_index": index, "connected": False})

def set_connected(connected: bool) -> None:
    write_state({"connected": connected})
