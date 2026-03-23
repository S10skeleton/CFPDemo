# CFP Demo Car

Raspberry Pi 5 OBD2 vehicle emulator for CrimsonForgePro investor demos.
3.5" XPT2046 touchscreen UI · 5-scenario demo platform · Twilio SMS integration.

## Quick Start

### Development (laptop, no hardware)
```bash
pip install -r requirements.txt
cp .env.example .env        # fill in Twilio credentials
python main.py --simulate
```

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

### Autostart (Pi — run once)
```bash
sudo systemctl enable cfp-ui cfp-obd
sudo systemctl start cfp-ui cfp-obd
```

## Architecture
See `docs/CFP_DemoCar_BuildBible_v2.md` for full hardware spec,
GPIO wiring, SPI bus allocation, and 3D enclosure spec.

## Scenarios
| # | Vehicle | Type | DTCs |
|---|---------|------|------|
| 1 | 2019 Chevrolet Malibu | Fault | P0420, P0171 |
| 2 | 2021 Ford F-150 | Fault | P0302, P0316 |
| 3 | 2020 Honda CR-V | Fault | P0087, P0093 |
| 4 | 2022 RAM 1500 | Clean / Intake | None |
| 5 | 2023 Toyota Camry | Maintenance | None |
