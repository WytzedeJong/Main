import pygame
import json
import os
from datetime import datetime

from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import styles


class LockScreen(Scene):

    def __init__(self, manager):
        super().__init__(manager)

        # Use shared styles instance so theme toggles affect the lockscreen
        self.styles = styles

        self.users = []
        self.load_users()

        self.selected_index = 0
        self.state = "select"

        self.input_sequence = []
        self.max_length = 4
        self.user = getattr(self.manager, 'current_user', 0) or 0

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

        self.icons = ["Monkey", "Penguin", "lorem", "lorem", "lorem", "lorem"]


        self.title_font = self.styles.create_font(self.styles.FONT_LOCK_TITLE_SIZE, bold=True)
        self.name_font = self.styles.create_font(self.styles.FONT_LOCK_NAME_SIZE)
        self.input_font = self.styles.create_font(self.styles.FONT_LOCK_INPUT_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_LOCK_TIME_SIZE)

    def get_user(self):
        user = self.user
        return user
    
    def set_user(self, user):
        self.user = user
    
    def load_settings(self):
        pass

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
        
        
    def set_style_user(self):
        pass

    def update(self, dt):
        if self.success_timer > 0:
            self.success_timer -= dt
            if self.success_timer <= 0:
                self.login_success()

        if self.shake_timer > 0:
            self.shake_timer -= dt

        for i in range(len(self.anim_dots)):
            if self.anim_dots[i] < 1.0:
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
        display = self.get_display_users()

        if event.key == pygame.K_RIGHT:
            self.selected_index = (self.selected_index + 1) % len(display)
        elif event.key == pygame.K_LEFT:
            self.selected_index = (self.selected_index - 1) % len(display)
        elif event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.key == pygame.K_RETURN:

            selected = display[self.selected_index]

            if "create" in selected:
                self.state = "create_name"
                self.new_name = ""
                self.new_password = []
                self.confirm_password = []
                self.select_grid_index = 0
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
                    self.manager.current_user = user
                    self.user = user

                    theme = user.get("theme", "standard")
                    if theme == "standard":
                        styles.set_standaard_kleuren()
                    elif theme == "gold":
                        styles.gold_color()
                    elif theme == "green":
                        styles.green_color()
                    elif theme == "blue":
                        styles.blue_color()
                    elif theme == "red":
                        styles.red_color()
                    self.success_timer = self.success_delay
                    self.set_user(user)
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
            "password": self.new_password,
            "theme": "standard"
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
                "name": "Nieuw",
                "color": (200, 200, 200),
                "create": True
            })

        return display


    def draw(self, surface):

        surface.fill(self.styles.BACKGROUND)
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

        title = self.title_font.render("WinMan", True, self.styles.TEXT_SET)
        surface.blit(title, (15, 15))

        now = datetime.now().strftime("%H:%M")
        t = self.time_font.render(now, True, self.styles.TEXT_SET)
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

            name = self.name_font.render(u["name"], True, self.styles.TEXT_SET)
            surface.blit(name, name.get_rect(center=(x, y + 65)))


    def draw_create_name(self, surface):

        cx = BASE_WIDTH // 2

        title = self.name_font.render("NAAM INVOEREN", True, self.styles.TEXT_SET)
        surface.blit(title, title.get_rect(center=(cx, 50)))

        box = pygame.Rect(cx - 110, 65, 220, 36)

        pygame.draw.rect(surface, self.styles.CARD_COLOR, box, border_radius=4)
        pygame.draw.rect(surface, self.styles.TEXT_SET, box, 2, border_radius=4)

        txt = self.input_font.render(self.new_name, True, self.styles.TEXT_SET)
        surface.blit(txt, (box.x + 8, box.y + 6))

        self.draw_keyboard(surface)


    def draw_keyboard(self, surface):

        key_w, key_h, spc = 28, 30, 4
        start_y = 140

        for r, row in enumerate(self.keyboard):

            row_w = sum([
                (key_w * 2.5 if k in ["_", "BACK", "OK"] else key_w) + spc
                for k in row
            ])

            curr_x = BASE_WIDTH // 2 - (row_w - spc) // 2

            for c, key in enumerate(row):

                w = key_w * 2.5 if key in ["_", "BACK", "OK"] else key_w

                rect = pygame.Rect(
                    curr_x,
                    start_y + r * (key_h + spc),
                    w,
                    key_h
                )

                sel = (r == self.kb_row and c == self.kb_col)

                color = (0, 120, 215) if sel else (220, 220, 220)
                if not sel and key == "OK":
                    color = (76, 175, 80)
                if not sel and key == "BACK":
                    color = (231, 76, 60)

                pygame.draw.rect(surface, color, rect, border_radius=3)
                pygame.draw.rect(surface, (0, 0, 0), rect, 1, border_radius=3)

                f = self.styles.create_font(self.styles.FONT_LOCK_KEYBOARD_SIZE, bold=sel)
                label = f.render(
                    key,
                    True,
                    (255, 255, 255) if sel or key in ["OK", "BACK"] else (0, 0, 0)
                )

                surface.blit(label, label.get_rect(center=rect.center))

                curr_x += w + spc


    def draw_create_color(self, surface):

        cx = BASE_WIDTH // 2

        txt = self.name_font.render("KIES KLEUR", True, (0, 0, 0))
        surface.blit(txt, txt.get_rect(center=(cx, 60)))

        for i, color in enumerate(self.colors):

            x = cx - 150 + i * 60
            y = 120

            rect = pygame.Rect(x, y, 40, 40)

            if i == self.select_grid_index:
                pygame.draw.rect(surface, (0, 120, 215), rect.inflate(10, 10), 2)

            pygame.draw.rect(surface, color, rect)


    def draw_create_icon(self, surface):

        cx = BASE_WIDTH // 2

        txt = self.name_font.render("KIES ICOON", True, (0, 0, 0))
        surface.blit(txt, txt.get_rect(center=(cx, 60)))

        for i, icon in enumerate(self.icons):

            x = cx - 150 + i * 60
            y = 120

            rect = pygame.Rect(x, y, 50, 50)

            if i == self.select_grid_index:
                pygame.draw.rect(surface, (0, 120, 215), rect.inflate(10, 10), 2)

            pygame.draw.rect(surface, (200, 200, 200), rect)

            label = self.name_font.render(icon[0], True, (0, 0, 0))
            surface.blit(label, label.get_rect(center=rect.center))


    def draw_password_screen(self, surface, shake_x, creating=False, confirm=False):

        cx = BASE_WIDTH // 2 + shake_x

        if confirm:
            label = "BEVESTIG PIN"
        elif creating:
            label = "KIES PINCODE"
        else:
            label = "VOER PINCODE IN"

        txt = self.name_font.render(label, True, (0, 0, 0))
        surface.blit(txt, txt.get_rect(center=(cx, 60)))

        if not creating and not confirm:
            u_color = self.users[self.selected_index]["color"]
            pygame.draw.circle(surface, u_color, (cx, 110), 30)
            pygame.draw.circle(surface, (0, 0, 0), (cx, 110), 30, 2)

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

            radius = int(8 * scale)

            if filled:
                pygame.draw.circle(surface, (0, 120, 215), (x, y), radius)

            pygame.draw.circle(surface, (self.styles.DOTS), (x, y), radius, 2)