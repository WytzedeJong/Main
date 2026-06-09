from config import styles

class SceneManager:
    def __init__(self):
        self.scene = None
        self.current_user = None
        self.styles = styles
        self.input_block_frames = 0
        self.game_menu_selected = 0

    def set_scene(self, scene):
        self.scene = scene
        # Ignore L/B confirm/back briefly so the same press doesn't hit the new scene
        self.input_block_frames = 2

    def handle_events(self, event):
        if self.scene:
            self.scene.handle_events(event)

    def update(self, dt):
        if self.scene:
            self.scene.update(dt)

    def draw(self, screen):
        if self.scene:
            self.scene.draw(screen)