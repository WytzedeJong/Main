import pygame
from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from config import styles


class SubMenu(Scene):
    def __init__(self, manager, title, options, parent_scene, action_callback=None):
        super().__init__(manager)
        self.title = title
        self.options = options
        self.parent_scene = parent_scene
        self.action_callback = action_callback  # Callback for special actions
        self.selected = 0
        
        # Use shared styles instance so theme changes apply app-wide
        self.styles = styles
        self.title_font = self.styles.create_font(self.styles.FONT_SETTINGS_TITLE_SIZE, bold=True)
        self.menu_font = self.styles.create_font(self.styles.FONT_SETTINGS_MENU_SIZE)

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            
            if event.key == pygame.K_RETURN:
                selected_option = self.options[self.selected]                
                # Check if there is a callback for this option
                if self.action_callback:
                    handled = self.action_callback(selected_option)
                    if handled:
                        return  # Callback handled it
                
                # Default: "Back" logic
                if selected_option == "Back":
                    self.manager.set_scene(self.parent_scene)
            
            if event.key == pygame.K_ESCAPE:
                # Back to settings
                self.manager.set_scene(self.parent_scene)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(self.styles.BACKGROUND)
        
        title = self.title_font.render(self.title, True, self.styles.TEXT_SET)
        title_rect = title.get_rect(center=(BASE_WIDTH // 2, 30))
        surface.blit(title, title_rect)
        
        y = 100
        for i, option in enumerate(self.options):
            color = self.styles.CARD_SELECTED if i == self.selected else self.styles.TEXT_SET
            text = self.menu_font.render(str(option), True, color)
            text_rect = text.get_rect(center=(BASE_WIDTH // 2, y))
            surface.blit(text, text_rect)
            y += 25
