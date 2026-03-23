# CFPDemo

Raspberry Pi 5 OBD2 vehicle emulator for **CrimsonForgePro** investor demos. Turns a Pi into a fake car that an OBDLink MX+ scanner reads as a real ECU over CAN bus — no actual vehicle required.

## What This Does

A technician plugs the OBDLink MX+ into the Pi's OBD2 port, scans it from their phone, and gets real fault codes, VIN, and live sensor data. The Pi's touchscreen shows the active scenario, and Twilio fires an SMS estimate to the "customer" who can approve or request a callback — all in an office setting.

## Hardware

- Raspberry Pi 5
- 3.5" XPT2046 SPI touchscreen (480x320)
- MCP2515 CAN transceiver on SPI1 wired to OBD2 female port
- OBDLink MX+ Bluetooth scanner

## Demo Scenarios

| # | Vehicle | Customer | Type | DTCs |
|---|---------|----------|------|------|
| S1 | 2019 Chevrolet Malibu | Marcus Webb | Fault | P0420, P0171 |
| S2 | 2021 Ford F-150 | James Kowalski | Fault | P0302, P0316 |
| S3 | 2020 Honda CR-V | Sarah Chen | Fault | P0087, P0093 |
| S4 | 2022 RAM 1500 | Derek Owens | Clean | None |
| S5 | 2023 Toyota Camry | Amy Torres | Maintenance | None |

Each scenario includes VIN, live PIDs (RPM, coolant, throttle, O2), DTC descriptions, AI summary, and a full repair estimate with line items.

## Demo Flow

1. Select scenario on touchscreen (or leave on default)
2. Plug OBDLink MX+ into Pi's OBD2 port
3. Scan from phone — MX+ reads the Pi as a real car
4. Twilio SMS fires to demo phone with scan results
5. Estimate SMS arrives — tap APPROVE or CALL ME on touchscreen
6. Reply fires back to shop number

## Quick Start

### Simulation (laptop, no Pi hardware)
```bash
cd cfp-demo-car
pip install -r requirements.txt
cp .env.example .env
python main.py --simulate
```

Keyboard shortcuts in sim mode: `C` = connect, `D` = disconnect, `E` = estimate, `ESC` = quit.

### Production (Raspberry Pi 5)
```bash
ssh s10skeleton@crimsonforgedemo.local
cd /home/s10skeleton/cfp-demo
python main.py
```

### VS Code Remote SSH
```
Ctrl+Shift+P → "Remote-SSH: Connect to Host"
→ s10skeleton@crimsonforgedemo.local
```

### Autostart
```bash
sudo systemctl enable cfp-ui cfp-obd
sudo systemctl start cfp-ui cfp-obd
```

## Project Structure

```
cfp-demo-car/
├── main.py              # Startup orchestrator (--simulate flag)
├── config.py            # 5 demo scenarios with all vehicle/estimate data
├── state.py             # Shared state broker via state.json
├── obd_emulator.py      # CAN bus OBD2 responder (0x7DF → 0x7E8)
├── twilio_trigger.py    # Outbound SMS on scanner connect
├── twilio_server.py     # Flask webhook for inbound SMS + reply
├── ui_app.py            # Pygame touchscreen UI (4 screens)
├── screens/             # Screen module stubs
├── assets/              # Logo + fonts
├── systemd/             # Service files for Pi autostart
└── requirements.txt
```

## UI Screens

- **Home** — 5 scenario cards, tap to select, crimson highlight on active
- **Live View** — Auto-shows on MX+ connect, VIN/DTCs/PIDs, pulsing banner
- **Settings** — Twilio credentials, reboot/shutdown controls
- **Estimate** — SMS thread UI with repair line items, APPROVE/CALL ME buttons

## Tech Stack

Python 3.12 · Pygame · python-can (socketcan) · Flask · Twilio · Pillow
