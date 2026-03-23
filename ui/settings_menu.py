import pygame
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import *


class SettingsMenu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = pygame.font.SysFont("arial", 28, bold=True)
        self.menu_font = pygame.font.SysFont("arial", 18)
        
        self.options = ["Geluid", "Helderheid", "Terug"]
        self.selected = 0

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            
            if event.key == pygame.K_RETURN:
                if self.options[self.selected] == "Terug":
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
            
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((50, 50, 50))
        t_color = (30, 40, 50)
        title = self.title_font.render("Instellingen", True, t_color)
        surface.blit(title, (30, 30))
        
        y = 100
        for i, option in enumerate(self.options):
            color = CARD_SELECTED if i == self.selected else t_color
            text = self.menu_font.render(option, True, color)
            surface.blit(text, (50, y))
            y += 50
