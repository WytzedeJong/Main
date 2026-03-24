import pygame
import json
import os
from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from config import *


class EditUsername(Scene):
    def __init__(self, manager, current_user, parent_scene):
        super().__init__(manager)
        self.current_user = current_user
        self.parent_scene = parent_scene
        self.new_name = current_user.get("name", "")
        
        self.title_font = pygame.font.SysFont("arial", 26, bold=True)
        self.name_font = pygame.font.SysFont("arial", 18)
        self.input_font = pygame.font.SysFont("arial", 20, bold=True)

        self.keyboard = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
            ["_", "BACK", "OK"]
        ]
        self.kb_row = 0
        self.kb_col = 0

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
                
                elif key == "BACK":
                    self.new_name = self.new_name[:-1]
                
                elif key == "OK":
                    if self.new_name.strip():
                        self.save_username()
                        self.manager.set_scene(self.parent_scene)
                
                else:
                    if len(self.new_name) < 10:
                        self.new_name += key
            
            elif event.key == pygame.K_ESCAPE:
                self.manager.set_scene(self.parent_scene)

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
        surface.fill((50, 50, 50))
        
        # Title
        title = self.title_font.render("Change Username", True, (255, 255, 255))
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, 20))
        surface.blit(title, title_rect)
        
        # Current input
        input_text = self.name_font.render(f"Name: {self.new_name}_", True, CARD_SELECTED)
        input_rect = input_text.get_rect(center=(BASE_WIDTH // 2, 50))
        surface.blit(input_text, input_rect)
        
        # Keyboard
        y = 90
        for row_idx, row in enumerate(self.keyboard):
            x = 40
            for col_idx, key in enumerate(row):
                width = 28 if key in ["_", "OK"] else (50 if key == "BACK" else 25)
                height = 25
                
                # Highlight selected
                if row_idx == self.kb_row and col_idx == self.kb_col:
                    pygame.draw.rect(surface, CARD_SELECTED, (x, y, width, height))
                    color = (50, 50, 50)
                else:
                    pygame.draw.rect(surface, (200, 200, 200), (x, y, width, height))
                    color = (50, 50, 50)
                
                pygame.draw.rect(surface, (100, 100, 100), (x, y, width, height), 1)
                
                text = self.name_font.render(key, True, color)
                text_rect = text.get_rect(center=(x + width // 2, y + height // 2))
                surface.blit(text, text_rect)
                
                x += width + 5
            
            y += 30
