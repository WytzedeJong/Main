class Scene:
    def __init__(self, manager):
        self.manager = manager

    def handle_events(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def draw_time_and_battery(self, surface, time_font, text_color, y=15, margin_right=15):
        """Tijd + batterij rechtsboven (psutil / data/battery.json)."""
        from ui.status import draw_time_and_battery
        draw_time_and_battery(surface, time_font, text_color, y=y, margin_right=margin_right)