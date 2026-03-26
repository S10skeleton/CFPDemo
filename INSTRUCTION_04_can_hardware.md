# INSTRUCTION 04 — CFP Demo Car: MCP2515 Wiring, SPI1 Config & CAN Bus Bring-Up
**CrimsonForgePro · Demo Hardware · OBD2 CAN Emulator — Hardware Integration**

---

## OVERVIEW

This instruction covers everything needed to go from simulation mode
to real hardware OBD2 emulation:

1. **Pi config** — enable SPI1, add MCP2515 overlay
2. **Wiring verification** — confirm all GPIO connections are correct
3. **CAN interface bring-up** — bring `can1` up and verify it's alive
4. **Kernel module check** — confirm MCP2515 driver loaded
5. **OBD emulator test** — verify CAN bus sends/receives before MX+ plugs in
6. **MX+ live test** — plug in scanner, verify VIN + DTC population in CFP
7. **Switch to production mode** — remove `--simulate` flag

**Do NOT modify:** `ui_app.py`, `config.py`, `screens/`

---

## ⚠️ WIRING — DO THIS BEFORE RUNNING ANY CODE

**Power the Pi OFF before wiring. Never connect GPIO with Pi powered on.**

---

## COMPLETE WIRING DIAGRAM

### Overview
```
Pi 5 GPIO                Level Converter              MCP2515
─────────────────        ─────────────────────        ───────────────────
GPIO20 (Pin 38) MOSI ── LV1 ────────────── HV1 ───── SI
GPIO19 (Pin 35) MISO ── LV2 ────────────── HV2 ───── SO
GPIO21 (Pin 40) SCLK ── LV3 ────────────── HV3 ───── SCK
GPIO18 (Pin 12) CE0  ── LV4 ────────────── HV4 ───── CS
Pin 17  (3.3V)       ── LV (ref)
Pin 2   (5V)         ───────────────────── HV (ref) ── VCC (MCP2515)
Pin 20  (GND)        ── GND ────────────── GND ─────── GND (MCP2515)
GPIO26  (Pin 37) INT ───────────────────────────────── INT (direct, no shifter)
```

### OBD2 Pigtail — MCP2515
```
OBD2 Pigtail Wire    →    MCP2515 Terminal
─────────────────         ───────────────────
Pin 6  (CAN High)    →    CANH
Pin 14 (CAN Low)     →    CANL
Pin 4  (Chassis GND) →    GND (share with Pi GND bus)
Pin 5  (Signal GND)  →    GND (share with Pi GND bus)
Pin 16 (Battery +)   →    Leave floating — do not connect
All other pins       →    Leave unconnected
```

### Power (Battery Mode)
```
18650 Pack (+) → Master Switch → Buck Converter IN+
18650 Pack (-) → Buck Converter IN-
Buck OUT 5V    → Pi USB-C (or GPIO Pin 2/4)
Buck OUT GND   → Pi GND (Pin 6)
```

> **Pre-set the buck converter output to exactly 5.1V before connecting to Pi.**
> Use a multimeter on the output terminals while adjusting the trim pot.
> Too high = fry the Pi. Take 30 seconds to verify first.

---

## PART 1 — UPDATE `/boot/firmware/config.txt`

SSH into the Pi and edit the config:

```bash
sudo nano /boot/firmware/config.txt
```

Navigate to the `[all]` section at the bottom. It currently has the
waveshare display lines. Add the following lines AFTER the existing
waveshare lines but still inside `[all]`:

```ini
# MCP2515 CAN controller on SPI1
dtoverlay=spi1-1cs
dtoverlay=mcp2515-can1,oscillator=8000000,interrupt=26
```

The bottom of your config.txt `[all]` section should look like this when done:

```ini
[all]
dtparam=spi=on
dtoverlay=waveshare35a
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 320 60 6 0 0 0
hdmi_drive=2
# MCP2515 CAN controller on SPI1
dtoverlay=spi1-1cs
dtoverlay=mcp2515-can1,oscillator=8000000,interrupt=26
```

Save with `Ctrl+X` → `Y` → `Enter`

Reboot:
```bash
sudo reboot
```

---

## PART 2 — VERIFY SPI1 AND CAN AFTER REBOOT

After reboot, SSH back in and verify:

```bash
# Should show spidev0.0 (display) AND spidev1.0 (MCP2515)
ls /dev/spi*

# Should show can1 in the list
ip link show | grep can

# Check MCP2515 loaded in kernel
dmesg | grep -i mcp251
dmesg | grep -i can1
```

**Expected output:**
```
/dev/spidev0.0  /dev/spidev1.0
4: can1: <NOARP,ECHO> mtu 16 ...
mcp251x spi1.0: MCP2515 successfully initialized
```

If `spidev1.0` is missing — the SPI1 overlay didn't load. Check config.txt for typos.
If `mcp251x` line is missing — the MCP2515 isn't responding, check physical wiring.

