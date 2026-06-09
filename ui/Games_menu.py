import pygame
import datetime
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import styles
from games.puzzle.game import PuzzleGame
from games.Pengu_Slider.game import AdventureGame
from games.Space.game import SpaceGame
from games.dungeon.game import DungeonGame
from games.monkey_stacker.game import MonkeyStacker
from games.tower_defense.game import TowerGame
from games.Pixelspin.game import PixelspinGame
from games.winman.game import WinMan
from games.farm_nation.game import FarmNationGame
from games.racer.game import RacerGame
from ui.settings_menu import SettingsMenu
from ui.vierkantjes import vierkantjes
from ui.status import draw_time_and_battery


class Game_Menu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = styles
        self.sq = vierkantjes
        self.games = [
            ("Puzzle", PuzzleGame),
            ("1 Minute Dungeon", DungeonGame),
            ("Pengu Slider", AdventureGame),
            ("Space", SpaceGame),
            ("Monkey Stacker", MonkeyStacker),
            ("Tower Defense", TowerGame),
            ("Farm Nation", FarmNationGame),
            ("Speed Racer", RacerGame),
            ("Pixelspin", PixelspinGame),
            ("System Purge", WinMan),
        ]

        self.selected = 0
        self.current_scroll = 0

        self.title_font = self.styles.create_font(self.styles.FONT_HOME_TITLE_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_HOME_TIME_SIZE)
        self.card_font = self.styles.create_font(self.styles.FONT_HOME_CARD_SIZE, bold=True)

        self.card_width = self.styles.CARD_WIDTH
        self.card_height = self.styles.GAMES_CARD_HEIGHT
        self.spacing = self.styles.CARD_SPACING

        self.font_cache = {}

        self.game_icons = {}
        self.icon_cache = {}
        try:
            self.game_icons["Monkey Stacker"] = pygame.image.load("ui/images/monkeystacker.png").convert_alpha()
            self.game_icons["System Purge"] = pygame.image.load("ui/images/systempurge.png").convert_alpha()
            self.game_icons["Space"] = pygame.image.load("ui/images/space.png").convert_alpha()
            self.game_icons["1 Minute Dungeon"] = pygame.image.load("ui/images/dungeon.png").convert_alpha()
            self.game_icons["Puzzle"] = pygame.image.load("ui/images/puzzle.png").convert_alpha()
            self.game_icons["Tower Defense"] = pygame.image.load("ui/images/towerdefence.png").convert_alpha()
            self.game_icons["Pixelspin"] = pygame.image.load("ui/images/pixelspin.png").convert_alpha()
            self.game_icons["Pengu Slider"] = pygame.image.load("ui/images/pinguslider.png").convert_alpha()
            self.game_icons["Speed Racer"] = pygame.image.load("ui/images/racer.png").convert_alpha()
            self.game_icons["Farm Nation"] = pygame.image.load("ui/images/farm.png").convert_alpha()
        except Exception:
            pass

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.selected += 1

            if event.key == pygame.K_LEFT:
                self.selected -= 1

            if event.key == pygame.K_RETURN:
                real_i = self.selected % len(self.games)
                self.manager.game_menu_selected = real_i
                game_class = self.games[real_i][1]
                self.manager.set_scene(game_class(self.manager))

            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def _get_scaled_icon(self, name, width, height):
        icon = self.game_icons.get(name)
        if icon is None:
            return None

        w = max(1, int(width))
        h = max(1, int(height))
        key = (name, w, h)
        cached = self.icon_cache.get(key)
        if cached is not None:
            return cached

        scaled = pygame.transform.smoothscale(icon, (w, h))
        self.icon_cache[key] = scaled
        return scaled

    def draw_card(self, surface, color, x, y, width, height, text, scale, border_radius, is_selected):
        rect = pygame.Rect(int(x), int(y), int(width), int(height))
        pygame.draw.rect(surface, color, rect, border_radius=int(border_radius))

        scaled_font_size = int(self.styles.FONT_HOME_CARD_SIZE * scale)
        scaled_font_size = max(10, scaled_font_size)

        if scaled_font_size not in self.font_cache:
            self.font_cache[scaled_font_size] = pygame.font.SysFont("Arial", scaled_font_size, bold=True)

        scaled_icon = self._get_scaled_icon(text, rect.width, rect.height)
        if scaled_icon is not None:
            surface.blit(scaled_icon, rect.topleft)

        if is_selected:
            label = self.font_cache[scaled_font_size].render(text, True, self.styles.TEXT_SET)
            label_rect = label.get_rect(center=(rect.centerx, rect.bottom + 18))
        
        if is_selected and label_rect.width > rect.width - 4:
            label_rect.width = rect.width - 4
            label_rect.centerx = rect.centerx
        
        if is_selected:
            surface.blit(label, label_rect)


    def update(self, dt):
        diff = self.selected - self.current_scroll
        self.current_scroll += diff * 0.1


    def draw(self, surface):
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)

        self.sq.vierkantjes(self)

        
        title = self.title_font.render("WinMan", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        draw_time_and_battery(base_surface, self.time_font, self.styles.TEXT_COLOR, y=25, margin_right=15)

        start_x = BASE_WIDTH // 2
        y_centre = BASE_HEIGHT // 2

        n = len(self.games)
        real_selected = self.selected % n

        for i, (name, _) in enumerate(self.games):
            distance = (i - self.current_scroll + n / 2) % n - n / 2
            standard_radius = 12

            
        
            scale = max(0.55, 1.0 - abs(distance) * 0.2)
            border_radius = standard_radius*(2 -scale)
            new_width = self.card_width * scale
            new_height = self.card_height * scale
            x = start_x + (distance * (self.card_width + (self.spacing * (scale ** 8)))) - (new_width // 2)
            curr_y = y_centre - (new_height // 2)

            is_active = (i == real_selected)
            base_color = pygame.Color(self.styles.CARD_COLOR)
            afstand = abs(start_x - x)
            factor = max(0.0, 1.0 - (afstand / BASE_WIDTH))     
            r = int(base_color.r * factor)
            g = int(base_color.g * factor)
            b = int(base_color.b * factor)

            vervaging_kleur = (r,g,b)
            color = self.styles.CARD_SELECTED if is_active else vervaging_kleur

            self.draw_card(base_surface, color, x, curr_y, new_width, new_height, name, scale, border_radius, is_active)

        a_text = self.card_font.render("", True, self.styles.TEXT_COLOR)
        b_text = self.card_font.render("", True, self.styles.TEXT_COLOR)

        base_surface.blit(a_text, (145, BASE_HEIGHT - 45))
        base_surface.blit(b_text, (385, BASE_HEIGHT - 45))
