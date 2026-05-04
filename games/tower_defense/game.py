import json
import math
import os
import random
from dataclasses import dataclass

import pygame

from core.scene import Scene
from settings import BASE_HEIGHT, BASE_WIDTH


FIELD_WIDTH = 400
MENU_WIDTH = BASE_WIDTH - FIELD_WIDTH
GRID = 25
COLS = FIELD_WIDTH // GRID
ROWS = BASE_HEIGHT // GRID
PATH_WIDTH = 25
MAX_TOWERS = 20


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

    def update(self, dt, waypoints, speed_multiplier=1.0):
        self._tick_effects(dt)
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

    @property
    def center(self):
        return (self.cell[0] * GRID + GRID // 2, self.cell[1] * GRID + GRID // 2)

    def stat(self, key, default=0):
        value = self.base.get(key, default)
        if isinstance(value, (int, float)):
            if key == "range":
                return value * (1.10 ** (self.level - 1))
            if key in ("trigger_radius", "chain_range", "splash_damage", "explosion_radius"):
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
        return int(self.base.get("cost", 0) * (self.level + 1))


@dataclass
class Mine:
    x: float
    y: float
    damage: float
    radius: float
    trigger: float
    color: tuple[int, int, int]


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    timer: float = 1.0


class TowerGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = pygame.font.SysFont("arial", 14, bold=True)
        self.font = pygame.font.SysFont("arial", 10)
        self.small_font = pygame.font.SysFont("arial", 8)
        self.big_font = pygame.font.SysFont("arial", 20, bold=True)

        self.stats = self._load_stats()
        self.tower_names = list(self.stats["towers"].keys())
        self.enemy_names = list(self.stats["enemies"].keys())
        self.colors = self._build_colors()

        self.path = self._generate_path()
        self.path_cells = self._build_path_cells()

        self.focus = "menu"
        self.state = "playing"
        self.menu_index = 0
        self.cursor = [4, 4]
        self.action_index = 0
        self.message = "Place towers, then start."
        self.banner_message = ""
        self.banner_timer = 0.0
        self.exit_confirm_timer = 0.0
        self.held_move_key = None
        self.held_move_timer = 0.0
        self.held_move_delay = 0.1
        self.held_move_interval = 0.07

        self.money = 150
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
        self.selected_tower = None
        self.game_over = False

    def _load_stats(self):
        path = os.path.join(os.path.dirname(__file__), "stats.json")
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _build_colors(self):
        palette = [
            (82, 183, 136), (87, 143, 202), (224, 138, 65), (116, 198, 157),
            (177, 117, 194), (245, 196, 66), (216, 88, 89), (126, 215, 230),
            (120, 176, 77), (111, 115, 220), (233, 116, 74), (230, 95, 145),
            (190, 190, 200), (60, 65, 75), (96, 160, 111),
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
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            if self.exit_confirm_timer > 0:
                from ui.Games_menu import Game_Menu
                self.manager.set_scene(Game_Menu(self.manager))
            else:
                self.exit_confirm_timer = 2.5
                self._flash_banner("Press Esc again to quit")
                self.message = "Press Esc again to quit."
            return

        if self.game_over:
            if event.key == pygame.K_b:
                self.__init__(self.manager)
            return

        if self.state == "placing":
            self._handle_placing(event.key)
        elif self.state == "actions":
            self._handle_actions(event.key)
        else:
            self._handle_normal(event.key)

    def _handle_normal(self, key):
        if key == pygame.K_l:
            self.focus = "field" if self.focus == "menu" else "menu"
            self.message = self._field_hover_message() if self.focus == "field" else self._menu_selection_label()
            return

        if self.focus == "menu":
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                self._move_menu_selection(key)
            elif key == pygame.K_b:
                if self.menu_index < self._control_count():
                    self._activate_menu_control()
                else:
                    self._start_placing()
        else:
            self._move_cursor(key)
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                self.message = self._field_hover_message()
            if key == pygame.K_b:
                tower = self._tower_at(tuple(self.cursor))
                if tower:
                    self.selected_tower = tower
                    self.action_index = 0
                    self.state = "actions"
                    self.message = "Upgrade, sell, or close."
                else:
                    self.message = "No tower here."

    def _handle_placing(self, key):
        if key == pygame.K_l:
            self.state = "playing"
            self.focus = "menu"
            self.message = "Placement canceled."
        elif key == pygame.K_b:
            self._place_selected_tower()
        else:
            self._move_cursor(key)

    def _handle_actions(self, key):
        if key == pygame.K_l:
            self.state = "playing"
            self.message = "Action closed."
        elif key == pygame.K_UP:
            self.action_index = (self.action_index - 1) % 3
        elif key == pygame.K_DOWN:
            self.action_index = (self.action_index + 1) % 3
        elif key == pygame.K_b:
            self._confirm_action()

    def _move_cursor(self, key):
        if key == pygame.K_LEFT:
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif key == pygame.K_RIGHT:
            self.cursor[0] = min(COLS - 1, self.cursor[0] + 1)
        elif key == pygame.K_UP:
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif key == pygame.K_DOWN:
            self.cursor[1] = min(ROWS - 1, self.cursor[1] + 1)

    def _move_menu_selection(self, key):
        columns = 2
        controls = self._control_count()
        if self.menu_index < controls:
            if key == pygame.K_LEFT and self.menu_index > 0:
                self.menu_index -= 1
            elif key == pygame.K_RIGHT and self.menu_index + 1 < controls:
                self.menu_index += 1
            elif key == pygame.K_DOWN:
                self.menu_index = controls + min(self.menu_index, columns - 1)
            self.message = self._menu_selection_label()
            return

        tower_idx = self.menu_index - controls
        row = tower_idx // columns
        col = tower_idx % columns
        total = len(self.tower_names)

        if key == pygame.K_LEFT and col > 0:
            tower_idx -= 1
        elif key == pygame.K_RIGHT and col < columns - 1 and tower_idx + 1 < total:
            tower_idx += 1
        elif key == pygame.K_UP:
            if row > 0:
                tower_idx -= columns
            elif controls:
                self.menu_index = min(col, controls - 1)
                self.message = self._menu_selection_label()
                return
        elif key == pygame.K_DOWN and tower_idx + columns < total:
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
        self.state = "placing"
        self.focus = "field"
        self.message = "D-pad moves. B places. L cancels."

    def _place_selected_tower(self):
        cell = tuple(self.cursor)
        tower_index = self._selected_tower_index()
        if tower_index < 0 or tower_index >= len(self.tower_names):
            self.message = "Choose a tower."
            return
        name = self.tower_names[tower_index]
        cost = int(self.stats["towers"][name].get("cost", 0))
        if not self._can_place(cell):
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

    def _can_place(self, cell):
        return (
            0 <= cell[0] < COLS
            and 0 <= cell[1] < ROWS
            and cell not in self.path_cells
            and self._tower_at(cell) is None
            and len(self.towers) < MAX_TOWERS
        )

    def _tower_at(self, cell):
        for tower in self.towers:
            if tower.cell == cell:
                return tower
        return None

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
        self.exit_confirm_timer = max(0, self.exit_confirm_timer - dt)
        self.banner_timer = max(0, self.banner_timer - dt)

        if self.game_over:
            return

        self._update_held_movement(dt)
        self._spawn_rounds(dt)
        speed_dt = dt * self.game_speed
        self._update_enemies(dt)
        self._update_towers(speed_dt)
        self._update_mines()
        self._update_effects(dt)

        if self.lives <= 0:
            self.game_over = True
            self.message = "Game over. Press B to restart."

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

        pressed = pygame.key.get_pressed()
        held_key = None
        for key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            if pressed[key]:
                held_key = key
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
        count = 8 + self.round * 3 + random.randint(0, 2 + self.round // 3)
        queue = ["grunt"] * count
        tank_count = self.round // 3 + random.randint(0, max(0, self.round // 6))
        for _ in range(tank_count):
            queue.insert(random.randrange(len(queue) + 1), "tank")
        self.spawn_queue = queue
        self.spawn_timer = random.uniform(0.05, 0.16)
        self.message = f"Round {self.round}"
        self._flash_banner(f"Round {self.round}")

    def _flash_banner(self, text, duration=1.6):
        self.banner_message = text
        self.banner_timer = duration

    def _next_spawn_delay(self):
        fast = max(0.08, 0.34 - self.round * 0.01)
        slow = max(fast + 0.04, 0.58 - self.round * 0.014)
        return random.uniform(fast, slow)

    def _round_factor(self):
        if self.round <= 20:
            return 1 + (self.round - 1) / 19
        return 2 + (self.round - 20) / 20

    def _spawn_enemy(self, name):
        data = self.stats["enemies"].get(name, self.stats["enemies"][self.enemy_names[0]])
        factor = self._round_factor()
        enemy = Enemy(
            name,
            data["health"] * factor,
            data["health"] * factor,
            max(1, int(data["damage"] * factor)),
            data["speed"] * (1 + min(0.35, self.round * 0.006)),
            int(data["reward"] * (1 + self.round * 0.03)),
        )
        enemy.x, enemy.y = self.path[0]
        self.enemies.append(enemy)

    def _update_enemies(self, dt):
        for enemy in list(self.enemies):
            escaped = enemy.update(dt, self.path, self.game_speed)
            if enemy.health <= 0:
                self.money += enemy.reward
                self.texts.append(FloatingText(f"+{enemy.reward}", enemy.x, enemy.y - 8, (255, 236, 130)))
                self.enemies.remove(enemy)
            elif escaped:
                self.lives -= enemy.damage
                self.texts.append(FloatingText(f"-{enemy.damage}", FIELD_WIDTH - 35, 20, (240, 80, 80)))
                self.enemies.remove(enemy)

    def _update_towers(self, dt):
        for tower in list(self.towers):
            tower.cooldown = max(0, tower.cooldown - dt)
            tower.flash_timer = max(0, tower.flash_timer - dt)
            if tower.name == "mine placer":
                self._update_mine_placer(tower)
                continue
            if tower.cooldown <= 0:
                if self._fire_tower(tower):
                    tower.cooldown = 1 / tower.fire_rate
                    tower.flash_timer = 0.08

    def _update_mine_placer(self, tower):
        if tower.cooldown > 0:
            return
        if len(self.mines) >= int(tower.stat("max_mines", 4)):
            return
        px, py = self._mine_position_near_tower(tower)
        mine = Mine(px, py, 28 * (1.25 ** (tower.level - 1)), 36, tower.stat("trigger_radius", 30), tower.color)
        self.mines.append(mine)
        tower.cooldown = 1 / tower.fire_rate
        tower.flash_timer = 0.08

    def _mine_position_near_tower(self, tower):
        cx, cy = tower.center
        for _ in range(35):
            start, end = random.choice(list(zip(self.path, self.path[1:])))
            t = random.random()
            px = start[0] + (end[0] - start[0]) * t
            py = start[1] + (end[1] - start[1]) * t
            angle = random.random() * math.tau
            jitter = random.uniform(0, min(10, tower.range * 0.25))
            px += math.cos(angle) * jitter
            py += math.sin(angle) * jitter
            if 0 <= px <= FIELD_WIDTH and 0 <= py <= BASE_HEIGHT and distance((cx, cy), (px, py)) <= tower.range:
                return px, py

        angle = random.random() * math.tau
        radius = random.uniform(0, tower.range)
        return (
            clamp(cx + math.cos(angle) * radius, 0, FIELD_WIDTH),
            clamp(cy + math.sin(angle) * radius, 0, BASE_HEIGHT),
        )

    def _fire_tower(self, tower):
        targets = self._targets_in_range(tower)
        if not targets:
            return False

        if tower.base.get("360_degree_attack"):
            for enemy in targets:
                self._damage_enemy(enemy, tower, tower.damage)
            self.shots.append((tower.center, None, tower.range, tower.color, 0.08))
            return True

        if tower.base.get("piercing"):
            line_targets, endpoint = self._piercing_line_targets(tower, targets[0])
            for enemy in line_targets:
                self._damage_enemy(enemy, tower, tower.damage)
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
                self._damage_enemy(enemy, tower, tower.damage)
            self.shots.append((tower.center, chain[0], 0, tower.color, 0.08))
            return True

        target = targets[0]
        self._damage_enemy(target, tower, tower.damage)
        splash = tower.stat("splash_damage", 0) or tower.stat("explosion_radius", 0)
        if splash:
            for enemy in self.enemies:
                if enemy is not target and distance((enemy.x, enemy.y), (target.x, target.y)) <= splash:
                    self._damage_enemy(enemy, tower, tower.damage * 0.55)
            if tower.name == "bomb":
                self.towers.remove(tower)
        self.shots.append((tower.center, target, splash, tower.color, 0.08))
        return True

    def _targets_in_range(self, tower):
        cx, cy = tower.center
        targets = [e for e in self.enemies if distance((cx, cy), (e.x, e.y)) <= tower.range]
        targets.sort(key=lambda enemy: enemy.progress, reverse=True)
        return targets

    def _piercing_line_targets(self, tower, primary):
        cx, cy = tower.center
        dx = primary.x - cx
        dy = primary.y - cy
        length = math.hypot(dx, dy)
        if length <= 0:
            return [primary], tower.center

        ux = dx / length
        uy = dy / length
        endpoint = (cx + ux * tower.range, cy + uy * tower.range)
        line_width = max(7, GRID * 0.35)
        hits = []
        for enemy in self.enemies:
            ex = enemy.x - cx
            ey = enemy.y - cy
            along = ex * ux + ey * uy
            if along < 0 or along > tower.range:
                continue
            perpendicular = abs(ex * uy - ey * ux)
            if perpendicular <= line_width:
                hits.append((along, enemy))

        hits.sort(key=lambda item: item[0])
        return ([enemy for _, enemy in hits] or [primary]), endpoint

    def _damage_enemy(self, enemy, tower, amount):
        enemy.health -= amount
        if tower.base.get("slow_effect"):
            self._apply_slow_area(enemy, tower)
        self._apply_status_effects(enemy, tower)

    def _apply_slow_area(self, enemy, tower):
        cx, cy = tower.center
        area = tower.stat("area_of_effect", 0)
        radius = min(tower.range, area * GRID * 0.5) if area else 0
        affected = self.enemies if radius else [enemy]
        for other in affected:
            if distance((cx, cy), (other.x, other.y)) <= tower.range and (not radius or distance((enemy.x, enemy.y), (other.x, other.y)) <= radius):
                other.slow_timer = 1.4
                other.slow_factor = tower.base["slow_effect"]

    def _apply_status_effects(self, enemy, tower):
        if tower.base.get("freeze_duration"):
            enemy.freeze_timer = max(enemy.freeze_timer, tower.stat("freeze_duration"))
        if tower.base.get("poison_duration"):
            enemy.poison_timer = max(enemy.poison_timer, tower.stat("poison_duration"))
            enemy.poison_dps = max(enemy.poison_dps, tower.damage * 0.25)
        if tower.base.get("burn_duration"):
            enemy.burn_timer = max(enemy.burn_timer, tower.stat("burn_duration"))
            enemy.burn_dps = max(enemy.burn_dps, tower.damage * 0.35)
        if tower.base.get("stun_effect") and random.random() < tower.base["stun_effect"]:
            enemy.stun_timer = max(enemy.stun_timer, 0.45)

    def _update_mines(self):
        for mine in list(self.mines):
            hit = None
            for enemy in self.enemies:
                if distance((mine.x, mine.y), (enemy.x, enemy.y)) <= mine.trigger:
                    hit = enemy
                    break
            if hit:
                for enemy in self.enemies:
                    if distance((mine.x, mine.y), (enemy.x, enemy.y)) <= mine.radius:
                        enemy.health -= mine.damage
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
        self._draw_towers(surface)
        self._draw_tower_range(surface)
        self._draw_enemies(surface)
        self._draw_shots(surface)
        self._draw_cursor(surface)
        self._draw_texts(surface)
        self._draw_menu(surface)
        self._draw_banner(surface)

        if self.game_over:
            self._draw_game_over(surface)

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

    def _draw_towers(self, surface):
        for tower in self.towers:
            x, y = tower.cell[0] * GRID, tower.cell[1] * GRID
            rect = pygame.Rect(x + 2, y + 2, GRID - 4, GRID - 4)
            pygame.draw.rect(surface, tower.color, rect, border_radius=3)
            pygame.draw.rect(surface, (22, 28, 32), rect, 1, border_radius=3)
            if tower.flash_timer > 0:
                pygame.draw.circle(surface, (255, 245, 180), tower.center, 3)
            level = self.small_font.render(str(tower.level), True, (255, 255, 255))
            surface.blit(level, (x + 5, y + 3))

    def _draw_enemies(self, surface):
        for enemy in self.enemies:
            color = (185, 67, 66) if enemy.kind == "grunt" else (102, 70, 58)
            pygame.draw.circle(surface, color, (int(enemy.x), int(enemy.y)), 7)
            pygame.draw.circle(surface, (35, 25, 25), (int(enemy.x), int(enemy.y)), 7, 1)
            bar_w = 16
            ratio = clamp(enemy.health / enemy.max_health, 0, 1)
            pygame.draw.rect(surface, (35, 35, 35), (enemy.x - 8, enemy.y - 12, bar_w, 3))
            pygame.draw.rect(surface, (84, 220, 104), (enemy.x - 8, enemy.y - 12, int(bar_w * ratio), 3))

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
        if tower is None and self.focus == "field" and self.state == "playing":
            tower = self._tower_at(tuple(self.cursor))
        if tower is None:
            return

        pygame.draw.circle(surface, tuple(min(255, c + 65) for c in tower.color), tower.center, int(tower.range), 1)

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
            pygame.draw.circle(surface, self.colors[name], (cx, cy), 8)
            pygame.draw.circle(surface, (0, 0, 0), (cx, cy), int(self.stats["towers"][name].get("range", 0)), 1)

    def _draw_texts(self, surface):
        for text in self.texts:
            label = self.small_font.render(text.text, True, text.color)
            surface.blit(label, (int(text.x), int(text.y)))

    def _draw_menu(self, surface):
        menu = pygame.Rect(FIELD_WIDTH, 0, MENU_WIDTH, BASE_HEIGHT)
        pygame.draw.rect(surface, (31, 40, 48), menu)
        pygame.draw.line(surface, (8, 12, 16), (FIELD_WIDTH, 0), (FIELD_WIDTH, BASE_HEIGHT), 2)

        stats = [
            f"${self.money}",
            "Prep" if self.preparing else f"R{self.round}",
            f"L{self.lives}",
            f"T{len(self.towers)}/{MAX_TOWERS}",
        ]
        for i, value in enumerate(stats):
            label = self.font.render(value, True, (242, 244, 236))
            surface.blit(label, (FIELD_WIDTH + 4, 5 + i * 12))

        if self.state == "actions":
            self._draw_action_menu(surface)
        else:
            self._draw_control_menu(surface)
            self._draw_tower_menu(surface)

        lines = self._wrap_text(self.message, MENU_WIDTH - 5)[:3]
        for i, line in enumerate(lines):
            label = self.small_font.render(line, True, (230, 236, 220))
            surface.blit(label, (FIELD_WIDTH + 3, 250 + i * 9))

    def _draw_tower_menu(self, surface):
        padding = 4
        gap = 4
        start_x = FIELD_WIDTH + padding
        start_y = 80
        columns = 2
        slot_width = (MENU_WIDTH - padding * 2 - gap) // columns
        slot_height = 17

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
            pygame.draw.rect(surface, self.colors[name], (rect.x + 2, rect.y + 2, 5, 13), border_radius=2)
            cost = int(self.stats["towers"][name].get("cost", 0))
            text_color = (25, 28, 30) if selected else (235, 240, 232)
            name_label = self.small_font.render(self._abbr_name(name), True, text_color)
            cost_label = self.small_font.render(str(cost), True, text_color)
            surface.blit(name_label, (rect.x + 9, rect.y + 1))
            surface.blit(cost_label, (rect.x + 9, rect.y + 8))

    def _draw_control_menu(self, surface):
        padding = 4
        gap = 4
        y = 56
        if self.preparing:
            rect = pygame.Rect(FIELD_WIDTH + padding, y, MENU_WIDTH - padding * 2, 19)
            selected = self.menu_index == 0 and self.focus == "menu"
            fill = (248, 210, 93) if selected else (63, 91, 70)
            pygame.draw.rect(surface, fill, rect, border_radius=3)
            color = (25, 28, 30) if selected else (235, 240, 232)
            label = self.small_font.render("Start", True, color)
            surface.blit(label, label.get_rect(center=rect.center))
            return

        button_width = (MENU_WIDTH - padding * 2 - gap) // 2
        for i, text in enumerate(("1x", "2x")):
            rect = pygame.Rect(FIELD_WIDTH + padding + i * (button_width + gap), y, button_width, 19)
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
        surface.blit(label, (FIELD_WIDTH + 4, 60))
        level = self.font.render(f"L{tower.level}" if tower else "", True, (245, 245, 245))
        surface.blit(level, (FIELD_WIDTH + 4, 74))

        upgrade_cost = tower.upgrade_cost if tower and tower.upgrade_cost is not None else "--"
        sell_value = (tower.total_spent if self.preparing else int(tower.total_spent * 0.75)) if tower else 0
        options = [f"Up {upgrade_cost}", f"Sell {sell_value}", "Close"]
        for i, option in enumerate(options):
            y = 96 + i * 22
            selected = i == self.action_index
            fill = (248, 210, 93) if selected else (52, 65, 74)
            rect = pygame.Rect(FIELD_WIDTH + 4, y, MENU_WIDTH - 8, 18)
            pygame.draw.rect(surface, fill, rect, border_radius=3)
            color = (25, 28, 30) if selected else (235, 240, 232)
            option_label = self.small_font.render(option, True, color)
            surface.blit(option_label, (rect.x + 4, rect.y + 5))

    def _draw_game_over(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        surface.blit(overlay, (0, 0))
        title = self.big_font.render("Game Over", True, (255, 255, 255))
        detail = self.title_font.render(f"Reached round {self.round}", True, (245, 245, 245))
        hint = self.title_font.render("Press B to restart", True, (245, 220, 120))
        surface.blit(title, title.get_rect(center=(FIELD_WIDTH // 2, 105)))
        surface.blit(detail, detail.get_rect(center=(FIELD_WIDTH // 2, 135)))
        surface.blit(hint, hint.get_rect(center=(FIELD_WIDTH // 2, 160)))

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
            "starter": "Str",
            "sniper": "Snp",
            "cannon": "Can",
            "slowing tower": "Slw",
            "earthquake machine": "Qak",
            "laser": "Las",
            "missile": "Msl",
            "freeze": "Frz",
            "poison": "Psn",
            "tesla": "Tsl",
            "flame": "Flm",
            "shock": "Shk",
            "railgun": "Rlg",
            "bomb": "Bmb",
            "mine placer": "Min",
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
