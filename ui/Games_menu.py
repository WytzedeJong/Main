import pygame
import datetime
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import styles
from games.adventure.game import PuzzleGame
from games.Pengu_Slider.game import AdventureGame
from games.racer.game import RacerGame
from games.dungeon.game import DungeonGame
from games.monkey_stacker.game import MonkeyStacker
from ui.settings_menu import SettingsMenu


class Game_Menu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = styles
        self.games = [
            ("Puzzle", PuzzleGame),
            ("Dungeon", DungeonGame),
            ("Pengu Slider", AdventureGame),
            ("Monkey", MonkeyStacker),
            ("test", MonkeyStacker)
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

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.selected += 1

            if event.key == pygame.K_LEFT:
                self.selected -= 1

            if event.key == pygame.K_RETURN:
                real_i = self.selected % len(self.games)
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

    def draw_card(self, surface, x, y, width, height, text, is_selected, scale):
        color = self.styles.CARD_SELECTED if is_selected else self.styles.CARD_COLOR
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=12)

        scaled_font_size = int(self.styles.FONT_HOME_CARD_SIZE * scale)
        scaled_font_size = max(10, scaled_font_size)

        if scaled_font_size not in self.font_cache:
            self.font_cache[scaled_font_size] = pygame.font.SysFont("Arial", scaled_font_size, bold=True)

        label = self.font_cache[scaled_font_size].render(text, True, self.styles.TEXT_SET)
        label_rect = label.get_rect(center=(x + width // 2, y + height - 20))
        surface.blit(label, label_rect)


    def update(self, dt):
        diff = self.selected - self.current_scroll
        self.current_scroll += diff * 0.03

    def draw(self, surface):
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)

        #vierkantjes rechtsboven
        # linksboven
       # linksboven (2 blokjes)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (470, 0, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (470, 0, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (461, 0, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (461, 0, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (470, 9, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (470, 9, 10, 10), width=1)

        #vierkantjes linksonder
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (470, 260, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (470, 260, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (461, 260, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (461, 260, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (461, 251, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (461, 251, 10, 10), width=1)
        
        title = self.title_font.render("WinMan", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        now = datetime.datetime.now().strftime("%H:%M")
        time_text = self.time_font.render(now, True, self.styles.TEXT_COLOR)
        base_surface.blit(time_text, (BASE_WIDTH - 90, 25))

        start_x = BASE_WIDTH // 2
        y_centre = BASE_HEIGHT // 2

        n = len(self.games)
        real_selected = self.selected % n

        for i, (name, _) in enumerate(self.games):
            distance = (i - self.current_scroll + n / 2) % n - n / 2

            scale = max(0.55, 1.0 - abs(distance) * 0.2)
            new_width = self.card_width * scale
            new_height = self.card_height * scale
            x = start_x + (distance * (self.card_width + (self.spacing * (scale ** 8)))) - (new_width // 2)
            curr_y = y_centre - (new_height // 2)

            is_active = (i == real_selected)

            self.draw_card(base_surface, x, curr_y, new_width, new_height, name, is_active, scale)

        a_text = self.card_font.render("", True, self.styles.TEXT_COLOR)
        b_text = self.card_font.render("", True, self.styles.TEXT_COLOR)

        base_surface.blit(a_text, (145, BASE_HEIGHT - 45))
        base_surface.blit(b_text, (385, BASE_HEIGHT - 45))