import math
import pygame
import json
import os

from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import AppStyles

from ui.lockscreen import LockScreen

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

        self.title_font = pygame.font.SysFont("arial", 44, bold=True)
        self.ui_font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)

        self.platform_color = (110, 75, 45)

        self.block_colors = [
            (255, 210, 60),
            (140, 240, 160),
            (140, 200, 255),
            (240, 150, 120),
            (200, 140, 240),
        ]

        self.monkey_color = (170, 110, 65)

        self._create_shapes()
        # determine current user first so highscores can be loaded per-player
        self.user = self.get_user()

        self._load_highscore()
        self._start_new_game()

    def get_user(self):
        # prefer manager's current_user if already set
        user = getattr(self.manager, 'current_user', None)
        if user:
            return user

        # fallback: create a LockScreen with the same manager and ask it
        try:
            lock = LockScreen(self.manager)
            return lock.get_user() or 0
        except Exception:
            return 0
    
    def _scores_path(self):
        return os.path.join(os.path.dirname(__file__), "monkey_scores.json")
    
    def user_highscore(self, score):
        path = os.path.join("data", "users.json")
        target_user = self.user 
        
        try:
            with open(path, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            print("User data not found")
            return
        
        found = False
        for player in data["users"]:
            if player["name"] == target_user:
                player["Highscore"].append(score)
                found = True
                break
                
        if found:
            with open(path, 'w') as file:
                json.dump(data, file, indent=4)
            print(f"Score {score} opgeslagen voor {target_user}")
        else:
            print(f"Gebruiker {target_user} niet gevonden in JSON")
                

    def _load_highscore(self):
        # Prefer per-user highscore from data/users.json
        self.highscore = 0

        # resolve user name
        uname = None
        if isinstance(self.user, dict):
            uname = self.user.get("name")
        elif isinstance(self.user, str):
            uname = self.user

        if uname:
            users_path = os.path.join("data", "users.json")
            try:
                with open(users_path, "r", encoding="utf-8") as f:
                    users_data = json.load(f)

                for player in users_data.get("users", []):
                    if player.get("name") == uname:
                        cur = player.get("Highscore")
                        if isinstance(cur, list) and cur:
                            try:
                                self.highscore = max(int(x) for x in cur)
                            except Exception:
                                self.highscore = 0
                        else:
                            try:
                                self.highscore = int(cur)
                            except Exception:
                                self.highscore = 0
                        return
            except Exception:
                # fall back to legacy path below
                pass

        # fallback: load legacy monkey_scores.json best value
        try:
            with open(self._scores_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            self.highscore = int(data.get("best", 0))
        except Exception:
            self.highscore = 0

    def _save_highscore(self):
        # normalize score to tens
        best = (self.highscore // 10) * 10

        # update user's Highscore in data/users.json, keeping only the highest value
        path = os.path.join("data", "users.json")

        try:
            with open(path, "r", encoding="utf-8") as f:
                users_data = json.load(f)
        except Exception:
            users_data = {"users": []}

        target = self.user
        target_name = None
        if isinstance(target, dict):
            target_name = target.get("name")
        elif isinstance(target, str):
            target_name = target

        if target_name:
            updated = False
            for player in users_data.get("users", []):
                if player.get("name") == target_name:
                    cur = player.get("Highscore")
                    # determine current best value
                    if isinstance(cur, list):
                        try:
                            cur_val = max(int(x) for x in cur) if cur else 0
                        except Exception:
                            cur_val = 0
                    else:
                        try:
                            cur_val = int(cur)
                        except Exception:
                            cur_val = 0

                    # update only if new best is higher
                    if best > cur_val:
                        player["Highscore"] = [best]
                    else:
                        # keep existing highest as a single-item list
                        player["Highscore"] = [cur_val]

                    updated = True
                    break

            if updated:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(users_data, f, indent=4)
                except Exception:
                    pass

        # legacy: also save a simple best value to monkey_scores.json for compatibility
        try:
            with open(self._scores_path(), "w", encoding="utf-8") as f:
                json.dump({"best": best}, f)
        except Exception:
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



    def handle_events(self, event):

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                from ui.Games_menu import Game_Menu
                self.manager.set_scene(Game_Menu(self.manager))
                return

            if self.state == "start":

                if event.key == pygame.K_SPACE:
                    self.state = "playing"

            elif self.state == "playing":

                if event.key == pygame.K_SPACE and self.block_state == "swing":

                    top = self.camera_offset
                    self.block_y = top + 2

                    self.block_state = "fall"

                if event.key in (pygame.K_UP, pygame.K_w):
                    self._rotate_current_shape()

            elif self.state == "game_over":

                if event.key == pygame.K_RETURN:

                    self._start_new_game()
                    self.state = "playing"

    def update(self, dt):

        if self.state != "playing":
            return

        if self.block_state == "swing":

            self._update_swing_speed()

            self.swing_angle += self.swing_speed * dt

            swing_offset = math.sin(self.swing_angle) * self.swing_amplitude

            self.block_x = self.swing_center_x + swing_offset

            self.block_x = max(0, min(self.block_x, self.grid_w - 1))

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

        factor = 1 + height * 0.05
        factor = max(1, min(factor, 3))

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

            if below >= self.grid_h:
                return True

            if (gx, below) in solid:
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

            on_platform = (
                self.platform_x <= gx < self.platform_x + self.platform_width
                and support_y >= self.platform_y
            )

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
            
            BG_TOP = (120, 200, 180)
            BG_BOTTOM = (40, 120, 140)
            
            r = int(BG_TOP[0]*(1-ratio)+BG_BOTTOM[0]*ratio)
            g = int(BG_TOP[1]*(1-ratio)+BG_BOTTOM[1]*ratio)
            b = int(BG_TOP[2]*(1-ratio)+BG_BOTTOM[2]*ratio)

            pygame.draw.line(surface,(r,g,b),(0,y),(BASE_WIDTH,y))

    def _draw_panel(self, surface, rect, color):

        shadow = rect.move(3,3)
        pygame.draw.rect(surface,(0,0,0,80),shadow,border_radius=8)

        pygame.draw.rect(surface,color,rect,border_radius=8)
        pygame.draw.rect(surface,(0,0,0),rect,2,border_radius=8)

    def _draw_button(self, surface, text, center_y):

        rect = pygame.Rect(0,0,240,46)
        rect.center = (BASE_WIDTH//2, center_y)

        self._draw_panel(surface,rect,(70,160,90))

        label = self.ui_font.render(text,True,(255,255,255))
        surface.blit(label,label.get_rect(center=rect.center))

    def _draw_grid_rect(self, surface, gx, gy, color):

        x = gx * self.tile
        y = (gy - self.camera_offset) * self.tile

        pygame.draw.rect(surface,color,(x,y,self.tile,self.tile))
        pygame.draw.rect(surface,(0,0,0),(x,y,self.tile,self.tile),1)

    def _draw_platform(self, surface):

        for x in range(self.platform_x,self.platform_x+self.platform_width):
            for y in range(self.platform_y,self.grid_h):
                self._draw_grid_rect(surface,x,y,self.platform_color)

    def _draw_monkey_and_block(self, surface):

        monkey_screen_y = self.tile
        monkey_x = int(round(self.block_x))

        start_x = monkey_x*self.tile + self.tile//2
        end_y = monkey_screen_y + self.tile//2

        pygame.draw.line(surface,(80,120,60),(start_x,0),(start_x,end_y),3)

        pygame.draw.circle(surface,self.monkey_color,(start_x,end_y+8),self.tile//2)

        if self.block_state == "swing":

            anchor = 2

            for dx,dy in self._rotated_shape():

                gx = int(round(self.block_x+dx))
                gy_screen = anchor+dy

                x = gx*self.tile
                y = gy_screen*self.tile

                pygame.draw.rect(surface,self.current_color,(x,y,self.tile,self.tile))
                pygame.draw.rect(surface,(0,0,0),(x,y,self.tile,self.tile),1)

        else:

            for dx,dy in self._rotated_shape():

                gx = int(round(self.block_x+dx))
                gy = int(round(self.block_y+dy))

                self._draw_grid_rect(surface,gx,gy,self.current_color)

    def _draw_placed_blocks(self, surface):

        for gx,gy in self.placed_tiles:

            color = self.placed_colors.get((gx,gy),(200,200,200))
            self._draw_grid_rect(surface,gx,gy,color)

    def _draw_hud(self, surface):

        panel = pygame.Rect(10,10,160,60)
        self._draw_panel(surface,panel,(60,120,70))

        score = self.ui_font.render(f"Score: {self.score}",True,(255,255,255))
        hs = self.small_font.render(f"Highscore: {self.highscore}",True,(255,255,255))

        surface.blit(score,(20,16))
        surface.blit(hs,(20,40))

    def _draw_game(self, surface):

        self._draw_platform(surface)
        self._draw_placed_blocks(surface)
        self._draw_monkey_and_block(surface)
        self._draw_hud(surface)

    def _draw_start_screen(self, surface):

        title = self.title_font.render("Monkey Stacker",True,(255,255,255))
        surface.blit(title,title.get_rect(center=(BASE_WIDTH//2,150)))

        self._draw_button(surface,"Press space to start",260)

    def _draw_game_over(self, surface):

        overlay = pygame.Surface((BASE_WIDTH,BASE_HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,150))
        surface.blit(overlay,(0,0))

        title = self.title_font.render("Game Over",True,(255,255,255))
        surface.blit(title,title.get_rect(center=(BASE_WIDTH//2,160)))

        self._draw_button(surface,"Press enter to try again",250)
