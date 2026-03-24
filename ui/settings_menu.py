import pygame
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import *
from ui.submenu import SubMenu


## mogelijk proleem: knoppen op het apparaat zijn geen keyboard keys dus moet nog checken of pygame.KEYDOWN dan werkt op een manier.

class SettingsMenu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = pygame.font.SysFont("arial", 28, bold=True)
        self.menu_font = pygame.font.SysFont("arial", 15)



        self.show_sett = False
        width, height = 300, 250
        sx = (BASE_WIDTH - width) // 2
        sy = (BASE_HEIGHT - height) // 2
        self.settings_rect = pygame.Rect(sx, sy, width, height)
        self.close_sett = pygame.Rect(self.settings_rect.right - 70, self.settings_rect.top + 10, 60, 30)
        
        self.options = ["Profile customization", "Language", "Text size", "Brightness", "Volume", "Version", "Change password", "Set to default", "Terug"]
        self.onoff = ['on','off' ]
        self.selected = 0

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            
            if event.key == pygame.K_RETURN:
                selected_option = self.options[self.selected]
                
                if selected_option == "Terug":
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
                
                elif selected_option == "Profile customization":
                    submenu = SubMenu(self.manager, "Profile Customization", ["Profile picture", "Change username", "Change theme", "Delete profile", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Language":
                    submenu = SubMenu(self.manager, "Language", ["English", "Nederlands", "Deutsch", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Text size":
                    submenu = SubMenu(self.manager, "Text Size", ["Klein", "Normaal", "Groot", "Extra Groot", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Brightness":
                    submenu = SubMenu(self.manager, "Brightness", ["50%", "60%", "70%", "80%", "90%", "100%", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Volume":
                    submenu = SubMenu(self.manager, "Volume", ["0%", "25%", "50%", "75%", "100%", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Version":
                    submenu = SubMenu(self.manager, "Version", ["Version 1.0.0", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Change password":
                    submenu = SubMenu(self.manager, "Change Password", ["Enter new password", "Terug"], self)
                    self.manager.set_scene(submenu)
                
                elif selected_option == "Set to default":
                    submenu = SubMenu(self.manager, "Set to Default", ["Confirm reset?", "Ja", "Nee"], self)
                    self.manager.set_scene(submenu)
            
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((50, 50, 50))
        t_color = (255,255,255)
        title = self.title_font.render("Instellingen", True, t_color)
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, 30))  # Horizontaal gecentreerd
        surface.blit(title, title_rect)
        
        y = 100
        for i, option in enumerate(self.options):
            color = CARD_SELECTED if i == self.selected else t_color
            text = self.menu_font.render(option, True, color)
            text_rect = text.get_rect(center=(BASE_WIDTH // 2, y))  # Gecentreerd
            surface.blit(text, text_rect)
            y += 20
            
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