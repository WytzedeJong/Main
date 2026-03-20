import pygame
from core.scene import Scene

class AdventureGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.SysFont("arial", 60)

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((50, 80, 120))

        text = self.font.render("Test Game", True, (255, 255, 255))
        text_rect = text.get_rect(center=(surface.get_width() // 2,
                                          surface.get_height() // 2))

        surface.blit(text, text_rect)