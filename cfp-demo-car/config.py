"""
config.py
CFP Demo Car — Scenario Data Store
All 5 demo vehicle/fault scenarios used by the OBD emulator and UI.
"""

SCENARIOS = [
    {
        "index": 0,
        "label": "S1",
        "year": 2019,
        "make": "Chevrolet",
        "model": "Malibu",
        "vehicle": "2019 Chevrolet Malibu",
        "vin": "1G1ZD5ST4KF123456",
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
        "estimate": {
            "greeting": "Hi Marcus! Your 2019 Malibu has been diagnosed.",
            "intro":    "Here's what we recommend:",
            "items": [
                {
                    "name":   "Upstream O2 Sensor Replacement",
                    "parts":  89.00,
                    "labor":  120.00,
                    "note":   "Likely cause of P0420 + P0171"
                },
                {
                    "name":   "Catalytic Converter Inspection",
                    "parts":  0.00,
                    "labor":  45.00,
                    "note":   "Confirm cat health post O2 repair"
                },
            ],
            "total":    254.00,
            "footer":   "Reply APPROVE or CALL ME",
        },
    },
    {
        "index": 1,
        "label": "S2",
        "year": 2021,
        "make": "Ford",
        "model": "F-150",
        "vehicle": "2021 Ford F-150",
        "vin": "1FTFW1ET5MFA12345",
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
        "estimate": {
            "greeting": "Hi James! Your 2021 F-150 has been diagnosed.",
            "intro":    "Here's what we recommend:",
            "items": [
                {
                    "name":   "Spark Plug Replacement — Cyl 2",
                    "parts":  24.00,
                    "labor":  85.00,
                    "note":   "Primary suspect for P0302"
                },
                {
                    "name":   "Coil-on-Plug Boot Inspection",
                    "parts":  0.00,
                    "labor":  35.00,
                    "note":   "Rule out COP failure"
                },
            ],
            "total":    144.00,
            "footer":   "Reply APPROVE or CALL ME",
        },
    },
    {
        "index": 2,
        "label": "S3",
        "year": 2020,
        "make": "Honda",
        "model": "CR-V",
        "vehicle": "2020 Honda CR-V",
        "vin": "5J6RW2H59LA012345",
        "customer": "Sarah Chen",
        "complaint": "Oil dilution concern, slight fuel smell",
        "dtcs": ["P0087", "P0093"],
        "dtc_descriptions": {
            "P0087": "Fuel Rail/System Pressure Too Low",
            "P0093": "Fuel System Large Leak Detected"
        },
        "ai_summary": "fuel system pressure fault consistent with known CR-V oil dilution TSB — recommend TSB review",
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
        "estimate": {
            "greeting": "Hi Sarah! Your 2020 CR-V has been diagnosed.",
            "intro":    "Here's what we recommend:",
            "items": [
                {
                    "name":   "Fuel System Pressure Test",
                    "parts":  0.00,
                    "labor":  65.00,
                    "note":   "Confirm P0087 root cause"
                },
                {
                    "name":   "Honda Oil Dilution TSB Review",
                    "parts":  0.00,
                    "labor":  45.00,
                    "note":   "Known CR-V issue — check TSB"
                },
            ],
            "total":    110.00,
            "footer":   "Reply APPROVE or CALL ME",
        },
    },
    {
        "index": 3,
        "label": "S4",
        "year": 2022,
        "make": "RAM",
        "model": "1500",
        "vehicle": "2022 RAM 1500",
        "vin": "1C6SRFFT5NN123456",
        "customer": "Derek Owens",
        "complaint": "Transmission shudder 45-55 mph, no codes",
        "dtcs": [],
        "dtc_descriptions": {},
        "ai_summary": "no DTCs — complaint-only intake. Known 8HP75 torque converter shudder pattern. Recommend fluid service and converter inspection.",
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
        "estimate": {
            "greeting": "Hi Derek! Your 2022 RAM 1500 has been checked.",
            "intro":    "No fault codes found. Based on your complaint:",
            "items": [
                {
                    "name":   "Transmission Fluid Service",
                    "parts":  65.00,
                    "labor":  85.00,
                    "note":   "Addresses 8HP75 shudder pattern"
                },
                {
                    "name":   "Torque Converter Inspection",
                    "parts":  0.00,
                    "labor":  55.00,
                    "note":   "Confirm shudder source"
                },
            ],
            "total":    205.00,
            "footer":   "Reply APPROVE or CALL ME",
        },
    },
    {
        "index": 4,
        "label": "S5",
        "year": 2023,
        "make": "Toyota",
        "model": "Camry",
        "vehicle": "2023 Toyota Camry",
        "vin": "4T1C11AK5PU123456",
        "customer": "Amy Torres",
        "complaint": "Routine oil change + 90k service",
        "dtcs": [],
        "dtc_descriptions": {},
        "ai_summary": "clean vehicle — no faults. Maintenance recommendations generated. Service summary SMS sent to customer.",
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
        "estimate": {
            "greeting": "Hi Amy! Your 2023 Camry is in great shape.",
            "intro":    "Here's your 90k service estimate:",
            "items": [
                {
                    "name":   "Full Synthetic Oil Change",
                    "parts":  42.00,
                    "labor":  25.00,
                    "note":   "0W-20 full synthetic"
                },
                {
                    "name":   "90k Inspection Service",
                    "parts":  0.00,
                    "labor":  89.00,
                    "note":   "Brakes, fluids, filters, belts"
                },
            ],
            "total":    156.00,
            "footer":   "Reply APPROVE or CALL ME",
        },
    }
]

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
