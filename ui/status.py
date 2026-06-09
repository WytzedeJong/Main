import json
import os
from datetime import datetime

import pygame

try:
    import psutil
except ImportError:
    psutil = None

from settings import BASE_WIDTH

BATTERY_FILE = os.path.join("data", "battery.json")

COLOR_BATTERY_HIGH = (0, 0, 0)
COLOR_BATTERY_MID = (255, 200, 0)
COLOR_BATTERY_LOW = (220, 40, 40)
COLOR_BATTERY_CHARGING = (0, 120, 255)
COLOR_BATTERY_OUTLINE = (40, 40, 40)
COLOR_BATTERY_EMPTY = (220, 220, 220)



def _load_battery_pijuice():
    try:
        from pijuice import PiJuice
        pj = PiJuice(1, 0x14)
        charge = pj.status.GetChargeLevel()
        status = pj.status.GetStatus()
        if charge.get("error") == "NO_ERROR" and status.get("error") == "NO_ERROR":
            percent = max(0, min(100, int(charge["data"])))
            charging = status["data"].get("battery", "") in ("CHARGING_FROM_5V_IO", "CHARGING_FROM_IN")
            return {"percent": percent, "charging": charging}
    except Exception:
        pass
    return None


def _load_battery_waveshare_ups():

    CELL_COUNT = 1
    V_MAX = 4.20 * CELL_COUNT
    V_MIN = 3.00 * CELL_COUNT

    try:
        import smbus2
        bus = smbus2.SMBus(1)

        for addr in (0x42, 0x43):
            try:
                raw = bus.read_i2c_block_data(addr, 0x02, 2)
                raw_v = ((raw[0] << 8) | raw[1]) >> 3
                voltage = raw_v * 0.004

                if voltage < 0.5:
                    continue

                percent = int((voltage - V_MIN) / (V_MAX - V_MIN) * 100)
                percent = max(0, min(100, percent))
                charging = voltage >= (V_MAX - 0.05)
                bus.close()
                return {"percent": percent, "charging": charging}
            except OSError:
                continue

        bus.close()
    except Exception:
        pass
    return None


def _load_battery_sysfs():

    power_supply_path = "/sys/class/power_supply"
    if not os.path.isdir(power_supply_path):
        return None

    try:
        entries = os.listdir(power_supply_path)
    except OSError:
        return None

    battery_dirs = [
        e for e in entries
        if any(kw in e.upper() for kw in ("BAT", "BATT", "UPS", "LIPO", "BATTERY"))
    ]
    candidates = battery_dirs or entries  # fall back to all if none match

    for entry in candidates:
        base = os.path.join(power_supply_path, entry)
        cap_file = os.path.join(base, "capacity")
        status_file = os.path.join(base, "status")

        if not os.path.exists(cap_file):
            continue

        try:
            with open(cap_file) as f:
                percent = max(0, min(100, int(f.read().strip())))

            charging = False
            if os.path.exists(status_file):
                with open(status_file) as f:
                    charging = f.read().strip().lower() in ("charging", "full")

            return {"percent": percent, "charging": charging}
        except (OSError, ValueError):
            continue

    return None


def _load_battery_from_psutil():
    if psutil is None:
        return None
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    percent = battery.percent
    if percent is None:
        percent = 100
    percent = max(0, min(100, int(percent)))
    charging = bool(battery.power_plugged)
    return {"percent": percent, "charging": charging}


def _load_battery_from_file():
    default = {"percent": 100, "charging": False}
    if not os.path.exists(BATTERY_FILE):
        return default
    try:
        with open(BATTERY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        percent = int(data.get("percent", 100))
        percent = max(0, min(100, percent))
        charging = bool(data.get("charging", False))
        return {"percent": percent, "charging": charging}
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return default


def load_battery_status():

    for reader in (
        _load_battery_pijuice,
        _load_battery_waveshare_ups,
        _load_battery_sysfs,
        _load_battery_from_psutil,
    ):
        result = reader()
        if result is not None:
            return result

    return _load_battery_from_file()



def _battery_fill_color(percent, charging):
    if charging:
        return COLOR_BATTERY_CHARGING
    if percent < 15:
        return COLOR_BATTERY_LOW
    if percent <= 50:
        return COLOR_BATTERY_MID
    return COLOR_BATTERY_HIGH


def draw_battery_icon(surface, x, y, percent, charging, scale=1.0):
    body_w = int(26 * scale)
    body_h = int(12 * scale)
    tip_w = int(3 * scale)
    tip_h = int(6 * scale)
    pad = max(1, int(2 * scale))
    border = max(1, int(2 * scale))

    body = pygame.Rect(x, y, body_w, body_h)
    tip = pygame.Rect(body.right, y + (body_h - tip_h) // 2, tip_w, tip_h)

    pygame.draw.rect(surface, COLOR_BATTERY_EMPTY, body, border_radius=2)
    pygame.draw.rect(surface, COLOR_BATTERY_OUTLINE, body, border, border_radius=2)
    pygame.draw.rect(surface, COLOR_BATTERY_OUTLINE, tip, border_radius=1)

    inner = body.inflate(-pad * 2, -pad * 2)
    if charging:
        fill_w = inner.width
        fill_color = COLOR_BATTERY_CHARGING
    else:
        fill_w = max(0, int(inner.width * (percent / 100.0)))
        fill_color = _battery_fill_color(percent, charging)
    if fill_w > 0:
        fill_rect = pygame.Rect(inner.x, inner.y, fill_w, inner.height)
        pygame.draw.rect(surface, fill_color, fill_rect, border_radius=1)


def battery_icon_width(scale=1.0):
    return int(26 * scale) + int(3 * scale)


def draw_time_and_battery(surface, time_font, text_color, y=15, margin_right=15):
    status = load_battery_status()
    percent = status["percent"]
    charging = status["charging"]

    now = datetime.now().strftime("%H:%M")
    time_surf = time_font.render(now, True, text_color)
    time_w = time_surf.get_width()

    gap = 8
    batt_w = battery_icon_width()

    pct_font = pygame.font.SysFont("arial", max(10, time_font.get_height() - 8), bold=True)
    pct_surf = pct_font.render(f"{percent}%", True, text_color)
    pct_w = pct_surf.get_width()

    right_edge = BASE_WIDTH - margin_right
    time_x = right_edge - time_w
    pct_x = time_x - gap - pct_w
    batt_x = pct_x - gap - batt_w
    batt_y = y + max(0, (time_surf.get_height() - 12) // 2)

    draw_battery_icon(surface, batt_x, batt_y, percent, charging)
    surface.blit(pct_surf, (pct_x, y + (time_surf.get_height() - pct_surf.get_height()) // 2))
    surface.blit(time_surf, (time_x, y))