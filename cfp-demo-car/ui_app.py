"""
ui_app.py
CFP Demo Car — Pygame Touchscreen UI
480x320 · 3.5" XPT2046 display (Pi) or desktop window (simulate)
"""

import os
import sys
import time
import pygame
import datetime
from state import read_state, set_scenario_index, get_scenario_index, write_state
from config import SCENARIOS, get_scenario

# —— Constants ————————————————————————————————————————————————————————————————
DISPLAY_W   = 480
DISPLAY_H   = 320
HEADER_H    = 32
FOOTER_H    = 36
CONTENT_TOP = HEADER_H
CONTENT_H   = DISPLAY_H - HEADER_H - FOOTER_H
CARD_H      = 46
CARD_MARGIN = 4
CARD_X      = 8
CARD_W      = DISPLAY_W - 16

SCREEN_HOME     = 0
SCREEN_LIVE     = 1
SCREEN_SETTINGS = 2
SCREEN_ESTIMATE = 3

COLORS = {
    "bg":           (10,  10,  10),
    "card_bg":      (26,  26,  26),
    "card_active":  (40,  10,  10),
    "crimson":      (234, 24,  35),
    "crimson_dark": (186, 13,  32),
    "blue":         (52,  137, 230),
    "cyan":         (74,  204, 254),
    "white":        (255, 255, 255),
    "gray":         (160, 160, 160),
    "dark_gray":    (55,  55,  55),
    "green":        (50,  200, 100),
    "black":        (0,   0,   0),
}

# —— Helpers ——————————————————————————————————————————————————————————————————

def draw_rect_outline(surface, color, rect, width=1, radius=4):
    pygame.draw.rect(surface, color, rect, width, border_radius=radius)

def draw_rect_filled(surface, color, rect, radius=4):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_text(surface, text, font, color, x, y, max_width=None):
    """Draw text. Truncate with ellipsis if max_width set."""
    if max_width:
        while font.size(text)[0] > max_width and len(text) > 4:
            text = text[:-2] + "\u2026"
    surf = font.render(text, True, color)
    surface.blit(surf, (x, y))
    return surf.get_width()

