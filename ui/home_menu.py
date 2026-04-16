import pygame
import datetime
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import styles
from ui.settings_menu import SettingsMenu
from ui.Games_menu import Game_Menu
from ui.lockscreen import LockScreen
from ui.Highscore import Highscore

from core.input_manager import InputHandler


class HomeMenu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = styles

        self.input = InputHandler()

        self.games = [
            ("Settings", SettingsMenu),
            ("Games", Game_Menu),
            ("High Scores", Highscore)
        ]

        self.selected = 0

        # Fonts laden
        self.title_font = self.styles.create_font(self.styles.FONT_HOME_TITLE_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_HOME_TIME_SIZE)
        self.card_font = self.styles.create_font(self.styles.FONT_HOME_CARD_SIZE, bold=True)

        self.card_width = self.styles.CARD_WIDTH
        self.card_height = self.styles.CARD_HEIGHT
        self.spacing = self.styles.CARD_SPACING

    def update(self, dt):
        self.input.update()

        if self.input.just_pressed("RIGHT"):
            self.selected = (self.selected + 1) % len(self.games)

        if self.input.just_pressed("LEFT"):
            self.selected = (self.selected - 1) % len(self.games)

        # Selecteren (A-knop op handheld, L op keyboard-mapping, of ENTER)
        if self.input.just_pressed("L") or self.input.just_pressed("ENTER"):
            game_class = self.games[self.selected][1]
            self.manager.set_scene(game_class(self.manager))

        if self.input.just_pressed("B"):
            self.manager.set_scene(LockScreen(self.manager))

    def handle_events(self, event):

        pass

    # -----------------------
    # Draw helpers
    # -----------------------
    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def draw_card(self, surface, x, y, width, height, text, is_selected):
        # Schaduw effect
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 60))
        surface.blit(shadow, (x + 6, y + 6))

        # Kleur bepalen op basis van selectie
        color = self.styles.CARD_SELECTED if is_selected else self.styles.CARD_COLOR
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=12)

        # Tekst renderen
        label = self.card_font.render(text, True, self.styles.TEXT_SET)
        label_rect = label.get_rect(center=(x + width // 2, y + height - 20))
        surface.blit(label, label_rect)

    def draw(self, surface):
        # Achtergrond en Gradient
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)

        # Titel bovenaan
        title = self.title_font.render("WinMan", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        # Tijd in de hoek
        now = datetime.datetime.now().strftime("%H:%M")
        time_text = self.time_font.render(now, True, self.styles.TEXT_COLOR)
        base_surface.blit(time_text, (BASE_WIDTH - 90, 25))

        # Bereken posities voor de kaarten (gecentreerd)
        total_width = len(self.games) * self.card_width + (len(self.games) - 1) * self.spacing
        start_x = (BASE_WIDTH - total_width) // 2
        y = 80

        for i, (name, _) in enumerate(self.games):
            x = start_x + i * (self.card_width + self.spacing)
            self.draw_card(base_surface, x, y, self.card_width, self.card_height, name, i == self.selected)

        # Voetnoot teksten (optioneel, nu leeg zoals in je bron)
        a_text = self.card_font.render("", True, self.styles.TEXT_COLOR)
        b_text = self.card_font.render("", True, self.styles.TEXT_COLOR)

        base_surface.blit(a_text, (145, BASE_HEIGHT - 45))
        base_surface.blit(b_text, (385, BASE_HEIGHT - 45))