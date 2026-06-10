import json
import math
import os
import random
from dataclasses import dataclass

import pygame

from core.scene import Scene
from settings import BASE_HEIGHT, BASE_WIDTH
from ui.lockscreen import LockScreen

from core.input_manager import InputHandler

FIELD_WIDTH = BASE_WIDTH
MENU_WIDTH = BASE_WIDTH // 2
MENU_X = BASE_WIDTH - MENU_WIDTH
GRID = 25
COLS = FIELD_WIDTH // GRID
ROWS = BASE_HEIGHT // GRID
PATH_WIDTH = 25
MAX_TOWERS = 40
MAX_BANKS = 8
PIERCING_RANGE_MULTIPLIER = 2.0
ARMORED_SHED_HEALTH_RATIO = 0.80

BUTTON_QUIT = "B"
BUTTON_CONFIRM = "L"
BUTTON_MENU = "A"
BUTTON_INFO = "INFO"
DIRECTION_BUTTONS = ("LEFT", "RIGHT", "UP", "DOWN")

KEY_QUIT_LABEL = "B"
KEY_CONFIRM_LABEL = "L"
KEY_MENU_LABEL = "A"
KEY_INFO_LABEL = "I"


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clamp(value, low, high):
    return max(low, min(value, high))


@dataclass
class Enemy:
    kind: str
    max_health: float
    health: float
    damage: int
    speed: float
    reward: int
    waypoint: int = 0
    x: float = 0.0
    y: float = 0.0
    progress: float = 0.0
    slow_timer: float = 0.0
    slow_factor: float = 1.0
    freeze_timer: float = 0.0
    stun_timer: float = 0.0
    poison_timer: float = 0.0
    poison_dps: float = 0.0
    burn_timer: float = 0.0
    burn_dps: float = 0.0
    regeneration_rate: float = 0.0
    regeneration_amount: float = 0.0
    regeneration_timer: float = 0.0
    armored: bool = False
    stealth: bool = False
    freeze_radius: float = 0.0
    freeze_duration: float = 0.0

    def knock_back(self, waypoints, amount):
        amount = max(0, amount)
        self.progress = max(0, self.progress - amount)

        while amount > 0 and self.waypoint >= 0:
            wx, wy = waypoints[self.waypoint]
            dx = self.x - wx
            dy = self.y - wy
            segment_back = math.hypot(dx, dy)
            if segment_back > 0:
                step = min(amount, segment_back)
                self.x -= dx / segment_back * step
                self.y -= dy / segment_back * step
                amount -= step
                if step < segment_back:
                    return

            if self.waypoint <= 0:
                self.x, self.y = waypoints[0]
                return

            self.waypoint -= 1
            self.x, self.y = waypoints[self.waypoint + 1]

    def update(self, dt, waypoints, speed_multiplier=1.0):
        self._tick_effects(dt)
        self._tick_regeneration(dt)
        self._shed_armor_if_weakened()
        if self.waypoint >= len(waypoints) - 1:
            return True

        if self.freeze_timer > 0 or self.stun_timer > 0:
            return False

        move_speed = self.speed * 38 * speed_multiplier * (self.slow_factor if self.slow_timer > 0 else 1.0)
        remaining = move_speed * dt

        while remaining > 0 and self.waypoint < len(waypoints) - 1:
            tx, ty = waypoints[self.waypoint + 1]
            dx = tx - self.x
            dy = ty - self.y
            segment = math.hypot(dx, dy)
            if segment <= 0:
                self.waypoint += 1
                continue

            if remaining >= segment:
                self.x = tx
                self.y = ty
                remaining -= segment
                self.waypoint += 1
                self.progress += segment
            else:
                self.x += dx / segment * remaining
                self.y += dy / segment * remaining
                self.progress += remaining
                remaining = 0

        return self.waypoint >= len(waypoints) - 1

    def _tick_effects(self, dt):
        self.slow_timer = max(0, self.slow_timer - dt)
        self.freeze_timer = max(0, self.freeze_timer - dt)
        self.stun_timer = max(0, self.stun_timer - dt)

        if self.poison_timer > 0:
            tick = min(dt, self.poison_timer)
            self.health -= self.poison_dps * tick
            self.poison_timer -= dt

        if self.burn_timer > 0:
            tick = min(dt, self.burn_timer)
            self.health -= self.burn_dps * tick
            self.burn_timer -= dt

    def _tick_regeneration(self, dt):
        if self.regeneration_rate <= 0 or self.regeneration_amount <= 0:
            return
        if self.health <= 0 or self.health >= self.max_health:
            return

        self.regeneration_timer -= dt
        if self.regeneration_timer <= 0:
            self.health = min(self.max_health, self.health + self.regeneration_amount)
            self.regeneration_timer = self.regeneration_rate

    def _shed_armor_if_weakened(self):
        if self.armored and self.health <= self.max_health * ARMORED_SHED_HEALTH_RATIO:
            self.armored = False


