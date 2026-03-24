import pygame
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import AppStyles
from ui.submenu import SubMenu
from ui.edit_username import EditUsername


## mogelijk proleem: knoppen op het apparaat zijn geen keyboard keys dus moet nog checken of pygame.KEYDOWN dan werkt op een manier.

class SettingsMenu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.styles = AppStyles()
        
        self.title_font = self.styles.create_font(self.styles.FONT_SETTINGS_TITLE_SIZE, bold=True)

        self.show_sett = False
        width, height = 300, 250
        sx = (BASE_WIDTH - width) // 2
        sy = (BASE_HEIGHT - height) // 2
        self.settings_rect = pygame.Rect(sx, sy, width, height)
        self.close_sett = pygame.Rect(self.settings_rect.right - 70, self.settings_rect.top + 10, 60, 30)
        
        self.options = ["Profile customization", "Language", "Text size", "Brightness", "Volume", "Version", "Change password", "Set to default", "Back"]
        self.onoff = ['on','off' ]
        self.selected = 0
        self.current_profile_submenu = None  # Voor delete callback
        self.text_size_value = 20  

    def handle_profile_customization(self, option):
        
        if option == "Change username":
            current_user = self.manager.current_user
            if current_user:
                edit_scene = EditUsername(self.manager, current_user, self)
                self.manager.set_scene(edit_scene)
            return True  # Handled
        
        elif option == "Delete profile":
            # Show confirmation popup
            confirm_submenu = SubMenu(
                self.manager, 
                "Delete Profile?", 
                ["Delete", "Cancel"], 
                self.current_profile_submenu,  # parent is the profile menu
                action_callback=self.handle_delete_confirmation
            )
            self.manager.set_scene(confirm_submenu)
            return True  # Handled
        
        elif option == "Switch profile":
            # Terug naar lockscreen om ander profiel te kiezen
            self.manager.current_user = None
            from ui.lockscreen import LockScreen
            self.manager.set_scene(LockScreen(self.manager))
            return True  # Handled
        
        return False  # Not handled, use default logic
    
    def handle_delete_confirmation(self, option):
        """Callback for delete confirmation"""
        if option == "Delete":
            import json
            import os
            
            current_user = self.manager.current_user
            if current_user:
                # Delete from users.json
                path = os.path.join("data", "users.json")
                if os.path.exists(path):
                    with open(path, "r") as f:
                        data = json.load(f)
                    
                    # Delete user
                    data["users"] = [u for u in data.get("users", []) if u.get("name") != current_user.get("name")]
                    
                    with open(path, "w") as f:
                        json.dump(data, f, indent=4)
                
                # Reset current_user
                self.manager.current_user = None
                
                # Back to lockscreen
                from ui.lockscreen import LockScreen
                self.manager.set_scene(LockScreen(self.manager))
            return True
        
        elif option == "Cancel":
            self.manager.set_scene(self.current_profile_submenu)
            return True
        
        return False

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            
            # Handle LEFT/RIGHT for Text size slider
            if self.options[self.selected] == "Text size":
                if event.key == pygame.K_LEFT:
                    self.text_size_value = max(12, self.text_size_value - 1)
                if event.key == pygame.K_RIGHT:
                    self.text_size_value = min(30, self.text_size_value + 1)
            
            if event.key == pygame.K_RETURN:
                selected_option = self.options[self.selected]
                
                if selected_option == "Back":
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
                
                elif selected_option == "Profile customization":
                    profile_submenu = SubMenu(self.manager, "Profile Customization", 
                                     ["Profile picture", "Change username", "Change theme", "Delete profile", "Switch profile", "Back"], 
                                     self, 
                                     action_callback=self.handle_profile_customization)
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
                
                elif selected_option == "Change password":
                    submenu = SubMenu(self.manager, "Change Password", ["Enter new password", "Back"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Set to default":
                    submenu = SubMenu(self.manager, "Set to Default", ["Confirm reset?", "Yes", "No"], self)
                    self.manager.set_scene(submenu)
            
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        pass

    def draw_text_size_slider(self, surface, x, y):
        slider_width = 100
        slider_height = 8
        
        # Map value (12-40) to percentage (0-100)
        percentage = ((self.text_size_value - 12) / (40 - 12)) * 100
        
        # Background bar
        pygame.draw.rect(surface, (100, 100, 100), (x, y - 4, slider_width, slider_height))
        
        # Filled portion
        filled_width = int(slider_width * (percentage / 100))
        pygame.draw.rect(surface, (76, 175, 80), (x, y - 4, filled_width, slider_height))
        
        # Border
        pygame.draw.rect(surface, (255, 255, 255), (x, y - 4, slider_width, slider_height), 1)

    def draw(self, surface):
        surface.fill((self.styles.BACKGROUND))
        t_color = (self.styles.TEXT_SET)
        title = self.title_font.render("Settings", True, t_color)
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, 30))  # Horizontally centered
        surface.blit(title, title_rect)
        
        # Create menu font dynamically based on text_size_value
        menu_font = self.styles.create_font(self.text_size_value)
        
        center_x = BASE_WIDTH // 2 - 150
        y = 70
        for i, option in enumerate(self.options):
            color = self.styles.CARD_SELECTED if i == self.selected else t_color
            text = menu_font.render(option, True, color)
            
            # Special handling for Text size - draw slider next to it
            if option == "Text size":
                text_rect = text.get_rect(topleft=(center_x + 20, y))
                surface.blit(text, text_rect)
                self.draw_text_size_slider(surface, center_x + 155, y + 6)
            else:
                text_rect = text.get_rect(topleft=(center_x + 20, y))
                surface.blit(text, text_rect)
            
            y += (20 + (self.text_size_value/10))
            
    def draw_custom(self, surface):
        surface.fill

        # if self.show_sett:
        #     pygame.draw.rect(surface, (0, 100, 0), self.settings_rect)
        #     sx, sy = self.settings_rect.topleft
        #     title = self.title_font.render('geluid', True, t_color)
        #     surface.blit(title, (sx + 10, sy + 10))

        #     local_y = sy + 50
        #     for i, onoff in enumerate(self.onoff):
        #         color = CARD_SELECTED if i == self.selected else t_color
        #         text = self.menu_font.render(onoff, True, color)
        #         surface.blit(text, (sx + 10, local_y))
        #         local_y += 50