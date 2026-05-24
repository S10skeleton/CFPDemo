# CFP Bench Tester

Windows desktop OBD2 emulator for testing ForgePilot features.

## Hardware Required
- DSD TECH SH-C31A USB CAN adapter (Candlelight firmware)
- USB to 12V boost converter -> OBD2 pigtail Pin 16
- OBD2 female pigtail (iKKEGOL)
- OBDLink MX+ scanner

## Wiring
```
SH-C31A terminal H   -> OBD2 Pin 6  (CAN High)
SH-C31A terminal L   -> OBD2 Pin 14 (CAN Low)
SH-C31A terminal GND -> OBD2 Pin 4/5 (GND)
12V boost OUT+       -> OBD2 Pin 16 (IGN+)
12V boost OUT-       -> OBD2 Pin 4/5 (GND, same bus)
```

## Usage
```
pip install -r requirements.txt
python bench_tester.py
```

## Simulate mode (no hardware)
```
python bench_tester.py --simulate
```
