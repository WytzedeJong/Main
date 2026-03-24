import pygame
import json
import os
from datetime import datetime

from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT


class LockScreen(Scene):

    def __init__(self, manager):
        super().__init__(manager)

        self.users = []
        self.load_users()

        self.selected_index = 0
        self.state = "select"

        self.input_sequence = []
        self.max_length = 4

        self.success_timer = 0
        self.success_delay = 0.6
        self.shake_timer = 0
        self.anim_dots = []

        self.new_name = ""
        self.new_password = []
        self.confirm_password = []
        self.new_color = None
        self.new_icon = None

        self.keyboard = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
            ["_", "BACK", "OK"]
        ]
        self.kb_row = 0
        self.kb_col = 0

        self.select_grid_index = 0

        self.colors = [
            (255, 203, 5),
            (238, 49, 53),
            (241, 102, 130),
            (177, 210, 73),
            (69, 185, 124),
            (69, 148, 211)
        ]

        self.icons = ["APE", "PENGUIN", "NINJA", "ROBOT", "CAT", "GHOST"]

        self.title_font = pygame.font.SysFont("arial", 22, bold=True)
        self.name_font = pygame.font.SysFont("arial", 15)
        self.input_font = pygame.font.SysFont("arial", 20, bold=True)
        self.time_font = pygame.font.SysFont("arial", 18)

    def load_users(self):
        path = os.path.join("data", "users.json")
        if not os.path.exists(path):
            os.makedirs("data", exist_ok=True)
            with open(path, "w") as f:
                json.dump({"users": []}, f, indent=4)

        with open(path, "r") as f:
            data = json.load(f)

        self.users = data.get("users", [])[:3]

    def save_users(self):
        path = os.path.join("data", "users.json")
        with open(path, "w") as f:
            json.dump({"users": self.users}, f, indent=4)

    def login_success(self):
        from ui.home_menu import HomeMenu
        self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):

        if self.success_timer > 0:
            self.success_timer -= dt
            if self.success_timer <= 0:
                self.login_success()

        if self.shake_timer > 0:
            self.shake_timer -= dt

        for i in range(len(self.anim_dots)):
            if self.anim_dots[i] < 1:
                self.anim_dots[i] += dt * 6

    def handle_events(self, event):

        if event.type != pygame.KEYDOWN or self.success_timer > 0:
            return

        if event.key == pygame.K_ESCAPE:
            self.handle_back()
            return

        if self.state == "select":
            self.handle_select(event)

        elif self.state == "password":
            self.handle_password(event)

        elif self.state == "create_name":
            self.handle_create_name(event)

        elif self.state == "create_color":
            self.handle_create_color(event)

        elif self.state == "create_icon":
            self.handle_create_icon(event)

        elif self.state == "create_password":
            self.handle_create_password(event)

        elif self.state == "confirm_password":
            self.handle_confirm_password(event)

    def handle_back(self):

        if self.state == "password":
            self.state = "select"

        elif self.state == "create_name":
            self.state = "select"

        elif self.state == "create_color":
            self.state = "create_name"

        elif self.state == "create_icon":
            self.state = "create_color"

        elif self.state == "create_password":
            self.state = "create_icon"
            self.new_password = []
            self.anim_dots = []

        elif self.state == "confirm_password":
            self.state = "create_password"
            self.confirm_password = []
            self.anim_dots = []

    def handle_select(self, event):

        users = self.get_display_users()

        if event.key == pygame.K_RIGHT:
            self.selected_index = (self.selected_index + 1) % len(users)

        elif event.key == pygame.K_LEFT:
            self.selected_index = (self.selected_index - 1) % len(users)

        elif event.key == pygame.K_RETURN:

            selected = users[self.selected_index]

            if "create" in selected:
                self.state = "create_name"
                self.new_name = ""
                return

            if not selected.get("password"):
                self.success_timer = self.success_delay
                return

            self.state = "password"
            self.input_sequence = []
            self.anim_dots = []

    def handle_password(self, event):

        key_map = {
            pygame.K_UP: "UP",
            pygame.K_DOWN: "DOWN",
            pygame.K_LEFT: "LEFT",
            pygame.K_RIGHT: "RIGHT"
        }

        if event.key in key_map:
            self.input_sequence.append(key_map[event.key])
            self.anim_dots.append(0.0)

            if len(self.input_sequence) == 4:
                user = self.users[self.selected_index]

                if self.input_sequence == user.get("password", []):
                    self.success_timer = self.success_delay
                else:
                    self.input_sequence = []
                    self.anim_dots = []
                    self.shake_timer = 0.4

    def handle_create_name(self, event):

        row = self.keyboard[self.kb_row]

        if event.key == pygame.K_RIGHT:
            self.kb_col = (self.kb_col + 1) % len(row)

        elif event.key == pygame.K_LEFT:
            self.kb_col = (self.kb_col - 1) % len(row)

        elif event.key == pygame.K_DOWN:
            self.kb_row = (self.kb_row + 1) % len(self.keyboard)
            self.kb_col = min(self.kb_col, len(self.keyboard[self.kb_row]) - 1)

        elif event.key == pygame.K_UP:
            self.kb_row = (self.kb_row - 1) % len(self.keyboard)
            self.kb_col = min(self.kb_col, len(self.keyboard[self.kb_row]) - 1)

        elif event.key == pygame.K_RETURN:

            key = self.keyboard[self.kb_row][self.kb_col]

            if key == "_":
                if len(self.new_name) < 8:
                    self.new_name += "_"

            elif key == "BACK":
                self.new_name = self.new_name[:-1]

            elif key == "OK":
                if self.new_name.strip():
                    self.state = "create_color"
                    self.select_grid_index = 0

            else:
                if len(self.new_name) < 8:
                    self.new_name += key


    def handle_create_color(self, event):

        if event.key == pygame.K_RIGHT:
            self.select_grid_index = (self.select_grid_index + 1) % len(self.colors)

        elif event.key == pygame.K_LEFT:
            self.select_grid_index = (self.select_grid_index - 1) % len(self.colors)

        elif event.key == pygame.K_RETURN:
            self.new_color = self.colors[self.select_grid_index]
            self.state = "create_icon"
            self.select_grid_index = 0

    def handle_create_icon(self, event):

        if event.key == pygame.K_RIGHT:
            self.select_grid_index = (self.select_grid_index + 1) % len(self.icons)

        elif event.key == pygame.K_LEFT:
            self.select_grid_index = (self.select_grid_index - 1) % len(self.icons)

        elif event.key == pygame.K_RETURN:
            self.new_icon = self.icons[self.select_grid_index]
            self.state = "create_password"
            self.new_password = []
            self.anim_dots = []


    def handle_create_password(self, event):

        key_map = {
            pygame.K_UP: "UP",
            pygame.K_DOWN: "DOWN",
            pygame.K_LEFT: "LEFT",
            pygame.K_RIGHT: "RIGHT"
        }

        if event.key in key_map:
            self.new_password.append(key_map[event.key])
            self.anim_dots.append(0.0)

            if len(self.new_password) == 4:
                self.state = "confirm_password"
                self.confirm_password = []
                self.anim_dots = []


    def handle_confirm_password(self, event):

        key_map = {
            pygame.K_UP: "UP",
            pygame.K_DOWN: "DOWN",
            pygame.K_LEFT: "LEFT",
            pygame.K_RIGHT: "RIGHT"
        }

        if event.key in key_map:
            self.confirm_password.append(key_map[event.key])
            self.anim_dots.append(0.0)

            if len(self.confirm_password) == 4:

                if self.confirm_password == self.new_password:
                    self.finish_create()
                else:
                    self.confirm_password = []
                    self.anim_dots = []
                    self.shake_timer = 0.4

    def finish_create(self):

        user = {
            "name": self.new_name,
            "color": self.new_color,
            "icon": self.new_icon,
            "password": self.new_password
        }

        if len(self.users) < 3:
            self.users.append(user)

        self.save_users()
        self.state = "select"
        self.load_users()

    def get_display_users(self):

        display = self.users.copy()

        if len(display) < 3:
            display.append({
                "name": "Create New Profile",
                "color": (200, 200, 200),
                "create": True
            })

        return display

    def draw(self, surface):

        surface.fill((240, 240, 240))
        self.draw_top(surface)

        shake_x = 0
        if self.shake_timer > 0:
            shake_x = int((self.shake_timer * 60) % 10 - 5)

        if self.state == "select":
            self.draw_select(surface)

        elif self.state == "password":
            self.draw_password_screen(surface, shake_x)

        elif self.state == "create_name":
            self.draw_create_name(surface)

        elif self.state == "create_color":
            self.draw_create_color(surface)

        elif self.state == "create_icon":
            self.draw_create_icon(surface)

        elif self.state == "create_password":
            self.draw_password_screen(surface, 0, creating=True)

        elif self.state == "confirm_password":
            self.draw_password_screen(surface, shake_x, confirm=True)

    def draw_top(self, surface):

        title = self.title_font.render("WinMan", True, (0, 0, 0))
        surface.blit(title, (15, 15))

        now = datetime.now().strftime("%H:%M")
        t = self.time_font.render(now, True, (0, 0, 0))
        surface.blit(t, t.get_rect(topright=(BASE_WIDTH - 15, 15)))

    def draw_select(self, surface):

        users = self.get_display_users()

        spacing = 150
        start_x = BASE_WIDTH // 2 - ((len(users) - 1) * spacing) // 2

        for i, u in enumerate(users):

            x = start_x + i * spacing
            y = BASE_HEIGHT // 2

            rect = pygame.Rect(x - 40, y - 40, 80, 80)

            if i == self.selected_index:
                pygame.draw.ellipse(surface, (0, 120, 215), rect.inflate(12, 12), 3)

            pygame.draw.ellipse(surface, u["color"], rect)
            pygame.draw.ellipse(surface, (0, 0, 0), rect, 2)

            name = self.name_font.render(u["name"], True, (0, 0, 0))
            surface.blit(name, name.get_rect(center=(x, y + 65)))

    def draw_create_name(self, surface):

        cx = BASE_WIDTH // 2

        title = self.name_font.render("Stap 1 van 5 - NAAM", True, (120, 120, 120))
        surface.blit(title, title.get_rect(center=(cx, 50)))

        box = pygame.Rect(cx - 110, 70, 220, 36)

        pygame.draw.rect(surface, (255, 255, 255), box, border_radius=4)
        pygame.draw.rect(surface, (0, 120, 215), box, 2, border_radius=4)

        txt = self.input_font.render(self.new_name, True, (0, 0, 0))
        surface.blit(txt, (box.x + 8, box.y + 6))

        self.draw_keyboard(surface)

    def draw_keyboard(self, surface):

        key_w, key_h, spacing = 28, 30, 4
        start_y = 140

        for r, row in enumerate(self.keyboard):

            row_width = 0
            for key in row:
                if key in ["_", "BACK", "OK"]:
                    row_width += key_w * 2.5 + spacing
                else:
                    row_width += key_w + spacing
            row_width -= spacing

            start_x = BASE_WIDTH // 2 - row_width // 2

            current_x = start_x

            for c, key in enumerate(row):

                width = key_w * 2.5 if key in ["_", "BACK", "OK"] else key_w

                rect = pygame.Rect(
                    current_x,
                    start_y + r * (key_h + spacing),
                    width,
                    key_h
                )

                selected = (r == self.kb_row and c == self.kb_col)

                color = (0, 120, 215) if selected else (220, 220, 220)

                if not selected and key == "OK":
                    color = (76, 175, 80)
                elif not selected and key == "BACK":
                    color = (231, 76, 60)

                pygame.draw.rect(surface, color, rect, border_radius=4)
                pygame.draw.rect(surface, (0, 0, 0), rect, 1, border_radius=4)

                font = pygame.font.SysFont("arial", 12, bold=selected)

                label = font.render(
                    key,
                    True,
                    (255, 255, 255) if selected or key in ["OK", "BACK"] else (0, 0, 0)
                )

                surface.blit(label, label.get_rect(center=rect.center))

                current_x += width + spacing
    def draw_create_color(self, surface):

        cx = BASE_WIDTH // 2

        txt = self.name_font.render("Stap 2 van 5 - KLEUR", True, (120, 120, 120))
        surface.blit(txt, txt.get_rect(center=(cx, 60)))

        size = 40
        spacing = 20
        total = len(self.colors) * size + (len(self.colors) - 1) * spacing
        start_x = cx - total // 2

        for i, color in enumerate(self.colors):

            x = start_x + i * (size + spacing)
            y = 130

            rect = pygame.Rect(x, y, size, size)

            if i == self.select_grid_index:
                pygame.draw.rect(surface, (0, 120, 215), rect.inflate(10, 10), 2)

            pygame.draw.rect(surface, color, rect, border_radius=6)

    def draw_create_icon(self, surface):

        cx = BASE_WIDTH // 2

        txt = self.name_font.render("Stap 3 van 5 - ICOON", True, (120, 120, 120))
        surface.blit(txt, txt.get_rect(center=(cx, 60)))

        size = 50
        spacing = 20
        total = len(self.icons) * size + (len(self.icons) - 1) * spacing
        start_x = cx - total // 2

        for i, icon in enumerate(self.icons):

            x = start_x + i * (size + spacing)
            y = 130

            rect = pygame.Rect(x, y, size, size)

            if i == self.select_grid_index:
                pygame.draw.rect(surface, (0, 120, 215), rect.inflate(10, 10), 2)

            pygame.draw.rect(surface, (230, 230, 230), rect, border_radius=8)
            pygame.draw.rect(surface, (0, 0, 0), rect, 1, border_radius=8)

            label = self.name_font.render(icon[0], True, (0, 0, 0))
            surface.blit(label, label.get_rect(center=rect.center))

    def draw_password_screen(self, surface, shake_x, creating=False, confirm=False):

        cx = BASE_WIDTH // 2 + shake_x

        if confirm:
            label = "Stap 5 van 5 - BEVESTIG"
        elif creating:
            label = "Stap 4 van 5 - PIN"
        else:
            label = "VOER PIN IN"

        txt = self.name_font.render(label, True, (0, 0, 0))
        surface.blit(txt, txt.get_rect(center=(cx, 60)))

        data = self.confirm_password if confirm else (self.new_password if creating else self.input_sequence)

        self.draw_dots(surface, data, cx)

    def draw_dots(self, surface, data, cx):
        y = 170

        for i in range(4):

            x = cx - 45 + i * 30
            filled = i < len(data)

            scale = 1.0

            if i < len(self.anim_dots):
                t = self.anim_dots[i]
                scale = 1.0 + 0.5 * max(0, (1.0 - t))

            r = int(8 * scale)

            if filled:
                pygame.draw.circle(surface, (0, 120, 215), (x, y), r)

            pygame.draw.circle(surface, (0, 0, 0), (x, y), r, 2)

