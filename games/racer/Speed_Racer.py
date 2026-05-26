"""
LANE RUNNER — A retro 2D endless runner
----------------------------------------
Move UP / DOWN arrows to switch lanes.
Dodge the obstacles scrolling from right to left.
Survive as long as possible!

Requirements:
    pip install pygame
Run:
    python lane_runner.py
"""

import pygame
import random
import sys

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 900, 520
FPS = 30
TITLE = "SPEED RACER"

# Lanes
NUM_LANES = 3
LANE_Y = [160, 260, 360]   # y-centre of each lane  ← adjust to reposition lanes
                            # screen height is 520px; 260 is the middle
LANE_SWITCH_SPEED = 1400  # pixels per second

# Player
PLAYER_SPRITE_PATH = r"Images\Racecar\Racecar_0-frame-0.png"
PLAYER_SCALE       = 1.0          # ← change this to resize the sprite (e.g. 0.8, 1.5)
PLAYER_W = int(100 * PLAYER_SCALE)
PLAYER_H = int(44  * PLAYER_SCALE)
PLAYER_X = 120                     # fixed horizontal position

# Background track
TRACK_PATH = r"Images\Race_Track\Racing_Track-frame-0.png"

# Obstacles
OBSTACLE_SPRITE_PATH = r"Images\Obstacles\Obstacle_0.png"
OBSTACLE_SCALE       = 1.0        # ← change this to resize obstacles (e.g. 0.8, 1.5)
OBS_W = int(20 * OBSTACLE_SCALE)  # fixed to match sprite dimensions
OBS_H = int(44 * OBSTACLE_SCALE)
OBS_SPAWN_INTERVAL_START = 30      # frames between spawns (decreases over time)
OBS_SPAWN_INTERVAL_MIN   = 15
OBS_SPEED_START = 600    # pixels per second
OBS_SPEED_MAX   = 2400   # pixels per second

# Scoring
SCORE_PER_FRAME = 0.1             # raw float, display as int

# ---------------------------------------------------------------------------
# COLOUR PALETTE  (retro CRT palette)
# ---------------------------------------------------------------------------
C_BG        = (10, 10, 22)
C_LANE_LINE = (30, 30, 60)
C_LANE_DIM  = (18, 18, 40)
C_LANE_HI   = (22, 22, 52)
C_PLAYER    = (80, 220, 160)
C_PLAYER_D  = (40, 140, 90)
C_PLAYER_EYE= (10, 10, 22)
C_OBS       = [(220, 60, 80), (240, 160, 40), (80, 140, 240),
               (200, 80, 220), (60, 200, 200)]
C_OBS_DARK  = [(140, 30, 50), (180, 110, 20), (40, 90, 180),
               (140, 40, 160), (30, 140, 140)]
C_HUD_TEXT  = (200, 200, 220)
C_HUD_HI    = (80, 220, 160)
C_HEART     = (220, 60, 80)
C_SCANLINE  = (0, 0, 0, 40)       # RGBA
C_GRID      = (20, 20, 50)
C_STAR      = (120, 120, 160)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def draw_retro_rect(surf, color, dark, rect, border=3):
    """Draw a chunky pixel-art style rectangle with a highlight and shadow."""
    x, y, w, h = rect
    pygame.draw.rect(surf, dark,  (x + border, y + border, w, h))   # shadow
    pygame.draw.rect(surf, color, (x, y, w, h))
    # top & left highlight
    pygame.draw.rect(surf, tuple(min(c+60,255) for c in color), (x, y, w, border))
    pygame.draw.rect(surf, tuple(min(c+60,255) for c in color), (x, y, border, h))
    # bottom & right shadow
    pygame.draw.rect(surf, dark, (x, y+h-border, w, border))
    pygame.draw.rect(surf, dark, (x+w-border, y, border, h))


def load_player_sprite():
    """Load and scale the player PNG. Returns None if the file is missing."""
    try:
        img = pygame.image.load(PLAYER_SPRITE_PATH).convert_alpha()
        img = pygame.transform.scale(img, (PLAYER_W, PLAYER_H))
        return img
    except Exception as e:
        print(f"[WARN] Could not load player sprite: {e}")
        return None


