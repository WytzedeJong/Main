import os
import sys
from gpiozero import Button, Device
from gpiozero.pins.lgpio import LGPIOFactory
from signal import pause
from datetime import datetime

Device.pin_factory = LGPIOFactory()

GREEN  = "\033[42m\033[97m"
RED    = "\033[41m\033[97m"
RESET  = "\033[0m"
CLEAR  = "\033c"

BUTTONS = {
    "UP":    4,
    "DOWN":  17,
    "LEFT":  18,
    "RIGHT": 22,
    "L":     24,
    "B":     23,
    "A":     27,
    "ESC":   25,
}

state  = {name: False for name in BUTTONS}
log    = []

btns = {}
for name, pin in BUTTONS.items():
    btns[name] = Button(pin)

def draw():
    os.write(sys.stdout.fileno(), CLEAR.encode())
    print("  GPIO knoppentest  —  Ctrl+C om te stoppen\n")

    row1 = ["UP", "DOWN", "LEFT", "RIGHT"]
    row2 = ["L", "B", "A", "ESC"]

    for row in [row1, row2]:
        line = "  "
        for name in row:
            color = GREEN if state[name] else RED
            label = f" {name:^6} "
            line += f"{color}{label}{RESET}  "
        print(line)

    print()
    print("  Laatste acties:")
    for entry in log[-6:]:
        print(f"    {entry}")

def press(name):
    state[name] = True
    log.append(f"{datetime.now().strftime('%H:%M:%S')}  {name} ingedrukt")
    draw()

def release(name):
    state[name] = False
    log.append(f"{datetime.now().strftime('%H:%M:%S')}  {name} losgelaten")
    draw()

for name, btn in btns.items():
    btn.when_pressed  = lambda n=name: press(n)
    btn.when_released = lambda n=name: release(n)

draw()

try:
    pause()
except KeyboardInterrupt:
    print("\nKlaar.")