def draw_header(surface, fonts, state, current_screen):
    """Draw top header bar — CFP branding + connection status."""
    pygame.draw.rect(surface, (18, 18, 18), (0, 0, DISPLAY_W, HEADER_H))
    pygame.draw.line(surface, COLORS["crimson"], (0, HEADER_H - 1), (DISPLAY_W, HEADER_H - 1), 1)

    draw_text(surface, "\u2b21 CRIMSONFORGE", fonts["header"], COLORS["crimson"], 10, 8)

    # Connection status dot + label
    connected = state.get("connected", False)
    dot_color = COLORS["cyan"] if connected else COLORS["green"]
    status_text = "CONNECTED" if connected else "READY"
    status_color = COLORS["cyan"] if connected else COLORS["green"]

    pygame.draw.circle(surface, dot_color, (DISPLAY_W - 90, HEADER_H // 2), 5)
    draw_text(surface, status_text, fonts["small"], status_color, DISPLAY_W - 80, 10)

def draw_footer_button(surface, fonts, text, rect, color, text_color=None):
    """Draw a footer action button."""
    text_color = text_color or COLORS["white"]
    draw_rect_filled(surface, color, rect, radius=4)
    label = fonts["label"].render(text, True, text_color)
    lx = rect[0] + (rect[2] - label.get_width()) // 2
    ly = rect[1] + (rect[3] - label.get_height()) // 2
    surface.blit(label, (lx, ly))

# —— Screen: HOME ————————————————————————————————————————————————————————————

def draw_home(surface, fonts, state, touch_feedback=None):
    """
    Home screen — 5 scenario cards.
    touch_feedback: index of card being pressed (for highlight animation)
    """
    surface.fill(COLORS["bg"])
    draw_header(surface, fonts, state, SCREEN_HOME)

    active_idx = state.get("scenario_index", 0)

    for i, scenario in enumerate(SCENARIOS):
        y = CONTENT_TOP + i * (CARD_H + CARD_MARGIN) + CARD_MARGIN
        rect = pygame.Rect(CARD_X, y, CARD_W, CARD_H)

        # Card background
        is_active = (i == active_idx)
        is_pressed = (touch_feedback == i)
        bg_color = COLORS["card_active"] if is_active else COLORS["card_bg"]
        if is_pressed:
            bg_color = (60, 15, 15)
        draw_rect_filled(surface, bg_color, rect, radius=4)

        # Active card — crimson left border bar
        if is_active:
            bar = pygame.Rect(CARD_X, y, 3, CARD_H)
            pygame.draw.rect(surface, COLORS["crimson"], bar, border_radius=2)
            border_color = COLORS["crimson"]
        else:
            border_color = COLORS["dark_gray"]
        draw_rect_outline(surface, border_color, rect, width=1, radius=4)

        # Scenario label (S1, S2...)
        label_x = CARD_X + 10
        draw_text(surface, scenario["label"], fonts["label"], COLORS["gray"], label_x, y + 8)

        # Vehicle name
        vehicle_x = label_x + 28
        vehicle_color = COLORS["white"] if is_active else COLORS["gray"]
        draw_text(surface, scenario["vehicle"], fonts["body"], vehicle_color,
                  vehicle_x, y + 7, max_width=220)

        # DTC badges or CLEAN badge
        badge_x = DISPLAY_W - CARD_X - 10
        if scenario["dtcs"]:
            for dtc in reversed(scenario["dtcs"]):
                badge_text = dtc
                badge_surf = fonts["small"].render(badge_text, True, COLORS["crimson"])
                badge_w = badge_surf.get_width() + 8
                badge_x -= badge_w + 4
                badge_rect = pygame.Rect(badge_x, y + 8, badge_w, 18)
                draw_rect_filled(surface, (50, 8, 10), badge_rect, radius=3)
                draw_rect_outline(surface, COLORS["crimson_dark"], badge_rect, width=1, radius=3)
                surface.blit(badge_surf, (badge_x + 4, y + 9))
            # Customer name on second line
            draw_text(surface, scenario["customer"], fonts["small"], COLORS["gray"],
                      vehicle_x, y + 26, max_width=200)
        else:
            # Clean badge
            clean_label = "\u2713 CLEAN" if scenario["scenario_type"] == "clean" else "\u2713 MAINT"
            badge_surf = fonts["small"].render(clean_label, True, COLORS["cyan"])
            badge_w = badge_surf.get_width() + 8
            badge_x -= badge_w + 4
            badge_rect = pygame.Rect(badge_x, y + 8, badge_w, 18)
            draw_rect_filled(surface, (8, 40, 50), badge_rect, radius=3)
            draw_rect_outline(surface, COLORS["cyan"], badge_rect, width=1, radius=3)
            surface.blit(badge_surf, (badge_x + 4, y + 9))
            draw_text(surface, scenario["customer"], fonts["small"], COLORS["gray"],
                      vehicle_x, y + 26, max_width=200)

    # Footer buttons
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    draw_footer_button(surface, fonts, "\u2699 SETTINGS",
                       (CARD_X, footer_y, 120, btn_h),
                       COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "\u23fb SHUTDOWN",
                       (DISPLAY_W - CARD_X - 120, footer_y, 120, btn_h),
                       (40, 10, 10), COLORS["crimson"])

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, DISPLAY_H - FOOTER_H), (DISPLAY_W, DISPLAY_H - FOOTER_H), 1)

def get_home_touch(x, y, state):
    """
    Returns action dict for a touch at (x, y) on home screen.
    Possible actions: {'type': 'select', 'index': N}
                      {'type': 'settings'}
                      {'type': 'shutdown'}
                      None
    """
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8

    # Settings button
    if pygame.Rect(CARD_X, footer_y, 120, btn_h).collidepoint(x, y):
        return {"type": "settings"}

    # Shutdown button
    if pygame.Rect(DISPLAY_W - CARD_X - 120, footer_y, 120, btn_h).collidepoint(x, y):
        return {"type": "shutdown"}

    # Scenario cards
    for i in range(len(SCENARIOS)):
        card_y = CONTENT_TOP + i * (CARD_H + CARD_MARGIN) + CARD_MARGIN
        if pygame.Rect(CARD_X, card_y, CARD_W, CARD_H).collidepoint(x, y):
            return {"type": "select", "index": i}

    return None

# —— Screen: LIVE VIEW ———————————————————————————————————————————————————————

def draw_live(surface, fonts, state, pulse_frame=0):
    """
    Live view screen — shown when MX+ is connected.
    pulse_frame: 0-59 counter for pulsing animation on connected banner.
    """
    surface.fill(COLORS["bg"])
    draw_header(surface, fonts, state, SCREEN_LIVE)

    scenario = get_scenario(state.get("scenario_index", 0))

    # Pulsing connected banner
    pulse_alpha = int(160 + 95 * abs((pulse_frame % 60) / 30 - 1))
    banner_color = (
        int(52  * pulse_alpha / 255),
        int(137 * pulse_alpha / 255),
        int(230 * pulse_alpha / 255),
    )
    banner_rect = pygame.Rect(CARD_X, CONTENT_TOP + 6, CARD_W, 24)
    draw_rect_filled(surface, (8, 20, 40), banner_rect, radius=3)
    draw_rect_outline(surface, banner_color, banner_rect, width=1, radius=3)
    draw_text(surface, "\u2601 OBDLINK MX+ CONNECTED",
              fonts["label"], banner_color,
              banner_rect.x + 10, banner_rect.y + 5)

    # Vehicle info block
    info_y = CONTENT_TOP + 38
    draw_text(surface, scenario["vehicle"], fonts["title"], COLORS["white"], CARD_X + 4, info_y)
    draw_text(surface, f"VIN: {scenario['vin']}", fonts["small"], COLORS["gray"],
              CARD_X + 4, info_y + 20)
    draw_text(surface, f"CUSTOMER: {scenario['customer']}", fonts["small"], COLORS["gray"],
              CARD_X + 4, info_y + 34)

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (CARD_X, info_y + 50), (DISPLAY_W - CARD_X, info_y + 50), 1)

    # DTCs or clean status
    dtc_y = info_y + 58
    if scenario["dtcs"]:
        draw_text(surface, "ACTIVE CODES", fonts["label"], COLORS["crimson"], CARD_X + 4, dtc_y)
        for j, dtc in enumerate(scenario["dtcs"]):
            desc = scenario["dtc_descriptions"].get(dtc, "")
            code_y = dtc_y + 18 + j * 20
            draw_text(surface, dtc, fonts["dtc"], COLORS["crimson"], CARD_X + 4, code_y)
            draw_text(surface, desc, fonts["small"], COLORS["gray"],
                      CARD_X + 52, code_y + 2, max_width=290)
    else:
        draw_text(surface, "\u2713 NO FAULT CODES", fonts["label"], COLORS["cyan"], CARD_X + 4, dtc_y)
        draw_text(surface, scenario["ai_summary"], fonts["small"], COLORS["gray"],
                  CARD_X + 4, dtc_y + 20, max_width=CARD_W)

    # Live PID strip
    pid_y = DISPLAY_H - FOOTER_H - 28
    pygame.draw.line(surface, COLORS["dark_gray"],
                     (CARD_X, pid_y - 4), (DISPLAY_W - CARD_X, pid_y - 4), 1)
    pid_items = [
        ("RPM", "790"),
        ("COOLANT", "195\u00b0F"),
        ("THROTTLE", "0%"),
        ("O2", "0.44V"),
    ]
    pid_col_w = CARD_W // len(pid_items)
    for k, (label, val) in enumerate(pid_items):
        px = CARD_X + k * pid_col_w + 4
        draw_text(surface, label, fonts["small"], COLORS["gray"], px, pid_y)
        draw_text(surface, val, fonts["label"], COLORS["white"], px, pid_y + 13)

    # SMS sent confirmation
    if state.get("sms_sent", False):
        draw_text(surface, f"\u2709 SMS SENT  \u2192  {os.getenv('DEMO_PHONE_NUMBER', 'demo phone')}",
                  fonts["small"], COLORS["cyan"], CARD_X + 4, pid_y - 21)

    # Footer
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    draw_footer_button(surface, fonts, "\u2190 BACK",
                       (CARD_X, footer_y, 100, btn_h), COLORS["dark_gray"])
    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, DISPLAY_H - FOOTER_H), (DISPLAY_W, DISPLAY_H - FOOTER_H), 1)