def load_track():
    """Load the track PNG scaled to fill the screen height. Returns None on failure."""
    try:
        img = pygame.image.load(TRACK_PATH).convert()
        img = pygame.transform.scale(img, (SCREEN_W, SCREEN_H))
        return img
    except Exception as e:
        print(f"[WARN] Could not load track image: {e}")
        return None


def load_obstacle_sprite():
    """Load and scale the obstacle PNG. Returns None if the file is missing."""
    try:
        img = pygame.image.load(OBSTACLE_SPRITE_PATH).convert_alpha()
        img = pygame.transform.scale(img, (OBS_W, OBS_H))
        return img
    except Exception as e:
        print(f"[WARN] Could not load obstacle sprite: {e}")
        return None


def draw_player(surf, x, y, sprite):
    """Blit the player sprite, or fall back to a simple rectangle."""
    if sprite:
        surf.blit(sprite, (x, y))
    else:
        # Fallback: plain coloured rectangle
        pygame.draw.rect(surf, C_PLAYER, (x, y, PLAYER_W, PLAYER_H))
        pygame.draw.rect(surf, C_PLAYER_D, (x, y, PLAYER_W, PLAYER_H), 3)


def draw_obstacle(surf, obs, sprite):
    if sprite:
        surf.blit(sprite, (int(obs['x']), int(obs['y'])))
    else:
        # Fallback: coloured rectangle
        ci = obs['color_i']
        r = pygame.Rect(obs['x'], obs['y'], obs['w'], obs['h'])
        draw_retro_rect(surf, C_OBS[ci], C_OBS_DARK[ci], r, border=3)


# ---------------------------------------------------------------------------
# STARS (parallax background)
# ---------------------------------------------------------------------------
class StarField:
    def __init__(self):
        self.stars = []
        for _ in range(120):
            x = random.randint(0, SCREEN_W)
            y = random.randint(0, SCREEN_H)
            speed = random.uniform(0.4, 2.5)
            size  = 1 if speed < 1.2 else 2
            brightness = int(60 + speed * 35)
            self.stars.append([x, y, speed, size, brightness])

    def update(self, game_speed_factor=1.0):
        for s in self.stars:
            s[0] -= s[2] * game_speed_factor
            if s[0] < 0:
                s[0] = SCREEN_W
                s[1] = random.randint(0, SCREEN_H)

    def draw(self, surf):
        for s in self.stars:
            c = (s[4], s[4], min(s[4]+40, 255))
            pygame.draw.rect(surf, c, (int(s[0]), int(s[1]), s[3], s[3]))


# ---------------------------------------------------------------------------
# PARTICLE SYSTEM
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, 6.28)
        speed = random.uniform(2, 7)
        self.x = x
        self.y = y
        self.vx = speed * __import__('math').cos(angle)
        self.vy = speed * __import__('math').sin(angle)
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.color = color
        self.size = random.randint(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= 1

    def draw(self, surf):
        alpha = int(255 * self.life / self.max_life)
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.color, alpha), (0, 0, self.size*2, self.size*2))
        surf.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


