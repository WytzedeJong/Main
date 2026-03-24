import pygame
from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from config import *


class SubMenu(Scene):
    def __init__(self, manager, title, options, parent_scene):
        super().__init__(manager)
        self.title = title
        self.options = options
        self.parent_scene = parent_scene
        self.selected = 0
        
        self.title_font = pygame.font.SysFont("arial", 28, bold=True)
        self.menu_font = pygame.font.SysFont("arial", 15)

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            
            if event.key == pygame.K_RETURN:
                selected_option = self.options[self.selected]
                if selected_option == "Terug":
                    self.manager.set_scene(self.parent_scene)
            
            if event.key == pygame.K_ESCAPE:
                # Terug naar settings
                self.manager.set_scene(self.parent_scene)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((50, 50, 50))
        t_color = (255, 255, 255)
        
        title = self.title_font.render(self.title, True, t_color)
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, 30))
        surface.blit(title, title_rect)
        
        y = 100
        for i, option in enumerate(self.options):
            color = CARD_SELECTED if i == self.selected else t_color
            text = self.menu_font.render(str(option), True, color)
            text_rect = text.get_rect(center=(BASE_WIDTH // 2, y))
            surface.blit(text, text_rect)
            y += 25
        
