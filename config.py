import pygame

# Colors
BG_TOP = (120, 200, 180)
BG_BOTTOM = (40, 120, 140)

CARD_COLOR = (255, 255, 255)
CARD_SELECTED = (255, 220, 120)

TEXT_COLOR = (30, 40, 50)

# Font sizes - General
FONT_NAME = "arial"
FONT_TITLE_SIZE = 28
FONT_MENU_SIZE = 15
FONT_INPUT_SIZE = 20

# Font sizes - Home Menu
FONT_HOME_TITLE_SIZE = 28
FONT_HOME_TIME_SIZE = 22
FONT_HOME_CARD_SIZE = 18

# Font sizes - Lock Screen
FONT_LOCK_TITLE_SIZE = 22
FONT_LOCK_NAME_SIZE = 15
FONT_LOCK_INPUT_SIZE = 20
FONT_LOCK_TIME_SIZE = 18
FONT_LOCK_KEYBOARD_SIZE = 12

# Font sizes - Edit Username
FONT_EDIT_TITLE_SIZE = 26
FONT_EDIT_NAME_SIZE = 18
FONT_EDIT_INPUT_SIZE = 20

# Font sizes - Settings/SubMenu
FONT_SETTINGS_TITLE_SIZE = 28
FONT_SETTINGS_MENU_SIZE = 15

# Card dimensions (Home Menu)
CARD_WIDTH = 100
CARD_HEIGHT = 140
CARD_SPACING = 20

# Helper function to create fonts
def create_font(size, bold=False):
    return pygame.font.SysFont(FONT_NAME, size, bold=bold)

