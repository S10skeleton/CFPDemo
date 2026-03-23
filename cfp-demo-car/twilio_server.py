"""
twilio_server.py
CFP Demo Car — Inbound Twilio Webhook Server

Tiny Flask server that:
1. Receives incoming SMS from CFP (estimate sent by tech)
2. Parses content, writes to state.json — triggers estimate screen on UI
3. Receives outbound reply trigger from UI — fires reply SMS via Twilio

Run alongside the UI and OBD emulator.
In simulation mode: exposes the same endpoints but logs instead of calling Twilio.

Endpoints:
    POST /sms/inbound     Twilio webhook — receives incoming SMS
    POST /sms/reply       Called by UI when customer taps APPROVE/CALL ME
    GET  /health          Health check
"""

import os
import json
from flask import Flask, request, Response
from dotenv import load_dotenv
from state import write_state, read_state
from twilio_trigger import fire_sms
from config import get_scenario
from state import get_scenario_index

load_dotenv()

SIMULATE     = os.environ.get("CFP_SIMULATE", "0") == "1"
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_FROM_NUMBER", "")
CFP_NUMBER   = os.getenv("CFP_PHONE_NUMBER", TWILIO_FROM)

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "simulate": SIMULATE}, 200

@app.route("/sms/inbound", methods=["POST"])
def sms_inbound():
    """
    Twilio webhook — receives incoming SMS to the demo number.
    If the message looks like an estimate from CFP, write to state.json
    to trigger the estimate screen on the UI.
    """
    body    = request.form.get("Body", "").strip()
    from_nr = request.form.get("From", "")

    print(f"[SMS] Inbound from {from_nr}: {body[:80]}")

    # Write incoming message to state — UI polls this
    write_state({
        "inbound_sms":      body,
        "inbound_from":     from_nr,
        "show_estimate":    True,
        "estimate_approved": False,
    })

    # Return empty TwiML response (no auto-reply)
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        mimetype="text/xml"
    )

@app.route("/sms/reply", methods=["POST"])
def sms_reply():
    """
    Called by the UI when customer taps APPROVE or CALL ME.
    Fires reply SMS back to CFP number.
    """
    data   = request.get_json()
    action = data.get("action", "APPROVE")   # "APPROVE" or "CALL ME"

    scenario = get_scenario(get_scenario_index())
    name     = scenario["customer"]
    vehicle  = scenario["vehicle"]

    if action == "APPROVE":
        msg = f"APPROVE — {name} has approved the estimate for their {vehicle}. Please proceed."
    else:
        msg = f"CALL ME — {name} would like to discuss the estimate for their {vehicle}. Please call."

    if SIMULATE:
        print(f"\n[SMS REPLY SIM] ———————————————————————————")
        print(f"[SMS REPLY SIM] TO:   {CFP_NUMBER}")
        print(f"[SMS REPLY SIM] MSG:  {msg}")
        print(f"[SMS REPLY SIM] ———————————————————————————\n")
    else:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            client.messages.create(
                to=CFP_NUMBER,
                from_=TWILIO_FROM,
                body=msg
            )
            print(f"[SMS] Reply sent: {action}")
        except Exception as e:
            print(f"[SMS] Reply error: {e}")
            return {"ok": False, "error": str(e)}, 500

    write_state({
        "estimate_approved": True,
        "approval_action":   action,
        "show_estimate":     False,
    })

    return {"ok": True, "action": action}, 200

def run_server():
    """Start the Flask webhook server."""
    port = int(os.getenv("WEBHOOK_PORT", "5000"))
    print(f"[SMS] Webhook server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    run_server()
