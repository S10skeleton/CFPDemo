"""
twilio_trigger.py
CFP Demo Car — Twilio SMS Integration
Fires SMS to demo phone when scanner connects.
Simulation mode: Prints SMS content to console instead of sending.
"""

import os
from dotenv import load_dotenv

load_dotenv()

SIMULATE = os.environ.get("CFP_SIMULATE", "0") == "1"

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_FROM_NUMBER", "")
DEMO_PHONE   = os.getenv("DEMO_PHONE_NUMBER", "")

def build_message(scenario: dict) -> str:
    """Build the SMS body for a given scenario."""
    name    = scenario["customer"]
    vehicle = scenario["vehicle"]

    if scenario["dtcs"]:
        codes   = ", ".join(scenario["dtcs"])
        summary = scenario["ai_summary"]
        return (
            f"Hi {name}, your {vehicle} has been scanned. "
            f"We found {codes}. Our AI flagged a likely {summary}. "
            f"We'll call shortly with an estimate. — CrimsonForgePro"
        )
    else:
        return (
            f"Hi {name}, your {vehicle} service is complete. "
            f"No fault codes found. {scenario['ai_summary'].capitalize()}. "
            f"Drive safe! — CrimsonForgePro"
        )

def fire_sms(scenario: dict) -> bool:
    """
    Send Twilio SMS for the given scenario.
    Returns True on success, False on failure.
    In simulation mode, prints to console and returns True.
    """
    message = build_message(scenario)

    if SIMULATE:
        print(f"\n[TWILIO SIM] ——————————————————————————————")
        print(f"[TWILIO SIM] TO:   {DEMO_PHONE or '(not set in .env)'}")
        print(f"[TWILIO SIM] FROM: {TWILIO_FROM or '(not set in .env)'}")
        print(f"[TWILIO SIM] MSG:  {message}")
        print(f"[TWILIO SIM] ——————————————————————————————\n")
        return True

    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, DEMO_PHONE]):
        print("[TWILIO] ERROR: Missing credentials in .env — SMS not sent")
        return False

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            to=DEMO_PHONE,
            from_=TWILIO_FROM,
            body=message
        )
        print(f"[TWILIO] SMS sent to {DEMO_PHONE}")
        return True
    except Exception as e:
        print(f"[TWILIO] ERROR: {e}")
        return False
