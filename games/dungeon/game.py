import pygame
import random
import math
import json
import os

from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT

# ====================== STANDAARD INPUT HANDLER ======================
from core.input_manager import InputHandler


class DungeonGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)

        self.font = pygame.font.SysFont("arial", 48)          # grote tekst (game over, etc.)
        self.hud_font = pygame.font.SysFont("arial", 32, bold=True)   # HUD nu groter + bold

        self.tile_size = 30
        self.viewport_width = BASE_WIDTH // self.tile_size
        self.viewport_height = BASE_HEIGHT // self.tile_size
        self.map_width = self.viewport_width * 10
        self.map_height = self.viewport_height * 10

        self.tile_palettes = [
            [(156, 80, 40), (115, 51, 17), (84, 39, 14)],
            [(60, 60, 70), (80, 80, 90), (100, 100, 110)],
            [(40, 80, 40), (50, 100, 50), (60, 120, 60)],
            [(176, 43, 14), (133, 40, 21), (207, 56, 27)]
        ]
        self.tile_colors = random.choice(self.tile_palettes)

        self.move_delay = 0.12
        self.time_since_move = 0.0

        self.vision_radius = 6
        self.explored = set()
        self.visible = set()

        self.user = getattr(self.manager, 'current_user', None) or 0

        self.walls, (self.player_x, self.player_y) = self.generate_rooms_and_corridors()

        try:
            self.player_image = pygame.image.load("games/dungeon/dungeon_explorer.png").convert_alpha()
            self.player_image = pygame.transform.scale(self.player_image, (self.tile_size, self.tile_size))
        except:
            self.player_image = None

        self.powerup_images = {}
        for name, path in [("time", "games/dungeon/time_power-up.png"),
                           ("speed", "games/dungeon/speed_power-up.png")]:
            try:
                img = pygame.image.load(path).convert_alpha()
                self.powerup_images[name] = pygame.transform.scale(img, (self.tile_size, self.tile_size))
            except:
                self.powerup_images[name] = None

        self.facing = 'right'
        self.timer = 60.0
        self.game_over = False
        self.score = 0
        self.highscore = 0

        self.dots = set()
        self.enemies = []
        self.powerups = {}

        self.time_powerup_count = 6
        self.speed_powerup_count = 4

        self.speed_boost_active = False
        self.speed_boost_time_remaining = 0.0
        self.speed_multiplier = 1.5

        self.stunned = False
        self.stun_time_remaining = 0.0

        self.show_instructions = True

        self._load_highscore()

        self.spawn_dots()
        self.spawn_enemies()
        self.spawn_powerups()

        self.input = InputHandler()

    # ====================== HIGHSCORE ======================
    def _scores_path(self):
        return os.path.join(os.path.dirname(__file__), "dungeon_scores.json")

    def _load_highscore(self):
        try:
            with open(self._scores_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            self.highscore = int(data.get("best", 0))
        except:
            self.highscore = 0

    def _save_highscore(self):
        best = (self.highscore // 10) * 10
        try:
            with open(self._scores_path(), "w", encoding="utf-8") as f:
                json.dump({"best": best}, f)
        except:
            pass

    # ====================== DUNGEON GENERATIE ======================
    def generate_rooms_and_corridors(self):
        all_walls = {(x, y) for x in range(self.map_width) for y in range(self.map_height)}

        room_min_w, room_min_h = 3, 3
        room_max_w, room_max_h = 6, 6
        room_count = 55
        rooms = []

        def overlaps(r1, r2):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            return not (x1 + w1 + 1 < x2 or x2 + w2 + 1 < x1 or y1 + h1 + 1 < y2 or y2 + h2 + 1 < y1)

        sections_x = 5
        sections_y = 5
        section_width = self.map_width // sections_x
        section_height = self.map_height // sections_y

        for sx in range(sections_x):
            for sy in range(sections_y):
                section_x_start = sx * section_width
                section_x_end = (sx + 1) * section_width - 1
                section_y_start = sy * section_height
                section_y_end = (sy + 1) * section_height - 1

                placed = False
                for attempt in range(20):
                    w = random.randint(room_min_w, room_max_w)
                    h = random.randint(room_min_h, room_max_h)
                    x = random.randint(max(1, section_x_start), min(section_x_end - w, self.map_width - w - 2))
                    y = random.randint(max(1, section_y_start), min(section_y_end - h, self.map_height - h - 2))
                    new_room = (x, y, w, h)

                    if not any(overlaps(new_room, existing) for existing in rooms):
                        rooms.append(new_room)
                        placed = True
                        break

                if not placed:
                    w = random.randint(room_min_w, room_max_w)
                    h = random.randint(room_min_h, room_max_h)
                    x = random.randint(max(1, section_x_start), min(section_x_end - w, self.map_width - w - 2))
                    y = random.randint(max(1, section_y_start), min(section_y_end - h, self.map_height - h - 2))
                    rooms.append((x, y, w, h))

        for _ in range(200):
            if len(rooms) >= room_count:
                break
            w = random.randint(room_min_w, room_max_w)
            h = random.randint(room_min_h, room_max_h)
            x = random.randint(1, self.map_width - w - 2)
            y = random.randint(1, self.map_height - h - 2)
            new_room = (x, y, w, h)

            if not any(overlaps(new_room, existing) for existing in rooms):
                rooms.append(new_room)

        if not rooms:
            rooms = [(1, 1, 8, 5)]

        for x, y, w, h in rooms:
            for ry in range(y, y + h):
                for rx in range(x, x + w):
                    all_walls.discard((rx, ry))

        def carve_corridor(a, b):
            ax, ay = a
            bx, by = b
            corridor_width = random.randint(1, 3)
            width_offset = corridor_width // 2

            if random.random() < 0.5:
                for x in range(min(ax, bx), max(ax, bx) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((x, ay - width_offset + w))
                for y in range(min(ay, by), max(ay, by) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((bx - width_offset + w, y))
            else:
                for y in range(min(ay, by), max(ay, by) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((ax - width_offset + w, y))
                for x in range(min(ax, bx), max(ax, bx) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((x, by - width_offset + w))

        centers = [(x + w // 2, y + h // 2) for x, y, w, h in rooms]

        for i in range(1, len(centers)):
            carve_corridor(centers[i - 1], centers[i])

        for i in range(self.map_width):
            all_walls.add((i, 0))
            all_walls.add((i, self.map_height - 1))
        for i in range(self.map_height):
            all_walls.add((0, i))
            all_walls.add((self.map_width - 1, i))

        return all_walls, centers[0]

    def spawn_dots(self):
        self.dots.clear()
        for _ in range(100):
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            if (x, y) not in self.walls and (x, y) != (self.player_x, self.player_y):
                self.dots.add((x, y))

    def spawn_enemies(self):
        self.enemies.clear()
        enemy_configs = [(1, 5), (2, 8), (3, 7)]
        for enemy_type, count in enemy_configs:
            for _ in range(count):
                attempts = 0
                while attempts < 50:
                    x = random.randint(0, self.map_width - 1)
                    y = random.randint(0, self.map_height - 1)
                    if (x, y) not in self.walls and (x, y) != (self.player_x, self.player_y):
                        self.enemies.append(Enemy(x, y, enemy_type, self.walls))
                        break
                    attempts += 1

    def spawn_powerups(self):
        self.powerups.clear()
        total_needed = self.time_powerup_count + self.speed_powerup_count
        spawned_time = 0
        spawned_speed = 0
        attempts = 0

        while (spawned_time < self.time_powerup_count or spawned_speed < self.speed_powerup_count) and attempts < 500:
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            pos = (x, y)
            if pos in self.walls or pos == (self.player_x, self.player_y) or pos in self.dots:
                attempts += 1
                continue

            enemy_positions = {(enemy.x, enemy.y) for enemy in self.enemies}
            if pos in enemy_positions or pos in self.powerups:
                attempts += 1
                continue

            if spawned_time < self.time_powerup_count and spawned_speed < self.speed_powerup_count:
                powerup_type = random.choice(['time', 'speed'])
            elif spawned_time < self.time_powerup_count:
                powerup_type = 'time'
            else:
                powerup_type = 'speed'

            self.powerups[pos] = powerup_type
            if powerup_type == 'time':
                spawned_time += 1
            else:
                spawned_speed += 1
            attempts += 1

        if spawned_time < self.time_powerup_count or spawned_speed < self.speed_powerup_count:
            available_positions = [
                (x, y) for x in range(self.map_width) for y in range(self.map_height)
                if (x, y) not in self.walls and (x, y) != (self.player_x, self.player_y)
                and (x, y) not in self.dots and (x, y) not in self.powerups
                and (x, y) not in {(enemy.x, enemy.y) for enemy in self.enemies}
            ]
            random.shuffle(available_positions)
            for pos in available_positions:
                if spawned_time < self.time_powerup_count:
                    self.powerups[pos] = 'time'
                    spawned_time += 1
                elif spawned_speed < self.speed_powerup_count:
                    self.powerups[pos] = 'speed'
                    spawned_speed += 1
                if spawned_time >= self.time_powerup_count and spawned_speed >= self.speed_powerup_count:
                    break

    def reset_game(self):
        self.walls, (self.player_x, self.player_y) = self.generate_rooms_and_corridors()
        self.timer = 60.0
        self.game_over = False
        self.score = 0
        self.facing = 'right'
        self.time_since_move = 0.0
        self.stunned = False
        self.stun_time_remaining = 0.0
        self.speed_boost_active = False
        self.speed_boost_time_remaining = 0.0

        self.explored.clear()
        self.visible.clear()
        self.tile_colors = random.choice(self.tile_palettes)

        self.spawn_dots()
        self.spawn_enemies()
        self.spawn_powerups()
        self.show_instructions = True

    def has_line_of_sight(self, x0, y0, x1, y1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1

        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if (x, y) in self.walls and (x, y) != (x0, y0):
                    return False
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if (x, y) in self.walls and (x, y) != (x0, y0):
                    return False
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        return True

    def update_visibility(self):
        self.visible.clear()
        for dy in range(-self.vision_radius, self.vision_radius + 1):
            for dx in range(-self.vision_radius, self.vision_radius + 1):
                x = self.player_x + dx
                y = self.player_y + dy
                if not (0 <= x < self.map_width and 0 <= y < self.map_height):
                    continue
                if dx * dx + dy * dy > self.vision_radius * self.vision_radius:
                    continue
                if self.has_line_of_sight(self.player_x, self.player_y, x, y):
                    self.visible.add((x, y))
                    self.explored.add((x, y))

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        self.input.update()

        if self.show_instructions:
            if self.input.just_pressed("B") or self.input.just_pressed("SPACE"):
                self.show_instructions = False
            return

        if self.game_over:
            if self.input.just_pressed("B") or self.input.just_pressed("SPACE"):
                self.reset_game()
            return

        if self.stunned:
            self.stun_time_remaining -= dt
            if self.stun_time_remaining <= 0:
                self.stunned = False

        if self.speed_boost_active:
            self.speed_boost_time_remaining -= dt
            if self.speed_boost_time_remaining <= 0:
                self.speed_boost_active = False

        self.time_since_move += dt
        self.timer -= dt

        if self.timer <= 0:
            self.game_over = True
            if self.score > self.highscore:
                self.highscore = self.score
                self._save_highscore()
            return

        move_delay = self.move_delay / self.speed_multiplier if self.speed_boost_active else self.move_delay
        if self.stunned:
            move_delay *= 2

        if self.time_since_move >= move_delay:
            new_x, new_y = self.player_x, self.player_y
            moved = False

            if self.input.is_pressed("LEFT"):
                new_x -= 1
                self.facing = 'left'
            elif self.input.is_pressed("RIGHT"):
                new_x += 1
                self.facing = 'right'
            elif self.input.is_pressed("UP"):
                new_y -= 1
                self.facing = 'up'
            elif self.input.is_pressed("DOWN"):
                new_y += 1
                self.facing = 'down'

            new_x = max(0, min(self.map_width - 1, new_x))
            new_y = max(0, min(self.map_height - 1, new_y))

            if (new_x, new_y) not in self.walls and (new_x, new_y) != (self.player_x, self.player_y):
                self.player_x, self.player_y = new_x, new_y
                moved = True

                if (self.player_x, self.player_y) in self.dots:
                    self.dots.remove((self.player_x, self.player_y))
                    self.score += random.randint(1, 5)

                if (self.player_x, self.player_y) in self.powerups:
                    ptype = self.powerups.pop((self.player_x, self.player_y))
                    if ptype == 'time':
                        self.timer += 5.0
                    elif ptype == 'speed':
                        self.speed_boost_active = True
                        self.speed_boost_time_remaining = 6.0

            if moved:
                self.time_since_move = 0.0

        self.update_visibility()

        for enemy in self.enemies:
            enemy.update(dt, self.player_x, self.player_y, self.has_line_of_sight)
            if enemy.x == self.player_x and enemy.y == self.player_y and enemy.can_attack():
                enemy.attack()
                if enemy.type == 1:
                    self.game_over = True
                elif enemy.type == 2:
                    self.score = max(0, self.score - 3)
                elif enemy.type == 3:
                    self.stunned = True
                    self.stun_time_remaining = 3.0


    # ====================== DRAW (HUD nu met donker paneel) ======================
    def draw(self, surface):
        if self.show_instructions:
            surface.fill((0, 0, 0))
            title_font = pygame.font.SysFont("arial", 42, bold=True)
            text_font = pygame.font.SysFont("arial", 24)
            small_font = pygame.font.SysFont("arial", 18)

            title = title_font.render("DUNGEON EXPLORER", True, (255, 255, 255))
            surface.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 45)))

            y = 100
            lh = 32

            goal = text_font.render("GOAL: Collect yellow dots!", True, (255, 255, 0))
            surface.blit(goal, (30, y))
            y += lh

            timer = text_font.render("60 second time limit", True, (255, 80, 80))
            surface.blit(timer, (30, y))
            y += lh

            enemies = text_font.render("ENEMIES:", True, (255, 200, 100))
            surface.blit(enemies, (30, y))
            y += 28

            surface.blit(small_font.render("Red   - Instant death", True, (255, 100, 100)), (50, y)); y += 24
            surface.blit(small_font.render("Purple - Lose 3 points", True, (200, 150, 255)), (50, y)); y += 24
            surface.blit(small_font.render("Orange - Stun 3 sec", True, (255, 200, 100)), (50, y)); y += 24

            surface.blit(small_font.render("Green  - +5 seconds", True, (100, 255, 100)), (50, y)); y += 24
            surface.blit(small_font.render("Blue   - 1.5x speed 6 sec", True, (100, 180, 255)), (50, y)); y += 38

            controls = text_font.render("CONTROLS:", True, (100, 200, 255))
            surface.blit(controls, (30, y))
            y += 28

            surface.blit(small_font.render("D-pad / Arrows = move", True, (200, 200, 200)), (50, y)); y += 24
            surface.blit(small_font.render("ESC = back to menu", True, (200, 200, 200)), (50, y))

            start = text_font.render("Press B or SPACE to start", True, (100, 255, 100))
            surface.blit(start, start.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT - 35)))
            return

        if self.game_over:
            surface.fill((0, 0, 0))
            go = self.font.render("TIME'S UP!", True, (255, 80, 80))
            restart = pygame.font.SysFont("arial", 28).render("Press B or SPACE to play again", True, (200, 200, 200))
            score_txt = pygame.font.SysFont("arial", 32).render(f"Score: {self.score}", True, (255, 255, 0))
            surface.blit(go, go.get_rect(center=(BASE_WIDTH//2, BASE_HEIGHT//2 - 60)))
            surface.blit(restart, restart.get_rect(center=(BASE_WIDTH//2, BASE_HEIGHT//2 + 10)))
            surface.blit(score_txt, score_txt.get_rect(center=(BASE_WIDTH//2, BASE_HEIGHT//2 + 70)))
            return

        surface.fill((50, 80, 120))

        # === HUD met donker paneel ===
        hud_panel = pygame.Rect(8, 8, 240, 78)
        pygame.draw.rect(surface, (255, 255, 255), hud_panel, border_radius=12)  # zeer donker
        pygame.draw.rect(surface, (255, 255, 255), hud_panel, 4, border_radius=12)

        timer_text = self.hud_font.render(f"Time: {int(self.timer)}", True, (255, 70, 70))
        score_text = self.hud_font.render(f"Score: {self.score}", True, (255, 240, 80))

        surface.blit(timer_text, (20, 18))
        surface.blit(score_text, (20, 48))

        # Camera
        cam_x = self.player_x - self.viewport_width // 2
        cam_y = self.player_y - self.viewport_height // 2
        cam_x = max(0, min(self.map_width - self.viewport_width, cam_x))
        cam_y = max(0, min(self.map_height - self.viewport_height, cam_y))

        # Tiles, enemies, dots, power-ups, player (onveranderd)
        for y in range(self.viewport_height):
            for x in range(self.viewport_width):
                wx = cam_x + x
                wy = cam_y + y
                rect = pygame.Rect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)

                if (wx, wy) not in self.explored:
                    pygame.draw.rect(surface, (0, 0, 0), rect)
                    continue

                rng = random.Random(wx * 10000 + wy)
                color = rng.choice(self.tile_colors)

                if (wx, wy) not in self.visible:
                    color = (40, 40, 40)

                pygame.draw.rect(surface, color, rect)

                if (wx, wy) in self.walls:
                    wall_color = (30, 30, 30) if (wx, wy) in self.visible else (15, 15, 15)
                    pygame.draw.rect(surface, wall_color, rect)

                pygame.draw.rect(surface, (80, 80, 80), rect, 1)

        for enemy in self.enemies:
            ex = enemy.x - cam_x
            ey = enemy.y - cam_y
            if 0 <= ex < self.viewport_width and 0 <= ey < self.viewport_height and (enemy.x, enemy.y) in self.visible:
                ex_pos = ex * self.tile_size + self.tile_size // 2
                ey_pos = ey * self.tile_size + self.tile_size // 2
                if enemy.type == 1:
                    pygame.draw.circle(surface, (255, 0, 0), (ex_pos, ey_pos), 7)
                elif enemy.type == 2:
                    pygame.draw.circle(surface, (200, 100, 255), (ex_pos, ey_pos), 6)
                elif enemy.type == 3:
                    pygame.draw.circle(surface, (255, 165, 0), (ex_pos, ey_pos), 5)

        for dot in self.dots:
            dx = dot[0] - cam_x
            dy = dot[1] - cam_y
            if 0 <= dx < self.viewport_width and 0 <= dy < self.viewport_height and dot in self.visible:
                dot_x = dx * self.tile_size + self.tile_size // 2
                dot_y = dy * self.tile_size + self.tile_size // 2
                pygame.draw.circle(surface, (255, 255, 0), (dot_x, dot_y), 5)

        for pos, ptype in self.powerups.items():
            px = pos[0] - cam_x
            py = pos[1] - cam_y
            if 0 <= px < self.viewport_width and 0 <= py < self.viewport_height and pos in self.visible:
                image = self.powerup_images.get(ptype)
                if image:
                    surface.blit(image, (px * self.tile_size, py * self.tile_size))
                else:
                    px_pos = px * self.tile_size + self.tile_size // 2
                    py_pos = py * self.tile_size + self.tile_size // 2
                    col = (100, 255, 100) if ptype == 'time' else (100, 180, 255)
                    pygame.draw.circle(surface, col, (px_pos, py_pos), 6)
                    pygame.draw.circle(surface, (255, 255, 255), (px_pos, py_pos), 2)

        player_x_pos = (self.player_x - cam_x) * self.tile_size
        player_y_pos = (self.player_y - cam_y) * self.tile_size
        if self.player_image:
            angle = {'right': 270, 'down': 180, 'left': 90, 'up': 0}[self.facing]
            rotated = pygame.transform.rotate(self.player_image, angle)
            rect = rotated.get_rect(center=(player_x_pos + self.tile_size // 2, player_y_pos + self.tile_size // 2))
            surface.blit(rotated, rect)
        else:
            pygame.draw.rect(surface, (220, 30, 30),
                             (player_x_pos + 4, player_y_pos + 4, self.tile_size - 8, self.tile_size - 8))

    def on_exit(self):
        self.input.close()


class Enemy:
    def __init__(self, x, y, enemy_type, walls):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.walls = walls
        self.vision_radius = 6
        self.move_delay = [0.8, 0.3, 0.4][enemy_type - 1]
        self.time_since_move = 0.0
        self.attack_cooldown = 5.0
        self.last_attack_time = 0.0

    def update(self, dt, player_x, player_y, has_line_of_sight_func):
        self.time_since_move += dt
        self.last_attack_time += dt
        distance = math.sqrt((self.x - player_x) ** 2 + (self.y - player_y) ** 2)
        if distance <= self.vision_radius and has_line_of_sight_func(self.x, self.y, player_x, player_y):
            if self.time_since_move >= self.move_delay:
                self.move_towards_player(player_x, player_y)
                self.time_since_move = 0.0

    def move_towards_player(self, player_x, player_y):
        new_x = self.x
        new_y = self.y
        if self.x < player_x: new_x += 1
        elif self.x > player_x: new_x -= 1
        if self.y < player_y: new_y += 1
        elif self.y > player_y: new_y -= 1
        if (new_x, new_y) not in self.walls:
            self.x = new_x
            self.y = new_y

    def can_attack(self):
        return self.last_attack_time >= self.attack_cooldown

    def attack(self):
        self.last_attack_time = 0.0