def get_live_touch(x, y):
    """Returns action for touch on live screen."""
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    if pygame.Rect(CARD_X, footer_y, 100, btn_h).collidepoint(x, y):
        return {"type": "back"}
    return None

# —— Screen: SETTINGS ————————————————————————————————————————————————————————

def draw_settings(surface, fonts, state, input_fields, active_field=None):
    """
    Settings screen — Twilio config + system controls.
    input_fields: dict of field_name -> current string value
    active_field: currently selected field name or None
    """
    surface.fill(COLORS["bg"])
    draw_header(surface, fonts, state, SCREEN_SETTINGS)

    title_y = CONTENT_TOP + 8
    draw_text(surface, "\u2699 SETTINGS", fonts["title"], COLORS["white"], CARD_X + 4, title_y)

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (CARD_X, title_y + 22), (DISPLAY_W - CARD_X, title_y + 22), 1)

    fields = [
        ("demo_phone",    "DEMO PHONE",   "DEMO_PHONE_NUMBER"),
        ("twilio_sid",    "TWILIO SID",   "TWILIO_ACCOUNT_SID"),
        ("twilio_token",  "AUTH TOKEN",   "TWILIO_AUTH_TOKEN"),
        ("twilio_from",   "FROM NUMBER",  "TWILIO_FROM_NUMBER"),
    ]

    field_y = title_y + 30
    field_h = 30
    field_gap = 6

    for fname, flabel, fenv in fields:
        is_active = (active_field == fname)
        val = input_fields.get(fname, os.getenv(fenv, ""))

        # Mask token field
        display_val = val
        if fname == "twilio_token" and val and not is_active:
            display_val = val[:6] + "\u2022" * 8 + val[-4:] if len(val) > 10 else "\u2022" * 10

        label_surf = fonts["small"].render(flabel, True, COLORS["gray"])
        surface.blit(label_surf, (CARD_X + 4, field_y + 2))

        field_rect = pygame.Rect(CARD_X + 95, field_y, CARD_W - 95, field_h - 4)
        field_bg = (35, 35, 35) if is_active else (20, 20, 20)
        border_color = COLORS["blue"] if is_active else COLORS["dark_gray"]
        draw_rect_filled(surface, field_bg, field_rect, radius=3)
        draw_rect_outline(surface, border_color, field_rect, width=1, radius=3)
        draw_text(surface, display_val, fonts["small"], COLORS["white"],
                  field_rect.x + 6, field_rect.y + 8, max_width=field_rect.width - 12)

        field_y += field_h + field_gap

    # Footer buttons
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    draw_footer_button(surface, fonts, "\u2190 BACK",
                       (CARD_X, footer_y, 90, btn_h), COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "\U0001f4be SAVE",
                       (CARD_X + 100, footer_y, 90, btn_h), COLORS["blue"])
    draw_footer_button(surface, fonts, "\U0001f504 REBOOT",
                       (CARD_X + 200, footer_y, 100, btn_h), COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "\u23fb SHUTDOWN",
                       (DISPLAY_W - CARD_X - 120, footer_y, 120, btn_h),
                       (40, 10, 10), COLORS["crimson"])

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, DISPLAY_H - FOOTER_H), (DISPLAY_W, DISPLAY_H - FOOTER_H), 1)

def get_settings_touch(x, y, fields_config):
    """Returns action for touch on settings screen."""
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8

    if pygame.Rect(CARD_X, footer_y, 90, btn_h).collidepoint(x, y):
        return {"type": "back"}
    if pygame.Rect(CARD_X + 100, footer_y, 90, btn_h).collidepoint(x, y):
        return {"type": "save"}
    if pygame.Rect(CARD_X + 200, footer_y, 100, btn_h).collidepoint(x, y):
        return {"type": "reboot"}
    if pygame.Rect(DISPLAY_W - CARD_X - 120, footer_y, 120, btn_h).collidepoint(x, y):
        return {"type": "shutdown"}

    # Field tap
    fields = ["demo_phone", "twilio_sid", "twilio_token", "twilio_from"]
    title_y = CONTENT_TOP + 8
    field_y = title_y + 30
    field_h = 30
    field_gap = 6
    for fname in fields:
        field_rect = pygame.Rect(CARD_X + 95, field_y, CARD_W - 95, field_h - 4)
        if field_rect.collidepoint(x, y):
            return {"type": "field_tap", "field": fname}
        field_y += field_h + field_gap

    return None

