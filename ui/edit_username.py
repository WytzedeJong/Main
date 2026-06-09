import pygame
import json
import os
from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from config import styles


class EditUsername(Scene):
    def __init__(self, manager, current_user, parent_scene):
        super().__init__(manager)
        self.styles = styles
        self.current_user = current_user
        self.parent_scene = parent_scene
        self.new_name = current_user.get("name", "")
        
        self.title_font = self.styles.create_font(self.styles.FONT_EDIT_TITLE_SIZE, bold=True)
        self.name_font = self.styles.create_font(self.styles.FONT_EDIT_NAME_SIZE)
        self.input_font = self.styles.create_font(self.styles.FONT_EDIT_INPUT_SIZE, bold=True)

        self.is_uppercase = True
        self.keyboard = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
            ["_", "CAPS", "BACK", "OK"]
        ]

        self.kb_row = 0
        self.kb_col = 0
        self.card_height = 28
        self.card_radius = 8

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.kb_col = (self.kb_col + 1) % len(self.keyboard[self.kb_row])
            
            elif event.key == pygame.K_LEFT:
                self.kb_col = (self.kb_col - 1) % len(self.keyboard[self.kb_row])
            
            elif event.key == pygame.K_DOWN:
                self.kb_row = (self.kb_row + 1) % len(self.keyboard)
                self.kb_col = min(self.kb_col, len(self.keyboard[self.kb_row]) - 1)
            
            elif event.key == pygame.K_UP:
                self.kb_row = (self.kb_row - 1) % len(self.keyboard)
                self.kb_col = min(self.kb_col, len(self.keyboard[self.kb_row]) - 1)
            
            elif event.key == pygame.K_RETURN:
                key = self.keyboard[self.kb_row][self.kb_col]
                
                if key == "_":
                    if len(self.new_name) < 10:
                        self.new_name += "_"

                elif key == "CAPS":
                    self.is_uppercase = not self.is_uppercase

                elif key == "BACK":
                    self.new_name = self.new_name[:-1]
                
                elif key == "OK":
                    if self.new_name.strip():
                        self.save_username()
                        self.manager.set_scene(self.parent_scene)

                else:
                    if len(self.new_name) < 8:
                        self.new_name += key if self.is_uppercase else key.lower()
            
            elif event.key == pygame.K_ESCAPE:
                self.manager.set_scene(self.parent_scene)

    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def save_username(self):
        # Update current user object
        old_name = self.current_user.get("name", "")
        self.current_user["name"] = self.new_name
        
        # Save to file - use SAME path as lockscreen (root data folder)
        path = os.path.join("data", "users.json")
        
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            
            # Find and update user
            for user in data.get("users", []):
                if user.get("name") == old_name:
                    user["name"] = self.new_name
                    break
            
            with open(path, "w") as f:
                json.dump(data, f, indent=4)

    def update(self, dt):
        pass

    def draw(self, surface):
        self.draw_gradient(surface)

        # Title
        title = self.title_font.render("Change Username", True, self.styles.TEXT_COLOR)
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, 25))
        surface.blit(title, title_rect)

        # Current input
        input_text = self.name_font.render(f"Name: {self.new_name}_", True, self.styles.TEXT_SET)
        input_rect = input_text.get_rect(center=(BASE_WIDTH // 2, 58))
        surface.blit(input_text, input_rect)

        # Keyboard
        y = 90
        for row_idx, row in enumerate(self.keyboard):
            x = 38
            for col_idx, key in enumerate(row):
                # --- OPTIONAL FIX: Added "CAPS" to the 30-width check so the text fits nicely ---
                width = 35 if key in ["_", "CAPS", "OK"] else (62 if key == "BACK" else 26)
                height = self.card_height

                # Highlight selected
                if row_idx == self.kb_row and col_idx == self.kb_col:
                    pygame.draw.rect(surface, (0, 0, 0, 40), (x + 3, y + 3, width, height),
                                     border_radius=self.card_radius)
                    pygame.draw.rect(surface, self.styles.CARD_SELECTED, (x, y, width, height),
                                     border_radius=self.card_radius)
                    pygame.draw.rect(surface, self.styles.TEXT_COLOR, (x, y, width, height), 2,
                                     border_radius=self.card_radius)
                    text_color = self.styles.TEXT_SET
                else:
                    pygame.draw.rect(surface, (0, 0, 0, 40), (x + 3, y + 3, width, height),
                                     border_radius=self.card_radius)

                    # Visual Polish: Give the CAPS button a distinct color when active
                    if key == "CAPS" and self.is_uppercase:
                        pygame.draw.rect(surface, (180, 180, 180), (x, y, width, height),
                                         border_radius=self.card_radius)
                    else:
                        pygame.draw.rect(surface, self.styles.CARD_COLOR, (x, y, width, height),
                                         border_radius=self.card_radius)

                    text_color = self.styles.TEXT_SET

                if key in ["_", "CAPS", "BACK", "OK"]:
                    display_text = key
                else:
                    display_text = key if self.is_uppercase else key.lower()

                text = self.name_font.render(display_text, True, text_color)
                text_rect = text.get_rect(center=(x + width // 2, y + height // 2))
                surface.blit(text, text_rect)

                x += width + 5

            y += 30