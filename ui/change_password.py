import pygame
import json
import os
from datetime import datetime
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import styles


class ChangePassword(Scene):
    def __init__(self, manager, current_user, parent_scene):
        super().__init__(manager)
        self.styles = styles
        self.current_user = current_user
        self.parent_scene = parent_scene

        self.user_has_password = bool(current_user.get("password", []))
        
        # States: menu -> verify/new_password -> confirm_password -> success
        self.state = "menu"
        self.action_type = None  # "set", "change", "remove"
        
        self.input_sequence = []  # Huidige wachtwoord
        self.new_password = []  # Nieuw wachtwoord
        self.confirm_password = []  # Bevestiging nieuw wachtwoord
        self.max_length = 4
        self.anim_dots = []
        
        self.success_timer = 0
        self.success_delay = 0.6
        self.shake_timer = 0
        self.error_message = ""
        self.error_timer = 0
        
        self.menu_options = []
        self.menu_selected = 0
        self.setup_menu()
        
        # Scroll functionality for menu
        self.scroll_y = 0
        self.target_scroll_y = 0
        self.card_height = 50
        self.spacing = 12
        self.visible_area_height = BASE_HEIGHT - 120

        self.title_font = self.styles.create_font(self.styles.FONT_LOCK_TITLE_SIZE, bold=True)
        self.name_font = self.styles.create_font(self.styles.FONT_LOCK_NAME_SIZE)
        self.input_font = self.styles.create_font(self.styles.FONT_LOCK_INPUT_SIZE, bold=True)
        self.time_font = self.styles.create_font(self.styles.FONT_LOCK_TIME_SIZE)

    def setup_menu(self):
        """Setup menu options based on whether user has a password"""
        if self.user_has_password:
            self.menu_options = ["Change password", "Remove password", "Back"]
        else:
            self.menu_options = ["Set password", "Back"]

    def update(self, dt):
        if self.success_timer > 0:
            self.success_timer -= dt
            if self.success_timer <= 0:
                self.password_changed_success()

        if self.shake_timer > 0:
            self.shake_timer -= dt

        if self.error_timer > 0:
            self.error_timer -= dt

        for i in range(len(self.anim_dots)):
            if self.anim_dots[i] < 1.0:
                self.anim_dots[i] += dt * 6
        
        # Update scroll for menu
        if self.state == "menu":
            item_y = 60 + self.menu_selected * (self.card_height + self.spacing)
            
            if item_y < self.scroll_y:
                self.target_scroll_y = item_y
            elif item_y + self.card_height > self.scroll_y + self.visible_area_height:
                self.target_scroll_y = item_y + self.card_height - self.visible_area_height
            
            self.scroll_y += (self.target_scroll_y - self.scroll_y) * 0.15

    def handle_events(self, event):
        if event.type != pygame.KEYDOWN or self.success_timer > 0:
            return

        if event.key == pygame.K_ESCAPE:
            self.manager.set_scene(self.parent_scene)
            return

        if self.state == "menu":
            self.handle_menu(event)
        elif self.state == "verify":
            self.handle_verify(event)
        elif self.state == "new_password":
            self.handle_new_password(event)
        elif self.state == "confirm_password":
            self.handle_confirm_password(event)

    def handle_menu(self, event):
        """Handle menu selection"""
        if event.key == pygame.K_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
        elif event.key == pygame.K_UP:
            self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
        elif event.key == pygame.K_RETURN:
            selected = self.menu_options[self.menu_selected]
            
            if selected == "Back":
                self.manager.set_scene(self.parent_scene)
            elif selected == "Set password":
                self.action_type = "set"
                self.state = "new_password"
                self.new_password = []
                self.anim_dots = []
            elif selected == "Change password":
                self.action_type = "change"
                self.state = "verify"
                self.input_sequence = []
                self.anim_dots = []
            elif selected == "Remove password":
                self.action_type = "remove"
                self.state = "verify"
                self.input_sequence = []
                self.anim_dots = []

    def handle_verify(self, event):
        """Verifies current password"""
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
                current_password = self.current_user.get("password", [])
                
                if self.input_sequence == current_password:
                    # Correct password
                    if self.action_type == "remove":
                        self.save_password(remove=True)
                        self.success_timer = self.success_delay
                    else:  # change
                        self.state = "new_password"
                        self.new_password = []
                        self.anim_dots = []
                else:
                    # Wrong password
                    self.input_sequence = []
                    self.anim_dots = []
                    self.shake_timer = 0.4
                    self.error_message = "WACHTWOORD ONJUIST"
                    self.error_timer = 1.5

    def handle_new_password(self, event):
        """Gets new password from user"""
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
        """Confirms new password"""
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
                    # Passwords match!
                    self.save_password()
                    self.success_timer = self.success_delay
                else:
                    # Passwords don't match
                    self.confirm_password = []
                    self.anim_dots = []
                    self.shake_timer = 0.4
                    self.error_message = "PINCODES KOMEN NIET OVEREEN"
                    self.error_timer = 1.5

    def save_password(self, remove=False):
        """Saves the new password to users.json or removes it"""
        path = os.path.join("data", "users.json")
        
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            
            # Find and update user password
            for user in data.get("users", []):
                if user.get("name") == self.current_user.get("name"):
                    if remove:
                        # Remove password
                        if "password" in user:
                            del user["password"]
                        if "password" in self.current_user:
                            del self.current_user["password"]
                        self.error_message = "WACHTWOORD VERWIJDERD"
                    else:
                        # Set or change password
                        user["password"] = self.new_password
                        self.current_user["password"] = self.new_password
                        self.error_message = "WACHTWOORD OPGESLAGEN"
                    break
            
            with open(path, "w") as f:
                json.dump(data, f, indent=4)

    def password_changed_success(self):
        """Redirects to parent scene after successful password change"""
        self.manager.set_scene(self.parent_scene)

    def draw(self, surface):
        surface.fill(self.styles.BACKGROUND)
        self.draw_top(surface)

        shake_x = 0
        if self.shake_timer > 0:
            shake_x = int((self.shake_timer * 60) % 10 - 5)

        if self.state == "menu":
            self.draw_menu(surface)
        elif self.state == "verify":
            self.draw_verify_screen(surface, shake_x)
        elif self.state == "new_password":
            self.draw_new_password_screen(surface, shake_x)
        elif self.state == "confirm_password":
            self.draw_confirm_password_screen(surface, shake_x)

    def draw_top(self, surface):
        title = self.title_font.render("WinMan", True, self.styles.TEXT_SET)
        surface.blit(title, (15, 15))

        now = datetime.now().strftime("%H:%M")
        t = self.time_font.render(now, True, self.styles.TEXT_SET)
        surface.blit(t, t.get_rect(topright=(BASE_WIDTH - 15, 15)))

    def draw_menu(self, surface):
        """Draw menu for password management"""
        cx = BASE_WIDTH // 2
        
        title = self.name_font.render("WACHTWOORD BEHEREN", True, self.styles.TEXT_SET)
        # Make title scroll with the menu
        surface.blit(title, title.get_rect(center=(cx, 50 - self.scroll_y)))
        
        card_width = 200
        
        # Add more top padding so buttons start lower
        start_y = 120 - self.scroll_y
        
        for i, option in enumerate(self.menu_options):
            y = start_y + i * (self.card_height + self.spacing)
            x = cx - card_width // 2
            
            rect = pygame.Rect(x, y, card_width, self.card_height)
            
            # Only draw if visible
            if -self.card_height < y < BASE_HEIGHT:
                # Highlight selected option
                if i == self.menu_selected:
                    pygame.draw.rect(surface, (0, 120, 215), rect, 3, border_radius=6)
                
                # Draw background
                pygame.draw.rect(surface, self.styles.CARD_COLOR, rect, border_radius=6)
                
                # Draw text
                opt_font = self.styles.create_font(20, bold=(i == self.menu_selected))
                lbl = opt_font.render(option, True, self.styles.TEXT_SET)
                surface.blit(lbl, lbl.get_rect(center=rect.center))

    def draw_verify_screen(self, surface, shake_x):
        cx = BASE_WIDTH // 2 + shake_x

        if self.action_type == "remove":
            label = self.name_font.render("VOER PINCODE IN OM TE VERWIJDEREN", True, self.styles.TEXT_SET)
        else:
            label = self.name_font.render("VOER HUDIG PINCODE IN", True, self.styles.TEXT_SET)
        surface.blit(label, label.get_rect(center=(cx, 60)))

        # Draw user color circle
        u_color = self.current_user.get("color", (200, 200, 200))
        pygame.draw.circle(surface, u_color, (cx, 110), 30)
        pygame.draw.circle(surface, (0, 0, 0), (cx, 110), 30, 2)

        self.draw_dots(surface, self.input_sequence, cx)

        # Draw error message
        if self.error_timer > 0:
            error_txt = self.name_font.render(self.error_message, True, (231, 76, 60))
            surface.blit(error_txt, error_txt.get_rect(center=(cx, 250)))

    def draw_new_password_screen(self, surface, shake_x):
        cx = BASE_WIDTH // 2 + shake_x

        if self.action_type == "set":
            label = self.name_font.render("VOER PINCODE IN", True, self.styles.TEXT_SET)
        else:
            label = self.name_font.render("VOER NIEUWE PINCODE IN", True, self.styles.TEXT_SET)
        surface.blit(label, label.get_rect(center=(cx, 60)))

        self.draw_dots(surface, self.new_password, cx)

    def draw_confirm_password_screen(self, surface, shake_x):
        cx = BASE_WIDTH // 2 + shake_x

        label = self.name_font.render("BEVESTIG PINCODE", True, self.styles.TEXT_SET)
        surface.blit(label, label.get_rect(center=(cx, 60)))

        self.draw_dots(surface, self.confirm_password, cx)

        # Draw error message
        if self.error_timer > 0:
            error_txt = self.name_font.render(self.error_message, True, (231, 76, 60))
            surface.blit(error_txt, error_txt.get_rect(center=(cx, 250)))

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
