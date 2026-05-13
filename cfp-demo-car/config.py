"""
config.py
CFP Demo Car — Scenario Data Store
All 5 demo vehicle/fault scenarios used by the OBD emulator and UI.

MOTOR Sandbox vehicles active — swap back to original VINs after
demo video recording is complete.
"""

SCENARIOS = [
    {
        # MOTOR Sandbox: 2012 Ford F-150
        # VCdb Base Vehicle ID: 118906  MOTOR Vehicle ID: 26332
        "index": 0,
        "label": "S1",
        "year": 2012,
        "make": "Ford",
        "model": "F-150",
        "vehicle": "2012 Ford F-150",
        "vin": "1FTFW1ET1CFA84056",
        "customer": "Marcus Webb",
        "complaint": "Check engine light on, rough idle, poor fuel economy",
        "dtcs": ["P0420", "P0171"],
        "dtc_descriptions": {
            "P0420": "Catalyst System Efficiency Below Threshold",
            "P0171": "System Too Lean Bank 1"
        },
        "ai_summary": "catalytic efficiency fault possibly related to prior O2 sensor repair",
        "rpm": "0C1A",
        "coolant": "7B",
        "throttle": "00",
        "o2_voltage": "44",
        "freeze_frame": "4101",
        "has_fault": True,
        "scenario_type": "fault",
        "ui_color": "fault",
        "rpm_value":        790,
        "coolant_c":        83,
        "throttle_pct":     0,
        "speed_kph":        0,
        "engine_load_pct":  22,
        "iat_c":            28,
        "o2_raw":           0x44,
    },
    {
        # MOTOR Sandbox: 2009 Chevrolet Silverado 1500
        # VCdb Base Vehicle ID: 30027  MOTOR Vehicle ID: 20680
        "index": 1,
        "label": "S2",
        "year": 2009,
        "make": "Chevrolet",
        "model": "Silverado 1500",
        "vehicle": "2009 Chevrolet Silverado 1500",
        "vin": "1GCEK29079E143364",
        "customer": "James Kowalski",
        "complaint": "Misfire at highway speed, intermittent — no CEL yet",
        "dtcs": ["P0302", "P0316"],
        "dtc_descriptions": {
            "P0302": "Cylinder 2 Misfire Detected",
            "P0316": "Misfire Detected on Startup"
        },
        "ai_summary": "cylinder 2 coil-on-plug or spark plug failure — pending fault before CEL triggered",
        "rpm": "0BB8",
        "coolant": "78",
        "throttle": "00",
        "o2_voltage": "3C",
        "freeze_frame": "4101",
        "has_fault": True,
        "scenario_type": "fault",
        "ui_color": "fault",
        "rpm_value":        750,
        "coolant_c":        80,
        "throttle_pct":     0,
        "speed_kph":        0,
        "engine_load_pct":  20,
        "iat_c":            26,
        "o2_raw":           0x3C,
    },
    {
        # MOTOR Sandbox: 2010 Honda Civic
        # VCdb Base Vehicle ID: 95946  MOTOR Vehicle ID: 22124
        "index": 2,
        "label": "S3",
        "year": 2010,
        "make": "Honda",
        "model": "Civic",
        "vehicle": "2010 Honda Civic",
        "vin": "19XFA1F51AE028415",
        "customer": "Sarah Chen",
        "complaint": "Slight fuel smell, rough cold start",
        "dtcs": ["P0087", "P0093"],
        "dtc_descriptions": {
            "P0087": "Fuel Rail/System Pressure Too Low",
            "P0093": "Fuel System Large Leak Detected"
        },
        "ai_summary": "fuel system pressure fault — recommend fuel pressure test and injector inspection",
        "rpm": "0C80",
        "coolant": "76",
        "throttle": "00",
        "o2_voltage": "50",
        "freeze_frame": "4101",
        "has_fault": True,
        "scenario_type": "fault",
        "ui_color": "fault",
        "rpm_value":        800,
        "coolant_c":        79,
        "throttle_pct":     0,
        "speed_kph":        0,
        "engine_load_pct":  24,
        "iat_c":            27,
        "o2_raw":           0x50,
    },
    {
        # MOTOR Sandbox: 2010 Nissan Altima
        # VCdb Base Vehicle ID: 95980  MOTOR Vehicle ID: 22156
        "index": 3,
        "label": "S4",
        "year": 2010,
        "make": "Nissan",
        "model": "Altima",
        "vehicle": "2010 Nissan Altima",
        "vin": "1N4AL2AP6AN555869",
        "customer": "Derek Owens",
        "complaint": "Transmission shudder 40-50 mph, no codes",
        "dtcs": [],
        "dtc_descriptions": {},
        "ai_summary": "no DTCs — complaint-only intake. CVT shudder pattern common on this generation. Recommend CVT fluid service and inspection.",
        "rpm": "0D48",
        "coolant": "7D",
        "throttle": "00",
        "o2_voltage": "48",
        "freeze_frame": "",
        "has_fault": False,
        "scenario_type": "clean",
        "ui_color": "clean",
        "rpm_value":        850,
        "coolant_c":        85,
        "throttle_pct":     0,
        "speed_kph":        0,
        "engine_load_pct":  18,
        "iat_c":            25,
        "o2_raw":           0x48,
    },
    {
        # MOTOR Sandbox: 2010 Toyota Camry
        # VCdb Base Vehicle ID: 30402  MOTOR Vehicle ID: 20957
        "index": 4,
        "label": "S5",
        "year": 2010,
        "make": "Toyota",
        "model": "Camry",
        "vehicle": "2010 Toyota Camry",
        "vin": "4T4BF3EK8AR074927",
        "customer": "Amy Torres",
        "complaint": "Routine oil change + inspection",
        "dtcs": [],
        "dtc_descriptions": {},
        "ai_summary": "clean vehicle — no faults detected. Maintenance recommendations generated based on mileage and service history.",
        "rpm": "0C00",
        "coolant": "7A",
        "throttle": "00",
        "o2_voltage": "40",
        "freeze_frame": "",
        "has_fault": False,
        "scenario_type": "maintenance",
        "ui_color": "clean",
        "rpm_value":        768,
        "coolant_c":        82,
        "throttle_pct":     0,
        "speed_kph":        0,
        "engine_load_pct":  20,
        "iat_c":            24,
        "o2_raw":           0x40,
    }
]

# UI color mapping
SCENARIO_UI_COLORS = {
    "fault": "fault",
    "clean": "clean",
    "maintenance": "clean"
}

def get_scenario(index: int) -> dict:
    """Return scenario by index. Clamps to valid range."""
    return SCENARIOS[max(0, min(index, len(SCENARIOS) - 1))]

def get_scenario_count() -> int:
    return len(SCENARIOS)
