"""
ui_app.py
CFP Demo Car — Pygame Touchscreen UI
800x480 · 5" HDMI display (Pi) or desktop window (simulate)
"""

import os
import sys
import pygame
from state import read_state, set_scenario_index
from config import SCENARIOS, get_scenario

# —— Constants ————————————————————————————————————————————————————————————————
DISPLAY_W   = 800
DISPLAY_H   = 480
HEADER_H    = 48
FOOTER_H    = 54
CONTENT_TOP = HEADER_H
CONTENT_H   = DISPLAY_H - HEADER_H - FOOTER_H
CARD_H      = 68
CARD_MARGIN = 6
CARD_X      = 12
CARD_W      = DISPLAY_W - 24

SCREEN_HOME     = 0
SCREEN_LIVE     = 1
SCREEN_SETTINGS = 2

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

    pygame.draw.circle(surface, dot_color, (DISPLAY_W - 130, HEADER_H // 2), 7)
    draw_text(surface, status_text, fonts["small"], status_color, DISPLAY_W - 118, 16)

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
    footer_y = DISPLAY_H - FOOTER_H + 6
    btn_h = FOOTER_H - 12
    draw_footer_button(surface, fonts, "\u2699 SETTINGS",
                       (CARD_X, footer_y, 180, btn_h),
                       COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "\u23fb SHUTDOWN",
                       (DISPLAY_W - CARD_X - 180, footer_y, 180, btn_h),
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
    footer_y = DISPLAY_H - FOOTER_H + 6
    btn_h = FOOTER_H - 12

    # Settings button
    if pygame.Rect(CARD_X, footer_y, 180, btn_h).collidepoint(x, y):
        return {"type": "settings"}

    # Shutdown button
    if pygame.Rect(DISPLAY_W - CARD_X - 180, footer_y, 180, btn_h).collidepoint(x, y):
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
    pid_y = DISPLAY_H - FOOTER_H - 42
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

    # Footer
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    draw_footer_button(surface, fonts, "\u2190 BACK",
                       (CARD_X, footer_y, 150, btn_h), COLORS["dark_gray"])
    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, DISPLAY_H - FOOTER_H), (DISPLAY_W, DISPLAY_H - FOOTER_H), 1)

def get_live_touch(x, y):
    """Returns action for touch on live screen."""
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    if pygame.Rect(CARD_X, footer_y, 150, btn_h).collidepoint(x, y):
        return {"type": "back"}
    return None

# —— Screen: SETTINGS ————————————————————————————————————————————————————————

def draw_settings(surface, fonts, state):
    """Settings screen — system controls only (reboot/shutdown)."""
    surface.fill(COLORS["bg"])
    draw_header(surface, fonts, state, SCREEN_SETTINGS)

    title_y = CONTENT_TOP + 8
    draw_text(surface, "\u2699 SETTINGS", fonts["title"], COLORS["white"], CARD_X + 4, title_y)

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (CARD_X, title_y + 22), (DISPLAY_W - CARD_X, title_y + 22), 1)

    info_y = title_y + 60
    draw_text(surface, "System Controls", fonts["label"], COLORS["gray"], CARD_X + 4, info_y)

    # Footer buttons
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8
    draw_footer_button(surface, fonts, "\u2190 BACK",
                       (CARD_X, footer_y, 150, btn_h), COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "\U0001f504 REBOOT",
                       (CARD_X + 166, footer_y, 180, btn_h), COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "\u23fb SHUTDOWN",
                       (DISPLAY_W - CARD_X - 180, footer_y, 180, btn_h),
                       (40, 10, 10), COLORS["crimson"])

    pygame.draw.line(surface, COLORS["dark_gray"],
                     (0, DISPLAY_H - FOOTER_H), (DISPLAY_W, DISPLAY_H - FOOTER_H), 1)

