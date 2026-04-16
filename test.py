import sys
import time

import pygame


GPIO_MAP = {
    "UP": 4,
    "DOWN": 17,
    "LEFT": 18,
    "RIGHT": 22,
    "L": 24,
    "B": 23
}


class DpadReader:
    def __init__(self, gpio_map: dict[str, int]):
        self.gpio_map = gpio_map
        self._backend = None
        self._buttons = {}
        self._last_keys = {
            "UP": False, "DOWN": False, "LEFT": False, "RIGHT": False,
            "L": False, "B": False
        }

        try:
            from gpiozero import Button

            self._backend = "gpiozero"
            for name, pin in gpio_map.items():
                self._buttons[name] = Button(pin, pull_up=True, bounce_time=0.03)
        except Exception:
            try:
                import RPi.GPIO as GPIO

                self._backend = "rpigpio"
                self.GPIO = GPIO
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                for pin in gpio_map.values():
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception as e:
                self._backend = "keyboard"
                self._backend_error = e

    def read(self, keys=None) -> dict[str, bool]:
        if self._backend == "gpiozero":
            return {name: bool(btn.is_pressed) for name, btn in self._buttons.items()}

        if self._backend == "rpigpio":
            GPIO = self.GPIO
            return {name: GPIO.input(pin) == 0 for name, pin in self.gpio_map.items()}

        if self._backend == "keyboard":
            if keys is None:
                return dict(self._last_keys)

            state = {
                "UP": bool(keys[pygame.K_UP]),
                "DOWN": bool(keys[pygame.K_DOWN]),
                "LEFT": bool(keys[pygame.K_LEFT]),
                "RIGHT": bool(keys[pygame.K_RIGHT]),
                "L": bool(keys[pygame.K_l]),
                "B": bool(keys[pygame.K_b]),
            }
            self._last_keys = state
            return state

        return {name: False for name in self.gpio_map}

    @property
    def backend_name(self) -> str:
        return str(self._backend)

    def close(self) -> None:
        if self._backend == "gpiozero":
            for btn in self._buttons.values():
                try:
                    btn.close()
                except Exception:
                    pass
        elif self._backend == "rpigpio":
            try:
                self.GPIO.cleanup()
            except Exception:
                pass


def main() -> int:
    reader = DpadReader(GPIO_MAP)

    pygame.init()
    pygame.display.set_caption("Raspberry Pi D-pad GPIO test (Pygame)")
    screen = pygame.display.set_mode((640, 360))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 36)
    font_small = pygame.font.SysFont(None, 22)

    bg = (18, 18, 22)
    panel = (34, 34, 44)
    off = (120, 120, 130)
    on = (60, 220, 120)
    text = (235, 235, 240)

    rects = {
        "UP": pygame.Rect(280, 60, 80, 60),
        "LEFT": pygame.Rect(200, 130, 80, 60),
        "RIGHT": pygame.Rect(360, 130, 80, 60),
        "DOWN": pygame.Rect(280, 200, 80, 60),
        "L": pygame.Rect(100, 130, 60, 60),
        "B": pygame.Rect(480, 130, 60, 60),
    }

    last_print = 0.0
    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            keys = pygame.key.get_pressed()
            pressed = reader.read(keys=keys)

            now = time.time()
            if now - last_print > 0.2:
                last_print = now
                sys.stdout.write(
                    "\rUP:{:1d} DOWN:{:1d} LEFT:{:1d} RIGHT:{:1d} L:{:1d} B:{:1d}   ".format(
                        int(pressed["UP"]),
                        int(pressed["DOWN"]),
                        int(pressed["LEFT"]),
                        int(pressed["RIGHT"]),
                        int(pressed["L"]),
                        int(pressed["B"]),
                    )
                )
                sys.stdout.flush()

            screen.fill(bg)

            for name, r in rects.items():
                pygame.draw.rect(screen, panel, r, border_radius=10)
                pygame.draw.rect(
                    screen,
                    on if pressed.get(name) else off,
                    r.inflate(-10, -10),
                    border_radius=10,
                )
                label = font.render(name, True, (10, 10, 14))
                label_pos = label.get_rect(center=r.center)
                screen.blit(label, label_pos)

            pygame.display.flip()
            clock.tick(60)

    finally:
        reader.close()
        pygame.quit()
        sys.stdout.write("\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())