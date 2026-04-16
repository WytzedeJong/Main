import pygame
import json
import os
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import styles
from core.input_manager import InputHandler


class EditUsername(Scene):
    def __init__(self, manager, current_user, parent_scene):
        super().__init__(manager)

        self.input = InputHandler()

        self.styles = styles
        self.current_user = current_user
        self.parent_scene = parent_scene
        self.new_name = current_user.get("name", "")

        self.title_font = self.styles.create_font(self.styles.FONT_EDIT_TITLE_SIZE, bold=True)
        self.name_font = self.styles.create_font(self.styles.FONT_EDIT_NAME_SIZE)
        self.input_font = self.styles.create_font(self.styles.FONT_EDIT_INPUT_SIZE, bold=True)

        self.keyboard = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
            ["_", "BACK", "OK"]
        ]

        self.kb_row = 0
        self.kb_col = 0

    def handle_events(self, event):
        pass

    def update(self, dt):
        self.input.update()

        row = self.keyboard[self.kb_row]

        if self.input.just_pressed("RIGHT"):
            self.kb_col = (self.kb_col + 1) % len(row)

        if self.input.just_pressed("LEFT"):
            self.kb_col = (self.kb_col - 1) % len(row)

        if self.input.just_pressed("DOWN"):
            self.kb_row = (self.kb_row + 1) % len(self.keyboard)
            self.kb_col = min(self.kb_col, len(self.keyboard[self.kb_row]) - 1)

        if self.input.just_pressed("UP"):
            self.kb_row = (self.kb_row - 1) % len(self.keyboard)
            self.kb_col = min(self.kb_col, len(self.keyboard[self.kb_row]) - 1)

        if self.input.just_pressed("L") or self.input.just_pressed("ENTER"):
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

        if self.input.just_pressed("B"):
            self.manager.set_scene(self.parent_scene)

    def save_username(self):
        old_name = self.current_user.get("name", "")
        self.current_user["name"] = self.new_name

        path = os.path.join("data", "users.json")

        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)

            for user in data.get("users", []):
                if user.get("name") == old_name:
                    user["name"] = self.new_name
                    break

            with open(path, "w") as f:
                json.dump(data, f, indent=4)

    def draw(self, surface):
        surface.fill((50, 50, 50))

        title = self.title_font.render("Change Username", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 20)))

        input_text = self.name_font.render(f"Name: {self.new_name}_", True, self.styles.CARD_SELECTED)
        surface.blit(input_text, input_text.get_rect(center=(BASE_WIDTH // 2, 50)))

        y = 90
        for r, row in enumerate(self.keyboard):
            x = 40
            for c, key in enumerate(row):
                width = 28 if key in ["_", "OK"] else (50 if key == "BACK" else 25)
                height = 25

                selected = (r == self.kb_row and c == self.kb_col)

                color = self.styles.CARD_SELECTED if selected else (200, 200, 200)
                text_color = (50, 50, 50) if selected else (0, 0, 0)

                pygame.draw.rect(surface, color, (x, y, width, height))
                pygame.draw.rect(surface, (100, 100, 100), (x, y, width, height), 1)

                label = self.name_font.render(key, True, text_color)
                surface.blit(label, label.get_rect(center=(x + width // 2, y + height // 2)))

                x += width + 5
            y += 30