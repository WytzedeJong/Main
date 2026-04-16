import pygame
from typing import Dict

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
            except Exception:
                self._backend = "keyboard"

    def read(self, keys=None) -> dict[str, bool]:
        if self._backend == "gpiozero":
            return {name: bool(btn.is_pressed) for name, btn in self._buttons.items()}

        if self._backend == "rpigpio":
            return {name: self.GPIO.input(pin) == 0 for name, pin in self.gpio_map.items()}

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


class InputHandler:
    def __init__(self):
        self.reader = DpadReader(GPIO_MAP)
        self.input_block_timer = 0
        self.current: Dict[str, bool] = {}
        self.previous: Dict[str, bool] = {}

        self.extra_keys = {
            "SPACE": pygame.K_SPACE,
            "ENTER": pygame.K_RETURN,
        }

    def update(self):
        keys = pygame.key.get_pressed()

        self.previous = dict(self.current)

        dpad_state = self.reader.read(keys=keys)
        self.current = dict(dpad_state)

        for name, key_const in self.extra_keys.items():
            self.current[name] = bool(keys[key_const])

    def is_pressed(self, button: str) -> bool:
        return self.current.get(button, False)

    def just_pressed(self, button: str) -> bool:
        """True alleen op het moment dat de knop ingedrukt wordt"""
        return self.current.get(button, False) and not self.previous.get(button, False)

    def close(self):
        self.reader.close()