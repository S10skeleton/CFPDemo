"""
main.py
CFP Demo Car — Startup Orchestrator

Usage:
    python main.py              # Production mode (Pi hardware required)
    python main.py --simulate   # Simulation mode (laptop dev, no hardware)
"""

import sys
import argparse
import subprocess
import os

def parse_args():
    parser = argparse.ArgumentParser(description="CFP Demo Car")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode (no GPIO, CAN, or Bluetooth hardware required)"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    simulate = args.simulate

    # Set environment flag so all modules can check it
    os.environ["CFP_SIMULATE"] = "1" if simulate else "0"

    if simulate:
        print("[CFP] Starting in SIMULATION MODE — no hardware required")
    else:
        print("[CFP] Starting in PRODUCTION MODE — Pi hardware expected")

    # Import here so simulate env var is set first
    from state import reset_state
    reset_state()

    # Start Twilio webhook server in background thread
    import threading
    from twilio_server import run_server
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("[CFP] Twilio webhook server started (background)")

    # Launch UI (blocking — runs until shutdown)
    from ui_app import run_ui
    run_ui(simulate=simulate)

if __name__ == "__main__":
    main()
