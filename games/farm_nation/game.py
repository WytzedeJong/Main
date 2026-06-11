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


GAME_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(GAME_DIR, "config.json")
USERS_PATH = os.path.abspath(os.path.join(GAME_DIR, "..", "..", "data", "users.json"))


def _load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = _load_config()


def color(name):
    return tuple(CONFIG["colors"][name])


STATS_PATH = os.path.join(GAME_DIR, CONFIG["files"]["stats"])
SAVE_DIR = os.path.join(GAME_DIR, "save_files")
REQUIRED_UPGRADE_IDS = set(CONFIG["required_upgrade_ids"])
FALLBACK_ANIMAL_COLORS = {
    animal_id: tuple(color)
    for animal_id, color in CONFIG["fallback_animal_colors"].items()
}
TABS = list(CONFIG["tabs"])
TAB_CLICK = 0
TAB_ANIMALS = 1
TAB_UPGRADES = 2
TAB_ANIMAL_UPGRADES = 3
TAB_REBIRTH = 4
BUY_MODES = list(CONFIG["buy_modes"])
BUY_MODE_MAX = "max"
MAX_OFFLINE_SECONDS = int(CONFIG["max_offline_seconds"])


def _normalise_stat_entries(entries, kind):
    normalised = []
    if not isinstance(entries, dict):
        return normalised

    for key, raw in entries.items():
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        item["id"] = key
        item["stat_id"] = str(raw["id"])
        item["sort_order"] = int(raw["id"])
        item["name"] = str(raw.get("name", key.replace("_", " ").title()))
        item["base_cost"] = float(raw.get("base_cost", 0))
        item["max_level"] = int(raw.get("max_level", 0))
        item["desc"] = str(raw.get("desc", raw.get("description", "")))
        if kind == "animal":
            item["base_income"] = float(raw.get("base_income", 0))
            item["color"] = FALLBACK_ANIMAL_COLORS.get(
                key,
                FALLBACK_ANIMAL_COLORS["default"],
            )
        else:
            item["cost_mult"] = float(raw["cost_multiplier"])
        normalised.append(item)

    return sorted(normalised, key=lambda item: item["sort_order"])


def _load_stats():
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    animals = _normalise_stat_entries(data.get("animals", {}), "animal")
    upgrades = _normalise_stat_entries(data.get("upgrades", {}), "upgrade")
    animal_upgrades = _normalise_stat_entries(data.get("animal_upgrades", {}), "animal_upgrade")

    missing_upgrades = REQUIRED_UPGRADE_IDS - {upgrade["id"] for upgrade in upgrades}
    if missing_upgrades:
        missing = ", ".join(sorted(missing_upgrades))
        raise ValueError(f"stats.json mist verplichte upgrades: {missing}")

    animals_by_stat_id = {animal["stat_id"]: animal["id"] for animal in animals}
    for upgrade in animal_upgrades:
        target_animal_id = str(upgrade["target_animal_id"])
        if target_animal_id not in animals_by_stat_id:
            raise ValueError(
                f"Animal upgrade '{upgrade['id']}' verwijst naar onbekende target_animal_id "
                f"'{target_animal_id}'"
            )
        upgrade["animal_id"] = animals_by_stat_id[target_animal_id]
        upgrade["income_bonus"] = float(upgrade["income_bonus"])

    return animals, upgrades, animal_upgrades


ANIMALS, UPGRADES, ANIMAL_UPGRADES = _load_stats()


