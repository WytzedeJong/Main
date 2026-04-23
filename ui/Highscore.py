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
        self.selected_x = 0  # X-as: horizontaal (game selection)
        self.selected_y = 0  # Y-as: verticaal (0=highscore, 1=achievement)
        
        self.title_font = self.styles.create_font(self.styles.FONT_HOME_TITLE_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_HOME_TIME_SIZE)
        self.card_font = self.styles.create_font(self.styles.FONT_HOME_CARD_SIZE, bold=True)

        self.card_width = self.styles.CARD_WIDTH
        self.card_height = self.styles.CARD_HEIGHT
        self.spacing = self.styles.CARD_SPACING
        self.current_scroll_x = 0
        self.current_scroll_y = 0
        
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
                if self.selected_x < len(self.game_keys) - 1:
                    self.selected_x += 1
                if self.selected_y > 0:
                    self.selected_y = 0

            if event.key == pygame.K_LEFT:
                if self.selected_x > 0:
                    self.selected_x -= 1
                if self.selected_y > 0:
                    self.selected_y = 0

            if event.key == pygame.K_DOWN:
                if self.selected_y < 1:  # 0=highscore, 1=achievement
                    self.selected_y += 1

            if event.key == pygame.K_UP:
                if self.selected_y > 0:
                    self.selected_y -= 1

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

    def draw_card(self, surface, color, x, y, width, height, text, scale, border_radius):

        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=int(border_radius))

        scaled_font_size = int(self.styles.FONT_HOME_CARD_SIZE * scale)
        scaled_font_size = max(10, scaled_font_size)

        lines = text.split('\n')
        if len(lines) > 1:
            line_height = int(12 * scale)
            total_text_height = len(lines) * line_height
            y_start = y + (height - total_text_height) // 2
            
            font_for_text = pygame.font.SysFont("Arial", scaled_font_size, bold=True)
            for i, line in enumerate(lines):
                label = font_for_text.render(line, True, self.styles.TEXT_SET)
                label_rect = label.get_rect(center=(x + width // 2, y_start + i * line_height))
                surface.blit(label, label_rect)
        else:
            # Single line text - centreren in de kaart
            font_for_text = pygame.font.SysFont("Arial", scaled_font_size, bold=True)
            label = font_for_text.render(text, True, self.styles.TEXT_SET)
            label_rect = label.get_rect(center=(x + width // 2, y + height // 2))
            surface.blit(label, label_rect)

    def draw_achievement(self, surface, color, x, y, width, height, text, scale, border_radius):
        

        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=int(border_radius))

        scaled_font_size = int(self.styles.FONT_HOME_CARD_SIZE * scale)
        scaled_font_size = max(10, scaled_font_size)

        lines = text.split('\n')
        if len(lines) > 1:
            line_height = int(12 * scale)
            total_text_height = len(lines) * line_height
            y_start = y + (height - total_text_height) // 2
            
            font_for_text = pygame.font.SysFont("Arial", scaled_font_size, bold=True)
            for i, line in enumerate(lines):
                label = font_for_text.render(line, True, self.styles.TEXT_SET)
                label_rect = label.get_rect(center=(x + width // 2, y_start + i * line_height))
                surface.blit(label, label_rect)
        else:
            # Single line text - centreren in de kaart
            font_for_text = pygame.font.SysFont("Arial", scaled_font_size, bold=True)
            label = font_for_text.render(text, True, self.styles.TEXT_SET)
            label_rect = label.get_rect(center=(x + width // 2, y + height // 2))
            surface.blit(label, label_rect)

    def update(self, dt):
        diff_x = self.selected_x - self.current_scroll_x
        self.current_scroll_x += diff_x * 0.03
        
        diff_y = self.selected_y - self.current_scroll_y
        self.current_scroll_y += diff_y * 0.03

    def draw(self, surface):
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)

        self.sq.vierkantjes(self)

        title = self.title_font.render("Highscores", True, self.styles.TEXT_COLOR)
        base_surface.blit(title, (30, 25))

        # user name toevoegen, werkt nog niet correct
        username = "Guest"
        if isinstance(self.user, dict):
            username = self.user.get("name", "Guest")
        elif isinstance(self.user, str):
            username = self.user

        now = datetime.datetime.now().strftime("%H:%M")
        time_text = self.time_font.render(now, True, self.styles.TEXT_COLOR)
        base_surface.blit(time_text, (BASE_WIDTH - 90, 25))

        # Display highscores for each game
        start_x = BASE_WIDTH // 2
        y_centre = BASE_HEIGHT // 2

        n = len(self.game_keys)

        for i, game_name in enumerate(self.game_keys):

            
            distance_y_highscore = 0 - self.current_scroll_y
            distance_x = i - self.current_scroll_x  
            standard_radius = 12
            scale = max(0.55, 1.0 - abs(distance_x) * 0.2)
            border_radius = standard_radius * (2 - scale)
            new_width = self.card_width * scale
            new_height = self.card_width * scale
            x = start_x + (distance_x * (self.card_width + self.spacing)) - (new_width // 2)       
            curr_y = y_centre + (distance_y_highscore * 80) - (new_height // 2)
            


               # distance_y_highscore = 0 - self.current_scroll_y
            #vertical_offset = 130
            #curr_y = y_centre + (distance_y_highscore * vertical_offset) - (new_height // 2)
            
            # Hide cards too far away
            if abs(distance_x) > 3:
                continue
            
            # Check if this card is selected (for highscores, y=0)
            is_active_highscore = (i == self.selected_x and self.selected_y == 0)
            color_highscore = self.styles.CARD_SELECTED if is_active_highscore else self.styles.CARD_COLOR

            # settings voor achievements cards
            spacing = 80
            a_width = self.card_width * 0.8 * scale
            a_height = self.card_width * 0.8 * scale
            curr_y_a = curr_y + (new_height // 2) + (spacing * 0.7)
            achievement_text = "test"
            corr = (new_width // 2) - (a_width // 2)
            achievement_x = x + corr
            
            # Check if this card is selected (for achievements, y=1)
            is_active_achievement = (i == self.selected_x and self.selected_y == 1)
            color_achievement = self.styles.CARD_SELECTED if is_active_achievement else self.styles.CARD_COLOR
             
            if game_name == 'Puzzle':
                puzzle_times = self.highscores.get(game_name, {})
                if isinstance(puzzle_times, dict):
                    times_list = []
                    for difficulty in ['Easy', 'Medium', 'Hard']:
                        time_str = puzzle_times.get(difficulty, '--:--')
                        times_list.append(f"{difficulty}: {time_str}")
                    score_text = "Puzzle\n\n" + "\n\n".join(times_list)
                else:
                    score_text = f"{game_name}: {puzzle_times}"
            else:
                score = self.highscores.get(game_name, 0)
                if game_name == 'Pengu':
                    score_text = f"{game_name}\n\nWins: {score}"
                else:
                    score_text = f"{game_name}\n\nScore: {score}"

            self.draw_card(base_surface, color_highscore, x, curr_y, new_width, new_height, score_text, scale, border_radius)
            self.draw_achievement(base_surface, color_achievement, achievement_x, curr_y_a, a_width, a_height, achievement_text, scale, border_radius)