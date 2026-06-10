import json
import os
import pygame
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import styles
from ui.profile_images import list_profile_images, draw_profile_avatar


class ProfilePicturePicker(Scene):
    IMAGES_PER_ROW = 5

    def __init__(self, manager, parent_scene):
        super().__init__(manager)
        self.parent_scene = parent_scene
        self.styles = styles
        self.images = list_profile_images()
        self.selected = 0
        self.state = "image"
        self.colors = [
            (255, 203, 5),
            (238, 49, 53),
            (241, 102, 130),
            (177, 210, 73),
            (69, 185, 124),
            (69, 148, 211)
        ]
        self.selected_color = self._current_color_index()

        self.title_font = self.styles.create_font(self.styles.FONT_SETTINGS_TITLE_SIZE, bold=True)
        self.name_font = self.styles.create_font(self.styles.FONT_SETTINGS_MENU_SIZE)

    def handle_events(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if not self.images:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.manager.set_scene(self.parent_scene)
            return

        if self.state == "color":
            self._handle_color_events(event)
            return

        if event.key == pygame.K_RIGHT:
            self.selected = (self.selected + 1) % len(self.images)
        elif event.key == pygame.K_LEFT:
            self.selected = (self.selected - 1) % len(self.images)
        elif event.key == pygame.K_DOWN:
            next_selected = self.selected + self.IMAGES_PER_ROW
            if next_selected < len(self.images):
                self.selected = next_selected
        elif event.key == pygame.K_UP:
            next_selected = self.selected - self.IMAGES_PER_ROW
            if next_selected >= 0:
                self.selected = next_selected
        elif event.key == pygame.K_RETURN:
            self.state = "color"
        elif event.key == pygame.K_ESCAPE:
            self.manager.set_scene(self.parent_scene)

    def _handle_color_events(self, event):
        if event.key == pygame.K_RIGHT:
            self.selected_color = (self.selected_color + 1) % len(self.colors)
        elif event.key == pygame.K_LEFT:
            self.selected_color = (self.selected_color - 1) % len(self.colors)
        elif event.key == pygame.K_RETURN:
            self._save_selection()
            self.manager.set_scene(self.parent_scene)
        elif event.key == pygame.K_ESCAPE:
            self.state = "image"

    def _current_color_index(self):
        user = self.manager.current_user
        if not user:
            return 0

        color = user.get("color")
        if isinstance(color, list):
            color = tuple(color)

        try:
            return self.colors.index(color)
        except ValueError:
            return 0

    def _save_selection(self):
        user = self.manager.current_user
        if not user or not self.images:
            return

        filename = self.images[self.selected]
        color = self.colors[self.selected_color]
        user["profile_image"] = filename
        user["color"] = color
        if "icon" in user:
            del user["icon"]

        path = os.path.join("data", "users.json")
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for u in data.get("users", []):
            if u.get("name") == user.get("name"):
                u["profile_image"] = filename
                u["color"] = color
                if "icon" in u:
                    del u["icon"]
                break

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def draw(self, surface):
        self.draw_gradient(surface)
        cx = BASE_WIDTH // 2

        if self.state == "color":
            self._draw_color_picker(surface)
            return

        title = self.title_font.render("Choose Profile Image", True, self.styles.TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(cx, 40)))

        if not self.images:
            msg = self.name_font.render("No images found in data/images", True, self.styles.TEXT_SET)
            surface.blit(msg, msg.get_rect(center=(cx, BASE_HEIGHT // 2)))
            return

        spacing_x = 70
        spacing_y = 92
        start_y = 120

        for i, filename in enumerate(self.images):
            row = i // self.IMAGES_PER_ROW
            col = i % self.IMAGES_PER_ROW
            images_in_row = min(
                self.IMAGES_PER_ROW,
                len(self.images) - row * self.IMAGES_PER_ROW,
            )
            start_x = cx - ((images_in_row - 1) * spacing_x) // 2
            x = start_x + col * spacing_x
            y = start_y + row * spacing_y
            preview_user = {
                "color": self.manager.current_user.get("color", (200, 200, 200))
                if self.manager.current_user
                else (200, 200, 200),
                "profile_image": filename,
            }
            draw_profile_avatar(
                surface, preview_user, (x, y), 56, selected=(i == self.selected)
            )

    def _draw_color_picker(self, surface):
        cx = BASE_WIDTH // 2

        title = self.title_font.render("Pick Background Color", True, self.styles.TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(cx, 40)))

        preview_user = {
            "color": self.colors[self.selected_color],
            "profile_image": self.images[self.selected],
        }
        draw_profile_avatar(surface, preview_user, (cx, 105), 64)

        for i, color in enumerate(self.colors):
            x = cx - 150 + i * 60
            y = 165
            rect = pygame.Rect(x, y, 40, 40)

            if i == self.selected_color:
                pygame.draw.rect(surface, (0, 120, 215), rect.inflate(10, 10), 2)

            pygame.draw.rect(surface, color, rect)