# —— Screen: ESTIMATE (SMS Thread) ———————————————————————————————————————————

def draw_estimate(surface, fonts, state, reply_bubble_text="", approval_sent=False):
    """
    Estimate screen — looks like a phone SMS thread.
    CFP message comes in as a left-aligned gray bubble.
    Customer reply (APPROVE/CALL ME) appears as right-aligned crimson bubble.
    """
    surface.fill(COLORS["bg"])

    scenario = get_scenario(state.get("scenario_index", 0))
    estimate = scenario.get("estimate", {})

    # Header
    pygame.draw.rect(surface, (18, 18, 18), (0, 0, DISPLAY_W, HEADER_H))
    pygame.draw.line(surface, COLORS["crimson"],
                     (0, HEADER_H - 1), (DISPLAY_W, HEADER_H - 1), 1)
    draw_text(surface, "\u2b21 CRIMSONFORGE", fonts["header"], COLORS["crimson"], 10, 8)
    draw_text(surface, "\u2709 ESTIMATE", fonts["small"], COLORS["cyan"],
              DISPLAY_W - 88, 10)

    # Contact bar
    contact_y = HEADER_H + 4
    draw_text(surface, scenario["customer"], fonts["label"], COLORS["white"],
              CARD_X + 4, contact_y)
    draw_text(surface, scenario["vehicle"], fonts["small"], COLORS["gray"],
              CARD_X + 4, contact_y + 16)

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, contact_y + 30), (DISPLAY_W, contact_y + 30), 1)

    # CFP message bubble (left-aligned, dark gray)
    bubble_top  = contact_y + 36
    bubble_x    = CARD_X
    bubble_maxw = 310
    bubble_pad  = 8

    # Build message lines
    lines = []
    lines.append(estimate.get("greeting", f"Hi {scenario['customer']}!"))
    lines.append(estimate.get("intro", "Here's your estimate:"))
    lines.append("")

    items = estimate.get("items", [])
    for item in items:
        lines.append(item["name"])
        parts = item.get("parts", 0)
        labor = item.get("labor", 0)
        if parts > 0:
            lines.append(f"  Parts ${parts:.0f}  \u00b7  Labor ${labor:.0f}")
        else:
            lines.append(f"  Labor ${labor:.0f}")

    lines.append("")
    lines.append(f"TOTAL  ${estimate.get('total', 0):.2f}")
    lines.append("")
    lines.append(estimate.get("footer", "Reply APPROVE or CALL ME"))

    # Measure bubble height
    line_h      = 14
    bubble_h    = len(lines) * line_h + bubble_pad * 2
    bubble_rect = pygame.Rect(bubble_x, bubble_top,
                              bubble_maxw + bubble_pad * 2, bubble_h)

    # Clamp bubble so it doesn't overlap footer
    footer_y   = DISPLAY_H - FOOTER_H
    max_bub_h  = footer_y - bubble_top - 28
    if bubble_h > max_bub_h:
        bubble_h    = max_bub_h
        bubble_rect = pygame.Rect(bubble_x, bubble_top,
                                  bubble_maxw + bubble_pad * 2, bubble_h)

    draw_rect_filled(surface, (35, 35, 35), bubble_rect, radius=10)

    # Draw message lines inside bubble (clip to bubble)
    surface.set_clip(bubble_rect.inflate(-bubble_pad, -bubble_pad))
    text_y = bubble_top + bubble_pad
    for line in lines:
        if text_y + line_h > bubble_top + bubble_h - bubble_pad:
            break
        if line == "":
            text_y += 5
            continue
        # Highlight TOTAL line
        if line.startswith("TOTAL"):
            draw_text(surface, line, fonts["label"], COLORS["white"],
                      bubble_x + bubble_pad, text_y)
        elif line.startswith("  "):
            draw_text(surface, line.strip(), fonts["small"], COLORS["gray"],
                      bubble_x + bubble_pad + 10, text_y)
        elif line == estimate.get("footer", ""):
            draw_text(surface, line, fonts["small"], COLORS["cyan"],
                      bubble_x + bubble_pad, text_y)
        else:
            draw_text(surface, line, fonts["body"], COLORS["white"],
                      bubble_x + bubble_pad, text_y)
        text_y += line_h
    surface.set_clip(None)

    # Timestamp
    ts = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
    draw_text(surface, ts, fonts["small"], COLORS["dark_gray"],
              bubble_x + 4, bubble_rect.bottom + 3)

    # Customer reply bubble (right-aligned, crimson)
    if reply_bubble_text and approval_sent:
        reply_surf  = fonts["label"].render(reply_bubble_text, True, COLORS["white"])
        rb_w        = reply_surf.get_width() + 20
        rb_h        = 26
        rb_x        = DISPLAY_W - CARD_X - rb_w
        rb_y        = bubble_rect.bottom + 20
        rb_rect     = pygame.Rect(rb_x, rb_y, rb_w, rb_h)
        draw_rect_filled(surface, COLORS["crimson_dark"], rb_rect, radius=10)
        surface.blit(reply_surf, (rb_x + 10, rb_y + 5))

        # Confirmation text
        confirm_text = "\u2713 Sent to shop!" if reply_bubble_text == "APPROVE" \
                       else "\u260e Shop will call you."
        draw_text(surface, confirm_text, fonts["small"], COLORS["cyan"],
                  DISPLAY_W - CARD_X - fonts["small"].size(confirm_text)[0] - 4,
                  rb_rect.bottom + 4)

    # Footer buttons
    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, DISPLAY_H - FOOTER_H), (DISPLAY_W, DISPLAY_H - FOOTER_H), 1)
    footer_btn_y = DISPLAY_H - FOOTER_H + 4
    btn_h        = FOOTER_H - 8

    if not approval_sent:
        draw_footer_button(surface, fonts, "\u2713 APPROVE",
                           (CARD_X, footer_btn_y, 150, btn_h),
                           COLORS["crimson_dark"], COLORS["white"])
        draw_footer_button(surface, fonts, "\u260e CALL ME",
                           (CARD_X + 160, footer_btn_y, 140, btn_h),
                           (20, 40, 70), COLORS["white"])
        draw_footer_button(surface, fonts, "\u2190 BACK",
                           (DISPLAY_W - CARD_X - 90, footer_btn_y, 90, btn_h),
                           COLORS["dark_gray"])
    else:
        draw_footer_button(surface, fonts, "\u2713 SENT",
                           (CARD_X, footer_btn_y, 150, btn_h),
                           COLORS["dark_gray"], COLORS["gray"])