def get_settings_touch(x, y):
    """Returns action for touch on settings screen."""
    footer_y = DISPLAY_H - FOOTER_H + 4
    btn_h = FOOTER_H - 8

    if pygame.Rect(CARD_X, footer_y, 150, btn_h).collidepoint(x, y):
        return {"type": "back"}
    if pygame.Rect(CARD_X + 166, footer_y, 180, btn_h).collidepoint(x, y):
        return {"type": "reboot"}
    if pygame.Rect(DISPLAY_W - CARD_X - 180, footer_y, 180, btn_h).collidepoint(x, y):
        return {"type": "shutdown"}

    return None

# —— Shutdown Confirm Overlay ————————————————————————————————————————————————

def draw_shutdown_confirm(surface, fonts):
    """Draw a centered confirmation overlay for shutdown."""
    overlay = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    box = pygame.Rect(200, 160, 400, 160)
    draw_rect_filled(surface, (25, 25, 25), box, radius=8)
    draw_rect_outline(surface, COLORS["crimson"], box, width=1, radius=8)

    draw_text(surface, "SHUT DOWN?", fonts["title"], COLORS["white"],
              box.x + 20, box.y + 18)
    draw_text(surface, "Device will power off safely.", fonts["small"],
              COLORS["gray"], box.x + 20, box.y + 46)

    draw_footer_button(surface, fonts, "CANCEL",
                       (box.x + 24, box.y + 100, 160, 42), COLORS["dark_gray"])
    draw_footer_button(surface, fonts, "SHUT DOWN",
                       (box.x + 216, box.y + 100, 160, 42),
                       COLORS["crimson_dark"], COLORS["white"])

def get_shutdown_confirm_touch(x, y):
    box_x, box_y = 200, 160
    if pygame.Rect(box_x + 24, box_y + 100, 160, 42).collidepoint(x, y):
        return {"type": "cancel"}
    if pygame.Rect(box_x + 216, box_y + 100, 160, 42).collidepoint(x, y):
        return {"type": "confirm"}
    return None

# —— Main UI Loop ————————————————————————————————————————————————————————————

def run_ui(simulate: bool = False):
    """Main UI entry point — called from main.py."""
    import subprocess

    pygame.init()
    pygame.display.set_caption("CFP Demo Car")

    if simulate:
        screen = pygame.display.set_mode((DISPLAY_W, DISPLAY_H))
    else:
        screen = pygame.display.set_mode(
            (DISPLAY_W, DISPLAY_H),
            pygame.FULLSCREEN
        )
        pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()

    # Init fonts after pygame.init()
    fonts = {
        "header": pygame.font.SysFont("monospace", 22, bold=True),
        "title":  pygame.font.SysFont("monospace", 24, bold=True),
        "body":   pygame.font.SysFont("monospace", 19),
        "small":  pygame.font.SysFont("monospace", 16),
        "label":  pygame.font.SysFont("monospace", 18, bold=True),
        "dtc":    pygame.font.SysFont("monospace", 20, bold=True),
        "large":  pygame.font.SysFont("monospace", 32, bold=True),
    }

    current_screen = SCREEN_HOME
    pulse_frame    = 0
    touch_feedback = None
    feedback_timer = 0
    show_shutdown_confirm = False

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

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if show_shutdown_confirm:
                    action = get_shutdown_confirm_touch(mx, my)
                    if action:
                        if action["type"] == "confirm":
                            pygame.quit()
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
                            current_screen = SCREEN_SETTINGS
                        elif action["type"] == "shutdown":
                            show_shutdown_confirm = True

                elif current_screen == SCREEN_LIVE:
                    action = get_live_touch(mx, my)
                    if action:
                        if action["type"] == "back":
                            current_screen = SCREEN_HOME

                elif current_screen == SCREEN_SETTINGS:
                    action = get_settings_touch(mx, my)
                    if action:
                        if action["type"] == "back":
                            current_screen = SCREEN_HOME
                        elif action["type"] == "shutdown":
                            show_shutdown_confirm = True
                        elif action["type"] == "reboot":
                            if not simulate:
                                subprocess.run(["sudo", "reboot"])

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
            draw_settings(screen, fonts, last_state)

        if show_shutdown_confirm:
            draw_shutdown_confirm(screen, fonts)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit(0)

