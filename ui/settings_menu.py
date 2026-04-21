import pygame
import json
import os
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import styles
from ui.submenu import SubMenu
from ui.edit_username import EditUsername
from ui.change_password import ChangePassword


class SettingsMenu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = styles

        self.current_theme = "standard"
        self.selected = 0
        self.text_size_value = 20
        self.current_profile_submenu = None


        self.scroll_y = 0
        self.target_scroll_y = 0
        self.card_height = 50
        self.spacing = 12
        self.visible_area_height = BASE_HEIGHT - 100


        self.title_font = self.styles.create_font(self.styles.FONT_SETTINGS_TITLE_SIZE, bold=True)

        self.options = [
            "Profile customization",
            "Language",
            "Text size",
            "Brightness",
            "Volume",
            "Version",
            "Manage password",
            "Set to default",
            "Back"
        ]


    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)

            if self.options[self.selected] == "Text size":
                if event.key == pygame.K_LEFT:
                    self.text_size_value = max(12, self.text_size_value - 1)
                elif event.key == pygame.K_RIGHT:
                    self.text_size_value = min(30, self.text_size_value + 1)

            if event.key == pygame.K_RETURN:
                self.handle_selection()

            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def handle_selection(self):
        selected_option = self.options[self.selected]

        if selected_option == "Back":
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))

        elif selected_option == "Profile customization":
            profile_submenu = SubMenu(
                self.manager,
                "Profile Customization",
                ["Profile picture", "Change username", "Change theme",
                 "Delete profile", "Switch profile", "Back"],
                self,
                action_callback=self.handle_profile_customization
            )
            self.current_profile_submenu = profile_submenu
            self.manager.set_scene(profile_submenu)

        elif selected_option == "Language":
            submenu = SubMenu(self.manager, "Language", ["English", "Dutch", "Deutsch", "Back"], self)
            self.manager.set_scene(submenu)

        elif selected_option == "Brightness":
            submenu = SubMenu(self.manager, "Brightness", ["50%", "60%", "70%", "80%", "90%", "100%", "Back"], self)
            self.manager.set_scene(submenu)

        elif selected_option == "Volume":
            submenu = SubMenu(self.manager, "Volume", ["0%", "25%", "50%", "75%", "100%", "Back"], self)
            self.manager.set_scene(submenu)

        elif selected_option == "Version":
            submenu = SubMenu(self.manager, "Version", ["Version 1.0.0", "Back"], self)
            self.manager.set_scene(submenu)

        elif selected_option == "Manage password":
            current_user = self.manager.current_user
            if current_user:
                change_scene = ChangePassword(self.manager, current_user, self)
                self.manager.set_scene(change_scene)

        elif selected_option == "Set to default":
            submenu = SubMenu(self.manager, "Set to Default", ["Confirm reset?", "Yes", "No"], self)
            self.manager.set_scene(submenu)


    def handle_profile_customization(self, option):
        if option == "Change username":
            current_user = self.manager.current_user
            if current_user:
                edit_scene = EditUsername(self.manager, current_user, self)
                self.manager.set_scene(edit_scene)
            return True

        elif option == "Delete profile":
            confirm_submenu = SubMenu(
                self.manager, "Delete Profile?", ["Delete", "Cancel"],
                self.current_profile_submenu,
                action_callback=self.handle_delete_confirmation
            )
            self.manager.set_scene(confirm_submenu)
            return True

        elif option == "Switch profile":
            self.manager.current_user = None
            from ui.lockscreen import LockScreen
            self.manager.set_scene(LockScreen(self.manager))
            return True

        elif option == "Change theme":
            themes = ["standard", "dark", "green", "blue", "red"]
            idx = themes.index(self.current_theme)
            self.current_theme = themes[(idx + 1) % len(themes)]

            if self.current_theme == "dark":
                self.styles.gold_color()
            elif self.current_theme == "green":
                self.styles.green_color()
            elif self.current_theme == "blue":
                self.styles.blue_color()
            elif self.current_theme == "red":
                self.styles.red_color()
            else:
                self.styles.set_standaard_kleuren()
            self.handle_theme()
            return True
        return False
    
    def handle_theme(self):
        theme = self.current_theme
        path = os.path.join("data", "users.json")
        
        # Maak bestand aan als het niet bestaat
        if not os.path.exists(path):
            os.makedirs("data", exist_ok=True)
            with open(path, "w") as f:
                json.dump({"users": []}, f, indent=4)
        
        # Lees de data
        with open(path, "r") as f:
            data = json.load(f)
        
        # Update het thema van de huidige gebruiker
        for user in data["users"]:
            if user["name"] == self.manager.current_user["name"]:  
                user["theme"] = theme
                break
        
        # Schrijf de bijgewerkte data terug
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        
        self.users = data.get("users", [])[:3]

    def handle_delete_confirmation(self, option):
        if option == "Delete":
            current_user = self.manager.current_user
            if current_user:
                path = os.path.join("data", "users.json")
                if os.path.exists(path):
                    with open(path, "r") as f:
                        data = json.load(f)
                    data["users"] = [u for u in data.get("users", []) if u.get("name") != current_user.get("name")]
                    with open(path, "w") as f:
                        json.dump(data, f, indent=4)
                self.manager.current_user = None
                from ui.lockscreen import LockScreen
                self.manager.set_scene(LockScreen(self.manager))
            return True
        elif option == "Cancel":
            self.manager.set_scene(self.current_profile_submenu)
            return True
        return False


    def update(self, dt):

        item_y = 60 + self.selected * (self.card_height + self.spacing)

        if item_y < self.scroll_y:
            self.target_scroll_y = item_y
        elif item_y + self.card_height > self.scroll_y + self.visible_area_height:
            self.target_scroll_y = item_y + self.card_height - self.visible_area_height

        self.scroll_y += (self.target_scroll_y - self.scroll_y) * 0.15


    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def draw_card(self, surface, x, y, width, height, text, is_selected):
        pygame.draw.rect(surface, (0, 0, 0, 40), (x + 3, y + 3, width, height), border_radius=12)
        color = self.styles.CARD_SELECTED if is_selected else self.styles.CARD_COLOR
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=12)

        if is_selected:
            pygame.draw.rect(surface, self.styles.TEXT_COLOR, (x, y, width, height), 2, border_radius=12)

        font = self.styles.create_font(self.text_size_value)
        label = font.render(text, True, self.styles.TEXT_SET)
        surface.blit(label, label.get_rect(center=(x + width // 2, y + height // 2)))

    def draw_text_size_slider(self, surface, x, y):
        width = 140
        pygame.draw.rect(surface, (200, 200, 200), (x, y, width, 12), border_radius=6)
        percentage = (self.text_size_value - 12) / (30 - 12)
        pygame.draw.rect(surface, self.styles.CARD_SELECTED, (x, y, int(width * percentage), 12), border_radius=6)
        val_txt = self.styles.create_font(14).render(str(self.text_size_value), True, self.styles.TEXT_SET)
        surface.blit(val_txt, (x + width + 10, y - 4))

    def draw(self, surface):
        self.draw_gradient(surface)


        content_start_y = 50 - self.scroll_y


        title = self.title_font.render("Settings", True, self.styles.TEXT_COLOR)
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, content_start_y))

        if -50 < title_rect.centery < BASE_HEIGHT + 50:
            surface.blit(title, title_rect)


        card_width = 380
        start_x = (BASE_WIDTH - card_width) // 2


        menu_start_y = content_start_y + 45

        for i, option in enumerate(self.options):
            y_pos = menu_start_y + (i * (self.card_height + self.spacing))

            if -self.card_height < y_pos < BASE_HEIGHT:
                self.draw_card(surface, start_x, y_pos, card_width, self.card_height, option, i == self.selected)

                if option == "Text size":
                    slider_x = start_x + card_width - 180
                    self.draw_text_size_slider(surface, slider_x, y_pos + 19)