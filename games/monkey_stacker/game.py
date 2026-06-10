import math
import pygame
import json
import os
import random
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import AppStyles
from core.input_manager import InputHandler

def game_name():
    return f"Monkey Stacker", MonkeyStacker


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def draw_text_outlined(surface, font, text, color, outline_color, center):
    outline = font.render(text, True, outline_color)
    inner = font.render(text, True, color)
    ox, oy = center[0] - outline.get_width() // 2, center[1] - outline.get_height() // 2
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx != 0 or dy != 0:
                surface.blit(outline, (ox + dx, oy + dy))
    surface.blit(inner, (ox, oy))


def draw_rounded_tile(surface, color, x, y, size, radius=4):
    rect = pygame.Rect(x + 1, y + 1, size - 2, size - 2)

    # Drop shadow
    shadow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 60),
                     pygame.Rect(2, 2, size - 2, size - 2), border_radius=radius)
    surface.blit(shadow_surf, (x, y))

    pygame.draw.rect(surface, color, rect, border_radius=radius)

    border_color = tuple(max(0, c - 50) for c in color)
    pygame.draw.rect(surface, border_color, rect, 2, border_radius=radius)

    hi_surf = pygame.Surface((rect.width, max(1, rect.height // 3)), pygame.SRCALPHA)
    hi_surf.fill((255, 255, 255, 55))
    surface.blit(hi_surf, (rect.x, rect.y + 1))


class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(30, 80)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 40
        self.x = x
        self.y = y
        self.color = color
        self.life = 1.0
        self.size = random.uniform(3, 6)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 120 * dt
        self.life -= dt * 2.2

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(self.life * 255)
        r = max(1, int(self.size))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surface.blit(s, (int(self.x - r), int(self.y - r)))


class MonkeyStacker(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = AppStyles

        self.tile = 16
        self.grid_w = BASE_WIDTH // self.tile
        self.grid_h = BASE_HEIGHT // self.tile

        self.platform_width = 10
        self.platform_y = self.grid_h - 3
        self.platform_x = self.grid_w // 2 - self.platform_width // 2

        self.state = "start"
        self.score = 0
        self.highscore = 0

        self.swing_center_x = self.grid_w // 2
        self.swing_amplitude = self.grid_w // 2
        self.swing_base_speed = 2.0
        self.swing_speed = self.swing_base_speed
        self.swing_angle = 0.0

        self.camera_offset = 0.0
        self.camera_speed = 5.0
        self.camera_margin = 6

        self.fall_speed = 9.0

        self.current_shape = None
        self.block_x = 0.0
        self.block_y = 0.0
        self.block_state = "swing"
        self.placed_tiles = set()
        self.placed_colors = {}
        self.current_rotation = 0
        self.last_collision_out_of_bounds = False

        self.auto_drop_timer = 0.0
        self.auto_drop_duration = 0.0

        self.particles = []
        self.score_pop_timer = 0.0
        self.score_pop_value = 0
        self.vine_phase = 0.0

        self.title_font = pygame.font.SysFont("arial", 46, bold=True)
        self.ui_font = pygame.font.SysFont("arial", 22, bold=True)
        self.small_font = pygame.font.SysFont("arial", 15, bold=True)

        self.platform_log_colors = [(101, 67, 33), (120, 80, 40), (85, 55, 25)]
        self.vine_color = (60, 130, 30)
        self.rope_color = (100, 160, 50)

        self.block_colors = [
            (255, 215, 60), (80, 220, 100), (100, 180, 255),
            (255, 140, 80), (220, 100, 240),
        ]

        self._create_shapes()
        self._load_highscore()
        self._build_background()
        self._load_monkey_image()

        self.input = self.manager.input_handler
        self.confirm_state = False
        self.confirm_just_closed = False

        # Nu pas het spel starten
        self._start_new_game()

    def _load_monkey_image(self):
        path = os.path.join(os.path.dirname(__file__), "images", "monkey.png")
        size = self.tile * 2 + 4
        try:
            raw = pygame.image.load(path).convert_alpha()  # ← convert_alpha() not convert()
            self.monkey_surf = pygame.transform.smoothscale(raw, (size, size))
        except Exception:
            size = self.tile * 2 + 4
            self.monkey_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(self.monkey_surf, (170, 110, 65), (size // 2, size // 2), size // 2)
            pygame.draw.circle(self.monkey_surf, (220, 160, 100), (size // 2, size // 2 + 4), size // 3)
        except Exception:
            size = self.tile * 2 + 4
            self.monkey_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(self.monkey_surf, (170, 110, 65), (size // 2, size // 2), size // 2)
            pygame.draw.circle(self.monkey_surf, (220, 160, 100), (size // 2, size // 2 + 4), size // 3)

    def _build_background(self):
        self._bg = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))

        for y in range(BASE_HEIGHT):
            t = y / BASE_HEIGHT
            col = lerp_color((30, 90, 30), (10, 40, 15), t)
            pygame.draw.line(self._bg, col, (0, y), (BASE_WIDTH, y))

        self._draw_foliage_layer(self._bg, (20, 70, 25), y_base=BASE_HEIGHT, count=14, w_range=(30, 60),
                                 h_range=(50, 100))
        self._draw_foliage_layer(self._bg, (25, 90, 30), y_base=BASE_HEIGHT - 10, count=10, w_range=(20, 45),
                                 h_range=(35, 70))
        self._draw_foliage_layer(self._bg, (35, 110, 40), y_base=BASE_HEIGHT, count=8, w_range=(15, 35),
                                 h_range=(20, 45))

        rng = random.Random(42)
        for _ in range(8):
            vx = rng.randint(10, BASE_WIDTH - 10)
            length = rng.randint(40, 120)
            for seg in range(length):
                sx = vx + int(math.sin(seg * 0.18) * 4)
                sy = seg * 2
                pygame.draw.circle(self._bg, (50, 110, 30), (sx, sy), 1)

        light_surf = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        rng2 = random.Random(7)
        for _ in range(18):
            lx = rng2.randint(0, BASE_WIDTH)
            ly = rng2.randint(0, BASE_HEIGHT // 2)
            r = rng2.randint(8, 22)
            pygame.draw.ellipse(light_surf, (255, 255, 180, 18), (lx - r, ly - r // 2, r * 2, r))
        self._bg.blit(light_surf, (0, 0))

    def _draw_foliage_layer(self, surf, color, y_base, count, w_range, h_range):
        rng = random.Random(color[1] + count)
        step = BASE_WIDTH // count
        for i in range(count + 2):
            cx = i * step + rng.randint(-step // 2, step // 2)
            w = rng.randint(*w_range)
            h = rng.randint(*h_range)
            points = []
            for a in range(0, 181, 18):
                rad = math.radians(a)
                points.append((cx + math.cos(rad) * w // 2, y_base - math.sin(rad) * h))
            points += [(cx + w // 2, y_base), (cx - w // 2, y_base)]
            if len(points) >= 3:
                pygame.draw.polygon(surf, color, points)

    def get_user(self):
        return getattr(self.manager, "current_user", None)

    def _scores_path(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        return os.path.join(base_dir, "data", "users.json")

    def _get_username(self):
        """Veilig username ophalen"""
        user = self.get_user()
        if isinstance(user, dict):
            return user.get("name")
        return user

    def _load_highscore(self):
        self.highscore = 0
        username = self._get_username()
        if not username:
            return

        try:
            path = self._scores_path()
            if not os.path.exists(path):
                return

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for user in data.get("users", []):
                user_name = user.get("name")
                # Handle corrupted nested name
                if isinstance(user_name, dict):
                    user_name = user_name.get("name")

                if user_name == username:
                    self.highscore = user.get("highscores", {}).get("Monkey", 0)
                    return

        except Exception as e:
            print(f"Load highscore error: {e}")

    def _save_highscore(self):
        try:
            path = self._scores_path()
            username = self._get_username()
            if not username:
                print("Warning: Geen username gevonden!")
                return

            # Laad data
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"users": []}

            # === BELANGRIJK: Opruimen van corrupte data ===
            cleaned_users = []
            seen_users = set()

            for user in data.get("users", []):
                user_name = user.get("name")
                if isinstance(user_name, dict):
                    user_name = user_name.get("name")

                if not user_name or user_name in seen_users:
                    continue  # Dubbele of corrupte entry overslaan

                seen_users.add(user_name)

                # Zorg dat highscores een dict is
                if "highscores" not in user or not isinstance(user["highscores"], dict):
                    user["highscores"] = {}

                cleaned_users.append(user)

            data["users"] = cleaned_users

            # === Nu echte gebruiker updaten ===
            user_found = False
            for user in data["users"]:
                user_name = user.get("name")
                if isinstance(user_name, dict):
                    user_name = user_name.get("name")

                if user_name == username:
                    user_found = True
                    current = user["highscores"].get("Monkey", 0)

                    if self.score > current:
                        user["highscores"]["Monkey"] = self.score
                        self.highscore = self.score
                    break

            # Nieuwe gebruiker (moet eigenlijk niet meer gebeuren)
            if not user_found:
                data["users"].append({
                    "name": username,
                    "highscores": {
                        "Monkey": self.score
                    }
                })
                self.highscore = self.score

            # Opslaan
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"Save highscore error: {e}")

    def _create_shapes(self):
        self.shapes = [
            [(0, 0), (1, 0), (-1, 0), (-2, 0)],
            [(0, 0), (0, -1), (0, 1), (1, 1)],
            [(0, 0), (0, -1), (0, 1), (-1, 1)],
            [(0, 0), (-1, 0), (1, 0), (0, -1)],
            [(0, 0), (1, 0), (0, -1), (1, -1)],
            [(0, 0), (1, 0), (0, -1), (-1, -1)],
            [(0, 0), (-1, 0), (0, -1), (1, -1)],
        ]

    def _start_new_game(self):
        self.score = 0
        self.placed_tiles.clear()
        self.placed_colors.clear()
        self.particles.clear()
        self.swing_angle = 0
        self.block_state = "swing"
        self.state = "start"
        self.camera_offset = 0
        self.last_collision_out_of_bounds = False
        self.confirm_state = False

        # Veilige input reset
        if hasattr(self.input, 'clear'):
            self.input.clear()
        if hasattr(self.input, 'keys'):
            self.input.keys.clear()

        self._spawn_new_block()

    def _spawn_new_block(self):
        ticks = pygame.time.get_ticks()
        self.current_shape = self.shapes[ticks % len(self.shapes)]
        self.current_rotation = 0
        self.current_color = self.block_colors[ticks % len(self.block_colors)]
        self.block_y = 2
        self.block_x = float(self.swing_center_x)
        self.block_state = "swing"
        self.last_collision_out_of_bounds = False

        if not self.placed_tiles:
            base = 12.0
        else:
            highest_y = min(y for _, y in self.placed_tiles)
            height_layers = self.grid_h - highest_y
            reduction = min(height_layers * 0.55, 8.5)
            base = max(3.5, 12.0 - reduction)
        spread = min(0.8, (base - 3.5) * 0.15)
        self.auto_drop_duration = base + random.uniform(-spread, spread)
        self.auto_drop_timer = self.auto_drop_duration

    def _rotate_current_shape(self):
        self.current_rotation = (self.current_rotation + 1) % 4

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == "playing":
                    self.confirm_state = True
                else:
                    self._go_to_home()

    def update(self, dt):
        self.vine_phase += dt * 0.8
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update(dt)

        if self.score_pop_timer > 0:
            self.score_pop_timer -= dt

        if self.confirm_state:
            if self.input.just_pressed("L") or self.input.just_pressed("ESC"):
                self._go_to_home()
            elif self.input.just_pressed("B"):
                self.confirm_state = False

                if hasattr(self.input, "clear"):
                    self.input.clear()

            return

        if self.state == "start":
            if self.input.just_pressed("L"):  # L = Start
                self.state = "playing"
                self._spawn_new_block()
            return

        if self.state == "game_over":
            if self.input.just_pressed("L"):  # L = Restart
                self._start_new_game()
                self.state = "playing"
            elif self.input.just_pressed("B"):
                self.confirm_state = False
                self.confirm_just_closed = True
                if self.confirm_just_closed:
                    if not self.input.is_pressed("B"):
                        self.confirm_just_closed = False
                    return
                return

        # === Playing State ===
        if self.block_state == "swing":
            self._update_swing_speed()
            self.swing_angle += self.swing_speed * dt
            swing_offset = math.sin(self.swing_angle) * self.swing_amplitude
            self.block_x = max(0, min(self.swing_center_x + swing_offset, self.grid_w - 1))

            self.auto_drop_timer -= dt
            if self.auto_drop_timer <= 0:
                self.block_y = self.camera_offset + 2
                self.block_state = "fall"

            if self.input.just_pressed("L"):  # L = Drop
                self.block_y = self.camera_offset + 2
                self.block_state = "fall"

        elif self.block_state == "fall":
            self.block_y += self.fall_speed * dt
            if self._check_collision():
                if self.last_collision_out_of_bounds:
                    self.state = "game_over"
                else:
                    self._lock_block()
                    if self._is_game_over():
                        self.state = "game_over"
                    else:
                        self._spawn_new_block()

        if self.input.just_pressed("UP"):
            self._rotate_current_shape()

        self._update_camera(dt)

    def _go_to_home(self):
        from ui.Games_menu import Game_Menu
        self.manager.set_scene(Game_Menu(self.manager))

    def _update_swing_speed(self):
        if not self.placed_tiles:
            self.swing_speed = self.swing_base_speed
            return
        highest = min(y for _, y in self.placed_tiles)
        height = self.grid_h - highest
        factor = max(1, min(1 + height * 0.06, 3.2))
        self.swing_speed = self.swing_base_speed * factor

    def _rotated_shape(self):
        shape = self.current_shape
        for _ in range(self.current_rotation % 4):
            shape = [(-dy, dx) for (dx, dy) in shape]
        return shape

    def _solid_tiles(self):
        tiles = set(self.placed_tiles)
        for x in range(self.platform_x, self.platform_x + self.platform_width):
            for y in range(self.platform_y, self.grid_h):
                tiles.add((x, y))
        return tiles

    def _check_collision(self):
        solid = self._solid_tiles()
        self.last_collision_out_of_bounds = False
        for dx, dy in self._rotated_shape():
            gx = int(round(self.block_x + dx))
            gy = int(round(self.block_y + dy))
            if gx < 0 or gx >= self.grid_w:
                self.last_collision_out_of_bounds = True
                return True
            below = gy + 1
            if below >= self.grid_h or (gx, below) in solid:
                return True
        return False

    def _lock_block(self):
        newly_placed = []
        has_support = False
        for dx, dy in self._rotated_shape():
            gx = int(round(self.block_x + dx))
            gy = int(round(self.block_y + dy))
            newly_placed.append((gx, gy))
            support_y = gy + 1
            on_platform = (self.platform_x <= gx < self.platform_x + self.platform_width
                           and support_y >= self.platform_y)
            on_block = (gx, support_y) in self.placed_tiles
            if on_platform or on_block:
                has_support = True

        if not has_support:
            self.state = "game_over"
            self.highscore = max(self.highscore, self.score)
            self._save_highscore()
            return

        for gx, gy in newly_placed:
            self.placed_tiles.add((gx, gy))
            self.placed_colors[(gx, gy)] = self.current_color

        px = int(round(self.block_x)) * self.tile + self.tile // 2
        py = int((self.block_y - self.camera_offset)) * self.tile
        for _ in range(14):
            self.particles.append(Particle(px, py, self.current_color))

        old_score = self.score
        self.score += 10
        top_y = min(y for _, y in self.placed_tiles)
        height_bonus = max(0, self.grid_h - top_y)
        self.score += (height_bonus // 4) * 10
        self.score = (self.score // 10) * 10
        self.score_pop_value = self.score - old_score
        self.score_pop_timer = 1.2
        self.highscore = max(self.highscore, self.score)
        self._save_highscore()

    def _is_game_over(self):
        if not self.placed_tiles:
            return False
        highest = min(y for _, y in self.placed_tiles)
        return (highest - self.camera_offset) <= 1

    def _update_camera(self, dt):
        if not self.placed_tiles:
            target = 0
        else:
            highest = min(y for _, y in self.placed_tiles)
            visible_tiles = BASE_HEIGHT / self.tile
            target = (highest - self.camera_margin) - (self.grid_h - visible_tiles / 2)
        self.camera_offset += (target - self.camera_offset) * min(1, self.camera_speed * dt)

    def _draw_confirmation(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(BASE_WIDTH // 2 - 160, BASE_HEIGHT // 2 - 50, 320, 140)
        pygame.draw.rect(surface, (20, 20, 30), panel, border_radius=12)
        pygame.draw.rect(surface, (255, 80, 80), panel, 3, border_radius=12)

        txt = self.ui_font.render("Are you sure?", True, (255, 255, 255))
        surface.blit(txt, txt.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT // 2 - 25)))

        txt2 = self.ui_font.render("Do you want to leave the game?", True, (255, 255, 255))
        surface.blit(txt2, txt2.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT // 2 - 2)))


        self._draw_stylish_button(surface, "Yes (L)", BASE_HEIGHT // 2 + 35, color=(170, 30, 30))
        self._draw_stylish_button(surface, "No (B)", BASE_HEIGHT // 2 + 68, color=(60, 60, 160))

    def draw(self, surface):
        surface.blit(self._bg, (0, 0))
        self._draw_animated_vines(surface)

        if self.state == "start":
            self._draw_game(surface)
            self._draw_start_screen(surface)
        elif self.state == "playing":
            self._draw_game(surface)
        elif self.state == "game_over":
            self._draw_game(surface)
            self._draw_game_over(surface)

        for p in self.particles:
            p.draw(surface)

        if self.confirm_state:
            self._draw_confirmation(surface)

    def _draw_animated_vines(self, surface):
        for vx, length, phase_off in [(15, 80, 0.0), (BASE_WIDTH - 18, 65, 1.3)]:
            for seg in range(length):
                sway = math.sin(self.vine_phase + seg * 0.15 + phase_off) * 5
                sx = int(vx + sway)
                sy = int(seg * 2.4)
                radius = 2 if seg % 5 == 0 else 1
                pygame.draw.circle(surface, self.vine_color, (sx, sy), radius)

    def _draw_platform(self, surface):
        t = self.tile
        px = self.platform_x * t
        py = int((self.platform_y - self.camera_offset) * t)
        pw = self.platform_width * t
        ph = (self.grid_h - self.platform_y) * t

        if py > BASE_HEIGHT:
            return

        pygame.draw.rect(surface, (50, 25, 5),
                         pygame.Rect(px - 2, py + 4, pw + 4, ph + 4), border_radius=4)
        pygame.draw.rect(surface, (101, 67, 33),
                         pygame.Rect(px, py, pw, ph), border_radius=3)

        for row in range(self.grid_h - self.platform_y):
            row_y = py + row * t
            for gx in range(self.platform_width):
                cx = px + gx * t
                shade = self.platform_log_colors[gx % 3]
                pygame.draw.rect(surface, shade, (cx + 1, row_y + 1, t - 2, t - 2))
                grain = tuple(min(255, c + 20) for c in shade)
                for g in range(3):
                    gy2 = row_y + 4 + g * 5
                    pygame.draw.line(surface, grain, (cx + 2, gy2), (cx + t - 3, gy2), 1)

        pygame.draw.rect(surface, (160, 110, 60), pygame.Rect(px, py, pw, 3), border_radius=2)
        pygame.draw.rect(surface, (50, 30, 10),
                         pygame.Rect(px - 2, py, pw + 4, ph + 4), 2, border_radius=4)

    def _draw_landing_shadow(self, surface):
        if self.block_state != "swing":
            return
        solid = self._solid_tiles()
        shape = self._rotated_shape()
        bx = int(round(self.block_x))
        by = int(self.camera_offset + 2)
        for _ in range(self.grid_h + 10):
            hit = any(
                by + dy + 1 >= self.grid_h or (bx + dx, by + dy + 1) in solid
                for dx, dy in shape
            )
            if hit:
                break
            by += 1

        ghost = pygame.Surface((self.tile, self.tile), pygame.SRCALPHA)
        pygame.draw.rect(ghost, (*self.current_color, 55),
                         (1, 1, self.tile - 2, self.tile - 2), border_radius=3)
        pygame.draw.rect(ghost, (*self.current_color, 100),
                         (1, 1, self.tile - 2, self.tile - 2), 1, border_radius=3)
        for dx, dy in shape:
            sx = (bx + dx) * self.tile
            sy = int((by + dy - self.camera_offset) * self.tile)
            if 0 <= sy < BASE_HEIGHT:
                surface.blit(ghost, (sx, sy))

    def _draw_monkey_and_block(self, surface):
        monkey_screen_y = self.tile
        monkey_x = int(round(self.block_x))
        center_x = monkey_x * self.tile + self.tile // 2
        rope_end_y = monkey_screen_y + self.tile // 2

        segments = 14
        for seg in range(segments):
            t0, t1 = seg / segments, (seg + 1) / segments
            sway = math.sin(self.swing_angle * 0.4 + seg * 0.4) * 2
            x0 = int(center_x + sway * t0);
            y0 = int(t0 * rope_end_y)
            x1 = int(center_x + sway * t1);
            y1 = int(t1 * rope_end_y)
            pygame.draw.line(surface, (55, 100, 25), (x0, y0), (x1, y1), 4)
            pygame.draw.line(surface, (90, 160, 50), (x0 + 1, y0), (x1 + 1, y1), 1)

        ms = self.monkey_surf
        mw, mh = ms.get_size()
        mx = center_x - mw // 2
        my = rope_end_y - mh // 4
        surface.blit(ms, (mx, my))

        if self.block_state == "swing":
            anchor = 2
            for dx, dy in self._rotated_shape():
                gx = int(round(self.block_x + dx))
                draw_rounded_tile(surface, self.current_color,
                                  gx * self.tile, (anchor + dy) * self.tile, self.tile)
        else:
            for dx, dy in self._rotated_shape():
                gx = int(round(self.block_x + dx))
                gy = int(round(self.block_y + dy))
                sx = gx * self.tile
                sy = int((gy - self.camera_offset) * self.tile)
                draw_rounded_tile(surface, self.current_color, sx, sy, self.tile)

    def _draw_placed_blocks(self, surface):
        for gx, gy in self.placed_tiles:
            color = self.placed_colors.get((gx, gy), (200, 200, 200))
            sx = gx * self.tile
            sy = int((gy - self.camera_offset) * self.tile)
            draw_rounded_tile(surface, color, sx, sy, self.tile)

    def _draw_hud(self, surface):
        pad = 8
        panel_w = 170
        panel_h = 90
        panel_rect = pygame.Rect(pad, BASE_HEIGHT - panel_h - pad, panel_w, panel_h)

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((10, 40, 10, 195))
        surface.blit(bg, panel_rect.topleft)
        pygame.draw.rect(surface, (60, 160, 40), panel_rect, 2, border_radius=8)

        label = self.small_font.render("SCORE", True, (140, 220, 100))
        score = self.ui_font.render(str(self.score), True, (255, 240, 80))
        surface.blit(label, (panel_rect.x + 10, panel_rect.y + 8))
        surface.blit(score, (panel_rect.x + 10, panel_rect.y + 22))

        hs = self.small_font.render(f"BEST: {self.highscore}", True, (180, 255, 150))
        surface.blit(hs, (panel_rect.x + 10, panel_rect.y + 52))

        bar_x = panel_rect.x + 10
        bar_y = panel_rect.y + 72
        bar_w = panel_w - 20
        bar_h = 8
        frac = max(0, self.auto_drop_timer / max(0.01, self.auto_drop_duration))
        bar_col = lerp_color((255, 60, 40), (80, 220, 80), frac)
        pygame.draw.rect(surface, (30, 30, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        if frac > 0:
            pygame.draw.rect(surface, bar_col,
                             (bar_x, bar_y, int(bar_w * frac), bar_h), border_radius=4)
        pygame.draw.rect(surface, (100, 200, 80), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

        if self.score_pop_timer > 0 and self.score_pop_value > 0:
            alpha = int(min(1.0, self.score_pop_timer) * 255)
            offset_y = int((1.2 - self.score_pop_timer) * 24)
            pop_surf = self.ui_font.render(f"+{self.score_pop_value}", True, (255, 240, 80))
            tmp = pygame.Surface(pop_surf.get_size(), pygame.SRCALPHA)
            tmp.blit(pop_surf, (0, 0))
            tmp.set_alpha(alpha)
            surface.blit(tmp, (panel_rect.right + 6, panel_rect.y + 18 - offset_y))

    def _draw_game(self, surface):
        self._draw_landing_shadow(surface)
        self._draw_platform(surface)
        self._draw_placed_blocks(surface)
        self._draw_monkey_and_block(surface)
        self._draw_hud(surface)

    def _draw_glass_panel(self, surface, rect, accent=(255, 230, 80)):
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((10, 50, 10, 215))
        surface.blit(bg, rect.topleft)
        stripe = pygame.Surface((rect.w, 5), pygame.SRCALPHA)
        stripe.fill((*accent, 130))
        surface.blit(stripe, rect.topleft)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=10)

    def _draw_stylish_button(self, surface, text, center_y, color=(34, 139, 34)):
        rect = pygame.Rect(0, 0, 220, 25)
        rect.center = (BASE_WIDTH // 2, center_y)
        # Shadow
        sh = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 110))
        surface.blit(sh, rect.move(3, 3).topleft)

        pygame.draw.rect(surface, color, rect, border_radius=8)
        hi = pygame.Surface((rect.w, rect.h // 2), pygame.SRCALPHA)
        hi.fill((255, 255, 255, 35))
        surface.blit(hi, rect.topleft)
        lighter = tuple(min(255, c + 60) for c in color)
        pygame.draw.rect(surface, lighter, rect, 2, border_radius=8)
        label = self.ui_font.render(text, True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_start_screen(self, surface):
        cy = BASE_HEIGHT // 2
        panel = pygame.Rect(BASE_WIDTH // 2 - 135, cy - 110, 270, 210)
        self._draw_glass_panel(surface, panel)
        draw_text_outlined(surface, self.title_font, "MONKEY",
                           (255, 230, 80), (0, 50, 0),
                           (BASE_WIDTH // 2, cy - 78))
        draw_text_outlined(surface, self.title_font, "STACKER",
                           (255, 230, 80), (0, 50, 0),
                           (BASE_WIDTH // 2, cy - 38))

        hs = self.small_font.render(f"BEST: {self.highscore}", True, (170, 255, 140))
        surface.blit(hs, hs.get_rect(center=(BASE_WIDTH // 2, cy + 5)))

        self._draw_stylish_button(surface, "PRESS L TO START", cy + 48)
        self._draw_stylish_button(surface, "HOME", cy + 82, color=(60, 60, 160))

    def _draw_game_over(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))
        surface.blit(overlay, (0, 0))

        cy = BASE_HEIGHT // 2
        panel = pygame.Rect(BASE_WIDTH // 2 - 135, cy - 100, 270, 195)
        self._draw_glass_panel(surface, panel, accent=(255, 80, 80))

        draw_text_outlined(surface, self.title_font, "GAME OVER",
                           (255, 80, 80), (60, 0, 0),
                           (BASE_WIDTH // 2, cy - 65))

        sc = self.ui_font.render(f"Score: {self.score}", True, (255, 240, 120))
        hs = self.small_font.render(f"BEST: {self.highscore}", True, (170, 255, 140))
        surface.blit(sc, sc.get_rect(center=(BASE_WIDTH // 2, cy - 25)))
        surface.blit(hs, hs.get_rect(center=(BASE_WIDTH // 2, cy - 4)))

        self._draw_stylish_button(surface, "PRESS L TO RESTART", cy + 42, color=(170, 30, 30))
        self._draw_stylish_button(surface, "PRESS B TO HOME", cy + 78, color=(60, 60, 160))

    def on_exit(self):
        self.input.close()