@dataclass
class Tower:
    name: str
    base: dict
    cell: tuple[int, int]
    color: tuple[int, int, int]
    level: int = 1
    cooldown: float = 0.0
    total_spent: int = 0
    flash_timer: float = 0.0
    freeze_timer: float = 0.0
    inferno_target: object = None
    inferno_charge: float = 0.0
    income_timer: float = 0.0

    @property
    def center(self):
        return (self.cell[0] * GRID + GRID // 2, self.cell[1] * GRID + GRID // 2)

    def stat(self, key, default=0):
        value = self.base.get(key, default)
        if isinstance(value, (int, float)):
            if key == "range":
                return value * (1.10 ** (self.level - 1))
            if key == "buff_effect":
                return value * (1 + (self.level - 1) / 4)
            if key in (
                "trigger_radius", "chain_range", "area_of_effect", "poison_duration", "burn_duration",
                "freeze_duration", "delay_duration", "time_to_max_damage", "pull_strength",
                 "upgrade_range", "upgrade_effect", "upgrade_max_links", "knockback_distance",
                "money_generation_interval",
            ):
                return value
            return value * (1.25 ** (self.level - 1))
        return value

    @property
    def damage(self):
        return self.stat("damage", 0)

    @property
    def range(self):
        return self.stat("range", 0)

    @property
    def fire_rate(self):
        return max(0.15, self.stat("fire_rate", 0.35))

    @property
    def upgrade_cost(self):
        if self.level >= 5:
            return None
        return int(self.base.get("cost", 0) * (self.level + 1) * 1.1)


@dataclass
class Mine:
    x: float
    y: float
    damage: float
    radius: float
    trigger: float
    color: tuple[int, int, int]
    owner: Tower


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    timer: float = 1.0


@dataclass
class DelayedAttack:
    timer: float
    tower: Tower
    targets: list
    damage: float
    splash: float = 0.0


class TowerGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = pygame.font.SysFont("arial", 14, bold=True)
        self.font = pygame.font.SysFont("arial", 10)
        self.small_font = pygame.font.SysFont("arial", 8)
        self.big_font = pygame.font.SysFont("arial", 20, bold=True)
        self.info_font = pygame.font.SysFont("arial", 14)
        self.menu_font = pygame.font.SysFont("arial", 12)
        self.input = self.manager.input_handler

        self.stats = self._load_stats()
        self.tower_names = list(self.stats["towers"].keys())
        self.enemy_names = list(self.stats["enemies"].keys())
        self.colors = self._build_colors()
        self.tower_images = self._load_tower_images()
        self.tower_image_cache = {}
        self.user = self.get_user()
        self.highscore = 0
        self.new_highscore = False
        self._load_highscore()

        self.path = self._generate_path()
        self.path_cells = self._build_path_cells()

        self.focus = "field"
        self.state = "playing"
        self.menu_index = 0
        self.cursor = [4, 4]
        self.action_index = 0
        self.info_tower = None
        self.info_tower_name = None
        self.message = "Place towers, then start."
        self.banner_message = ""
        self.banner_timer = 0.0
        self.quit_dialog_open = False
        self.quit_dialog_index = 1
        self.quit_options = ["Stoppen", "Doorgaan"]
        self.held_move_key = None
        self.held_move_timer = 0.0
        self.held_move_delay = 0.1
        self.held_move_interval = 0.07

        self.money = 200
        self.lives = 100
        self.round = 0
        self.preparing = True
        self.game_speed = 1
        self.round_timer = 0.5
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.round_cleared_announced = True
        self.enemies = []
        self.towers = []
        self.mines = []
        self.texts = []
        self.shots = []
        self.delayed_attacks = []
        self.selected_tower = None
        self.game_over = False

    def get_user(self):
        user = getattr(self.manager, "current_user", None)
        if user:
            return user

        try:
            lock = LockScreen(self.manager)
            return lock.get_user() or 0
        except Exception:
            return 0

    def _user_name(self):
        if isinstance(self.user, dict):
            return self.user.get("name")
        if isinstance(self.user, str):
            return self.user
        return None

    def _load_stats(self):
        path = os.path.join(os.path.dirname(__file__), "stats.json")
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
        
    def _load_tower_images(self):
        image_dir = os.path.join(os.path.dirname(__file__), "images")
        if not os.path.isdir(image_dir):
            return {}

        towers_by_key = {
            self._image_name_key(name): name
            for name in self.stats.get("towers", {})
        }
        images = {}
        for filename in os.listdir(image_dir):
            if not filename.lower().endswith(".png"):
                continue

            stem = os.path.splitext(filename)[0]
            tower_name = towers_by_key.get(self._image_name_key(stem))
            if tower_name is None:
                continue

            path = os.path.join(image_dir, filename)
            try:
                images[tower_name] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue
        return images

    def _image_name_key(self, name):
        return " ".join(name.replace("_", " ").replace("-", " ").lower().split())

    def _tower_image(self, name, size):
        image = self.tower_images.get(name)
        if image is None:
            return None

        if isinstance(size, int):
            max_width = max_height = size
            cache_size = (size, size)
        else:
            max_width, max_height = size
            cache_size = (max_width, max_height)

        cache_key = (name, cache_size)
        if cache_key in self.tower_image_cache:
            return self.tower_image_cache[cache_key]

        width, height = image.get_size()
        if width <= 0 or height <= 0:
            return None

        scale = min(max_width / width, max_height / height)
        scaled_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        scaled = pygame.transform.smoothscale(image, scaled_size)
        self.tower_image_cache[cache_key] = scaled
        return scaled

    def _draw_tower_icon(self, surface, name, rect):
        image = self._tower_image(name, rect.size)
        if image is None:
            pygame.draw.rect(surface, self.colors[name], rect, border_radius=3)
            return False

        image_rect = image.get_rect(center=rect.center)
        surface.blit(image, image_rect)
        return True

    def _load_highscore(self):
        self.highscore = 0
        user_name = self._user_name()
        if not user_name:
            return

        try:
            with open(os.path.join("data", "users.json"), "r", encoding="utf-8") as file:
                users_data = json.load(file)
        except Exception:
            return

        for player in users_data.get("users", []):
            if player.get("name") != user_name:
                continue
            try:
                self.highscore = int(player.get("highscores", {}).get("Tower Defense", 0))
            except Exception:
                self.highscore = 0
            return

    def _save_highscore(self):
        user_name = self._user_name()
        if not user_name:
            return

        path = os.path.join("data", "users.json")
        try:
            with open(path, "r", encoding="utf-8") as file:
                users_data = json.load(file)
        except Exception:
            users_data = {"users": []}

        for player in users_data.get("users", []):
            if player.get("name") != user_name:
                continue

            if "highscores" not in player:
                player["highscores"] = {}

            try:
                current = int(player["highscores"].get("Tower Defense", 0))
            except Exception:
                current = 0

            if self.highscore > current:
                player["highscores"]["Tower Defense"] = self.highscore

            try:
                with open(path, "w", encoding="utf-8") as file:
                    json.dump(users_data, file, indent=4)
            except Exception:
                pass
            return

    def _finish_game(self):
        self.game_over = True
        self.new_highscore = self.round > self.highscore
        if self.new_highscore:
            self.highscore = self.round
            self._save_highscore()
        self.message = f"Game over. Press {KEY_CONFIRM_LABEL} to restart."

    def _build_colors(self):
        palette = [
            (82, 183, 136), (0, 0, 0), (224, 138, 65),
            (212, 36, 0), (138, 76, 21), (179, 175, 82),
            (16, 61, 16), (7, 13, 163), (126, 215, 230), 
            (111, 115, 220), (230, 95, 145), (233, 116, 74),
            (190, 190, 200), (224, 130, 245), (96, 160, 111), 
            (150, 90, 200), (245, 196, 66), (16, 61, 16), 
            (176, 179, 18), (80, 210, 240), (16, 224, 9), 
            (255, 159, 5), (200, 80, 90), (0, 0, 0),
        ]
        return {name: palette[i % len(palette)] for i, name in enumerate(self.tower_names)}

    def _generate_path(self):
        x_cells = sorted(random.sample(range(2, COLS - 2), 4))
        y_cells = [random.randrange(1, ROWS - 1)]
        for _ in x_cells:
            choices = [y for y in range(1, ROWS - 1) if abs(y - y_cells[-1]) >= 2]
            y_cells.append(random.choice(choices))

        points = [(-GRID // 2, y_cells[0] * GRID + GRID // 2)]
        current_y = points[0][1]
        for i, cell_x in enumerate(x_cells):
            x = cell_x * GRID + GRID // 2
            points.append((x, current_y))
            current_y = y_cells[i + 1] * GRID + GRID // 2
            points.append((x, current_y))
        points.append((FIELD_WIDTH + GRID // 2, current_y))
        return points

    def _build_path_cells(self):
        blocked = set()
        for y in range(ROWS):
            for x in range(COLS):
                point = (x * GRID + GRID // 2, y * GRID + GRID // 2)
                if self._distance_to_path(point) <= GRID * 0.72:
                    blocked.add((x, y))
        return blocked

    def _distance_to_path(self, point):
        best = 9999
        px, py = point
        for start, end in zip(self.path, self.path[1:]):
            ax, ay = start
            bx, by = end
            dx = bx - ax
            dy = by - ay
            length_sq = dx * dx + dy * dy
            if length_sq == 0:
                best = min(best, distance(point, start))
                continue
            t = clamp(((px - ax) * dx + (py - ay) * dy) / length_sq, 0, 1)
            closest = (ax + t * dx, ay + t * dy)
            best = min(best, distance(point, closest))
        return best

    def handle_events(self, event):
        return

    def _handle_input(self):
        if self.quit_dialog_open:
            self._handle_quit_dialog_input()
            return True

        if self.input.just_pressed("ESC"):
            if self.state == "info":
                self._close_tower_info()
                return True

            self._open_quit_dialog()
            return True

        if self.game_over:
            if self.input.just_pressed(BUTTON_CONFIRM):
                self.input.close()
                self.__init__(self.manager)
                return True
            return False

        button = self._next_pressed_button()
        if button is None:
            return False

        if self.state == "placing":
            self._handle_placing(button)
        elif self.state == "actions":
            self._handle_actions(button)
        elif self.state == "info":
            self._handle_info(button)
        else:
            self._handle_normal(button)
        return False

    def _open_quit_dialog(self):
        self.quit_dialog_open = True
        self.quit_dialog_index = 1

    def _close_quit_dialog(self):
        self.quit_dialog_open = False
        self.quit_dialog_index = 1

    def _handle_quit_dialog_input(self):
        if self.input.just_pressed("ESC"):
            self._close_quit_dialog()
        elif self.input.just_pressed("LEFT") or self.input.just_pressed("UP"):
            self.quit_dialog_index = (self.quit_dialog_index - 1) % len(self.quit_options)
        elif self.input.just_pressed("RIGHT") or self.input.just_pressed("DOWN"):
            self.quit_dialog_index = (self.quit_dialog_index + 1) % len(self.quit_options)
        elif self.input.just_pressed(BUTTON_CONFIRM):
            if self.quit_options[self.quit_dialog_index] == "Stoppen":
                from ui.Games_menu import Game_Menu
                self.input.close()
                self.manager.set_scene(Game_Menu(self.manager))
            else:
                self._close_quit_dialog()

    def _next_pressed_button(self):
        for button in (BUTTON_INFO, BUTTON_MENU, BUTTON_CONFIRM, *DIRECTION_BUTTONS):
            if self.input.just_pressed(button):
                return button
        return None

    def _handle_normal(self, button):
        if button == BUTTON_INFO:
            self._open_hovered_tower_info()
            return

        if button == BUTTON_MENU:
            self.focus = "field" if self.focus == "menu" else "menu"
            self.message = self._field_hover_message() if self.focus == "field" else self._menu_selection_label()
            return

        if self.focus == "menu":
            if button in DIRECTION_BUTTONS:
                self._move_menu_selection(button)
            elif button == BUTTON_CONFIRM:
                if self.menu_index < self._control_count():
                    self._activate_menu_control()
                else:
                    self._start_placing()
        else:
            self._move_cursor(button)
            if button in DIRECTION_BUTTONS:
                self.message = self._field_hover_message()
            if button == BUTTON_CONFIRM:
                tower = self._tower_at(tuple(self.cursor))
                if tower:
                    self.selected_tower = tower
                    self.action_index = 0
                    self.state = "actions"
                    self.message = "Upgrade, sell, or close."
                else:
                    self.message = "No tower here."

    def _handle_placing(self, button):
        if button == BUTTON_MENU:
            self.state = "playing"
            self.focus = "menu"
            self.message = "Placement canceled."
        elif button == BUTTON_CONFIRM:
            self._place_selected_tower()
        else:
            self._move_cursor(button)

    def _handle_actions(self, button):
        if button == BUTTON_MENU:
            self.state = "playing"
            self.message = "Action closed."
        elif button == "UP":
            self.action_index = (self.action_index - 1) % 3
        elif button == "DOWN":
            self.action_index = (self.action_index + 1) % 3
        elif button == BUTTON_CONFIRM:
            self._confirm_action()

    def _handle_info(self, button):
        if button in (BUTTON_INFO, BUTTON_CONFIRM, BUTTON_MENU):
            self._close_tower_info()

    def _open_hovered_tower_info(self):
        self.info_tower = None
        self.info_tower_name = None

        if self.focus == "field":
            tower = self._tower_at(tuple(self.cursor))
            if tower is None:
                self.message = "No tower here."
                return
            self.info_tower = tower
            self.info_tower_name = tower.name
        else:
            tower_index = self._selected_tower_index()
            if tower_index < 0 or tower_index >= len(self.tower_names):
                self.message = "Select a tower first."
                return
            self.info_tower_name = self.tower_names[tower_index]

        self.state = "info"
        self.message = f"{self._display_name(self.info_tower_name)} info."

    def _close_tower_info(self):
        self.info_tower = None
        self.info_tower_name = None
        self.state = "playing"
        self.message = self._field_hover_message() if self.focus == "field" else self._menu_selection_label()

    def _move_cursor(self, button):
        if button == "LEFT":
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif button == "RIGHT":
            self.cursor[0] = min(COLS - 1, self.cursor[0] + 1)
        elif button == "UP":
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif button == "DOWN":
            self.cursor[1] = min(ROWS - 1, self.cursor[1] + 1)

    def _move_menu_selection(self, button):
        columns = 3
        controls = self._control_count()
        if self.menu_index < controls:
            if button == "LEFT" and self.menu_index > 0:
                self.menu_index -= 1
            elif button == "RIGHT" and self.menu_index + 1 < controls:
                self.menu_index += 1
            elif button == "DOWN":
                self.menu_index = controls + min(self.menu_index, columns - 1)
            self.message = self._menu_selection_label()
            return

        tower_idx = self.menu_index - controls
        row = tower_idx // columns
        col = tower_idx % columns
        total = len(self.tower_names)

        if button == "LEFT" and col > 0:
            tower_idx -= 1
        elif button == "RIGHT" and col < columns - 1 and tower_idx + 1 < total:
            tower_idx += 1
        elif button == "UP":
            if row > 0:
                tower_idx -= columns
            elif controls:
                self.menu_index = min(col, controls - 1)
                self.message = self._menu_selection_label()
                return
        elif button == "DOWN" and tower_idx + columns < total:
            tower_idx += columns

        self.menu_index = controls + tower_idx
        self.message = self._menu_selection_label()

    def _menu_selection_label(self):
        if self.menu_index < self._control_count():
            if self.preparing:
                return "Start game."
            return f"{self.game_speed}x active." if self.menu_index == self.game_speed - 1 else f"Set {self.menu_index + 1}x."

        tower_index = self._selected_tower_index()
        if 0 <= tower_index < len(self.tower_names):
            name = self.tower_names[tower_index]
            cost = int(self.stats["towers"][name].get("cost", 0))
            return f"{self._display_name(name)} ${cost}"
        return ""

    def _field_hover_message(self):
        tower = self._tower_at(tuple(self.cursor))
        if tower:
            return f"{self._display_name(tower.name)} L{tower.level}"
        return "Field cursor."

    def _control_count(self):
        return 1 if self.preparing else 2

    def _selected_tower_index(self):
        return self.menu_index - self._control_count()

    def _activate_menu_control(self):
        if self.preparing:
            self.preparing = False
            self.game_speed = 1
            self.menu_index = 0
            self.message = "Round 1 incoming."
        else:
            self.game_speed = 1 if self.menu_index == 0 else 2
            self.message = f"Speed {self.game_speed}x."

    def _start_placing(self):
        tower_index = self._selected_tower_index()
        if tower_index < 0 or tower_index >= len(self.tower_names):
            return
        name = self.tower_names[tower_index]
        cost = int(self.stats["towers"][name].get("cost", 0))
        if self.money < cost:
            self.message = "Not enough money."
            return
        if len(self.towers) >= MAX_TOWERS:
            self.message = "Tower limit reached."
            return
        if name == "bank" and self._bank_count() >= MAX_BANKS:
            self.message = f"Bank limit reached ({MAX_BANKS})."
            return
        self.state = "placing"
        self.focus = "field"
        self.message = f"D-pad moves. {KEY_CONFIRM_LABEL} places. {KEY_MENU_LABEL} cancels."

    def _place_selected_tower(self):
        cell = tuple(self.cursor)
        tower_index = self._selected_tower_index()
        if tower_index < 0 or tower_index >= len(self.tower_names):
            self.message = "Choose a tower."
            return
        name = self.tower_names[tower_index]
        cost = int(self.stats["towers"][name].get("cost", 0))
        if not self._can_place(cell, name):
            if name == "bank" and self._bank_count() >= MAX_BANKS:
                self.message = f"Bank limit reached ({MAX_BANKS})."
            else:
                self.message = "Can't place there."
            return
        if self.money < cost:
            self.message = "Not enough money."
            return

        self.money -= cost
        self.towers.append(
            Tower(name, self.stats["towers"][name], cell, self.colors[name], total_spent=cost)
        )
        self.state = "playing"
        self.message = f"{self._short_name(name)} placed."

    def _can_place(self, cell, tower_name=None):
        if tower_name is None:
            tower_index = self._selected_tower_index()
            tower_name = (
                self.tower_names[tower_index]
                if 0 <= tower_index < len(self.tower_names)
                else None
            )
        if tower_name == "bank" and self._bank_count() >= MAX_BANKS:
            return False
        path_rule = cell in self.path_cells if tower_name == "bomb" else cell not in self.path_cells
        return (
            0 <= cell[0] < COLS
            and 0 <= cell[1] < ROWS
            and path_rule
            and self._tower_at(cell) is None
            and len(self.towers) < MAX_TOWERS
        )

    def _tower_at(self, cell):
        for tower in self.towers:
            if tower.cell == cell:
                return tower
        return None

    def _bank_count(self):
        return sum(1 for tower in self.towers if tower.name == "bank")

    def _confirm_action(self):
        tower = self.selected_tower
        if tower is None:
            self.state = "playing"
            return

        if self.action_index == 0:
            cost = tower.upgrade_cost
            if cost is None:
                self.message = "Already level 5."
            elif self.money < cost:
                self.message = "Not enough money."
            else:
                self.money -= cost
                tower.total_spent += cost
                tower.level += 1
                self.message = f"Upgraded to L{tower.level}."
        elif self.action_index == 1:
            refund = tower.total_spent if self.preparing else int(tower.total_spent * 0.75)
            self.money += refund
            self.towers.remove(tower)
            self.selected_tower = None
            self.state = "playing"
            self.message = f"Sold for ${refund}."
        else:
            self.state = "playing"
            self.message = "Action closed."

    def update(self, dt):
        self.banner_timer = max(0, self.banner_timer - dt)

        if self._handle_input():
            return

        if self.game_over:
            return

        self._update_held_movement(dt)
        self._spawn_rounds(dt)
        speed_dt = dt * self.game_speed
        self._update_enemies(dt)
        self._update_towers(speed_dt)
        self._update_delayed_attacks(speed_dt)
        self._update_mines()
        self._update_effects(dt)

        if self.lives <= 0:
            self._finish_game()

    def _spawn_rounds(self, dt):
        if self.preparing:
            return

        if not self.spawn_queue and not self.enemies:
            if self.round > 0 and not self.round_cleared_announced:
                self.round_cleared_announced = True
                self._flash_banner(f"Round {self.round} cleared")
                self.message = f"Round {self.round} cleared."
                self.round_timer = max(self.round_timer, 1.4)
            self.round_timer -= dt
            if self.round_timer <= 0:
                self._begin_round()

        if self.spawn_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self._spawn_enemy(self.spawn_queue.pop(0))
                self.spawn_timer = self._next_spawn_delay()

    def _update_held_movement(self, dt):
        if not (self.state == "placing" or (self.state == "playing" and self.focus == "field")):
            self.held_move_key = None
            self.held_move_timer = 0.0
            return

        held_key = None
        for button in DIRECTION_BUTTONS:
            if self.input.is_pressed(button):
                held_key = button
                break

        if held_key is None:
            self.held_move_key = None
            self.held_move_timer = 0.0
            return

        if held_key != self.held_move_key:
            self.held_move_key = held_key
            self.held_move_timer = self.held_move_delay
            return

        self.held_move_timer -= dt
        if self.held_move_timer <= 0:
            self._move_cursor(held_key)
            self.message = self._field_hover_message()
            self.held_move_timer = self.held_move_interval

    def _begin_round(self):
        self.round += 1
        self.round_cleared_announced = False
        queue = self._round_spawn_queue()

        self.spawn_queue = queue
        self.spawn_timer = random.uniform(0.05, 0.16)
        boss_count = queue.count("boss")
        boss_label = f" - Boss x{boss_count}" if boss_count else ""
        self.message = f"Round {self.round}{boss_label}"
        self._flash_banner(f"Round {self.round}{boss_label}")

    def _round_spawn_queue(self):
        round_data = self.stats.get("rounds", {}).get(str(self.round))
        if not round_data:
            return self._generated_spawn_queue()

        enemies = round_data.get("enemies", {})
        queue = []
        for name, count in enemies.items():
            if name not in self.stats["enemies"]:
                continue
            for _ in range(max(0, int(count))):
                queue.append(name)

        if not queue:
            return self._generated_spawn_queue()

        random.shuffle(queue)
        return queue

    def _generated_spawn_queue(self):
        count = 8 + self.round * 3 + random.randint(0, 2 + self.round // 3)
        queue = ["grunt"] * count

        if self.round >= 4 and "fast" in self.stats["enemies"]:
            fast_count = self.round // 4 + random.randint(0, max(1, self.round // 8))
            for _ in range(fast_count):
                queue.insert(random.randrange(len(queue) + 1), "fast")

        tank_count = self.round // 3 + random.randint(0, max(0, self.round // 6))
        for _ in range(tank_count):
            queue.insert(random.randrange(len(queue) + 1), "tank")

        if self.round >= 8 and "armored" in self.stats["enemies"]:
            armored_count = max(1, self.round // 7)
            for _ in range(armored_count):
                queue.insert(random.randrange(len(queue) + 1), "armored")

        if self.round >= 12 and "regenerating" in self.stats["enemies"]:
            regen_count = max(1, self.round // 10)
            for _ in range(regen_count):
                queue.insert(random.randrange(len(queue) + 1), "regenerating")

        if self.round >= 14 and "stealth" in self.stats["enemies"]:
            stealth_count = max(1, self.round // 9)
            for _ in range(stealth_count):
                queue.insert(random.randrange(len(queue) + 1), "stealth")

        if self.round >= 16 and "frost" in self.stats["enemies"]:
            frost_count = max(1, self.round // 12)
            for _ in range(frost_count):
                queue.insert(random.randrange(len(queue) + 1), "frost")

        if self.round >= 18 and "regenerating_fast" in self.stats["enemies"]:
            regen_fast_count = max(1, self.round // 14)
            for _ in range(regen_fast_count):
                queue.insert(random.randrange(len(queue) + 1), "regenerating_fast")

        if self.round % 10 == 0 and "boss" in self.stats["enemies"]:
            boss_count = self.round // 10
            for _ in range(boss_count):
                queue.append("boss")

        return queue

    def _flash_banner(self, text, duration=1.6):
        self.banner_message = text
        self.banner_timer = duration

    def _next_spawn_delay(self):
        fast = max(0.08, 0.34 - self.round * 0.01)
        slow = max(fast + 0.04, 0.58 - self.round * 0.014)
        return random.uniform(fast, slow)

    def _round_factor(self):
        return 1 + (self.round - 1) / 6

    def _spawn_enemy(self, name):
        data = self.stats["enemies"].get(name, self.stats["enemies"][self.enemy_names[0]])
        factor = self._round_factor()
        enemy = Enemy(
            name,
            data["health"] * factor,
            data["health"] * factor,
            max(1, int(data["damage"])),
            data["speed"],
            int(data["reward"]),
        )
        enemy.armored = bool(data.get("armored"))
        enemy.stealth = bool(data.get("stealth"))
        enemy.regeneration_rate = data.get("regeneration_rate", 0.0)
        enemy.regeneration_amount = data.get("regeneration_amount", 0.0) * factor * 0.5
        enemy.regeneration_timer = enemy.regeneration_rate
        enemy.freeze_radius = data.get("freeze_radius", 0.0)
        enemy.freeze_duration = data.get("freeze_duration", 0.0)
        enemy.x, enemy.y = self.path[0]
        self.enemies.append(enemy)

    def _update_enemies(self, dt):
        for enemy in list(self.enemies):
            escaped = enemy.update(dt, self.path, self.game_speed)
            if enemy.health <= 0:
                self._trigger_frost_death(enemy)
                self.money += enemy.reward
                self.texts.append(FloatingText(f"+{enemy.reward}", enemy.x, enemy.y - 8, (255, 236, 130)))
                self.enemies.remove(enemy)
            elif escaped:
                self.lives -= enemy.damage
                self.texts.append(FloatingText(f"-{enemy.damage}", FIELD_WIDTH - 35, 20, (240, 80, 80)))
                self.enemies.remove(enemy)

    def _update_towers(self, dt):
        for tower in list(self.towers):
            tower.freeze_timer = max(0, tower.freeze_timer - dt)
            tower.cooldown = max(0, tower.cooldown - dt)
            tower.flash_timer = max(0, tower.flash_timer - dt)
            if tower.freeze_timer > 0:
                continue
            if tower.name == "inferno":
                self._update_inferno(tower, dt)
                continue
            if tower.name == "black hole generator":
                self._update_black_hole(tower, dt)
                continue
            if tower.name == "bank":
                self._update_bank(tower, dt)
                continue
            if tower.name == "mine placer":
                self._update_mine_placer(tower)
                continue
            if tower.cooldown <= 0:
                if self._fire_tower(tower):
                    tower.cooldown = 1 / self._tower_fire_rate(tower)
                    tower.flash_timer = 0.08

    def _update_inferno(self, tower, dt):
        targets = self._targets_in_range(tower)
        if not targets:
            tower.inferno_target = None
            tower.inferno_charge = 0.0
            return

        target = tower.inferno_target
        if target not in targets:
            target = targets[0]
            tower.inferno_target = target
            tower.inferno_charge = 0.0

        tower.inferno_charge = min(tower.stat("time_to_max_damage", 5.0), tower.inferno_charge + dt)
        damage = self._tower_damage(tower)
        max_dps = tower.stat("max_damage_per_second", tower.damage) * self._buffer_multiplier(tower)
        ramp_time = max(0.01, tower.stat("time_to_max_damage", 5.0))
        ramp = clamp(tower.inferno_charge / ramp_time, 0, 1)
        dps = damage + (max_dps - damage) * ramp
        self._damage_enemy(target, tower, dps * dt)
        self.shots.append((tower.center, target, 0, tower.color, 0.05))
        tower.flash_timer = 0.05

    def _update_black_hole(self, tower, dt):
        affected = False
        max_slow = clamp(tower.stat("pull_strength", 0.2), 0, 0.9)
        tower_range = self._tower_range(tower)
        radius = tower.stat("pull_radius", tower_range) or tower_range
        damage = self._tower_damage(tower) * dt
        for enemy in self.enemies:
            if not self._tower_can_hit_enemy(tower, enemy):
                continue
            dist = distance(tower.center, (enemy.x, enemy.y))
            if dist > tower_range:
                continue
            self._damage_enemy(enemy, tower, damage)
            if not self._can_slow(enemy):
                affected = True
                continue
            closeness = 1 - clamp(dist / max(1, radius), 0, 1)
            slow_factor = 1 - max_slow * closeness
            previous_slow = enemy.slow_factor if enemy.slow_timer > 0 else 1.0
            enemy.slow_timer = max(enemy.slow_timer, 0.14)
            enemy.slow_factor = min(previous_slow, slow_factor)
            affected = True

        if affected:
            tower.flash_timer = 0.05
            if tower.cooldown <= 0:
                self.shots.append((tower.center, None, tower_range, tower.color, 0.10))
                tower.cooldown = 1 / tower.fire_rate

    def _update_bank(self, tower, dt):
        interval = max(0.05, tower.stat("money_generation_interval", 1.0))
        if tower.income_timer <= 0:
            tower.income_timer = interval

        tower.income_timer -= dt
        while tower.income_timer <= 0:
            income = int(tower.stat("money_generation", 0))
            if income <= 0:
                tower.income_timer = interval
                return
            self.money += income
            self.texts.append(FloatingText(f"+{income}", tower.center[0] - 6, tower.center[1] - 14, (255, 236, 130)))
            tower.flash_timer = 0.08
            tower.income_timer += interval

    def _update_mine_placer(self, tower):
        if tower.cooldown > 0:
            return
        active_mines = sum(1 for mine in self.mines if mine.owner is tower)
        if active_mines >= int(tower.stat("max_mines_per_tower", 4)):
            return
        px, py = self._mine_position_near_tower(tower)
        mine_damage = 28 * (1.25 ** (tower.level - 1)) * self._buffer_multiplier(tower)
        mine = Mine(px, py, mine_damage, 36, tower.stat("trigger_radius", 30), tower.color, tower)
        self.mines.append(mine)
        tower.cooldown = 1 / tower.fire_rate
        tower.flash_timer = 0.08

    def _mine_position_near_tower(self, tower):
        cx, cy = tower.center
        tower_range = self._tower_range(tower)
        for _ in range(35):
            start, end = random.choice(list(zip(self.path, self.path[1:])))
            t = random.random()
            px = start[0] + (end[0] - start[0]) * t
            py = start[1] + (end[1] - start[1]) * t
            angle = random.random() * math.tau
            jitter = random.uniform(0, min(10, tower_range * 0.25))
            px += math.cos(angle) * jitter
            py += math.sin(angle) * jitter
            if 0 <= px <= FIELD_WIDTH and 0 <= py <= BASE_HEIGHT and distance((cx, cy), (px, py)) <= tower_range:
                return px, py

        angle = random.random() * math.tau
        radius = random.uniform(0, tower_range)
        return (
            clamp(cx + math.cos(angle) * radius, 0, FIELD_WIDTH),
            clamp(cy + math.sin(angle) * radius, 0, BASE_HEIGHT),
        )

    def _fire_tower(self, tower):
        targets = self._targets_in_range(tower)
        if not targets:
            return False

        if tower.base.get("360_degree_attack"):
            damage = self._tower_damage(tower)
            for enemy in targets:
                self._damage_enemy(enemy, tower, damage)
            if tower.base.get("delayed_2nd_attack"):
                delay = tower.stat("delay_duration", 0.25)
                self.delayed_attacks.append(DelayedAttack(delay, tower, list(targets), damage * 0.5))
            self.shots.append((tower.center, None, self._tower_range(tower), tower.color, 0.08))
            return True

        if tower.base.get("piercing"):
            line_targets, endpoint = self._piercing_line_targets(tower, targets[0])
            for enemy in line_targets:
                self._damage_enemy(enemy, tower, self._tower_damage(tower))
            self.shots.append((tower.center, endpoint, 0, tower.color, 0.12))
            return True

        if tower.base.get("chain_effect"):
            chain = [targets[0]]
            for enemy in targets[1:]:
                if len(chain) >= 3:
                    break
                if distance((enemy.x, enemy.y), (chain[-1].x, chain[-1].y)) <= tower.stat("chain_range", 3) * GRID:
                    chain.append(enemy)
            for enemy in chain:
                self._damage_enemy(enemy, tower, self._tower_damage(tower))
            self.shots.append((tower.center, chain[0], 0, tower.color, 0.08))
            return True

        target = targets[0]
        damage = self._tower_damage(tower)
        self._damage_enemy(target, tower, damage)
        if tower.base.get("knockback_distance") and self._can_knock_back(target):
            target.knock_back(self.path, tower.stat("knockback_distance", 0))
        splash = tower.stat("splash_damage", 0) or tower.stat("explosion_radius", 0)
        if splash:
            for enemy in self.enemies:
                if (
                    enemy is not target
                    and self._tower_can_hit_enemy(tower, enemy)
                    and distance((enemy.x, enemy.y), (target.x, target.y)) <= splash
                ):
                    self._damage_enemy(enemy, tower, damage * 0.55)
            if tower.name == "bomb":
                self.towers.remove(tower)
                if self.selected_tower is tower:
                    self.selected_tower = None
        self.shots.append((tower.center, target, splash, tower.color, 0.08))
        return True

    def _tower_damage(self, tower):
        damage = tower.damage * self._buffer_multiplier(tower)
        if tower.base.get("upgrade_link"):
            damage *= self._upgrade_link_multiplier(tower)
        return damage

    def _tower_range(self, tower):
        return tower.range * self._buffer_multiplier(tower)

    def _buffer_multiplier(self, tower):
        best_bonus = 0.0
        for buffer_tower in self.towers:
            if buffer_tower is tower or buffer_tower.name != "buffer":
                continue
            if distance(buffer_tower.center, tower.center) <= buffer_tower.range:
                best_bonus = max(best_bonus, buffer_tower.stat("buff_effect", 0.125))
        return 1.0 + best_bonus

    def _tower_fire_rate(self, tower):
        fire_rate = tower.fire_rate
        if tower.base.get("upgrade_link"):
            fire_rate *= self._upgrade_link_multiplier(tower)
        return fire_rate

    def _upgrade_link_multiplier(self, tower):
        links = self._nearby_upgrade_links(tower)
        return 1 + len(links) * tower.stat("upgrade_effect", 0.2)

    def _nearby_upgrade_links(self, tower):
        link_range = tower.stat("upgrade_range", tower.range)
        max_links = int(tower.stat("upgrade_max_links", 9999))
        links = [
            (distance(tower.center, other.center), other) for other in self.towers
            if other is not tower
            and other.base.get("upgrade_link")
            and distance(tower.center, other.center) <= link_range
        ]
        links.sort(key=lambda item: item[0])
        return [other for _, other in links[:max_links]]

    def _update_delayed_attacks(self, dt):
        for attack in list(self.delayed_attacks):
            attack.timer -= dt
            if attack.timer > 0:
                continue
            self.delayed_attacks.remove(attack)
            if attack.tower not in self.towers or attack.tower.freeze_timer > 0:
                continue
            hit_any = False
            for enemy in attack.targets:
                if enemy in self.enemies and self._tower_can_hit_enemy(attack.tower, enemy):
                    self._damage_enemy(enemy, attack.tower, attack.damage)
                    hit_any = True
            if hit_any:
                self.shots.append((attack.tower.center, None, self._tower_range(attack.tower), attack.tower.color, 0.10))

    def _targets_in_range(self, tower):
        cx, cy = tower.center
        tower_range = self._tower_range(tower)
        targets = [
            e for e in self.enemies
            if self._tower_can_hit_enemy(tower, e)
            and distance((cx, cy), (e.x, e.y)) <= tower_range
        ]
        targets.sort(key=lambda enemy: self._target_sort_key(tower, enemy))
        return targets

    def _tower_can_hit_enemy(self, tower, enemy):
        return not enemy.stealth or tower.base.get("detect_stealth", False)

    def _target_sort_key(self, tower, enemy):
        priority = tower.base.get("targeting_priority", "first")
        if priority == "strongest":
            return (-enemy.health, -enemy.max_health, -enemy.progress)
        if priority == "weakest":
            return (enemy.health, enemy.max_health, -enemy.progress)
        if priority == "last":
            return (enemy.progress,)
        return (-enemy.progress,)

    def _piercing_line_targets(self, tower, primary):
        cx, cy = tower.center
        dx = primary.x - cx
        dy = primary.y - cy
        length = math.hypot(dx, dy)
        if length <= 0:
            return [primary], tower.center

        ux = dx / length
        uy = dy / length
        shot_range = self._tower_range(tower) * tower.base.get("pierce_range_multiplier", PIERCING_RANGE_MULTIPLIER)
        endpoint = (cx + ux * shot_range, cy + uy * shot_range)
        line_width = max(7, GRID * 0.35)
        hits = []
        for enemy in self.enemies:
            if not self._tower_can_hit_enemy(tower, enemy):
                continue
            ex = enemy.x - cx
            ey = enemy.y - cy
            along = ex * ux + ey * uy
            if along < 0 or along > shot_range:
                continue
            perpendicular = abs(ex * uy - ey * ux)
            if perpendicular <= line_width:
                hits.append((along, enemy))

        hits.sort(key=lambda item: item[0])
        return ([enemy for _, enemy in hits] or [primary]), endpoint

    def _damage_enemy(self, enemy, tower, amount):
        if enemy.armored:
            amount *= 0.65
        enemy.health -= amount
        enemy._shed_armor_if_weakened()
        if tower.base.get("slow_effect"):
            self._apply_slow_area(enemy, tower)
        self._apply_status_effects(enemy, tower)

    def _trigger_frost_death(self, enemy):
        if enemy.freeze_radius <= 0 or enemy.freeze_duration <= 0:
            return
        for tower in self.towers:
            if distance(tower.center, (enemy.x, enemy.y)) <= enemy.freeze_radius:
                tower.freeze_timer = max(tower.freeze_timer, enemy.freeze_duration)

    def _apply_slow_area(self, enemy, tower):
        area = tower.stat("area_of_effect", 0)
        affected = self.enemies if area else [enemy]
        for other in affected:
            if not self._can_slow(other):
                continue
            if self._tower_can_hit_enemy(tower, other) and (not area or distance((enemy.x, enemy.y), (other.x, other.y)) <= area):
                other.slow_timer = 1.4
                other.slow_factor = tower.base["slow_effect"]

    def _apply_status_effects(self, enemy, tower):
        if tower.base.get("freeze_duration") and self._can_freeze(enemy):
            enemy.freeze_timer = max(enemy.freeze_timer, tower.stat("freeze_duration"))
        if tower.base.get("poison_duration"):
            enemy.poison_timer = max(enemy.poison_timer, tower.stat("poison_duration"))
            enemy.poison_dps = max(enemy.poison_dps, tower.damage * 0.25)
        if tower.base.get("burn_duration"):
            enemy.burn_timer = max(enemy.burn_timer, tower.stat("burn_duration"))
            enemy.burn_dps = max(enemy.burn_dps, tower.damage * 0.35)
        if tower.base.get("stun_effect") and random.random() < tower.base["stun_effect"]:
            enemy.stun_timer = max(enemy.stun_timer, 0.45)

    def _can_freeze(self, enemy):
        return enemy.kind != "boss"

    def _can_knock_back(self, enemy):
        return enemy.kind != "boss" and not enemy.armored

    def _can_slow(self, enemy):
        return not enemy.armored

    def _update_mines(self):
        for mine in list(self.mines):
            hit = None
            for enemy in self.enemies:
                if enemy.stealth and not mine.owner.base.get("detect_stealth", False):
                    continue
                if distance((mine.x, mine.y), (enemy.x, enemy.y)) <= mine.trigger:
                    hit = enemy
                    break
            if hit:
                for enemy in self.enemies:
                    if enemy.stealth and not mine.owner.base.get("detect_stealth", False):
                        continue
                    if distance((mine.x, mine.y), (enemy.x, enemy.y)) <= mine.radius:
                        damage = mine.damage * 0.65 if enemy.armored else mine.damage
                        enemy.health -= damage
                self.shots.append(((mine.x, mine.y), None, mine.radius, mine.color, 0.16))
                self.mines.remove(mine)

    def _update_effects(self, dt):
        self.shots = [(a, b, r, c, t - dt) for a, b, r, c, t in self.shots if t - dt > 0]
        for text in list(self.texts):
            text.timer -= dt
            text.y -= 18 * dt
            if text.timer <= 0:
                self.texts.remove(text)

    def draw(self, surface):
        self._draw_field(surface)
        self._draw_path(surface)
        self._draw_mines(surface)
        self._draw_upgrade_links(surface)
        self._draw_towers(surface)
        self._draw_tower_range(surface)
        self._draw_enemies(surface)
        self._draw_shots(surface)
        self._draw_cursor(surface)
        self._draw_texts(surface)
        self._draw_hud(surface)
        self._draw_menu(surface)
        self._draw_banner(surface)
        if self.state == "info":
            self._draw_tower_info(surface)

        if self.game_over:
            self._draw_game_over(surface)

        if self.quit_dialog_open:
            self._draw_quit_dialog(surface)

    def _draw_field(self, surface):
        surface.fill((75, 122, 86))
        for y in range(0, BASE_HEIGHT, GRID):
            pygame.draw.line(surface, (88, 138, 97), (0, y), (FIELD_WIDTH, y))
        for x in range(0, FIELD_WIDTH, GRID):
            pygame.draw.line(surface, (88, 138, 97), (x, 0), (x, BASE_HEIGHT))

        if self.state == "placing":
            for y in range(ROWS):
                for x in range(COLS):
                    rect = pygame.Rect(x * GRID, y * GRID, GRID, GRID)
                    pygame.draw.rect(surface, (0, 0, 0), rect, 1)

    def _draw_path(self, surface):
        pygame.draw.lines(surface, (171, 139, 93), False, self.path, PATH_WIDTH)
        pygame.draw.lines(surface, (117, 91, 59), False, self.path, 2)

    def _draw_mines(self, surface):
        for mine in self.mines:
            pygame.draw.circle(surface, mine.color, (int(mine.x), int(mine.y)), 4)
            pygame.draw.circle(surface, (20, 25, 25), (int(mine.x), int(mine.y)), 4, 1)

    def _draw_upgrade_links(self, surface):
        links = [tower for tower in self.towers if tower.base.get("upgrade_link")]
        drawn = set()
        for tower in links:
            for other in self._nearby_upgrade_links(tower):
                key = tuple(sorted((id(tower), id(other))))
                if key in drawn:
                    continue
                drawn.add(key)
                pulse = 1 + int((tower.flash_timer > 0 or other.flash_timer > 0))
                pygame.draw.line(surface, (150, 235, 255), tower.center, other.center, pulse)
                mid = ((tower.center[0] + other.center[0]) // 2, (tower.center[1] + other.center[1]) // 2)
                pygame.draw.circle(surface, (245, 250, 190), mid, 2)

    def _draw_towers(self, surface):
        for tower in self.towers:
            x, y = tower.cell[0] * GRID, tower.cell[1] * GRID
            rect = pygame.Rect(x + 2, y + 2, GRID - 4, GRID - 4)
            self._draw_tower_icon(surface, tower.name, rect)
            pygame.draw.rect(surface, (22, 28, 32), rect, 1, border_radius=3)
            if tower.freeze_timer > 0:
                pygame.draw.rect(surface, (160, 225, 255), rect, 2, border_radius=3)
            if tower.flash_timer > 0:
                pygame.draw.circle(surface, (255, 245, 180), tower.center, 3)
            pygame.draw.rect(surface, (12, 16, 18), (x + 4, y + 3, 4, 8), border_radius=2)
            level = self.small_font.render(str(tower.level), True, (255, 255, 255))
            surface.blit(level, (x + 4, y + 2.5))

    def _draw_enemies(self, surface):
        for enemy in self.enemies:
            color = self._enemy_color(enemy)
            radius = 11 if enemy.kind == "boss" else 8 if enemy.armored else 6 
            pygame.draw.circle(surface, color, (int(enemy.x), int(enemy.y)), radius)
            if enemy.stealth:
                pygame.draw.circle(surface, (205, 215, 230), (int(enemy.x), int(enemy.y)), radius + 2, 1)
            pygame.draw.circle(surface, (35, 25, 25), (int(enemy.x), int(enemy.y)), radius, 1)
            bar_w = 24 if enemy.kind == "boss" else 16
            ratio = clamp(enemy.health / enemy.max_health, 0, 1)
            pygame.draw.rect(surface, (35, 35, 35), (enemy.x - bar_w // 2, enemy.y - radius - 6, bar_w, 3))
            pygame.draw.rect(surface, (84, 220, 104), (enemy.x - bar_w // 2, enemy.y - radius - 6, int(bar_w * ratio), 3))

    def _enemy_color(self, enemy):
        colors = {
            "grunt": (185, 67, 66),
            "tank": (102, 70, 58),
            "fast": (225, 152, 64),
            "boss": (120, 42, 132),
            "armored": (96, 104, 112),
            "regenerating": (75, 166, 96),
            "stealth": (106, 112, 132),
            "frost": (92, 180, 218),
            "regenerating_fast": (73, 184, 142),
        }
        return colors.get(enemy.kind, (185, 67, 66))

    def _draw_shots(self, surface):
        for origin, target, radius, color, timer in self.shots:
            alpha_color = tuple(min(255, c + 45) for c in color)
            if target is not None:
                if hasattr(target, "x"):
                    end = (int(target.x), int(target.y))
                else:
                    end = (int(target[0]), int(target[1]))
                pygame.draw.line(surface, alpha_color, origin, end, 2)
            if radius:
                pygame.draw.circle(surface, alpha_color, (int(origin[0]), int(origin[1])), int(radius), 1)

    def _draw_banner(self, surface):
        if self.banner_timer <= 0 or not self.banner_message:
            return

        alpha = int(210 * clamp(self.banner_timer / 0.35, 0, 1)) if self.banner_timer < 0.35 else 210
        label = self.title_font.render(self.banner_message, True, (255, 246, 196))
        rect = label.get_rect(center=(FIELD_WIDTH // 2, 34))
        pad_x, pad_y = 12, 6
        box = pygame.Rect(rect.x - pad_x, rect.y - pad_y, rect.width + pad_x * 2, rect.height + pad_y * 2)
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill((20, 26, 30, alpha))
        surface.blit(overlay, box.topleft)
        pygame.draw.rect(surface, (248, 210, 93), box, 1, border_radius=4)
        surface.blit(label, rect)

    def _draw_tower_range(self, surface):
        tower = self.selected_tower if self.state == "actions" else None
        if tower is None and self.state == "info":
            tower = self.info_tower
        if tower is None and self.focus == "field" and self.state == "playing":
            tower = self._tower_at(tuple(self.cursor))
        if tower is None:
            return

        radius = tower.stat("upgrade_range", tower.range) if tower.base.get("upgrade_link") else self._tower_range(tower)
        pygame.draw.circle(surface, tuple(min(255, c + 65) for c in tower.color), tower.center, int(radius), 1)

    def _draw_cursor(self, surface):
        if self.focus != "field" and self.state != "placing":
            return
        rect = pygame.Rect(self.cursor[0] * GRID, self.cursor[1] * GRID, GRID, GRID)
        valid = self._can_place(tuple(self.cursor))
        color = (250, 226, 102) if self.state != "placing" else ((80, 240, 120) if valid else (230, 60, 60))
        pygame.draw.rect(surface, color, rect, 2)
        if self.state == "placing":
            tower_index = self._selected_tower_index()
            if tower_index < 0 or tower_index >= len(self.tower_names):
                return
            name = self.tower_names[tower_index]
            cx, cy = rect.center
            preview_rect = pygame.Rect(0, 0, GRID - 6, GRID - 6)
            preview_rect.center = (cx, cy)
            self._draw_tower_icon(surface, name, preview_rect)
            pygame.draw.rect(surface, (22, 28, 32), preview_rect, 1, border_radius=3)
            pygame.draw.circle(surface, (0, 0, 0), (cx, cy), int(self.stats["towers"][name].get("range", 0)), 1)

    def _draw_texts(self, surface):
        for text in self.texts:
            label = self.small_font.render(text.text, True, text.color)
            surface.blit(label, (int(text.x), int(text.y)))

    def _draw_hud(self, surface):
        values = [
            f"${self.money}",
            "Prep" if self.preparing else f"R{self.round}",
            f"L{self.lives}",
            f"T{len(self.towers)}/{MAX_TOWERS}",
            f"{KEY_MENU_LABEL} Menu" if self.focus != "menu" else f"{KEY_MENU_LABEL} Close",
        ]
        text = "  ".join(values)
        label = self.small_font.render(text, True, (242, 244, 236))
        box = pygame.Rect(4, 4, label.get_width() + 10, 15)
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill((20, 26, 30, 170))
        surface.blit(overlay, box.topleft)
        pygame.draw.rect(surface, (248, 210, 93), box, 1, border_radius=3)
        surface.blit(label, (box.x + 5, box.y + 4))

    def _draw_menu(self, surface):
        if self.focus != "menu" and self.state != "actions":
            return

        menu = pygame.Rect(MENU_X, 0, MENU_WIDTH, BASE_HEIGHT)
        overlay = pygame.Surface(menu.size, pygame.SRCALPHA)
        overlay.fill((31, 40, 48, 232))
        surface.blit(overlay, menu.topleft)
        pygame.draw.line(surface, (8, 12, 16), (MENU_X, 0), (MENU_X, BASE_HEIGHT), 2)

        stats = [
            f"${self.money}                      {'Preperation' if self.preparing else f'R{self.round}'}",
            f"Lives {self.lives}                   Towers {len(self.towers)}/{MAX_TOWERS}",
        ]
        for i, value in enumerate(stats):
            label = self.menu_font.render(value, True, (242, 244, 236))
            surface.blit(label, (MENU_X + 6, 5 + i * 12))

        if self.state == "actions":
            self._draw_action_menu(surface)
        else:
            self._draw_control_menu(surface)
            self._draw_tower_menu(surface)

        lines = self._wrap_text(self.message, MENU_WIDTH - 5)[:3]
        for i, line in enumerate(lines):
            label = self.small_font.render(line, True, (230, 236, 220))
            surface.blit(label, (MENU_X + 6, 244 + i * 9))

    def _draw_tower_menu(self, surface):
        padding = 4
        gap = 3
        start_x = MENU_X + padding
        start_y = 60
        columns = 3
        slot_width = (MENU_WIDTH - padding * 2 - gap) // columns
        slot_height = 20

        for idx, name in enumerate(self.tower_names):
            col = idx % columns
            row = idx // columns
            x = start_x + col * (slot_width + gap)
            y = start_y + row * (slot_height + gap)
            name = self.tower_names[idx]
            selected = (
                self.menu_index == self._control_count() + idx
                and self.focus == "menu"
                and self.state != "placing"
            )
            fill = (248, 210, 93) if selected else (52, 65, 74)
            rect = pygame.Rect(x, y, slot_width, slot_height)
            pygame.draw.rect(surface, fill, rect, border_radius=3)
            icon_rect = pygame.Rect(rect.x + 2, rect.y + 3, 14, 14)
            has_image = self._draw_tower_icon(surface, name, icon_rect)
            if has_image:
                pygame.draw.rect(surface, (22, 28, 32), icon_rect, 1, border_radius=2)
            cost = int(self.stats["towers"][name].get("cost", 0))
            text_color = (25, 28, 30) if selected else (235, 240, 232)
            name_label = self.font.render(self._abbr_name(name), True, text_color)
            cost_label = self.font.render(str(cost), True, text_color)
            name_y = rect.y + 1
            surface.blit(name_label, (rect.x + 18, name_y))
            surface.blit(cost_label, (rect.x + 18, name_y + name_label.get_height() - 2.5))

    def _draw_control_menu(self, surface):
        padding = 4
        gap = 4
        y = 35
        if self.preparing:
            rect = pygame.Rect(MENU_X + padding, y, MENU_WIDTH - padding * 2, 19)
            selected = self.menu_index == 0 and self.focus == "menu"
            fill = (248, 210, 93) if selected else (63, 91, 70)
            pygame.draw.rect(surface, fill, rect, border_radius=3)
            color = (25, 28, 30) if selected else (235, 240, 232)
            label = self.small_font.render("Start", True, color)
            surface.blit(label, label.get_rect(center=rect.center))
            return

        button_width = (MENU_WIDTH - padding * 2 - gap) // 2
        for i, text in enumerate(("1x", "2x")):
            rect = pygame.Rect(MENU_X + padding + i * (button_width + gap), y, button_width, 19)
            selected = self.menu_index == i and self.focus == "menu"
            active = self.game_speed == i + 1
            fill = (248, 210, 93) if selected else ((74, 111, 84) if active else (52, 65, 74))
            pygame.draw.rect(surface, fill, rect, border_radius=3)
            color = (25, 28, 30) if selected else (235, 240, 232)
            label = self.small_font.render(text, True, color)
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_action_menu(self, surface):
        tower = self.selected_tower
        title = self._short_name(tower.name) if tower else "Tower"
        label = self.font.render(title, True, (245, 245, 245))
        surface.blit(label, (MENU_X + 6, 60))
        level = self.font.render(f"L{tower.level}" if tower else "", True, (245, 245, 245))
        surface.blit(level, (MENU_X + 6, 74))

        upgrade_cost = tower.upgrade_cost if tower and tower.upgrade_cost is not None else "--"
        sell_value = (tower.total_spent if self.preparing else int(tower.total_spent * 0.75)) if tower else 0
        options = [f"Up {upgrade_cost}", f"Sell {sell_value}", "Close"]
        for i, option in enumerate(options):
            y = 96 + i * 22
            selected = i == self.action_index
            fill = (248, 210, 93) if selected else (52, 65, 74)
            rect = pygame.Rect(MENU_X + 6, y, MENU_WIDTH - 12, 18)
            pygame.draw.rect(surface, fill, rect, border_radius=3)
            color = (25, 28, 30) if selected else (235, 240, 232)
            option_label = self.small_font.render(option, True, color)
            surface.blit(option_label, (rect.x + 4, rect.y + 5))

        self._draw_upgrade_preview(surface, tower)

    def _draw_upgrade_preview(self, surface, tower):
        if tower is None:
            return

        green = (105, 238, 132)
        y = 164
        if tower.upgrade_cost is None:
            label = self.small_font.render("Max level", True, green)
            surface.blit(label, (MENU_X + 6, y))
            return

        current_damage, damage_gain, current_range, range_gain = self._upgrade_preview_values(tower)
        self._draw_upgrade_preview_line(surface, "Damage", current_damage, damage_gain, y, green)
        self._draw_upgrade_preview_line(surface, "Range", current_range, range_gain, y + 10, green)

    def _draw_upgrade_preview_line(self, surface, label, current, gain, y, gain_color):
        x = MENU_X + 6
        current_text = f"{label}: {self._format_stat(current)} "
        current_label = self.small_font.render(current_text, True, (235, 240, 232))
        surface.blit(current_label, (x, y))

        gain_label = self.small_font.render(f"+{self._format_stat(gain)}", True, gain_color)
        surface.blit(gain_label, (x + current_label.get_width(), y))

    def _upgrade_preview_values(self, tower):
        next_level = tower.level + 1
        if tower.name == "mine placer":
            current_damage = 28 * (1.25 ** (tower.level - 1))
            next_damage = 28 * (1.25 ** (next_level - 1))
        else:
            current_damage = tower.damage
            next_damage = self._tower_info_stat(tower.base, "damage", next_level, 0)
        current_range = tower.range
        next_range = self._tower_info_stat(tower.base, "range", next_level, 0)
        return current_damage, next_damage - current_damage, current_range, next_range - current_range

    def _draw_tower_info(self, surface):
        if not self.info_tower_name:
            return

        box = pygame.Rect(34, 28, BASE_WIDTH - 68, BASE_HEIGHT - 56)
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 90))
        surface.blit(overlay, (0, 0))

        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((28, 37, 44, 238))
        surface.blit(panel, box.topleft)
        pygame.draw.rect(surface, (248, 210, 93), box, 2, border_radius=5)

        color = self.colors.get(self.info_tower_name, (230, 230, 230))
        icon_rect = pygame.Rect(box.x + 10, box.y + 10, 24, 24)
        if not self._draw_tower_icon(surface, self.info_tower_name, icon_rect):
            pygame.draw.rect(surface, color, icon_rect, border_radius=3)
        pygame.draw.rect(surface, (22, 28, 32), icon_rect, 1, border_radius=3)

        level = self.info_tower.level if self.info_tower else 1
        title = self._display_name(self.info_tower_name)
        if self.info_tower:
            title = f"{title} L{level}"
        title_label = self.title_font.render(title, True, (250, 250, 244))
        surface.blit(title_label, (box.x + 42, box.y + 10))

        y = box.y + 42
        for line in self._tower_info_lines(self.info_tower_name, level):
            for wrapped in self._wrap_text(line, box.width - 24):
                label = self.info_font.render(wrapped, True, (232, 238, 226))
                surface.blit(label, (box.x + 12, y))
                y += 20
            y += 2
            if y > box.bottom - 22:
                break

        hint = self.small_font.render(
            f"{KEY_INFO_LABEL}/{KEY_CONFIRM_LABEL}/{KEY_MENU_LABEL} closes",
            True,
            (248, 210, 93),
        )
        surface.blit(hint, (box.right - hint.get_width() - 10, box.bottom - 16))

    def _tower_info_lines(self, name, level=1):
        base = self.stats["towers"].get(name, {})
        cost = int(base.get("cost", 0))
        damage = self._tower_info_stat(base, "damage", level, 0)
        tower_range = self._tower_info_stat(base, "range", level, 0)
        fire_rate = self._tower_info_stat(base, "fire_rate", level, 0)

        lines = [f"Cost ${cost}"]
        if damage:
            lines.append(f"Damage {self._format_stat(damage)}")
        elif name == "mine placer":
            lines.append(f"Mine damage {self._format_stat(28 * (1.25 ** (level - 1)))}")
        else:
            lines.append("Damage 0")
        lines.append(f"Range {self._format_stat(tower_range)}")
        if fire_rate:
            lines.append(f"Fire rate {self._format_stat(fire_rate)} shots/sec")

        abilities = self._tower_ability_lines(base, level)
        if abilities:
            lines.append("Abilities:")
            lines.extend(abilities)
        return lines

    def _tower_info_stat(self, base, key, level, default=0):
        value = base.get(key, default)
        if not isinstance(value, (int, float)):
            return value
        if key == "range":
            return value * (1.10 ** (level - 1))
        if key == "buff_effect":
            return value * (1 + (level - 1) / 4)
        if key in (
            "trigger_radius", "chain_range", "area_of_effect", "poison_duration", "burn_duration",
            "freeze_duration", "delay_duration", "time_to_max_damage", "pull_strength",
            "pull_radius", "upgrade_range", "upgrade_effect", "upgrade_max_links", "knockback_distance",
            "money_generation_interval",
        ):
            return value
        return value * (1.25 ** (level - 1))

    def _tower_ability_lines(self, base, level):
        lines = []
        if base.get("targeting_priority"):
            lines.append(f"Targets {base['targeting_priority']} enemies first")
        if base.get("piercing"):
            pierce_range = self._tower_info_stat(base, "range", level, 0) * base.get("pierce_range_multiplier", PIERCING_RANGE_MULTIPLIER)
            lines.append(f"Piercing shot travels {self._format_stat(pierce_range)} px in a line")
        if base.get("360_degree_attack"):
            lines.append("Hits every enemy inside range")
        if base.get("splash_damage"):
            lines.append(f"Splash damage around the target: {self._format_stat(base['splash_damage'])}")
        if base.get("explosion_radius"):
            lines.append(f"Explodes in a {self._format_stat(base['explosion_radius'])} px radius")
        if base.get("chain_effect"):
            lines.append(f"Chains to nearby enemies within {self._format_stat(base.get('chain_range', 0) * GRID)} px")
        if base.get("slow_effect"):
            slow_percent = int((1 - base["slow_effect"]) * 100)
            lines.append(f"Slows enemies by {slow_percent}%")
        if base.get("delayed_2nd_attack"):
            lines.append("Fires a delayed second hit for 50% damage")
        if base.get("increasing_damage"):
            max_dps = self._tower_info_stat(base, "max_damage_per_second", level, 0)
            ramp_time = self._tower_info_stat(base, "time_to_max_damage", level, 0)
            lines.append(f"Locks onto one enemy and ramps to {self._format_stat(max_dps)} DPS over {self._format_stat(ramp_time)} sec")
        if base.get("pull_strength"):
            slow_percent = int(base["pull_strength"] * 100)
            lines.append(f"Slows enemies by up to {slow_percent}% near the center")
        if base.get("knockback_distance"):
            lines.append(f"Knocks enemies back {self._format_stat(base['knockback_distance'])} px")
        if base.get("upgrade_link"):
            effect_percent = int(base.get("upgrade_effect", 0) * 100)
            link_range = self._tower_info_stat(base, "upgrade_range", level, 0)
            max_links = int(self._tower_info_stat(base, "upgrade_max_links", level, 9999))
            lines.append(f"Links to up to {max_links} upgrade links within {self._format_stat(link_range)} px for +{effect_percent}% damage/fire rate each")
        if base.get("buff_effect"):
            effect_percent = int(self._tower_info_stat(base, "buff_effect", level, 0) * 100)
            lines.append(f"Buffs nearby towers once with +{effect_percent}% damage and range")
        if base.get("money_generation"):
            income = self._tower_info_stat(base, "money_generation", level, 0)
            interval = self._tower_info_stat(base, "money_generation_interval", level, 1.0)
            lines.append(f"Generates ${self._format_stat(income)} every {self._format_stat(interval)} sec. Max {MAX_BANKS} banks")
        if base.get("freeze_duration"):
            lines.append(f"Freezes for {self._format_stat(base['freeze_duration'])} sec")
        if base.get("poison_duration"):
            lines.append(f"Poisons for {self._format_stat(base['poison_duration'])} sec")
        if base.get("burn_duration"):
            lines.append(f"Burns for {self._format_stat(base['burn_duration'])} sec")
        if base.get("trigger_radius"):
            lines.append(f"Places mines with {self._format_stat(base['trigger_radius'])} px trigger radius")
        if base.get("detect_stealth"):
            lines.append("Can detect stealth enemies")
        return lines

    def _format_stat(self, value):
        if isinstance(value, float) and not value.is_integer():
            return f"{value:.1f}"
        return str(int(value))

    def _draw_game_over(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        surface.blit(overlay, (0, 0))
        title = self.big_font.render("Game Over", True, (255, 255, 255))
        detail = self.title_font.render(f"Reached round {self.round}", True, (245, 245, 245))
        if self.new_highscore:
            best = self.title_font.render("NEW HIGHSCORE!", True, (255, 215, 0))
            highscore_detail = self.title_font.render(f"Best round: {self.highscore}", True, (255, 215, 0))
        else:
            best = self.title_font.render(f"Best round: {self.highscore}", True, (210, 216, 210))
            highscore_detail = None
        hint = self.title_font.render(f"Press {KEY_CONFIRM_LABEL} to restart", True, (245, 220, 120))
        surface.blit(title, title.get_rect(center=(FIELD_WIDTH // 2, 105)))
        surface.blit(detail, detail.get_rect(center=(FIELD_WIDTH // 2, 135)))
        surface.blit(best, best.get_rect(center=(FIELD_WIDTH // 2, 160)))
        if highscore_detail:
            surface.blit(highscore_detail, highscore_detail.get_rect(center=(FIELD_WIDTH // 2, 181)))
            hint_y = 207
        else:
            hint_y = 187
        surface.blit(hint, hint.get_rect(center=(FIELD_WIDTH // 2, hint_y)))

    def _draw_quit_dialog(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(0, 0, 250, 112)
        box.center = (BASE_WIDTH // 2, BASE_HEIGHT // 2)
        pygame.draw.rect(surface, (28, 37, 44), box, border_radius=8)
        pygame.draw.rect(surface, (248, 210, 93), box, 2, border_radius=8)

        title = self.big_font.render("Stoppen?", True, (250, 250, 244))
        hint = self.small_font.render(f"{KEY_CONFIRM_LABEL} bevestigt, Esc annuleert", True, (232, 238, 226))
        surface.blit(title, title.get_rect(center=(box.centerx, box.y + 24)))
        surface.blit(hint, hint.get_rect(center=(box.centerx, box.y + 45)))

        button_width = 88
        button_height = 28
        gap = 16
        total_width = button_width * len(self.quit_options) + gap
        start_x = box.centerx - total_width // 2

        for index, option in enumerate(self.quit_options):
            rect = pygame.Rect(
                start_x + index * (button_width + gap),
                box.y + 66,
                button_width,
                button_height,
            )
            selected = index == self.quit_dialog_index
            fill = (248, 210, 93) if selected else (52, 65, 74)
            text_color = (25, 28, 30) if selected else (235, 240, 232)
            pygame.draw.rect(surface, fill, rect, border_radius=5)
            pygame.draw.rect(surface, (22, 28, 32), rect, 1, border_radius=5)

            label = self.title_font.render(option, True, text_color)
            surface.blit(label, label.get_rect(center=rect.center))

    def _short_name(self, name):
        pieces = {
            "starter": "Start",
            "slowing tower": "Slow",
            "earthquake machine": "Quake",
            "mine placer": "Mines",
        }
        return pieces.get(name, name[:6].title())

    def _display_name(self, name):
        return name.title()

    def _abbr_name(self, name):
        pieces = {
            "starter": "Starter",
            "piercer": "Piercer",
            "sniper": "Sniper",
            "cannon": "Cannon",
            "slowing tower": "Slowing tower",
            "earthquake machine": "Quake machine",
            "laser": "Laser",
            "missile": "Missile",
            "freeze": "Freeze",
            "poison": "Poison",
            "tesla": "Tesla",
            "flame": "Flame",
            "shock": "Shock",
            "railgun": "Railgun",
            "bomb": "Bomb",
            "mine placer": "Mine Placer",
            "excavator": "Excavator",
            "inferno": "Inferno",
            "black hole generator": "Black Hole",
            "buffer": "Buffer",
            "bank": "Bank",
            "boxer": "Boxer",
            "upgrade link": "Upgrade Link",
            "machinegunner": "Machinegun",
        }
        return pieces.get(name, name[:3].title())

    def _wrap_text(self, text, max_width):
        words = text.split()
        if not words:
            return [""]

        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if self.small_font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines
