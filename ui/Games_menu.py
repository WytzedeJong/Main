import pygame
import datetime
from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from config import styles
from games.Pengu_Slider.game import AdventureGame
from games.monkey_stacker.game import MonkeyStacker
from games.winman.game import WinMan
from games.dungeon.game import DungeonGame
from core.input_manager import InputHandler


class Game_Menu(Scene):
    def __init__(self, manager):
        super().__init__(manager)

        self.input = InputHandler()

        self.styles = styles
        self.games = [
            ("Pengu Slider", AdventureGame),
            ("Monkey", MonkeyStacker),
            ("WinMan", WinMan),
            ("1 Minute Dungeon", DungeonGame),
        ]

        self.selected = 0

        self.title_font = self.styles.create_font(self.styles.FONT_HOME_TITLE_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_HOME_TIME_SIZE)
        self.card_font = self.styles.create_font(self.styles.FONT_HOME_CARD_SIZE, bold=True)

        self.card_width = self.styles.CARD_WIDTH
        self.card_height = self.styles.CARD_HEIGHT
        self.spacing = self.styles.CARD_SPACING

    def handle_events(self, event):
        # Niet meer nodig
        pass

    def update(self, dt):
        self.input.update()

        if len(self.games) == 0:
            return

        # Navigatie
        if self.input.just_pressed("RIGHT"):
            self.selected = (self.selected + 1) % len(self.games)

        if self.input.just_pressed("LEFT"):
            self.selected = (self.selected - 1) % len(self.games)

        # Selecteren
        if self.input.just_pressed("L") or self.input.just_pressed("ENTER"):
            game_class = self.games[self.selected][1]
            self.manager.set_scene(game_class(self.manager))

        # Terug
        if self.input.just_pressed("B"):
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))

    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def draw_card(self, surface, x, y, width, height, text, is_selected):
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 60))
        surface.blit(shadow, (x + 6, y + 6))

        color = self.styles.CARD_SELECTED if is_selected else self.styles.CARD_COLOR
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=12)

        label = self.card_font.render(text, True, self.styles.TEXT_SET)
        surface.blit(label, label.get_rect(center=(x + width // 2, y + height - 20)))

    def draw(self, surface):
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)

        title = self.title_font.render("WinMan", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        now = datetime.datetime.now().strftime("%H:%M")
        time_text = self.time_font.render(now, True, self.styles.TEXT_COLOR)
        base_surface.blit(time_text, (BASE_WIDTH - 90, 25))

        total_width = len(self.games) * self.card_width + (len(self.games) - 1) * self.spacing
        start_x = (BASE_WIDTH - total_width) // 2
        y = 80

        for i, (name, _) in enumerate(self.games):
            x = start_x + i * (self.card_width + self.spacing)
            self.draw_card(base_surface, x, y, self.card_width, self.card_height, name, i == self.selected)

        # placeholders
        a_text = self.card_font.render("", True, self.styles.TEXT_COLOR)
        b_text = self.card_font.render("", True, self.styles.TEXT_COLOR)

        base_surface.blit(a_text, (145, BASE_HEIGHT - 45))
        base_surface.blit(b_text, (385, BASE_HEIGHT - 45))