# ---------------------------------------------------------------------------
# GAME STATE
# ---------------------------------------------------------------------------
class Game:
    def __init__(self, screen, clock, fonts):
        self.screen = screen
        self.clock  = clock
        self.fonts  = fonts
        self.player_sprite   = load_player_sprite()
        self.obstacle_sprite = load_obstacle_sprite()
        self.track_img       = load_track()
        self.track_scroll  = 0.0          # horizontal scroll offset for the track
        self.scanline_surf = self._make_scanlines()
        self.stars = StarField()
        self.reset()

    def _make_scanlines(self):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 4):
            pygame.draw.line(s, (0, 0, 0, 28), (0, y), (SCREEN_W, y))
        return s

    def reset(self):
        self.lane = 1                        # 0 = top, 1 = mid, 2 = bottom
        self.player_y = float(LANE_Y[1] - PLAYER_H // 2)
        self.target_y  = self.player_y

        self.obstacles  = []
        self.particles  = []
        self.score      = 0.0
        self.best       = getattr(self, 'best', 0)
        self.frame      = 0
        self.elapsed    = 0.0   # real seconds played

        self.obs_speed    = float(OBS_SPEED_START)
        self.spawn_timer  = 0
        self.spawn_interval = OBS_SPAWN_INTERVAL_START

        self.running = False
        self.game_over = False

    # --- input handling ---

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                if self.game_over:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset()
                        self.running = True
                    elif event.key == pygame.K_BACKSPACE:
                        self.reset()   # running stays False → title screen
                    return

                if not self.running:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset()
                        self.running = True
                    return

                if event.key == pygame.K_UP and self.lane > 0:
                    self.lane -= 1
                    self.target_y = float(LANE_Y[self.lane] - PLAYER_H // 2)
                if event.key == pygame.K_DOWN and self.lane < NUM_LANES - 1:
                    self.lane += 1
                    self.target_y = float(LANE_Y[self.lane] - PLAYER_H // 2)

    # --- update ---

    def update(self, dt):
        if not self.running or self.game_over:
            return

        self.frame += 1
        self.elapsed += dt

        # Ramp difficulty every 10 seconds — speed grows 10% of start per step
        ramp = int(self.elapsed // 2)
        self.obs_speed = min(OBS_SPEED_START + ramp * (OBS_SPEED_START * 0.1), OBS_SPEED_MAX)
        self.spawn_interval = max(OBS_SPAWN_INTERVAL_MIN,
                                  OBS_SPAWN_INTERVAL_START - ramp * 6)

        # Smooth lane movement (dt-scaled)
        dy = self.target_y - self.player_y
        step = LANE_SWITCH_SPEED * dt
        if abs(dy) < step:
            self.player_y = self.target_y
        else:
            self.player_y += step * (1 if dy > 0 else -1)

        # Score
        self.score += SCORE_PER_FRAME * (self.obs_speed / OBS_SPEED_START)

        # Scroll track background (dt-scaled)
        self.track_scroll = (self.track_scroll + self.obs_speed * dt) % SCREEN_W

        # Spawn obstacles (still frame-counted, interval already tuned per ramp)
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self._spawn_obstacle()

        # Move obstacles (dt-scaled)
        for obs in self.obstacles:
            obs['x'] -= self.obs_speed * dt
        self.obstacles = [o for o in self.obstacles if o['x'] + o['w'] > -20]

        # Collision — one hit = game over
        px = PLAYER_X + 14
        py = int(self.player_y) + 8
        pw = PLAYER_W - 20
        ph = PLAYER_H - 16
        for obs in self.obstacles:
            ox, oy, ow, oh = obs['x']+4, obs['y']+4, obs['w']-8, obs['h']-8
            if px < ox+ow and px+pw > ox and py < oy+oh and py+ph > oy:
                self._hit()
                break

        # Particles
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        # Stars
        self.stars.update(self.obs_speed / OBS_SPEED_START)

    def _spawn_obstacle(self):
        # Always block exactly 2 lanes — leaves exactly 1 safe lane
        blocked = random.sample(range(NUM_LANES), 2)
        for lane in blocked:
            ly = LANE_Y[lane]
            self.obstacles.append({
                'x': float(SCREEN_W + 20),
                'y': ly - OBS_H // 2,
                'w': OBS_W, 'h': OBS_H,
                'color_i': 0,
                'lane': lane,
            })

    def _hit(self):
        cx = PLAYER_X + PLAYER_W // 2
        cy = int(self.player_y) + PLAYER_H // 2
        for _ in range(22):
            self.particles.append(Particle(cx, cy, C_HEART))
        self.game_over = True
        self.best = max(self.best, int(self.score))

    # --- draw ---

    def draw(self):
        self.screen.fill(C_BG)

        # Scrolling track background
        if self.track_img:
            x = -int(self.track_scroll)
            self.screen.blit(self.track_img, (x, 0))
            # Second copy to fill the gap as it scrolls
            self.screen.blit(self.track_img, (x + SCREEN_W, 0))
        else:
            # Fallback: plain grid + lanes if image failed to load
            for gx in range(0, SCREEN_W, 80):
                pygame.draw.line(self.screen, C_GRID, (gx, 0), (gx, SCREEN_H), 1)
            self.stars.draw(self.screen)
            lane_h = 90
            for i, ly in enumerate(LANE_Y):
                rect = pygame.Rect(0, ly - lane_h//2, SCREEN_W, lane_h)
                color = C_LANE_HI if i == self.lane else C_LANE_DIM
                pygame.draw.rect(self.screen, color, rect)
            for i in range(NUM_LANES + 1):
                y = LANE_Y[0] - 45 + i * 90
                for dash_x in range(0, SCREEN_W, 30):
                    pygame.draw.line(self.screen, C_LANE_LINE,
                                     (dash_x, y), (dash_x + 18, y), 2)

        # Obstacles
        for obs in self.obstacles:
            draw_obstacle(self.screen, obs, self.obstacle_sprite)

        # Particles
        for p in self.particles:
            p.draw(self.screen)

        # Player
        draw_player(self.screen,
                    PLAYER_X, int(self.player_y),
                    self.player_sprite)

        # HUD
        self._draw_hud()

        # Scanlines overlay
        self.screen.blit(self.scanline_surf, (0, 0))

        # Screens
        if not self.running and not self.game_over:
            self._draw_title_screen()
        elif self.game_over:
            self._draw_game_over_screen()

    def _draw_hud(self):
        # Score
        score_txt = self.fonts['med'].render(f"SCORE  {int(self.score):>6}", True, C_HUD_TEXT)
        self.screen.blit(score_txt, (20, 14))

        # Best
        best_txt = self.fonts['small'].render(f"BEST {self.best:>6}", True, C_HUD_TEXT)
        self.screen.blit(best_txt, (20, 46))

        # Speed indicator
        spd_pct = (self.obs_speed - OBS_SPEED_START) / (OBS_SPEED_MAX - OBS_SPEED_START)
        spd_txt = self.fonts['small'].render(
            f"SPD {'█' * int(spd_pct * 10)}{'░' * (10 - int(spd_pct * 10))}", True,
            C_HUD_HI if spd_pct > 0.6 else C_HUD_TEXT)
        self.screen.blit(spd_txt, (SCREEN_W // 2 - 80, 14))

    def _draw_overlay(self, lines, sub=None):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 10, 180))
        self.screen.blit(overlay, (0, 0))

        y = SCREEN_H // 2 - 60
        for i, (text, font_key, color) in enumerate(lines):
            surf = self.fonts[font_key].render(text, True, color)
            self.screen.blit(surf, (SCREEN_W//2 - surf.get_width()//2, y))
            y += surf.get_height() + 12

        if sub:
            s = self.fonts['small'].render(sub, True, (120, 120, 160))
            self.screen.blit(s, (SCREEN_W//2 - s.get_width()//2, SCREEN_H - 60))

    def _draw_title_screen(self):
        self._draw_overlay([
            ("SPEED RACER",  'big',   C_HUD_HI),
            ("dodge everything", 'small', C_HUD_TEXT),
        ], sub="ENTER / SPACE  to start   •   ↑ ↓  to switch lanes   •   ESC to quit")

    def _draw_game_over_screen(self):
        self._draw_overlay([
            ("GAME OVER",              'big',   C_HEART),
            (f"SCORE  {int(self.score)}", 'med', C_HUD_TEXT),
            (f"BEST   {self.best}",      'med',  C_HUD_HI),
        ], sub="ENTER / SPACE  play again   •   BACKSPACE  title screen   •   ESC  quit")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    pygame.init()

    # Real fullscreen display at the monitor's native resolution
    real_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    REAL_W, REAL_H = real_screen.get_size()
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # Fixed-size canvas — all game logic runs against this
    canvas = pygame.Surface((SCREEN_W, SCREEN_H))

    # Try to load a pixel-art style font; fall back to SysFont
    def load_font(size):
        try:
            return pygame.font.SysFont("Courier New", size, bold=True)
        except Exception:
            return pygame.font.Font(None, size)

    fonts = {
        'big':   load_font(62),
        'med':   load_font(28),
        'small': load_font(20),
    }

    game = Game(canvas, clock, fonts)

    while True:
        dt = clock.tick(FPS) / 1000.0   # seconds since last frame
        game.handle_input()
        game.update(dt)
        game.draw()

        # Scale canvas to fill the real screen (stretch to fit, no bars)
        scaled = pygame.transform.scale(canvas, (REAL_W, REAL_H))
        real_screen.blit(scaled, (0, 0))
        pygame.display.flip()

        clock.tick(FPS)


if __name__ == "__main__":
    main()