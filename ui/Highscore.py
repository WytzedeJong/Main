import pygame
import datetime
import json
import os
from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from config import styles
from ui.lockscreen import LockScreen
from core.input_manager import InputHandler


class Highscore(Scene):
    def __init__(self, manager):
        super().__init__(manager)

        self.input = InputHandler()

        self.styles = styles
        self.user = self.get_user()
        self.game_keys = self.get_members()
        self.selected = 0

        self.title_font = self.styles.create_font(self.styles.FONT_HOME_TITLE_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_HOME_TIME_SIZE)
        self.card_font = self.styles.create_font(self.styles.FONT_HOME_CARD_SIZE, bold=True)

        self.card_width = self.styles.CARD_WIDTH
        self.card_height = self.styles.CARD_HEIGHT
        self.spacing = self.styles.CARD_SPACING

        self.highscores = self.load_highscores()

    def get_user(self):
        user = getattr(self.manager, 'current_user', None)
        if user:
            return user
        try:
            lock = LockScreen(self.manager)
            return lock.get_user() or 0
        except Exception:
            return 0

    def get_members(self):
        path = os.path.join("data", "users.json")

        username = None
        if isinstance(self.user, dict):
            username = self.user.get("name")
        elif isinstance(self.user, str):
            username = self.user

        if not username:
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for player in data.get("users", []):
                if player.get("name") == username:
                    return list(player.get("highscores", {}).keys())

            return []
        except Exception:
            return []

    def load_highscores(self):
        highscores = {key: 0 for key in self.game_keys}

        username = None
        if isinstance(self.user, dict):
            username = self.user.get("name")
        elif isinstance(self.user, str):
            username = self.user

        if not username:
            return highscores

        path = os.path.join("data", "users.json")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for player in data.get("users", []):
                if player.get("name") == username:
                    highscores.update(player.get("highscores", {}))
                    return highscores
        except Exception:
            pass

        return highscores

    def handle_events(self, event):
        pass

    def update(self, dt):
        self.input.update()

        if len(self.game_keys) == 0:
            return

        if self.input.just_pressed("RIGHT"):
            self.selected = (self.selected + 1) % len(self.game_keys)

        if self.input.just_pressed("LEFT"):
            self.selected = (self.selected - 1) % len(self.game_keys)

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

        title = self.title_font.render("Highscores", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        username = "Guest"
        if isinstance(self.user, dict):
            username = self.user.get("name", "Guest")
        elif isinstance(self.user, str):
            username = self.user

        now = datetime.datetime.now().strftime("%H:%M")
        time_text = self.time_font.render(now, True, self.styles.TEXT_COLOR)
        base_surface.blit(time_text, (BASE_WIDTH - 90, 25))

        player_text = self.card_font.render(f"Player: {username}", True, self.styles.TEXT_COLOR)
        base_surface.blit(player_text, (30, 60))

        if not self.game_keys:
            return

        total_width = len(self.game_keys) * self.card_width + (len(self.game_keys) - 1) * self.spacing
        start_x = (BASE_WIDTH - total_width) // 2
        y = 120

        for i, game_name in enumerate(self.game_keys):
            x = start_x + i * (self.card_width + self.spacing)
            score = self.highscores.get(game_name, 0)
            self.draw_card(base_surface, x, y, self.card_width, self.card_height,
                           f"{game_name}:{score}", i == self.selected)