---

## PART 3 — BRING UP CAN1 INTERFACE

```bash
sudo ip link set can1 up type can bitrate 500000
ip link show can1
```

**Expected:**
```
can1: <NOARP,UP,LOWER_UP,ECHO> mtu 16 qdisc pfifo_fast state UP ...
    link/can
```

State should be `UP`. If it says `DOWN` or errors — physical wiring issue with MCP2515.

---

## PART 4 — ADD CAN1 AUTO-BRING-UP ON BOOT

Create a systemd network config so `can1` comes up automatically on boot:

```bash
sudo nano /etc/network/interfaces.d/can1
```

Add:
```
auto can1
iface can1 inet manual
    pre-up ip link set can1 type can bitrate 500000
    up ip link set can1 up
    down ip link set can1 down
```

Save with `Ctrl+X` → `Y` → `Enter`

Or alternatively add to `/etc/rc.local` before `exit 0`:
```bash
sudo nano /etc/rc.local
```
Add before `exit 0`:
```bash
/sbin/ip link set can1 up type can bitrate 500000
```

---

## PART 5 — TEST CAN BUS WITH candump

Install can-utils if not already installed:
```bash
sudo apt install -y can-utils
```

Open two SSH terminals simultaneously:

**Terminal 1 — listen:**
```bash
candump can1
```

**Terminal 2 — send a test frame:**
```bash
cansend can1 7DF#0201050000000000
```

**Expected in Terminal 1:**
```
can1  7DF   [8]  02 01 05 00 00 00 00 00
```

If you see the frame echo back — **CAN bus is alive and working.** ✓

If nothing appears — check CANH/CANL wiring between MCP2515 and OBD2 pigtail.

> **Note:** For the MX+ to communicate, both ends of the CAN bus need
> 120Ω termination resistors. The MCP2515 module has one built in.
> The MX+ has one built in. Together they provide the correct 60Ω
> differential termination for a two-node CAN network. No additional
> resistors needed.

---

## PART 6 — UPDATE `start_cfp.sh`

Once CAN bus is confirmed working, switch from simulate to production mode.

```bash
nano /home/s10skeleton/start_cfp.sh
```

Change:
```bash
#!/bin/bash
cd /home/s10skeleton/CFPDemo/cfp-demo-car
python3 main.py --simulate
```

To:
```bash
#!/bin/bash
# Bring up CAN interface
sudo /sbin/ip link set can1 up type can bitrate 500000 2>/dev/null || true

# Launch CFP Demo Car in production mode
cd /home/s10skeleton/CFPDemo/cfp-demo-car
DISPLAY=:0 python3 main.py
```

Save with `Ctrl+X` → `Y` → `Enter`

---

## PART 7 — UPDATE `systemd/cfp-obd.service`

The OBD emulator now needs to run as a separate service alongside the UI.
Update the service file:

```bash
nano /home/s10skeleton/CFPDemo/cfp-demo-car/systemd/cfp-obd.service
```

Replace contents with:
```ini
[Unit]
Description=CFP OBD2 CAN Bus Emulator
After=network.target
Wants=network.target

[Service]
ExecStartPre=/sbin/ip link set can1 up type can bitrate 500000
ExecStart=/usr/bin/python3 /home/s10skeleton/CFPDemo/cfp-demo-car/obd_emulator.py
Environment=CFP_SIMULATE=0
Restart=always
RestartSec=3
User=s10skeleton

[Install]
WantedBy=multi-user.target
```

Install and enable:
```bash
sudo cp /home/s10skeleton/CFPDemo/cfp-demo-car/systemd/cfp-obd.service \
        /etc/systemd/system/cfp-obd.service
sudo systemctl daemon-reload
sudo systemctl enable cfp-obd
sudo systemctl start cfp-obd
sudo systemctl status cfp-obd
```

---

## PART 8 — LIVE MX+ TEST PROCEDURE

With CAN bus confirmed working and production mode active:

**Step 1 — Set scenario on Pi touchscreen**
Tap S1 (2019 Malibu) → card highlights crimson

**Step 2 — Start OBD emulator**
```bash
sudo systemctl start cfp-obd
sudo journalctl -u cfp-obd -f
```
You should see:
```
[OBD] Starting CAN bus listener on can1...
[OBD] CAN bus ready. Waiting for OBD2 requests...
```

**Step 3 — Plug OBDLink MX+ into OBD2 pigtail**
On Pi terminal you should see:
```
[OBD] Scanner connected → 2019 Chevrolet Malibu
[TWILIO] SMS sent to [demo phone]
```
Pi screen should transition to Live View automatically.

**Step 4 — Open CFP on phone**
- Connect phone to OBDLink MX+ via Bluetooth
- Open CFP → New Repair Order
- Tap scan VIN
- VIN `1G1ZD5ST4KF123456` should populate
- Tap read codes → P0420, P0171 should appear

