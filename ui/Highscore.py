import pygame
import datetime
import json
import os
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import styles
from ui.settings_menu import SettingsMenu
from ui.Games_menu import Game_Menu
from ui.lockscreen import LockScreen
from ui.vierkantjes import vierkantjes




class Highscore(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = styles
        self.sq = vierkantjes
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
        
        # Get username from self.user
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
            
            # Zoek de speler in users array
            for player in data.get("users", []):
                if player.get("name") == username:
                    highscores = player.get("highscores", {})
                    return list(highscores.keys())  # Return keys: ["Monkey", "Racer", "Puzzle"]
            
            # User niet gevonden
            return []
        except Exception as e:
            print(f"Error loading members: {e}")
            return []

    def load_highscores(self):
        highscores = {key: 0 for key in self.game_keys}
        
        if not self.user or (isinstance(self.user, int) and self.user == 0):
            return highscores
        
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
                    user_scores = player.get("highscores", {})
                    # Update met de waarden van de user
                    highscores.update(user_scores)
                    return highscores
        except Exception as e:
            print(f"Error loading highscores: {e}")
        
        return highscores

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.selected = (self.selected + 1) % len(self.game_keys)

            if event.key == pygame.K_LEFT:
                self.selected = (self.selected - 1) % len(self.game_keys)

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

    def draw_card(self, surface, x, y, width, height, text, is_selected):
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 60))
        surface.blit(shadow, (x + 6, y + 6))

        color = self.styles.CARD_SELECTED if is_selected else self.styles.CARD_COLOR
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=12)

        # Handle multi-line text (for Puzzle)
        lines = text.split('\n')
        if len(lines) > 1:
            # Multi-line text (Puzzle) - centreren in de kaart
            line_height = 14
            total_text_height = len(lines) * line_height
            y_start = y + (height - total_text_height) // 2
            
            for i, line in enumerate(lines):
                label = self.card_font.render(line, True, self.styles.TEXT_SET)
                label_rect = label.get_rect(center=(x + width // 2, y_start + i * line_height))
                surface.blit(label, label_rect)
        else:
            # Single line text - centreren in de kaart
            label = self.card_font.render(text, True, self.styles.TEXT_SET)
            label_rect = label.get_rect(center=(x + width // 2, y + height // 2))
            surface.blit(label, label_rect)

    def update(self, dt):
        pass

    def draw(self, surface):
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)

        self.sq.vierkantjes(self)

        title = self.title_font.render("Highscores", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        # Get user name for display
        username = "Guest"
        if isinstance(self.user, dict):
            username = self.user.get("name", "Guest")
        elif isinstance(self.user, str):
            username = self.user

        now = datetime.datetime.now().strftime("%H:%M")
        time_text = self.time_font.render(now, True, self.styles.TEXT_COLOR)
        base_surface.blit(time_text, (BASE_WIDTH - 90, 25))

        # Display player name
        player_text = self.card_font.render(f"Player: {username}", True, self.styles.TEXT_COLOR)
        base_surface.blit(player_text, (30, 60))

        # Display highscores for each game
        total_width = len(self.game_keys) * self.card_width + (len(self.game_keys) - 1) * self.spacing
        start_x = (BASE_WIDTH - total_width) // 2
        y = (BASE_HEIGHT - self.card_height) // 2 + 40  # Iets lager

        for i, game_name in enumerate(self.game_keys):
            x = start_x + i * (self.card_width + self.spacing)
            
            # Puzzle toont difficulty times
            if game_name == 'Puzzle':
                Puzzle_times = self.highscores.get(game_name, {})
                if isinstance(Puzzle_times, dict):
                    # Toon de 3 moeilijkheden met hun best times
                    times_list = []
                    for difficulty in ['Easy', 'Medium', 'Hard']:
                        time_str = Puzzle_times.get(difficulty, '--:--')
                        times_list.append(f"{difficulty}: {time_str}")
                    
                    score_text = "Puzzle\n" + "\n".join(times_list)
                else:
                    score_text = f"{game_name}: {Puzzle_times}"
            else:
                score = self.highscores.get(game_name, 0)
                if game_name == 'Pengu':
                    score_text = f"{game_name}\nWins: {score}"
                else:
                    score_text = f"{game_name}\nScore: {score}"
            
            self.draw_card(base_surface, x, y, self.card_width, self.card_height, score_text, i == self.selected)