def format_money(value):
    value = float(value)
    if value < 0:
        return f"-${format_money(-value)[1:]}"
    if value < 1000:
        if value == int(value):
            return f"${int(value)}"
        return f"${value:.2f}"
    suffixes = ["", "K", "M", "B", "T", "Qa", "Qi", "Se", "Sx", "Sp", "Oc", "No"]
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
    def __init__(self, x, y, text, color, lifetime=None):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.lifetime = lifetime or CONFIG["timers"]["floating_text_lifetime"]
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        self.y -= CONFIG["timers"]["floating_text_speed"] * dt

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
        self.input_handler = self.manager.input_handler

        font_config = CONFIG["fonts"]
        font_family = font_config["family"]
        self.title_font = pygame.font.SysFont(font_family, font_config["title_size"], bold=True)
        self.money_font = pygame.font.SysFont(font_family, font_config["money_size"], bold=True)
        self.ui_font = pygame.font.SysFont(font_family, font_config["ui_size"])
        self.small_font = pygame.font.SysFont(font_family, font_config["small_size"])
        self.big_font = pygame.font.SysFont(font_family, font_config["big_size"], bold=True)

        self.user = self._get_user()
        self.save_path = self._save_path()

        self.tab = 0
        self.selected_row = 0
        self.buy_mode_index = 0
        self.rebirth_confirm = False

        self.money = 0.0
        self.total_clicks = 0
        self.rebirths = 0
        self.rebirth_bonus = 0.0
        self.animal_counts = {a["id"]: 0 for a in ANIMALS}
        self.upgrade_levels = {u["id"]: 0 for u in UPGRADES}
        self.animal_upgrade_levels = {u["id"]: 0 for u in ANIMAL_UPGRADES}
        self.animal_images = self._load_animal_images()
        self.click_button_image = self._load_click_button_image()
        self.last_timestamp = time.time()

        self.click_pulse = 0.0
        self.toast_message = ""
        self.toast_timer = 0.0
        self.floating_texts = []
        self._autosave_timer = 0.0

        self._load_save()
        self._apply_offline_income()

        layout = CONFIG["layout"]
        click_x, click_y, click_w = layout["click_rect"]
        list_x, list_y, list_right_margin = layout["list_rect"]
        bottom_reserved = layout["bottom_reserved_height"]
        self.click_rect = pygame.Rect(click_x, click_y, click_w, BASE_HEIGHT - bottom_reserved)
        self.list_rect = pygame.Rect(
            list_x,
            list_y,
            BASE_WIDTH - list_right_margin,
            BASE_HEIGHT - bottom_reserved,
        )

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
        safe_name = "".join(c if c.isalnum() else "_" for c in self._user_key())
        save_prefix = CONFIG["files"]["save_prefix"]
        return os.path.join(SAVE_DIR, f"{save_prefix}{safe_name}.json")

    def _legacy_save_path(self):
        safe_name = "".join(c if c.isalnum() else "_" for c in self._user_key())
        save_prefix = CONFIG["files"]["save_prefix"]
        return os.path.join(GAME_DIR, f"{save_prefix}{safe_name}.json")

    def _image_slug(self, value):
        return "".join(c.lower() if c.isalnum() else "_" for c in value).strip("_")

    def _load_animal_images(self):
        asset_config = CONFIG["assets"]
        search_folders = [
            os.path.join(GAME_DIR, folder)
            for folder in asset_config["animal_image_folders"]
        ]
        images = {}
        for animal in ANIMALS:
            filename = f"{self._image_slug(animal['name'])}{asset_config['animal_image_suffix']}"
            for search_folder in search_folders:
                path = os.path.join(search_folder, filename)
                if not os.path.exists(path):
                    continue
                try:
                    image = pygame.image.load(path)
                    try:
                        image = image.convert_alpha()
                    except pygame.error:
                        pass
                    images[animal["id"]] = image
                    break
                except pygame.error:
                    continue
        return images

    def _load_click_button_image(self):
        path = os.path.join(GAME_DIR, "images", "farm_button.png")
        if not os.path.exists(path):
            return None
        try:
            image = pygame.image.load(path)
            try:
                return image.convert_alpha()
            except pygame.error:
                return image
        except pygame.error:
            return None

    def _animal_upgrade_level(self, animal_id):
        total = 0
        for upgrade in ANIMAL_UPGRADES:
            if upgrade.get("animal_id") == animal_id:
                total += self.animal_upgrade_levels.get(upgrade["id"], 0)
        return total

    def _animal_income_bonus(self, animal_id):
        bonus = 0.0
        for upgrade in ANIMAL_UPGRADES:
            if upgrade.get("animal_id") == animal_id:
                bonus += self.animal_upgrade_levels.get(upgrade["id"], 0) * upgrade["income_bonus"]
        return bonus

    def _animal_income(self, animal):
        economy = CONFIG["economy"]
        whisper = self.upgrade_levels["animal_whisper"]
        mega = self.upgrade_levels["mega_barn"]
        income = self.animal_counts[animal["id"]] * animal["base_income"]
        income *= 1.0 + whisper * economy["animal_whisper_income_multiplier"]
        income *= 1.0 + mega * economy["mega_barn_income_multiplier"]
        income *= 1.0 + self._animal_income_bonus(animal["id"])
        income *= self._rebirth_multiplier()
        return income

    def _animal_cost(self, animal_id, amount=1):
        animal = next(a for a in ANIMALS if a["id"] == animal_id)
        count = self.animal_counts[animal_id]
        total = 0.0
        for _ in range(amount):
            try:
                total += animal["base_cost"] * (CONFIG["economy"]["animal_cost_growth"] ** count)
            except OverflowError:
                return math.inf
            if not math.isfinite(total):
                return math.inf
            count += 1
        return total

    def _upgrade_cost(self, upgrade_id, amount=1, upgrades=None, levels=None):
        upgrades = upgrades or UPGRADES
        levels = levels or self.upgrade_levels
        upgrade = next(u for u in upgrades if u["id"] == upgrade_id)
        level = levels[upgrade_id]
        total = 0.0
        for _ in range(amount):
            if level >= upgrade["max_level"]:
                return None
            try:
                total += upgrade["base_cost"] * (upgrade["cost_mult"] ** level)
            except OverflowError:
                return math.inf
            if not math.isfinite(total):
                return math.inf
            level += 1
        return total

    def _click_value(self):
        economy = CONFIG["economy"]
        hands = self.upgrade_levels["strong_hands"]
        golden = self.upgrade_levels["golden_touch"]
        mega = self.upgrade_levels["mega_barn"]
        base = economy["base_click_value"] + hands * economy["strong_hands_click_bonus"]
        base *= 1.0 + golden * economy["golden_touch_click_multiplier"]
        base *= 1.0 + mega * economy["mega_barn_income_multiplier"]
        base *= self._rebirth_multiplier()
        return base

    def _rebirth_multiplier(self):
        return 1.0 + self.rebirth_bonus

    def _rebirth_cost(self):
        base_cost = CONFIG["rebirth"]["money_per_bonus"]
        return base_cost * (1000 ** self.rebirths)

    def _can_rebirth(self):
        return self.money >= self._rebirth_cost()

    def _rebirth_bonus_available(self):
        if not self._can_rebirth():
            return 0.0
        return CONFIG["rebirth"]["bonus_per_money_unit"]

    def _format_bonus_percent(self, bonus):
        return f"{bonus * 100:.0f}%"

    def _income_per_second(self):
        total = 0.0
        for animal in ANIMALS:
            total += self._animal_income(animal)
        return total

    def _buy_mode(self):
        return BUY_MODES[self.buy_mode_index]

    def _buy_mode_label(self):
        mode = self._buy_mode()
        if mode == BUY_MODE_MAX:
            return "MAX"
        return f"{int(mode)}x"

    def _max_affordable_amount(self, cost_fn, item_id, max_amount=None):
        if max_amount is not None and max_amount <= 0:
            return 0

        first_cost = cost_fn(item_id, 1)
        if first_cost is None or self.money < first_cost:
            return 0

        low = 1
        high = 1
        search_high = 1
        while max_amount is None or high < max_amount:
            next_high = high * 2
            if max_amount is not None:
                next_high = min(next_high, max_amount)

            cost = cost_fn(item_id, next_high)
            if cost is None or self.money < cost:
                search_high = next_high - 1
                break
            high = next_high
            low = high

            if max_amount is not None and high >= max_amount:
                return high
        else:
            search_high = high

        while low < search_high:
            mid = (low + search_high + 1) // 2
            cost = cost_fn(item_id, mid)
            if cost is not None and self.money >= cost:
                low = mid
            else:
                search_high = mid - 1
        return low

    def _amount_for_buy_mode(self, cost_fn, item_id, max_amount=None):
        mode = self._buy_mode()
        if mode == BUY_MODE_MAX:
            return self._max_affordable_amount(cost_fn, item_id, max_amount)

        amount = int(mode)
        if max_amount is not None and amount > max_amount:
            return 0
        cost = cost_fn(item_id, amount)
        if cost is not None and self.money >= cost:
            return amount
        return 0

    def _show_toast(self, message, duration=None):
        self.toast_message = message
        self.toast_timer = duration or CONFIG["timers"]["toast_default_seconds"]

    def _apply_offline_income(self):
        now = time.time()
        elapsed = max(0.0, now - self.last_timestamp)
        elapsed = min(elapsed, MAX_OFFLINE_SECONDS)
        income = self._income_per_second() * elapsed
        if income > 0:
            self.money += income
            mins = int(elapsed // 60)
            if mins >= 1:
                self._show_toast(
                    f"Offline: +{format_money(income)} ({mins}m)",
                    CONFIG["timers"]["offline_toast_seconds"],
                )
        self.last_timestamp = now

    def _load_save(self):
        legacy_path = self._legacy_save_path()
        if not os.path.exists(self.save_path) and os.path.exists(legacy_path):
            self.save_path = legacy_path

        if not os.path.exists(self.save_path):
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        self.money = float(data.get("money", 0))
        self.total_clicks = int(data.get("total_clicks", 0))
        self.rebirths = int(data.get("rebirths", 0))
        self.rebirth_bonus = float(data.get("rebirth_bonus", 0.0))
        self.last_timestamp = float(data.get("last_timestamp", time.time()))
        saved_animals = data.get("animals", {})
        saved_upgrades = data.get("upgrades", {})
        saved_animal_upgrades = data.get("animal_upgrades", {})
        for animal in ANIMALS:
            self.animal_counts[animal["id"]] = int(
                saved_animals.get(animal["id"], 0)
            )
        for upgrade in UPGRADES:
            self.upgrade_levels[upgrade["id"]] = int(
                saved_upgrades.get(upgrade["id"], 0)
            )
        for upgrade in ANIMAL_UPGRADES:
            self.animal_upgrade_levels[upgrade["id"]] = int(
                saved_animal_upgrades.get(upgrade["id"], 0)
            )
        self.save_path = self._save_path()

    def _farm_highscore_data(self):
        return {
            "money": self.money,
            "total_clicks": self.total_clicks,
            "rebirths": self.rebirths,
        }

    def _save_highscore(self):
        username = self._user_key()
        if not username:
            return

        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        changed = False
        for player in data.get("users", []):
            if player.get("name") != username:
                continue
            if "highscores" not in player or not isinstance(player["highscores"], dict):
                player["highscores"] = {}
            player["highscores"]["Farm Nation"] = self._farm_highscore_data()
            changed = True
            break

        if not changed:
            return

        try:
            with open(USERS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except OSError:
            pass

    def _save_game(self):
        data = {
            "money": self.money,
            "total_clicks": self.total_clicks,
            "rebirths": self.rebirths,
            "rebirth_bonus": self.rebirth_bonus,
            "last_timestamp": time.time(),
            "animals": dict(self.animal_counts),
            "upgrades": dict(self.upgrade_levels),
            "animal_upgrades": dict(self.animal_upgrade_levels),
        }
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass
        self._save_highscore()

    def _reset_run_progress(self):
        self.money = 0.0
        if CONFIG["rebirth"]["reset_total_clicks"]:
            self.total_clicks = 0
        self.animal_counts = {a["id"]: 0 for a in ANIMALS}
        self.upgrade_levels = {u["id"]: 0 for u in UPGRADES}
        self.animal_upgrade_levels = {u["id"]: 0 for u in ANIMAL_UPGRADES}
        self.last_timestamp = time.time()
        self.selected_row = 0
        self.rebirth_confirm = False
        self.floating_texts.clear()

    def _rebirth(self):
        if not self._can_rebirth():
            self._show_toast("Nog niet genoeg geld voor rebirth!", 1.2)
            return False

        gained_bonus = CONFIG["rebirth"]["bonus_per_money_unit"]
        self.rebirths += 1
        self.rebirth_bonus += gained_bonus
        self._reset_run_progress()
        self._save_game()
        self._show_toast(
            f"Rebirth! Permanent +{self._format_bonus_percent(gained_bonus)}",
            CONFIG["rebirth"]["toast_seconds"],
        )
        return True

    def _do_click(self, x=None, y=None):
        value = self._click_value()
        self.money += value
        self.total_clicks += 1
        self.click_pulse = 1.0

        fx = x if x is not None else self.click_rect.centerx
        fy = y if y is not None else self.click_rect.centery - 20
        self.floating_texts.append(
            FloatingText(fx, fy, f"+{format_money(value)}", color("floating_click_text"))
        )

    def _buy_animals(self, index):
        animal = ANIMALS[index]
        amount = self._amount_for_buy_mode(self._animal_cost, animal["id"])
        if amount <= 0:
            self._show_toast("Niet genoeg geld!", 1.0)
            return False
        cost = self._animal_cost(animal["id"], amount)
        self.money -= cost
        self.animal_counts[animal["id"]] += amount
        self._show_toast(f"Gekocht: {amount}x {animal['name']}!", 1.3)
        return True

    def _buy_upgrade_from(self, index, upgrades, levels, label):
        upgrade = upgrades[index]
        level = levels[upgrade["id"]]
        if level >= upgrade["max_level"]:
            self._show_toast("Max level bereikt!", 1.0)
            return False

        remaining_levels = upgrade["max_level"] - level
        amount = self._amount_for_buy_mode(
            lambda upgrade_id, amount: self._upgrade_cost(upgrade_id, amount, upgrades, levels),
            upgrade["id"],
            remaining_levels,
        )
        if amount <= 0:
            self._show_toast("Niet genoeg geld!", 1.0)
            return False

        cost = self._upgrade_cost(upgrade["id"], amount, upgrades, levels)
        self.money -= cost
        levels[upgrade["id"]] += amount
        self._show_toast(f"{label}: {upgrade['name']} x{amount}!", 1.3)
        return True

    def _buy_upgrade(self, index):
        return self._buy_upgrade_from(index, UPGRADES, self.upgrade_levels, "Upgrade")

    def _buy_animal_upgrade(self, index):
        return self._buy_upgrade_from(
            index,
            ANIMAL_UPGRADES,
            self.animal_upgrade_levels,
            "Dier upgrade",
        )

    def _list_item_count(self):
        if self.tab == TAB_ANIMALS:
            return len(ANIMALS)
        if self.tab == TAB_UPGRADES:
            return len(UPGRADES)
        if self.tab == TAB_ANIMAL_UPGRADES:
            return len(ANIMAL_UPGRADES)
        if self.tab == TAB_REBIRTH:
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

        if inp.just_pressed("LEFT"):
            self.tab = (self.tab - 1) % len(TABS)
            self.selected_row = 0
            self.rebirth_confirm = False
        if inp.just_pressed("RIGHT"):
            self.tab = (self.tab + 1) % len(TABS)
            self.selected_row = 0
            self.rebirth_confirm = False

        if (
            self.tab in (TAB_ANIMALS, TAB_UPGRADES, TAB_ANIMAL_UPGRADES)
            and inp.just_pressed("INFO")
        ):
            self._cycle_buy_mode(1)

        if self.tab in (TAB_ANIMALS, TAB_UPGRADES, TAB_ANIMAL_UPGRADES, TAB_REBIRTH):
            if inp.just_pressed("UP"):
                self.selected_row -= 1
                self._clamp_selection()
            if inp.just_pressed("DOWN"):
                self.selected_row += 1
                self._clamp_selection()

        if inp.just_pressed("L"):
            if self.tab == TAB_REBIRTH and self.rebirth_confirm:
                self.rebirth_confirm = False
            self.tab = TAB_CLICK
            self.selected_row = 0
            self._show_toast("Terug naar klik-tab", 1.2)
            self._save_game()
            return

        if inp.just_pressed("B") or inp.just_pressed("SPACE"):
            self._action_confirm()

    def _action_confirm(self):
        if self.tab == TAB_CLICK:
            self._do_click()
        elif self.tab == TAB_ANIMALS:
            self._buy_animals(self.selected_row)
        elif self.tab == TAB_UPGRADES:
            self._buy_upgrade(self.selected_row)
        elif self.tab == TAB_ANIMAL_UPGRADES:
            self._buy_animal_upgrade(self.selected_row)
        elif self.tab == TAB_REBIRTH:
            if self.selected_row == 0:
                self.rebirth_confirm = not self.rebirth_confirm
            elif self.selected_row == 1 and self.rebirth_confirm:
                self._rebirth()

    def _cycle_buy_mode(self, direction):
        self.buy_mode_index = (self.buy_mode_index + direction) % len(BUY_MODES)

    def update(self, dt):
       
        self._handle_input()

        self._autosave_timer += dt
        if self._autosave_timer >= CONFIG["autosave_seconds"]:
            self._autosave_timer = 0.0
            self._save_game()

        income = self._income_per_second()
        if income > 0:
            self.money += income * dt

        self.last_timestamp = time.time()

        if self.click_pulse > 0:
            self.click_pulse = max(0.0, self.click_pulse - dt * CONFIG["timers"]["click_pulse_decay"])
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)

        self.floating_texts = [t for t in self.floating_texts if t.alive]
        for text in self.floating_texts:
            text.update(dt)

    def _draw_background(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            top = color("background_top")
            bottom = color("background_bottom")
            r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
            g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
            b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def _draw_header(self, surface):
        pygame.draw.rect(surface, color("header_background"), (0, 0, BASE_WIDTH, 48))
        title = self.title_font.render("Farm Nation", True, color("header_title"))
        surface.blit(title, (10, 8))

        money_text = self.money_font.render(format_money(self.money), True, color("money"))
        surface.blit(money_text, (BASE_WIDTH - money_text.get_width() - 10, 6))

        income = self._income_per_second()
        inc_label = self.small_font.render(
            f"{format_money(income)}/s | Klik: {format_money(self._click_value())} | RB: +{self._format_bonus_percent(self.rebirth_bonus)}",
            True,
            color("header_subtext"),
        )
        surface.blit(inc_label, (BASE_WIDTH - inc_label.get_width() - 10, 28))

    def _draw_tabs(self, surface):
        tab_y = BASE_HEIGHT - CONFIG["layout"]["tab_bar_height"]
        tab_w = BASE_WIDTH // len(TABS)
        for i, name in enumerate(TABS):
            rect = pygame.Rect(i * tab_w, tab_y, tab_w - 2, CONFIG["layout"]["tab_height"])
            active = i == self.tab
            tab_color = color("tab_active") if active else color("tab_inactive")
            pygame.draw.rect(surface, tab_color, rect, border_radius=6)
            if active:
                pygame.draw.rect(surface, color("tab_border"), rect, 2, border_radius=6)
            label = self.small_font.render(name, True, color("white"))
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_click_tab(self, surface):
        pulse = 1.0 + self.click_pulse * 0.08
        rect = self.click_rect.copy()
        cx, cy = rect.center
        w = int(rect.width * pulse)
        h = int(rect.height * pulse)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)

        if self.click_button_image:
            scaled = pygame.transform.smoothscale(self.click_button_image, rect.size)
            surface.blit(scaled, rect)
        else:
            barn_color = color("barn")
            if self.click_pulse > 0:
                barn_color = color("barn_pulse")
            pygame.draw.rect(surface, color("barn_shadow"), rect, border_radius=12)
            pygame.draw.rect(surface, barn_color, rect.inflate(-8, -8), border_radius=10)

            roof = [
                (rect.left + 8, rect.top + 28),
                (rect.centerx, rect.top + 4),
                (rect.right - 8, rect.top + 28),
            ]
            pygame.draw.polygon(surface, color("barn_roof"), roof)

            label = self.big_font.render("KLIK!", True, color("white"))
            surface.blit(label, label.get_rect(center=(rect.centerx, rect.centery + 20)))

        hint = self.small_font.render("SPACE / B = klikken", True, color("click_hint"))
        surface.blit(hint, (rect.x + 8, rect.bottom - 18))

        stats_rect = self.list_rect
        pygame.draw.rect(surface, color("stats_panel"), stats_rect, border_radius=8)
        pygame.draw.rect(surface, color("stats_border"), stats_rect, 2, border_radius=8)

        lines = [
            "Jouw boerderij",
            f"Totaal kliks: {self.total_clicks}",
            f"Inkomen/s: {format_money(self._income_per_second())}",
            f"Rebirth bonus: +{self._format_bonus_percent(self.rebirth_bonus)}",
            "",
            "Top dieren:",
        ]
        ranked = sorted(
            ANIMALS,
            key=self._animal_income,
            reverse=True,
        )
        for animal in ranked[:4]:
            count = self.animal_counts[animal["id"]]
            if count > 0:
                lines.append(f"  {animal['name']}: {count}x")

        y = stats_rect.y + 10
        for i, line in enumerate(lines):
            font = self.ui_font if i == 0 else self.small_font
            text_color = color("stats_title") if i == 0 else color("stats_text")
            text = font.render(line, True, text_color)
            surface.blit(text, (stats_rect.x + 10, y))
            y += 16 if i > 0 else 20

        for floater in self.floating_texts:
            floater.draw(surface, self.ui_font)

    def _draw_buy_mode(self, surface, x, y):
        label = self.small_font.render(f"Koop: {self._buy_mode_label()}", True, color("buy_mode"))
        surface.blit(label, (x, y))
        hint = self.small_font.render("I: 1/10/100/MAX", True, color("buy_mode_hint"))
        surface.blit(hint, (x + 80, y))

    def _draw_animal_icon(self, surface, animal, icon_rect):
        image = self.animal_images.get(animal["id"])
        if image:
            scaled = pygame.transform.smoothscale(image, icon_rect.size)
            surface.blit(scaled, icon_rect)
            return
        pygame.draw.ellipse(surface, animal["color"], icon_rect)

    def _draw_animal_row(self, surface, index, y, height):
        animal = ANIMALS[index]
        selected = index == self.selected_row
        row_rect = pygame.Rect(self.list_rect.x, y, self.list_rect.width, height - 2)

        if selected:
            row_color = color("animal_row_selected")
            pygame.draw.rect(surface, row_color, row_rect, border_radius=6)
            pygame.draw.rect(surface, color("row_border"), row_rect, 2, border_radius=6)
        else:
            pygame.draw.rect(surface, color("animal_row"), row_rect, border_radius=6)

        icon_x, icon_y, icon_w, icon_height_margin = CONFIG["layout"]["animal_icon"]
        icon_rect = pygame.Rect(
            row_rect.x + icon_x,
            row_rect.y + icon_y,
            icon_w,
            height - icon_height_margin,
        )
        self._draw_animal_icon(surface, animal, icon_rect)

        count = self.animal_counts[animal["id"]]
        income = self._animal_income(animal)
        animal_bonus = self._animal_upgrade_level(animal["id"])

        name = self.ui_font.render(f"{animal['name']} x{count}", True, color("white"))
        surface.blit(name, (row_rect.x + 40, row_rect.y + 4))

        info = self.small_font.render(
            f"+{format_money(animal['base_income'])}/s elk  |  Lv.{animal_bonus} voer  |  Totaal: {format_money(income)}/s",
            True,
            color("animal_info"),
        )
        surface.blit(info, (row_rect.x + 40, row_rect.y + 20))

        bulk = self._amount_for_buy_mode(self._animal_cost, animal["id"])
        if bulk <= 0:
            bulk = self._buy_mode()
            if bulk == BUY_MODE_MAX:
                bulk = 1
            cost = self._animal_cost(animal["id"], int(bulk))
            cost_color = color("cost_unaffordable")
        else:
            cost = self._animal_cost(animal["id"], bulk)
            cost_color = color("cost_affordable")

        cost_text = self.small_font.render(f"{bulk}x {format_money(cost)}", True, cost_color)
        surface.blit(cost_text, (row_rect.right - cost_text.get_width() - 8, row_rect.centery - 6))

    def _draw_upgrade_row(self, surface, index, y, height, upgrades=None, levels=None, color_set=None):
        upgrades = upgrades or UPGRADES
        levels = levels or self.upgrade_levels
        color_set = color_set or (
            color("upgrade_row_selected"),
            color("upgrade_row"),
            color("upgrade_info"),
        )
        upgrade = upgrades[index]
        selected = index == self.selected_row
        row_rect = pygame.Rect(self.list_rect.x, y, self.list_rect.width, height - 2)
        level = levels[upgrade["id"]]
        row_color = color_set[0] if selected else color_set[1]
        pygame.draw.rect(surface, row_color, row_rect, border_radius=6)
        if selected:
            pygame.draw.rect(surface, color("row_border"), row_rect, 2, border_radius=6)

        name = self.ui_font.render(f"{upgrade['name']} Lv.{level}", True, color("white"))
        surface.blit(name, (row_rect.x + 8, row_rect.y + 4))

        desc = self.small_font.render(upgrade["desc"], True, color_set[2])
        surface.blit(desc, (row_rect.x + 8, row_rect.y + 20))

        if level >= upgrade["max_level"]:
            cost_text = self.small_font.render("MAX", True, color("cost_affordable"))
        else:
            remaining_levels = upgrade["max_level"] - level
            cost_fn = lambda upgrade_id, amount: self._upgrade_cost(upgrade_id, amount, upgrades, levels)
            bulk = self._amount_for_buy_mode(cost_fn, upgrade["id"], remaining_levels)
            if bulk <= 0:
                bulk = self._buy_mode()
                if bulk == BUY_MODE_MAX:
                    bulk = min(1, remaining_levels)
                cost = self._upgrade_cost(upgrade["id"], int(bulk), upgrades, levels)
            else:
                cost = self._upgrade_cost(upgrade["id"], bulk, upgrades, levels)
            cost_color = color("cost_affordable") if cost and self.money >= cost else color("cost_unaffordable")
            cost_text = self.small_font.render(
                f"{bulk}x {format_money(cost) if cost else '?'}",
                True,
                cost_color,
            )
        surface.blit(cost_text, (row_rect.right - cost_text.get_width() - 8, row_rect.centery - 6))

    def _draw_animals_tab(self, surface):
        self._draw_buy_mode(surface, self.list_rect.x, self.list_rect.y - 14)
        row_h = CONFIG["layout"]["row_height"]
        visible = max(1, self.list_rect.height // row_h)
        start = max(0, min(self.selected_row - visible // 2, len(ANIMALS) - visible))
        start = max(0, start)

        for i in range(start, min(len(ANIMALS), start + visible)):
            y = self.list_rect.y + (i - start) * row_h
            self._draw_animal_row(surface, i, y, row_h)

    def _draw_upgrades_tab(self, surface):
        self._draw_buy_mode(surface, self.list_rect.x, self.list_rect.y - 14)
        row_h = CONFIG["layout"]["row_height"]
        visible = max(1, self.list_rect.height // row_h)
        start = max(0, min(self.selected_row - visible // 2, len(UPGRADES) - visible))
        start = max(0, start)

        for i in range(start, min(len(UPGRADES), start + visible)):
            y = self.list_rect.y + (i - start) * row_h
            self._draw_upgrade_row(surface, i, y, row_h)

    def _draw_animal_upgrades_tab(self, surface):
        self._draw_buy_mode(surface, self.list_rect.x, self.list_rect.y - 14)
        row_h = CONFIG["layout"]["row_height"]
        visible = max(1, self.list_rect.height // row_h)
        start = max(0, min(self.selected_row - visible // 2, len(ANIMAL_UPGRADES) - visible))
        start = max(0, start)

        colors = (
            color("animal_upgrade_row_selected"),
            color("animal_upgrade_row"),
            color("animal_upgrade_info"),
        )
        for i in range(start, min(len(ANIMAL_UPGRADES), start + visible)):
            y = self.list_rect.y + (i - start) * row_h
            self._draw_upgrade_row(
                surface,
                i,
                y,
                row_h,
                ANIMAL_UPGRADES,
                self.animal_upgrade_levels,
                colors,
            )

    def _draw_rebirth_tab(self, surface):
        panel = self.list_rect
        pygame.draw.rect(surface, color("rebirth_panel"), panel, border_radius=8)
        pygame.draw.rect(surface, color("rebirth_border"), panel, 2, border_radius=8)

        gained_bonus = self._rebirth_bonus_available()
        rebirth_cost = self._rebirth_cost()
        can_rebirth = self._can_rebirth()
        next_bonus = self.rebirth_bonus + gained_bonus

        info_lines = [
            "Rebirth",
            f"Huidige permanente bonus: +{self._format_bonus_percent(self.rebirth_bonus)}",
            f"Volgende rebirth: {format_money(rebirth_cost)}",
            f"Na rebirth: +{self._format_bonus_percent(next_bonus)} totaal",
        ]
        y = panel.y + 10
        for i, line in enumerate(info_lines):
            font = self.ui_font if i == 0 else self.small_font
            text_color = color("rebirth_text") if i == 0 else color("rebirth_warning")
            label = font.render(line, True, text_color)
            surface.blit(label, (panel.x + 12, y))
            y += 18 if i == 0 else 15

        options = [
            ("Rebirth bevestigen", self.rebirth_confirm),
            (f"REBIRTH +{self._format_bonus_percent(gained_bonus)}", self.rebirth_confirm),
        ]
        row_h = CONFIG["layout"]["rebirth_row_height"]
        for i, (text, needs_confirm) in enumerate(options):
            row_y = panel.y + 86 + i * row_h
            row_rect = pygame.Rect(panel.x + 10, row_y, panel.width - 20, row_h - 6)
            selected = i == self.selected_row
            if selected:
                pygame.draw.rect(surface, color("rebirth_row_selected"), row_rect, border_radius=6)
                pygame.draw.rect(surface, color("rebirth_row_border"), row_rect, 2, border_radius=6)
            else:
                pygame.draw.rect(surface, color("rebirth_row"), row_rect, border_radius=6)

            if i == 1 and not can_rebirth:
                text_color = color("rebirth_disabled")
                display = f"Nodig: {format_money(rebirth_cost)}"
            elif i == 1 and not self.rebirth_confirm:
                text_color = color("rebirth_disabled")
                display = "Eerst bevestigen..."
            else:
                text_color = color("rebirth_text")
                display = text

            label = self.ui_font.render(display, True, text_color)
            surface.blit(label, label.get_rect(center=row_rect.center))

        warn = self.small_font.render(
            "Rebirth reset deze run, maar je permanente bonus blijft.",
            True,
            color("rebirth_warning"),
        )
        surface.blit(warn, warn.get_rect(centerx=panel.centerx, bottom=panel.bottom - 12))

    def _draw_toast(self, surface):
        if self.toast_timer <= 0 or not self.toast_message:
            return
        label = self.ui_font.render(self.toast_message, True, color("toast_text"))
        pad_x, pad_y = 12, 6
        box = label.get_rect()
        box.inflate_ip(pad_x * 2, pad_y * 2)
        box.centerx = BASE_WIDTH // 2
        box.y = 54
        pygame.draw.rect(surface, color("toast_background"), box, border_radius=8)
        pygame.draw.rect(surface, color("toast_border"), box, 2, border_radius=8)
        surface.blit(label, label.get_rect(center=box.center))

    def draw(self, surface):
        self._draw_background(surface)
        self._draw_header(surface)

        if self.tab == TAB_CLICK:
            self._draw_click_tab(surface)
        elif self.tab == TAB_ANIMALS:
            self._draw_animals_tab(surface)
        elif self.tab == TAB_UPGRADES:
            self._draw_upgrades_tab(surface)
        elif self.tab == TAB_ANIMAL_UPGRADES:
            self._draw_animal_upgrades_tab(surface)
        elif self.tab == TAB_REBIRTH:
            self._draw_rebirth_tab(surface)

        self._draw_tabs(surface)
        self._draw_toast(surface)