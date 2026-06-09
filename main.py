import os
import sys

if getattr(sys, "frozen", False):
    os.chdir(sys._MEIPASS)

import pygame
from settings import screen, clock, base_surface
from core.scene_manager import SceneManager
from core.input_manager import InputHandler
from ui.lockscreen import LockScreen
def main():
    manager = SceneManager()
    manager.set_scene(LockScreen(manager))
    input_handler = InputHandler()
    manager.input_handler = input_handler

    running = True
    while running:
        dt = clock.tick(60) / 1000

        input_handler.update()

        events = pygame.event.get()

        if manager.input_block_frames > 0:
            manager.input_block_frames -= 1

        if input_handler.backend != "keyboard":
            if input_handler.just_pressed("UP"):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
            if input_handler.just_pressed("DOWN"):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            if input_handler.just_pressed("LEFT"):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
            if input_handler.just_pressed("RIGHT"):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        if manager.input_block_frames == 0:
            if input_handler.just_pressed("L"):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            if input_handler.just_pressed("B"):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

        for event in events:
            if event.type == pygame.QUIT:
                running = False
            manager.handle_events(event)

        manager.update(dt)

        manager.draw(base_surface)

        scaled = pygame.transform.smoothscale(
            base_surface,
            (screen.get_width(), screen.get_height())
        )

        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
