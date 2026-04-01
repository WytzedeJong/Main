import pygame
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
from config import styles


class SubMenu(Scene):
    def __init__(self, manager, title, options, parent_scene, action_callback=None):
        super().__init__(manager)
        self.title = title
        self.options = options
        self.parent_scene = parent_scene
        self.action_callback = action_callback
        self.selected = 0

        self.styles = styles
        self.title_font = self.styles.create_font(self.styles.FONT_SETTINGS_TITLE_SIZE, bold=True)
        self.menu_font = self.styles.create_font(self.styles.FONT_SETTINGS_MENU_SIZE)


        self.scroll_y = 0
        self.target_scroll_y = 0
        self.card_height = 50
        self.spacing = 12
        self.visible_area_height = BASE_HEIGHT - 100


    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)

            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)

            elif event.key == pygame.K_RETURN:
                selected_option = self.options[self.selected]
                if self.action_callback:
                    handled = self.action_callback(selected_option)
                    if handled:
                        return

                if selected_option == "Back":
                    self.manager.set_scene(self.parent_scene)

            elif event.key == pygame.K_ESCAPE:
                self.manager.set_scene(self.parent_scene)

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

        label = self.menu_font.render(str(text), True, self.styles.TEXT_SET)
        surface.blit(label, label.get_rect(center=(x + width // 2, y + height // 2)))

    def draw(self, surface):
        self.draw_gradient(surface)


        content_start_y = 50 - self.scroll_y


        title_text = self.title_font.render(self.title, True, self.styles.TEXT_COLOR)
        title_rect = title_text.get_rect(center=(BASE_WIDTH // 2, content_start_y))
        if -50 < title_rect.centery < BASE_HEIGHT + 50:
            surface.blit(title_text, title_rect)


        card_width = 340
        start_x = (BASE_WIDTH - card_width) // 2

        menu_start_y = content_start_y + 45

        for i, option in enumerate(self.options):
            y_pos = menu_start_y + (i * (self.card_height + self.spacing))

            if -self.card_height < y_pos < BASE_HEIGHT:
                self.draw_card(surface, start_x, y_pos, card_width, self.card_height, option, i == self.selected)