**Step 5 — Verify AI context**
- CFP Diagnostic AI should pre-load with vehicle + code context
- Ask: "What's the most likely root cause?"
- AI should reference catalytic efficiency + O2 sensor history

**Step 6 — Verify Twilio SMS**
- Demo phone should have received fault notification SMS
- Pi screen should show "✓ SMS SENT" confirmation

**Step 7 — Test estimate flow**
- In CFP, build a quick estimate and send to demo number
- Pi screen should transition to ESTIMATE screen
- Tap APPROVE on Pi
- CFP should receive approval reply

---

## PART 9 — VERIFY ALL 5 SCENARIOS

Rotate through all 5 scenarios on the Pi touchscreen and verify each:

| Scenario | Tap Card | Unplug/Replug MX+ | Expected DTCs | Expected SMS |
|---|---|---|---|---|
| S1 Malibu | ✓ | ✓ | P0420, P0171 | Fault notification |
| S2 F-150 | ✓ | ✓ | P0302, P0316 | Fault notification |
| S3 CR-V | ✓ | ✓ | P0087, P0093 | Fault notification |
| S4 RAM | ✓ | ✓ | No codes | Clean intake |
| S5 Camry | ✓ | ✓ | No codes | Maintenance summary |

> **Scenario switching:** Unplug MX+ between scenarios. Pi screen
> returns to Home after disconnect timeout (~5 seconds). Tap new
> scenario card, replug MX+.

---

## TROUBLESHOOTING

### MCP2515 not found in dmesg
```
Check: dtoverlay=mcp2515-can1,oscillator=8000000,interrupt=26 in config.txt
Check: GPIO18=CS, GPIO19=MISO, GPIO20=MOSI, GPIO21=SCLK, GPIO26=INT
Check: Level converter HV side powered from Pi 5V (Pin 2)
Check: Level converter LV side powered from Pi 3.3V (Pin 17)
Check: MCP2515 VCC connected to HV side of level converter output (5V)
```

### CAN1 comes up but no frames received
```
Check: CANH → OBD2 Pin 6, CANL → OBD2 Pin 14
Check: MCP2515 GND connected to Pi GND
Check: MX+ fully seated in OBD2 connector
Check: MX+ Bluetooth paired to phone and CFP open
```

### VIN populates but wrong vehicle
```
Check: state.json scenario_index matches expected scenario
Check: config.py VIN for that scenario index
Run: cat /home/s10skeleton/CFPDemo/cfp-demo-car/state.json
```

### Pi screen doesn't transition to Live View
```
Check: obd_emulator.py is running: systemctl status cfp-obd
Check: state.json "connected": true after MX+ plugs in
Check: ui_app.py polling interval (500ms) — may take up to 1 second
```

### Twilio SMS not sending
```
Check: .env file exists with correct credentials
Run: cat /home/s10skeleton/CFPDemo/cfp-demo-car/.env
Check: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER all set
Check: DEMO_PHONE_NUMBER set to your demo phone
```

---

## PRODUCTION MODE CHECKLIST

Before first real demo run:

- [ ] `candump can1` shows frames when MX+ plugged in
- [ ] VIN populates correctly in CFP for all 5 scenarios
- [ ] DTCs populate correctly (P0420/P0171 for Malibu etc.)
- [ ] Twilio SMS fires on connect for all scenarios
- [ ] Pi screen transitions Home → Live View on connect
- [ ] Pi screen transitions Live View → Home on disconnect
- [ ] Estimate screen appears when CFP sends estimate SMS
- [ ] APPROVE button fires reply back to CFP
- [ ] All 5 scenarios cycle correctly
- [ ] `start_cfp.sh` has `--simulate` removed
- [ ] `cfp-obd.service` enabled and starts on boot
- [ ] Clean shutdown from Settings screen works
- [ ] Full 9-step demo flow rehearsed end to end

---

## NOTES FOR CLAUDE CODE

- Only modify `start_cfp.sh`, `systemd/cfp-obd.service`,
  and `/boot/firmware/config.txt` in this instruction
- Do NOT modify `ui_app.py`, `obd_emulator.py`, or `config.py`
  unless a specific bug is identified during testing
- The `--simulate` removal in `start_cfp.sh` is the key production
  switch — everything else stays the same
- `obd_emulator.py` already has the full production CAN loop written
  from INSTRUCTION_03 — it just needs the hardware to be present
- If `ip link set can1 up` fails in the service ExecStartPre,
  the `|| true` prevents the service from failing to start

---

*INSTRUCTION 04 of N — CFP Demo Car*
*Next: INSTRUCTION_05 — Touch calibration, demo rehearsal polish,
boot splash screen, and V1 final checklist*
