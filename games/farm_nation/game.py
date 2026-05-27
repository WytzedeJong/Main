import json
import math
import os
import time

import pygame

from core.input_manager import InputHandler
from core.scene import Scene
from settings import BASE_HEIGHT, BASE_WIDTH
from ui.lockscreen import LockScreen


def game_name():
    return f"Farm Nation", FarmNationGame


ANIMALS = [
    {"id": "chicken", "name": "Kip", "base_income": 0.1, "base_cost": 15, "color": (255, 220, 100)},
    {"id": "cow", "name": "Koe", "base_income": 1.0, "base_cost": 100, "color": (160, 100, 60)},
    {"id": "pig", "name": "Varken", "base_income": 4.0, "base_cost": 500, "color": (255, 180, 200)},
    {"id": "sheep", "name": "Schaap", "base_income": 18.0, "base_cost": 2500, "color": (230, 230, 230)},
    {"id": "horse", "name": "Paard", "base_income": 80.0, "base_cost": 12000, "color": (140, 90, 50)},
    {"id": "goat", "name": "Geit", "base_income": 350.0, "base_cost": 55000, "color": (200, 200, 180)},
    {"id": "duck", "name": "Eend", "base_income": 1500.0, "base_cost": 250000, "color": (100, 180, 255)},
]

UPGRADES = [
    {
        "id": "strong_hands",
        "name": "Sterke Handen",
        "desc": "+1 per klik",
        "base_cost": 50,
        "cost_mult": 1.55,
        "max_level": 100,
    },
    {
        "id": "golden_touch",
        "name": "Gouden Vingers",
        "desc": "+15% klik bonus",
        "base_cost": 250,
        "cost_mult": 1.65,
        "max_level": 50,
    },
    {
        "id": "animal_whisper",
        "name": "Dierenfluisteraar",
        "desc": "+10% dieren inkomen",
        "base_cost": 500,
        "cost_mult": 1.7,
        "max_level": 50,
    },
    {
        "id": "mega_barn",
        "name": "Mega Schuur",
        "desc": "+25% al het inkomen",
        "base_cost": 5000,
        "cost_mult": 2.0,
        "max_level": 25,
    },
]

TABS = ["Klik", "Dieren", "Upgrades", "Reset"]
BUY_MODES = [1, 10, 100]
MAX_OFFLINE_SECONDS = 24 * 3600


def format_money(value):
    value = float(value)
    if value < 0:
        return f"-${format_money(-value)[1:]}"
    if value < 1000:
        if value == int(value):
            return f"${int(value)}"
        return f"${value:.2f}"
    suffixes = ["", "K", "M", "B", "T", "Qa", "Qi"]
    tier = 0
    while value >= 1000 and tier < len(suffixes) - 1:
        value /= 1000
        tier += 1
    if value >= 100:
        return f"${value:.1f}{suffixes[tier]}"
    if value >= 10:
        return f"${value:.2f}{suffixes[tier]}"
    return f"${value:.3f}{suffixes[tier]}"


class FloatingText:
    def __init__(self, x, y, text, color, lifetime=0.9):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = lifetime
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        self.y -= 28 * dt

    @property
    def alive(self):
        return self.age < self.lifetime

    def draw(self, surface, font):
        alpha = max(0, 255 - int(255 * (self.age / self.lifetime)))
        label = font.render(self.text, True, self.color)
        label.set_alpha(alpha)
        surface.blit(label, (int(self.x - label.get_width() / 2), int(self.y)))


class FarmNationGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.input_handler = InputHandler()

        self.title_font = pygame.font.SysFont("arial", 22, bold=True)
        self.money_font = pygame.font.SysFont("arial", 20, bold=True)
        self.ui_font = pygame.font.SysFont("arial", 14)
        self.small_font = pygame.font.SysFont("arial", 11)
        self.big_font = pygame.font.SysFont("arial", 18, bold=True)

        self.user = self._get_user()
        self.save_path = self._save_path()

        self.tab = 0
        self.selected_row = 0
        self.buy_mode_index = 0
        self.reset_confirm = False

        self.money = 0.0
        self.total_clicks = 0
        self.animal_counts = {a["id"]: 0 for a in ANIMALS}
        self.upgrade_levels = {u["id"]: 0 for u in UPGRADES}
        self.last_timestamp = time.time()

        self.click_pulse = 0.0
        self.flash_timer = 0.0
        self.toast_message = ""
        self.toast_timer = 0.0
        self.purchase_flash_row = -1
        self.purchase_flash_timer = 0.0
        self.floating_texts = []
        self._autosave_timer = 0.0

        self._load_save()
        self._apply_offline_income()

        self.click_rect = pygame.Rect(12, 52, 200, BASE_HEIGHT - 100)
        self.list_rect = pygame.Rect(220, 52, BASE_WIDTH - 232, BASE_HEIGHT - 100)

    def _get_user(self):
        user = getattr(self.manager, "current_user", None)
        if user:
            return user
        try:
            lock = LockScreen(self.manager)
            return lock.get_user() or "guest"
        except Exception:
            return "guest"

    def _user_key(self):
        if isinstance(self.user, dict):
            return str(self.user.get("name", "guest"))
        return str(self.user)

    def _save_path(self):
        folder = os.path.dirname(__file__)
        safe_name = "".join(c if c.isalnum() else "_" for c in self._user_key())
        return os.path.join(folder, f"save_{safe_name}.json")

    def _animal_cost(self, animal_id, amount=1):
        animal = next(a for a in ANIMALS if a["id"] == animal_id)
        count = self.animal_counts[animal_id]
        total = 0.0
        for _ in range(amount):
            total += animal["base_cost"] * (1.12 ** count)
            count += 1
        return total

    def _upgrade_cost(self, upgrade_id, amount=1):
        upgrade = next(u for u in UPGRADES if u["id"] == upgrade_id)
        level = self.upgrade_levels[upgrade_id]
        total = 0.0
        for _ in range(amount):
            if level >= upgrade["max_level"]:
                return None
            total += upgrade["base_cost"] * (upgrade["cost_mult"] ** level)
            level += 1
        return total

    def _click_value(self):
        hands = self.upgrade_levels["strong_hands"]
        golden = self.upgrade_levels["golden_touch"]
        mega = self.upgrade_levels["mega_barn"]
        base = 1.0 + hands
        base *= 1.0 + golden * 0.15
        base *= 1.0 + mega * 0.25
        return base

    def _income_per_second(self):
        whisper = self.upgrade_levels["animal_whisper"]
        mega = self.upgrade_levels["mega_barn"]
        total = 0.0
        for animal in ANIMALS:
            count = self.animal_counts[animal["id"]]
            income = count * animal["base_income"]
            income *= 1.0 + whisper * 0.10
            income *= 1.0 + mega * 0.25
            total += income
        return total

    def _buy_mode(self):
        return BUY_MODES[self.buy_mode_index]

    def _max_affordable_bulk(self, single_cost_fn, item_id):
        mode = self._buy_mode()
        cost = single_cost_fn(item_id, mode)
        if cost is not None and self.money >= cost:
            return mode
        for fallback in (10, 1):
            if fallback <= mode:
                cost = single_cost_fn(item_id, fallback)
                if cost is not None and self.money >= cost:
                    return fallback
        return 0

    def _show_toast(self, message, duration=1.4):
        self.toast_message = message
        self.toast_timer = duration

    def _apply_offline_income(self):
        now = time.time()
        elapsed = max(0.0, now - self.last_timestamp)
        elapsed = min(elapsed, MAX_OFFLINE_SECONDS)
        income = self._income_per_second() * elapsed
        if income > 0:
            self.money += income
            mins = int(elapsed // 60)
            if mins >= 1:
                self._show_toast(f"Offline: +{format_money(income)} ({mins}m)", 2.2)
        self.last_timestamp = now

    def _load_save(self):
        if not os.path.exists(self.save_path):
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        self.money = float(data.get("money", 0))
        self.total_clicks = int(data.get("total_clicks", 0))
        self.last_timestamp = float(data.get("last_timestamp", time.time()))
        for animal in ANIMALS:
            self.animal_counts[animal["id"]] = int(
                data.get("animals", {}).get(animal["id"], 0)
            )
        for upgrade in UPGRADES:
            self.upgrade_levels[upgrade["id"]] = int(
                data.get("upgrades", {}).get(upgrade["id"], 0)
            )

    def _save_game(self):
        data = {
            "money": self.money,
            "total_clicks": self.total_clicks,
            "last_timestamp": time.time(),
            "animals": dict(self.animal_counts),
            "upgrades": dict(self.upgrade_levels),
        }
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _reset_game(self):
        self.money = 0.0
        self.total_clicks = 0
        self.animal_counts = {a["id"]: 0 for a in ANIMALS}
        self.upgrade_levels = {u["id"]: 0 for u in UPGRADES}
        self.last_timestamp = time.time()
        self.selected_row = 0
        self.reset_confirm = False
        self.floating_texts.clear()
        try:
            if os.path.exists(self.save_path):
                os.remove(self.save_path)
        except OSError:
            pass
        self._show_toast("Boerderij gereset!", 1.8)

    def _do_click(self, x=None, y=None):
        value = self._click_value()
        self.money += value
        self.total_clicks += 1
        self.click_pulse = 1.0
        self.flash_timer = 0.12

        fx = x if x is not None else self.click_rect.centerx
        fy = y if y is not None else self.click_rect.centery - 20
        self.floating_texts.append(
            FloatingText(fx, fy, f"+{format_money(value)}", (255, 240, 120))
        )

    def _buy_animals(self, index):
        animal = ANIMALS[index]
        amount = self._max_affordable_bulk(self._animal_cost, animal["id"])
        if amount <= 0:
            self._show_toast("Niet genoeg geld!", 1.0)
            return False
        cost = self._animal_cost(animal["id"], amount)
        self.money -= cost
        self.animal_counts[animal["id"]] += amount
        self.purchase_flash_row = index
        self.purchase_flash_timer = 0.35
        self._show_toast(f"Gekocht: {amount}x {animal['name']}!", 1.3)
        return True

    def _buy_upgrade(self, index):
        upgrade = UPGRADES[index]
        level = self.upgrade_levels[upgrade["id"]]
        if level >= upgrade["max_level"]:
            self._show_toast("Max level bereikt!", 1.0)
            return False

        amount = self._buy_mode()
        affordable = 0
        for try_amount in (amount, 10, 1):
            cost = self._upgrade_cost(upgrade["id"], try_amount)
            if cost is not None and self.money >= cost:
                affordable = try_amount
                break
        if affordable <= 0:
            self._show_toast("Niet genoeg geld!", 1.0)
            return False

        cost = self._upgrade_cost(upgrade["id"], affordable)
        self.money -= cost
        self.upgrade_levels[upgrade["id"]] += affordable
        self.purchase_flash_row = index
        self.purchase_flash_timer = 0.35
        self._show_toast(f"Upgrade: {upgrade['name']} x{affordable}!", 1.3)
        return True

    def _list_item_count(self):
        if self.tab == 1:
            return len(ANIMALS)
        if self.tab == 2:
            return len(UPGRADES)
        if self.tab == 3:
            return 2
        return 0

    def _clamp_selection(self):
        count = self._list_item_count()
        if count <= 0:
            self.selected_row = 0
            return
        self.selected_row = max(0, min(self.selected_row, count - 1))

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._save_game()
            from ui.Games_menu import Game_Menu

            self.manager.set_scene(Game_Menu(self.manager))

    def _handle_input(self):
        inp = self.input_handler

        if self.tab in (1, 2):
            if inp.just_pressed("LEFT"):
                self._cycle_buy_mode(-1)
            if inp.just_pressed("RIGHT"):
                self._cycle_buy_mode(1)
        else:
            if inp.just_pressed("LEFT"):
                self.tab = (self.tab - 1) % len(TABS)
                self.selected_row = 0
                self.reset_confirm = False
            if inp.just_pressed("RIGHT"):
                self.tab = (self.tab + 1) % len(TABS)
                self.selected_row = 0
                self.reset_confirm = False

        if self.tab in (1, 2, 3):
            if inp.just_pressed("UP"):
                self.selected_row -= 1
                self._clamp_selection()
            if inp.just_pressed("DOWN"):
                self.selected_row += 1
                self._clamp_selection()

        if inp.just_pressed("L"):
            if self.tab in (1, 2):
                self.tab = 0
                self.selected_row = 0
                self._show_toast("Terug – wissel tabs met ← →", 1.2)
                return
            if self.tab == 3 and self.reset_confirm:
                self.reset_confirm = False
                return
            self._save_game()
            from ui.Games_menu import Game_Menu

            self.manager.set_scene(Game_Menu(self.manager))
            return

        if inp.just_pressed("B") or inp.just_pressed("SPACE"):
            self._action_confirm()

    def _action_confirm(self):
        if self.tab == 0:
            self._do_click()
        elif self.tab == 1:
            self._buy_animals(self.selected_row)
        elif self.tab == 2:
            self._buy_upgrade(self.selected_row)
        elif self.tab == 3:
            if self.selected_row == 0:
                self.reset_confirm = not self.reset_confirm
            elif self.selected_row == 1 and self.reset_confirm:
                self._reset_game()

    def _cycle_buy_mode(self, direction):
        self.buy_mode_index = (self.buy_mode_index + direction) % len(BUY_MODES)

    def update(self, dt):
        self.input_handler.update()
        self._handle_input()

        self._autosave_timer += dt
        if self._autosave_timer >= 15.0:
            self._autosave_timer = 0.0
            self._save_game()

        income = self._income_per_second()
        if income > 0:
            self.money += income * dt

        self.last_timestamp = time.time()

        if self.click_pulse > 0:
            self.click_pulse = max(0.0, self.click_pulse - dt * 3.5)
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
        if self.purchase_flash_timer > 0:
            self.purchase_flash_timer = max(0.0, self.purchase_flash_timer - dt)

        self.floating_texts = [t for t in self.floating_texts if t.alive]
        for text in self.floating_texts:
            text.update(dt)

    def _draw_background(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            top = (135, 200, 120)
            bottom = (55, 120, 70)
            r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
            g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
            b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def _draw_header(self, surface):
        pygame.draw.rect(surface, (40, 70, 45), (0, 0, BASE_WIDTH, 48))
        title = self.title_font.render("Farm Nation", True, (255, 245, 210))
        surface.blit(title, (10, 8))

        money_text = self.money_font.render(format_money(self.money), True, (255, 230, 80))
        surface.blit(money_text, (BASE_WIDTH - money_text.get_width() - 10, 6))

        income = self._income_per_second()
        inc_label = self.small_font.render(
            f"{format_money(income)}/s  |  Klik: {format_money(self._click_value())}",
            True,
            (210, 240, 200),
        )
        surface.blit(inc_label, (BASE_WIDTH - inc_label.get_width() - 10, 28))

    def _draw_tabs(self, surface):
        tab_y = BASE_HEIGHT - 36
        tab_w = BASE_WIDTH // len(TABS)
        for i, name in enumerate(TABS):
            rect = pygame.Rect(i * tab_w, tab_y, tab_w - 2, 34)
            active = i == self.tab
            color = (90, 160, 90) if active else (55, 95, 60)
            pygame.draw.rect(surface, color, rect, border_radius=6)
            if active:
                pygame.draw.rect(surface, (255, 240, 150), rect, 2, border_radius=6)
            label = self.small_font.render(name, True, (255, 255, 255))
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_click_tab(self, surface):
        pulse = 1.0 + self.click_pulse * 0.08
        rect = self.click_rect.copy()
        cx, cy = rect.center
        w = int(rect.width * pulse)
        h = int(rect.height * pulse)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)

        barn_color = (180, 70, 55)
        if self.click_pulse > 0:
            barn_color = (220, 100, 75)
        pygame.draw.rect(surface, (120, 80, 50), rect, border_radius=12)
        pygame.draw.rect(surface, barn_color, rect.inflate(-8, -8), border_radius=10)

        roof = [
            (rect.left + 8, rect.top + 28),
            (rect.centerx, rect.top + 4),
            (rect.right - 8, rect.top + 28),
        ]
        pygame.draw.polygon(surface, (150, 40, 40), roof)

        label = self.big_font.render("KLIK!", True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=(rect.centerx, rect.centery + 20)))

        hint = self.small_font.render("SPACE / B = klikken", True, (240, 255, 240))
        surface.blit(hint, (rect.x + 8, rect.bottom - 18))

        stats_rect = self.list_rect
        pygame.draw.rect(surface, (30, 55, 35), stats_rect, border_radius=8)
        pygame.draw.rect(surface, (80, 130, 85), stats_rect, 2, border_radius=8)

        lines = [
            "Jouw boerderij",
            f"Totaal kliks: {self.total_clicks}",
            f"Inkomen/s: {format_money(self._income_per_second())}",
            "",
            "Top dieren:",
        ]
        ranked = sorted(
            ANIMALS,
            key=lambda a: self.animal_counts[a["id"]] * a["base_income"],
            reverse=True,
        )
        for animal in ranked[:4]:
            count = self.animal_counts[animal["id"]]
            if count > 0:
                lines.append(f"  {animal['name']}: {count}x")

        y = stats_rect.y + 10
        for i, line in enumerate(lines):
            font = self.ui_font if i == 0 else self.small_font
            color = (255, 245, 200) if i == 0 else (210, 230, 200)
            text = font.render(line, True, color)
            surface.blit(text, (stats_rect.x + 10, y))
            y += 16 if i > 0 else 20

        for floater in self.floating_texts:
            floater.draw(surface, self.ui_font)

        if self.flash_timer > 0:
            flash = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
            alpha = int(80 * (self.flash_timer / 0.12))
            flash.fill((255, 255, 200, alpha))
            surface.blit(flash, (0, 0))

    def _draw_buy_mode(self, surface, x, y):
        mode = self._buy_mode()
        label = self.small_font.render(f"Koop: {mode}x", True, (255, 240, 160))
        surface.blit(label, (x, y))
        hint = self.small_font.render("< 1/10/100 >", True, (180, 210, 180))
        surface.blit(hint, (x + 80, y))

    def _draw_animal_row(self, surface, index, y, height):
        animal = ANIMALS[index]
        selected = index == self.selected_row
        row_rect = pygame.Rect(self.list_rect.x, y, self.list_rect.width, height - 2)

        if selected:
            flash = self.purchase_flash_row == index and self.purchase_flash_timer > 0
            color = (70, 140, 75) if not flash else (100, 200, 110)
            pygame.draw.rect(surface, color, row_rect, border_radius=6)
            pygame.draw.rect(surface, (255, 240, 140), row_rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surface, (35, 60, 40), row_rect, border_radius=6)

        icon_rect = pygame.Rect(row_rect.x + 6, row_rect.y + 6, 28, height - 14)
        pygame.draw.ellipse(surface, animal["color"], icon_rect)

        count = self.animal_counts[animal["id"]]
        income = count * animal["base_income"]
        whisper = self.upgrade_levels["animal_whisper"]
        mega = self.upgrade_levels["mega_barn"]
        income *= 1.0 + whisper * 0.10
        income *= 1.0 + mega * 0.25

        name = self.ui_font.render(f"{animal['name']} x{count}", True, (255, 255, 255))
        surface.blit(name, (row_rect.x + 40, row_rect.y + 4))

        info = self.small_font.render(
            f"+{format_money(animal['base_income'])}/s elk  |  Totaal: {format_money(income)}/s",
            True,
            (200, 230, 200),
        )
        surface.blit(info, (row_rect.x + 40, row_rect.y + 20))

        bulk = self._max_affordable_bulk(self._animal_cost, animal["id"])
        if bulk > 0:
            cost = self._animal_cost(animal["id"], bulk)
            cost_color = (255, 230, 100)
        else:
            bulk = self._buy_mode()
            cost = self._animal_cost(animal["id"], bulk)
            cost_color = (180, 100, 100)

        cost_text = self.small_font.render(f"{bulk}x {format_money(cost)}", True, cost_color)
        surface.blit(cost_text, (row_rect.right - cost_text.get_width() - 8, row_rect.centery - 6))

    def _draw_upgrade_row(self, surface, index, y, height):
        upgrade = UPGRADES[index]
        selected = index == self.selected_row
        row_rect = pygame.Rect(self.list_rect.x, y, self.list_rect.width, height - 2)
        level = self.upgrade_levels[upgrade["id"]]

        if selected:
            flash = self.purchase_flash_row == index and self.purchase_flash_timer > 0
            color = (70, 120, 150) if not flash else (90, 180, 220)
            pygame.draw.rect(surface, color, row_rect, border_radius=6)
            pygame.draw.rect(surface, (255, 240, 140), row_rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surface, (35, 55, 65), row_rect, border_radius=6)

        name = self.ui_font.render(f"{upgrade['name']} Lv.{level}", True, (255, 255, 255))
        surface.blit(name, (row_rect.x + 8, row_rect.y + 4))

        desc = self.small_font.render(upgrade["desc"], True, (200, 220, 240))
        surface.blit(desc, (row_rect.x + 8, row_rect.y + 20))

        if level >= upgrade["max_level"]:
            cost_text = self.small_font.render("MAX", True, (255, 220, 100))
        else:
            bulk = self._buy_mode()
            cost = self._upgrade_cost(upgrade["id"], bulk)
            if cost is None or self.money < cost:
                for try_bulk in (10, 1):
                    cost = self._upgrade_cost(upgrade["id"], try_bulk)
                    if cost is not None and self.money >= cost:
                        bulk = try_bulk
                        break
            cost_color = (255, 230, 100) if cost and self.money >= cost else (180, 100, 100)
            cost_text = self.small_font.render(
                f"{bulk}x {format_money(cost) if cost else '?'}",
                True,
                cost_color,
            )
        surface.blit(cost_text, (row_rect.right - cost_text.get_width() - 8, row_rect.centery - 6))

    def _draw_animals_tab(self, surface):
        self._draw_buy_mode(surface, self.list_rect.x, self.list_rect.y - 14)
        row_h = 42
        visible = max(1, self.list_rect.height // row_h)
        start = max(0, min(self.selected_row - visible // 2, len(ANIMALS) - visible))
        start = max(0, start)

        for i in range(start, min(len(ANIMALS), start + visible)):
            y = self.list_rect.y + (i - start) * row_h
            self._draw_animal_row(surface, i, y, row_h)

    def _draw_upgrades_tab(self, surface):
        self._draw_buy_mode(surface, self.list_rect.x, self.list_rect.y - 14)
        row_h = 42
        visible = max(1, self.list_rect.height // row_h)
        start = max(0, min(self.selected_row - visible // 2, len(UPGRADES) - visible))
        start = max(0, start)

        for i in range(start, min(len(UPGRADES), start + visible)):
            y = self.list_rect.y + (i - start) * row_h
            self._draw_upgrade_row(surface, i, y, row_h)

    def _draw_reset_tab(self, surface):
        panel = self.list_rect
        pygame.draw.rect(surface, (45, 35, 35), panel, border_radius=8)
        pygame.draw.rect(surface, (120, 70, 70), panel, 2, border_radius=8)

        options = [
            ("Reset bevestigen", self.reset_confirm),
            ("JA - wis alles", self.reset_confirm),
        ]
        row_h = 50
        for i, (text, needs_confirm) in enumerate(options):
            y = panel.y + 16 + i * row_h
            row_rect = pygame.Rect(panel.x + 10, y, panel.width - 20, row_h - 6)
            selected = i == self.selected_row
            if selected:
                pygame.draw.rect(surface, (130, 60, 60), row_rect, border_radius=6)
                pygame.draw.rect(surface, (255, 200, 120), row_rect, 2, border_radius=6)
            else:
                pygame.draw.rect(surface, (70, 45, 45), row_rect, border_radius=6)

            if i == 1 and not self.reset_confirm:
                color = (140, 140, 140)
                display = "Eerst bevestigen..."
            else:
                color = (255, 230, 230)
                display = text

            label = self.ui_font.render(display, True, color)
            surface.blit(label, label.get_rect(center=row_rect.center))

        warn = self.small_font.render("Let op: al je voortgang gaat verloren!", True, (255, 180, 180))
        surface.blit(warn, warn.get_rect(centerx=panel.centerx, bottom=panel.bottom - 12))

    def _draw_toast(self, surface):
        if self.toast_timer <= 0 or not self.toast_message:
            return
        label = self.ui_font.render(self.toast_message, True, (30, 30, 30))
        pad_x, pad_y = 12, 6
        box = label.get_rect()
        box.inflate_ip(pad_x * 2, pad_y * 2)
        box.centerx = BASE_WIDTH // 2
        box.y = 54
        pygame.draw.rect(surface, (255, 240, 160), box, border_radius=8)
        pygame.draw.rect(surface, (80, 60, 20), box, 2, border_radius=8)
        surface.blit(label, label.get_rect(center=box.center))

    def _draw_footer_hints(self, surface):
        hints = "← →: tabs | UP/DOWN: kies | SPACE/B: actie | L: menu"
        if self.tab in (1, 2):
            hints = "L: terug | ← →: 1/10/100x | UP/DOWN: kies | SPACE/B: koop"
        label = self.small_font.render(hints, True, (220, 240, 220))
        surface.blit(label, (8, BASE_HEIGHT - 52))

    def draw(self, surface):
        self._draw_background(surface)
        self._draw_header(surface)
        self._draw_footer_hints(surface)

        if self.tab == 0:
            self._draw_click_tab(surface)
        elif self.tab == 1:
            self._draw_animals_tab(surface)
        elif self.tab == 2:
            self._draw_upgrades_tab(surface)
        elif self.tab == 3:
            self._draw_reset_tab(surface)

        self._draw_tabs(surface)
        self._draw_toast(surface)
