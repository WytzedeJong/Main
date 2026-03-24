from config import AppStyles

class SceneManager:
    def __init__(self):
        self.scene = None
        self.current_user = None
        self.styles = AppStyles()

    def set_scene(self, scene):
        self.scene = scene

    def handle_events(self, event):
        if self.scene:
            self.scene.handle_events(event)

    def update(self, dt):
        if self.scene:
            self.scene.update(dt)

    def draw(self, screen):
        if self.scene:
            self.scene.draw(screen)