import pygame
from core.scene import Scene


class RacerGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)

        # Fonts (iets kleiner dan 60)
        self.title_font = pygame.font.SysFont("arial", 48, bold=True)
        self.button_font = pygame.font.SysFont("arial", 24)

        # Talen
        self.languages = [
            ("English", "Hello World"),
            ("Nederlands", "Hallo Wereld"),
            ("Español", "Hola Mundo"),
        ]

        self.selected_index = 0
        self.current_text = self.languages[0][1]

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

            if event.key == pygame.K_RIGHT:
                self.selected_index = (self.selected_index + 1) % len(self.languages)

            if event.key == pygame.K_LEFT:
                self.selected_index = (self.selected_index - 1) % len(self.languages)

            if event.key == pygame.K_RETURN:
                self.current_text = self.languages[self.selected_index][1]

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((120, 60, 60))

        width = surface.get_width()
        height = surface.get_height()

        text = self.title_font.render(self.current_text, True, (255, 255, 255))
        text_rect = text.get_rect(center=(width // 2, height // 2 - 40))
        surface.blit(text, text_rect)

        button_width = 140
        button_height = 40
        spacing = 20

        total_width = len(self.languages) * button_width + (len(self.languages) - 1) * spacing
        start_x = (width - total_width) // 2
        y = height - 80

        for i, (lang_name, _) in enumerate(self.languages):
            x = start_x + i * (button_width + spacing)

            if i == self.selected_index:
                color = (255, 200, 100)
            else:
                color = (255, 255, 255)

            pygame.draw.rect(surface, color, (x, y, button_width, button_height), border_radius=8)

            label = self.button_font.render(lang_name, True, (0, 0, 0))
            label_rect = label.get_rect(center=(x + button_width // 2,
                                                y + button_height // 2))
            surface.blit(label, label_rect)