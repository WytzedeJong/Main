import math
import pygame
import json
import os
import random

from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import AppStyles

from core.input_manager import InputHandler

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

        self.title_font = pygame.font.SysFont("arial", 48, bold=True)
        self.ui_font = pygame.font.SysFont("arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("arial", 18)

        self.platform_color = (139, 69, 19)
        self.monkey_color = (170, 110, 65)
        self.button_color = (34, 139, 34)
        self.hud_panel_color = (40, 100, 40)

        self.block_colors = [
            (255, 215, 60),
            (80, 220, 100),
            (100, 180, 255),
            (255, 140, 80),
            (180, 100, 240),
        ]

        self._create_shapes()
        self._load_highscore()
        self._start_new_game()

        self.input = InputHandler()

    def _scores_path(self):
        return os.path.join(os.path.dirname(__file__), "monkey_scores.json")

    def _load_highscore(self):
        try:
            with open(self._scores_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            self.highscore = int(data.get("best", 0))
        except:
            self.highscore = 0

    def _save_highscore(self):
        best = (self.highscore // 10) * 10
        data = {"best": best}
        try:
            with open(self._scores_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except:
            pass

    def _create_shapes(self):
        self.shapes = [
            [(0,0),(1,0),(-1,0),(-2,0)],
            [(0,0),(0,-1),(0,1),(1,1)],
            [(0,0),(0,-1),(0,1),(-1,1)],
            [(0,0),(-1,0),(1,0),(0,-1)],
            [(0,0),(1,0),(0,-1),(1,-1)],
            [(0,0),(1,0),(0,-1),(-1,-1)],
            [(0,0),(-1,0),(0,-1),(1,-1)]
        ]

    def _start_new_game(self):
        self.score = 0
        self.placed_tiles.clear()
        self.placed_colors.clear()

        self.swing_angle = 0
        self.block_state = "swing"
        self.state = "start"
        self.camera_offset = 0
        self.last_collision_out_of_bounds = False

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
            base = 9.0
        else:
            highest_y = min(y for _, y in self.placed_tiles)
            height_layers = self.grid_h - highest_y
            reduction = min(height_layers * 0.75, 6.5)
            base = max(3.8, 9.5 - reduction)
        self.auto_drop_duration = random.uniform(base - 1.8, base + 1.2)
        self.auto_drop_timer = self.auto_drop_duration

    def _rotate_current_shape(self):
        self.current_rotation = (self.current_rotation + 1) % 4

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))
            return


    def update(self, dt):
        self.input.update()

        if self.state == "start":
            if self.input.just_pressed("B") or self.input.just_pressed("SPACE"):
                self.state = "playing"
            return

        if self.state == "game_over":
            if self.input.just_pressed("B") or self.input.just_pressed("SPACE"):
                self._start_new_game()
                self.state = "playing"
            return

        if self.block_state == "swing":
            self._update_swing_speed()

            self.swing_angle += self.swing_speed * dt
            swing_offset = math.sin(self.swing_angle) * self.swing_amplitude
            self.block_x = self.swing_center_x + swing_offset
            self.block_x = max(0, min(self.block_x, self.grid_w - 1))

            self.auto_drop_timer -= dt
            if self.auto_drop_timer <= 0:
                top = self.camera_offset
                self.block_y = top + 2
                self.block_state = "fall"

            if self.input.just_pressed("B") or self.input.just_pressed("SPACE"):
                top = self.camera_offset
                self.block_y = top + 2
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
            else:
                visible_tiles = BASE_HEIGHT / self.tile
                max_screen_row = max(
                    (self.block_y + dy) - self.camera_offset
                    for _, dy in self._rotated_shape()
                )
                if max_screen_row > visible_tiles:
                    self.state = "game_over"

        if self.input.just_pressed("L") or self.input.just_pressed("UP"):
            self._rotate_current_shape()

        self._update_camera(dt)

    def draw(self, surface):
        self._draw_background(surface)

        if self.state == "start":
            self._draw_start_screen(surface)
        elif self.state == "playing":
            self._draw_game(surface)
        elif self.state == "game_over":
            self._draw_game(surface)
            self._draw_game_over(surface)

    def _update_swing_speed(self):
        if not self.placed_tiles:
            self.swing_speed = self.swing_base_speed
            return
        highest = min(y for _, y in self.placed_tiles)
        height = self.grid_h - highest
        factor = 1 + height * 0.06
        factor = max(1, min(factor, 3.2))
        self.swing_speed = self.swing_base_speed * factor

    def _rotated_shape(self):
        shape = self.current_shape
        rot = self.current_rotation % 4
        for _ in range(rot):
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
            on_platform = (self.platform_x <= gx < self.platform_x + self.platform_width and
                           support_y >= self.platform_y)
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

        self.score += 10
        top_y = min(y for _, y in self.placed_tiles)
        height_bonus = max(0, (self.grid_h - top_y))
        self.score += (height_bonus // 4) * 10
        self.score = (self.score // 10) * 10
        self.highscore = max(self.highscore, self.score)
        self._save_highscore()

    def _is_game_over(self):
        if not self.placed_tiles:
            return False
        highest = min(y for _, y in self.placed_tiles)
        highest_screen = highest - self.camera_offset
        return highest_screen <= 1

    def _update_camera(self, dt):
        if not self.placed_tiles:
            target = 0
        else:
            highest = min(y for _, y in self.placed_tiles)
            visible_tiles = BASE_HEIGHT / self.tile
            target_highest = visible_tiles / 2
            target = (highest - self.camera_margin) - (self.grid_h - target_highest)
        self.camera_offset += (target - self.camera_offset) * min(1, self.camera_speed * dt)

    def _draw_background(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            BG_TOP = (100, 190, 80)
            BG_BOTTOM = (25, 85, 45)
            r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
            g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
            b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def _draw_panel(self, surface, rect, color):
        shadow = rect.move(4, 4)
        pygame.draw.rect(surface, (0, 0, 0, 90), shadow, border_radius=12)
        pygame.draw.rect(surface, color, rect, border_radius=12)
        pygame.draw.rect(surface, (20, 60, 20), rect, 4, border_radius=12)

    def _draw_button(self, surface, text, center_y):
        rect = pygame.Rect(0, 0, 260, 54)
        rect.center = (BASE_WIDTH // 2, center_y)
        self._draw_panel(surface, rect, self.button_color)
        label = self.ui_font.render(text, True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_grid_rect(self, surface, gx, gy, color):
        x = gx * self.tile
        y = (gy - self.camera_offset) * self.tile
        pygame.draw.rect(surface, color, (x, y, self.tile, self.tile))
        pygame.draw.rect(surface, (0, 0, 0), (x, y, self.tile, self.tile), 2)

    def _draw_platform(self, surface):
        for x in range(self.platform_x, self.platform_x + self.platform_width):
            for y in range(self.platform_y, self.grid_h):
                self._draw_grid_rect(surface, x, y, self.platform_color)

    def _draw_monkey_and_block(self, surface):
        monkey_screen_y = self.tile
        monkey_x = int(round(self.block_x))
        start_x = monkey_x * self.tile + self.tile // 2
        end_y = monkey_screen_y + self.tile // 2
        pygame.draw.line(surface, (80, 120, 40), (start_x, 0), (start_x, end_y), 5)
        pygame.draw.circle(surface, self.monkey_color, (start_x, end_y + 8), self.tile // 2 + 2)

        if self.block_state == "swing":
            anchor = 2
            for dx, dy in self._rotated_shape():
                gx = int(round(self.block_x + dx))
                gy_screen = anchor + dy
                x = gx * self.tile
                y = gy_screen * self.tile
                pygame.draw.rect(surface, self.current_color, (x, y, self.tile, self.tile))
                pygame.draw.rect(surface, (0, 0, 0), (x, y, self.tile, self.tile), 2)
        else:
            for dx, dy in self._rotated_shape():
                gx = int(round(self.block_x + dx))
                gy = int(round(self.block_y + dy))
                self._draw_grid_rect(surface, gx, gy, self.current_color)

    def _draw_placed_blocks(self, surface):
        for gx, gy in self.placed_tiles:
            color = self.placed_colors.get((gx, gy), (200, 200, 200))
            self._draw_grid_rect(surface, gx, gy, color)

    def _draw_hud(self, surface):
        panel_height = 92
        panel = pygame.Rect(10, BASE_HEIGHT - panel_height - 10, 165, panel_height)
        self._draw_panel(surface, panel, self.hud_panel_color)

        score_y = panel.y + 8
        hs_y = panel.y + 33
        timer_y = panel.y + 60

        score = self.ui_font.render(f"Score: {self.score}", True, (255, 255, 200))
        hs = self.small_font.render(f"Highscore: {self.highscore}", True, (255, 255, 200))
        surface.blit(score, (22, score_y))
        surface.blit(hs, (22, hs_y))

        time_left = max(0, int(self.auto_drop_timer))
        timer_color = (255, 240, 80) if time_left > 4 else (255, 70, 70)
        timer_text = self.small_font.render(f"Time {time_left}s", True, timer_color)
        surface.blit(timer_text, (22, timer_y))

    def _draw_game(self, surface):
        self._draw_platform(surface)
        self._draw_placed_blocks(surface)
        self._draw_monkey_and_block(surface)
        self._draw_hud(surface)

    def _draw_start_screen(self, surface):
        cy = BASE_HEIGHT // 2
        title = self.title_font.render("MONKEY", True, (255, 230, 80))
        title2 = self.title_font.render("STACKER", True, (255, 230, 80))
        surface.blit(title, title.get_rect(center=(BASE_WIDTH // 2, cy - 110)))
        surface.blit(title2, title2.get_rect(center=(BASE_WIDTH // 2, cy - 55)))
        self._draw_button(surface, "Press B To Start", cy + 65)

    def _draw_game_over(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        cy = BASE_HEIGHT // 2
        title = self.title_font.render("GAME OVER", True, (255, 80, 80))
        surface.blit(title, title.get_rect(center=(BASE_WIDTH // 2, cy - 50)))
        self._draw_button(surface, "Press B To Restart", cy + 65)

    def on_exit(self):
        self.input.close()