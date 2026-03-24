import pygame


class AppStyles:
    def __init__(self):
        self.set_standaard_kleuren()
            
    def set_standaard_kleuren(self):
        
        
        self.BG_TOP = (120, 200, 180)
        self.BG_BOTTOM = (40, 120, 140)

        self.CARD_COLOR = (255, 255, 255)
        self.CARD_SELECTED = (255, 220, 120)

        self.TEXT_COLOR = (30, 40, 50)

        # Font sizes - General
        self.FONT_NAME = "arial"
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_INPUT_SIZE = 20

        # Font sizes - Home Menu
        self.FONT_HOME_TITLE_SIZE = 28
        self.FONT_HOME_TIME_SIZE = 22
        self.FONT_HOME_CARD_SIZE = 18

        # Font sizes - Lock Screen
        self.FONT_LOCK_TITLE_SIZE = 22
        self.FONT_LOCK_NAME_SIZE = 15
        self.FONT_LOCK_INPUT_SIZE = 20
        self.FONT_LOCK_TIME_SIZE = 18
        self.FONT_LOCK_KEYBOARD_SIZE = 12

        # Font sizes - Edit Username
        self.FONT_EDIT_TITLE_SIZE = 26
        self.FONT_EDIT_NAME_SIZE = 18
        self.FONT_EDIT_INPUT_SIZE = 20

        # Card dimensions (Home Menu)
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.CARD_SPACING = 20


        # Font sizes - Settings/SubMenu
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15


        #settings kleuren
        self.BACKGROUND = 50, 50, 50
        self.TEXT_SET = 255,255,255

# Helper function to create fonts
    def create_font(self, size, bold=False):
        return pygame.font.SysFont(self.FONT_NAME, size, bold)

