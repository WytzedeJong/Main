import pygame
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT



class AppStyles:
    def __init__(self):

        self.font = "segoeui"
        self.set_standaard_kleuren()
    
    def set_standaard_kleuren(self):
        
        
        self.BG_TOP = (100, 100, 100)    
        self.BG_BOTTOM = (255, 255, 255) 
        self.BG = (240, 240, 240)           # Lichtgrijze "canvas" achtergrond
        self.SQ_COLOR = (220, 220, 220)     # Subtiele grijze blokjes
        self.CARD_COLOR = (255, 255, 255)    # Puur witte kaarten (steken af tegen BG)
        self.CARD_SELECTED = (255, 200, 0)

        self.TEXT_COLOR = (30, 40, 50)
        self.DOTS = 0, 0, 0

        # Font sizes - General
        self.FONT_NAME = self.font
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
        self.GAMES_CARD_HEIGHT = 100
        self.CARD_SPACING = 20


        # Font sizes - Settings/SubMenu
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15


        #settings kleuren
        self.BACKGROUND = 255, 255, 255
        self.TEXT_SET = 0, 0, 0
        
    def gold_color(self):
        
        self.BG = (255, 233, 147)
        self.SQ_COLOR = (255, 203, 5)
        self.CARD_COLOR = (255, 203, 5)
        self.CARD_SELECTED = (255, 245, 120)

        self.TEXT_COLOR = (30, 40, 50)
        self.DOTS = 255, 255, 255
        # Font sizes - General
        self.FONT_NAME = self.font
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
        self.GAMES_CARD_HEIGHT = 100
        self.CARD_SPACING = 20


        # Font sizes - Settings/SubMenu
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15


        #settings kleuren
        self.BACKGROUND = (255, 255, 255)
        self.TEXT_SET = (0, 0, 0)

    def green_color(self):
        
        self.BG = (50, 200, 150)           # Fel mint/aquagroen
        self.SQ_COLOR = (30, 160, 120)     # Dieper turquoise voor vulling
        self.CARD_COLOR = (20, 80, 60)      # Donkergroen (bijna "Forest") voor contrast
        self.CARD_SELECTED = (150, 200, 40)  
        self.TEXT_COLOR = (0, 0, 0)
        self.TEXT_SET = (0, 0, 0)
        self.DOTS = (50, 80, 30) 
        self.BACKGROUND = (255, 255, 255)
        self.FONT_NAME = self.font
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_INPUT_SIZE = 20
        self.FONT_HOME_TITLE_SIZE = 28
        self.FONT_HOME_TIME_SIZE = 22
        self.FONT_HOME_CARD_SIZE = 18
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.GAMES_CARD_HEIGHT = 100
        self.CARD_SPACING = 20
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15
        
    def blue_color(self):
        self.BG = (132, 177, 214)
        self.SQ_COLOR = (45, 115, 175)
        self.CARD_COLOR = (69, 148, 211)
        self.CARD_SELECTED = (40, 160, 175)
        self.TEXT_COLOR = (0, 0, 0)
        self.TEXT_SET = (0, 0, 0)
        self.DOTS = (60, 110, 170) 
        self.BACKGROUND = (255, 255, 255)
        self.FONT_NAME = self.font
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_INPUT_SIZE = 20
        self.FONT_HOME_TITLE_SIZE = 28
        self.FONT_HOME_TIME_SIZE = 22
        self.FONT_HOME_CARD_SIZE = 18
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.GAMES_CARD_HEIGHT = 100
        self.CARD_SPACING = 20
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15
        
    def red_color(self):
        self.BG_TOP = (255, 255, 255)
        self.BG_BOTTOM = (255, 255, 255)
        self.BG = (255, 142, 142)
        self.SQ_COLOR = (255, 27, 27)
        self.CARD_COLOR = (238, 49 ,53)
        self.CARD_SELECTED = (241, 102, 130)
        self.TEXT_COLOR = (0, 0, 0)
        self.TEXT_SET = (0, 0, 0)
        self.DOTS = (220, 20, 20) 
        self.BACKGROUND = (255, 255, 255)
        self.FONT_NAME = self.font
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_HOME_TITLE_SIZE = 28
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.GAMES_CARD_HEIGHT = 100
        self.CARD_SPACING = 20

    
        

# Helper function to create fonts
    def create_font(self, size, bold=False):
        return pygame.font.SysFont(self.FONT_NAME, size, bold)


# Shared styles instance for app-wide theming
styles = AppStyles()

