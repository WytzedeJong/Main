import pygame
from settings import screen, clock, base_surface
from core.scene_manager import SceneManager
from ui.lockscreen import LockScreen

def main():
    manager = SceneManager()
    manager.set_scene(LockScreen(manager))

    running = True
    while running:
        dt = clock.tick(60) / 1000

        # 🔥 INPUT BLOCK (FIX)
        if manager.input_block_timer > 0:
            manager.input_block_timer -= dt

            # Wel events ophalen (anders window freeze)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # ⚠️ GEEN update → dus geen input verwerking
            manager.draw(base_surface)

            scaled = pygame.transform.smoothscale(
                base_surface,
                (screen.get_width(), screen.get_height())
            )

            screen.blit(scaled, (0, 0))
            pygame.display.flip()
            continue

        # Normale flow
        for event in pygame.event.get():
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