def get_estimate_touch(x, y):
    """Returns action for touch on estimate screen."""
    footer_btn_y = DISPLAY_H - FOOTER_H + 4
    btn_h        = FOOTER_H - 8

    if pygame.Rect(CARD_X, footer_btn_y, 150, btn_h).collidepoint(x, y):
        return {"type": "approve"}
    if pygame.Rect(CARD_X + 160, footer_btn_y, 140, btn_h).collidepoint(x, y):
        return {"type": "callme"}
    if pygame.Rect(DISPLAY_W - CARD_X - 90, footer_btn_y, 90, btn_h).collidepoint(x, y):
        return {"type": "back"}
    return None


def _fire_reply(action: str, simulate: bool):
    """Fire reply to CFP via webhook or simulate."""
    import urllib.request
    import json

    payload = json.dumps({"action": action}).encode()
    port    = int(os.getenv("WEBHOOK_PORT", "5000"))

    if simulate:
        print(f"\n[UI] Customer reply: {action}")
        print(f"[UI] (In production this fires POST to localhost:{port}/sms/reply)")
        return

    try:
        req = urllib.request.Request(
            f"http://localhost:{port}/sms/reply",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        print(f"[UI] Reply webhook error: {e}")

# —— Shutdown Confirm Overlay ————————————————————————————————————————————————

def draw_shutdown_confirm(surface, fonts):
    """Draw a centered confirmation overlay for shutdown."""
    overlay = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    box = pygame.Rect(80, 100, 320, 120)
    draw_rect_filled(surface, (25, 25, 25), box, radius=8)
    draw_rect_outline(surface, COLORS["crimson"], box, width=1, radius=8)

    draw_text(surface, "SHUT DOWN?", fonts["title"], COLORS["white"],
              box.x + 20, box.y + 18)
    draw_text(surface, "Device will power off safely.", fonts["small"],
              COLORS["gray"], box.x + 20, box.y + 46)

    draw_footer_button(surface, fonts, "CANCEL",
                       (box.x + 20, box.y + 76, 120, 30), COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "SHUT DOWN",
                       (box.x + 160, box.y + 76, 140, 30),
                       COLORS["crimson_dark"], COLORS["white"])

def get_shutdown_confirm_touch(x, y):
    box_x, box_y = 80, 100
    if pygame.Rect(box_x + 20, box_y + 76, 120, 30).collidepoint(x, y):
        return {"type": "cancel"}
    if pygame.Rect(box_x + 160, box_y + 76, 140, 30).collidepoint(x, y):
        return {"type": "confirm"}
    return None

# —— Main UI Loop ————————————————————————————————————————————————————————————

def run_ui(simulate: bool = False):
    """Main UI entry point — called from main.py."""
    import subprocess

    pygame.init()
    pygame.display.set_caption("CFP Demo Car \u2014 Simulation")

    if simulate:
        screen = pygame.display.set_mode((DISPLAY_W, DISPLAY_H))
    else:
        screen = pygame.display.set_mode(
            (DISPLAY_W, DISPLAY_H),
            pygame.FULLSCREEN | pygame.NOFRAME
        )
        pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()

    # Init fonts after pygame.init()
    fonts = {
        "header": pygame.font.SysFont("monospace", 15, bold=True),
        "title":  pygame.font.SysFont("monospace", 17, bold=True),
        "body":   pygame.font.SysFont("monospace", 13),
        "small":  pygame.font.SysFont("monospace", 11),
        "label":  pygame.font.SysFont("monospace", 12, bold=True),
        "dtc":    pygame.font.SysFont("monospace", 14, bold=True),
        "large":  pygame.font.SysFont("monospace", 22, bold=True),
    }

    current_screen = SCREEN_HOME
    pulse_frame    = 0
    touch_feedback = None
    feedback_timer = 0
    show_shutdown_confirm = False

    # Estimate screen state
    approval_sent     = False
    approval_timer    = 0
    reply_bubble_text = ""

    # Settings input fields (loaded from env on open)
    settings_fields = {}
    active_field    = None

    # State polling
    last_state    = read_state()
    state_poll_ms = 500   # poll state.json every 500ms
    last_poll     = pygame.time.get_ticks()

    running = True
    while running:
        now = pygame.time.get_ticks()

        # —— Poll shared state ————————————————————————————————————————————
        if now - last_poll > state_poll_ms:
            last_poll  = now
            last_state = read_state()

            # Auto-transition to LIVE when connected
            if last_state.get("connected") and current_screen == SCREEN_HOME:
                current_screen = SCREEN_LIVE
                pulse_frame    = 0

            # Auto-transition back to HOME when disconnected
            if not last_state.get("connected") and current_screen == SCREEN_LIVE:
                current_screen = SCREEN_HOME

            # Auto-transition to ESTIMATE when show_estimate is set
            if last_state.get("show_estimate") and current_screen not in (SCREEN_ESTIMATE,):
                current_screen    = SCREEN_ESTIMATE
                approval_sent     = False
                approval_timer    = 0
                reply_bubble_text = ""

        # —— Events ———————————————————————————————————————————————————————
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Simulate connect/disconnect with keyboard in sim mode
                if simulate:
                    if event.key == pygame.K_c and current_screen != SCREEN_SETTINGS:
                        from state import set_connected
                        set_connected(True)
                        last_state = read_state()
                    if event.key == pygame.K_d and current_screen != SCREEN_SETTINGS:
                        from state import set_connected
                        set_connected(False)
                        last_state = read_state()
                    # Press E in simulate mode to trigger estimate screen
                    if event.key == pygame.K_e:
                        write_state({
                            "show_estimate":     True,
                            "inbound_sms":       "",
                            "estimate_approved": False,
                        })
                        last_state = read_state()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if show_shutdown_confirm:
                    action = get_shutdown_confirm_touch(mx, my)
                    if action:
                        if action["type"] == "confirm":
                            pygame.quit()
                            if not simulate:
                                subprocess.run(["sudo", "shutdown", "-h", "now"])
                            sys.exit(0)
                        elif action["type"] == "cancel":
                            show_shutdown_confirm = False
                    continue

                if current_screen == SCREEN_HOME:
                    action = get_home_touch(mx, my, last_state)
                    if action:
                        if action["type"] == "select":
                            touch_feedback = action["index"]
                            feedback_timer = now
                            set_scenario_index(action["index"])
                            last_state = read_state()
                        elif action["type"] == "settings":
                            current_screen  = SCREEN_SETTINGS
                            settings_fields = {}
                            active_field    = None
                        elif action["type"] == "shutdown":
                            show_shutdown_confirm = True

                elif current_screen == SCREEN_LIVE:
                    action = get_live_touch(mx, my)
                    if action:
                        if action["type"] == "back":
                            current_screen = SCREEN_HOME

                elif current_screen == SCREEN_SETTINGS:
                    action = get_settings_touch(mx, my, settings_fields)
                    if action:
                        if action["type"] == "back":
                            current_screen = SCREEN_HOME
                        elif action["type"] == "shutdown":
                            show_shutdown_confirm = True
                        elif action["type"] == "reboot":
                            if not simulate:
                                subprocess.run(["sudo", "reboot"])
                        elif action["type"] == "save":
                            _save_settings(settings_fields)
                            current_screen = SCREEN_HOME
                        elif action["type"] == "field_tap":
                            active_field = action["field"]

                elif current_screen == SCREEN_ESTIMATE:
                    action = get_estimate_touch(mx, my)
                    if action:
                        if action["type"] in ("approve", "callme"):
                            label = "APPROVE" if action["type"] == "approve" else "CALL ME"
                            reply_bubble_text = label
                            approval_sent     = True
                            approval_timer    = now
                            _fire_reply(label, simulate)
                        elif action["type"] == "back":
                            write_state({"show_estimate": False})
                            current_screen = SCREEN_HOME

            # Keyboard input for settings fields (simulate mode convenience)
            if current_screen == SCREEN_SETTINGS and active_field:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        settings_fields[active_field] = \
                            settings_fields.get(active_field, "")[:-1]
                    elif event.key == pygame.K_RETURN:
                        active_field = None
                    elif event.unicode:
                        settings_fields[active_field] = \
                            settings_fields.get(active_field, "") + event.unicode

        # —— Clear touch feedback after 150ms ————————————————————————————
        if touch_feedback is not None and now - feedback_timer > 150:
            touch_feedback = None

        # —— Draw —————————————————————————————————————————————————————————
        if current_screen == SCREEN_HOME:
            draw_home(screen, fonts, last_state, touch_feedback)
        elif current_screen == SCREEN_LIVE:
            draw_live(screen, fonts, last_state, pulse_frame)
            pulse_frame = (pulse_frame + 1) % 60
        elif current_screen == SCREEN_SETTINGS:
            draw_settings(screen, fonts, last_state, settings_fields, active_field)
        elif current_screen == SCREEN_ESTIMATE:
            draw_estimate(screen, fonts, last_state, reply_bubble_text, approval_sent)
            # Return to home 2.5 seconds after approval sent
            if approval_sent and now - approval_timer > 2500:
                approval_sent     = False
                reply_bubble_text = ""
                write_state({"show_estimate": False, "estimate_approved": True})
                current_screen = SCREEN_HOME

        if show_shutdown_confirm:
            draw_shutdown_confirm(screen, fonts)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit(0)

# —— Settings Save Helper ————————————————————————————————————————————————————

def _save_settings(fields: dict):
    """
    Write updated settings to .env file.
    Only writes fields that have been changed (non-empty).
    """
    env_map = {
        "demo_phone":   "DEMO_PHONE_NUMBER",
        "twilio_sid":   "TWILIO_ACCOUNT_SID",
        "twilio_token": "TWILIO_AUTH_TOKEN",
        "twilio_from":  "TWILIO_FROM_NUMBER",
    }
    env_path = os.path.join(os.path.dirname(__file__), ".env")

    # Read existing lines
    existing = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    # Merge updates
    for field_name, env_key in env_map.items():
        val = fields.get(field_name, "").strip()
        if val:
            existing[env_key] = val

    # Write back
    with open(env_path, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    print("[SETTINGS] .env updated")
