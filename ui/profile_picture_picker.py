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

        self.title_font = self.styles.create_font(self.styles.FONT_SETTINGS_TITLE_SIZE, bold=True)
        self.name_font = self.styles.create_font(self.styles.FONT_SETTINGS_MENU_SIZE)

    def handle_events(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if not self.images:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.manager.set_scene(self.parent_scene)
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
            self._save_selection()
            self.manager.set_scene(self.parent_scene)
        elif event.key == pygame.K_ESCAPE:
            self.manager.set_scene(self.parent_scene)

    def _save_selection(self):
        user = self.manager.current_user
        if not user or not self.images:
            return

        filename = self.images[self.selected]
        user["profile_image"] = filename
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

