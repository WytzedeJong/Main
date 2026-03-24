import pygame


class AppStyles:
    def __init__(self):
        self.set_standaard_kleuren()
    
    def set_standaard_kleuren(self):
        
        
        self.BG_TOP = (100, 100, 100)    
        self.BG_BOTTOM = (255, 255, 255) 
        self.CARD_COLOR = (255, 255, 255)
        self.CARD_SELECTED = (255, 220, 120)

        self.TEXT_COLOR = (30, 40, 50)
        self.DOTS = 0, 0, 0

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
        self.BACKGROUND = 255, 255, 255
        self.TEXT_SET = 0, 0, 0
        
    def dark_color(self):
        self.BG_TOP = (120, 200, 180)
        self.BG_BOTTOM = (40, 120, 140)

        # Dark Mode Kleuren
        self.BG_TOP = (255, 255, 255)   
        self.BG_BOTTOM = (100, 100, 100)
        self.CARD_COLOR = (45, 45, 48)     
        self.CARD_SELECTED = (0, 120, 215)

        self.TEXT_COLOR = (30, 40, 50)
        self.DOTS = 255, 255, 255
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
        self.BACKGROUND = 0, 0, 0,
        self.TEXT_SET = 255,255,255
    def green_color(self):
        self.BG_TOP = (204, 232, 173)    
        self.BG_BOTTOM = (160, 200, 130) 
        self.CARD_COLOR = (85, 120, 50)     
        self.CARD_SELECTED = (110, 150, 70) 
        self.TEXT_COLOR = (0, 0, 0)
        self.TEXT_SET = (0, 0, 0)
        self.DOTS = (50, 80, 30) 
        self.BACKGROUND = (204, 232, 173)
        self.FONT_NAME = "arial"
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_INPUT_SIZE = 20
        self.FONT_HOME_TITLE_SIZE = 28
        self.FONT_HOME_TIME_SIZE = 22
        self.FONT_HOME_CARD_SIZE = 18
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.CARD_SPACING = 20
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15
        
    def blue_color(self):
        self.BG_TOP = (135, 185, 220)    
        self.BG_BOTTOM = (100, 150, 200) 
        self.CARD_COLOR = (80, 150, 210)     
        self.CARD_SELECTED = (110, 180, 240) 
        self.TEXT_COLOR = (0, 0, 0)
        self.TEXT_SET = (0, 0, 0)
        self.DOTS = (60, 110, 170) 
        self.BACKGROUND = (135, 185, 220)
        self.FONT_NAME = "arial"
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_INPUT_SIZE = 20
        self.FONT_HOME_TITLE_SIZE = 28
        self.FONT_HOME_TIME_SIZE = 22
        self.FONT_HOME_CARD_SIZE = 18
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.CARD_SPACING = 20
        self.FONT_SETTINGS_TITLE_SIZE = 28
        self.FONT_SETTINGS_MENU_SIZE = 15
        
    def red_color(self):
        self.BG_TOP = (255, 145, 145)    
        self.BG_BOTTOM = (240, 110, 110) 
        self.CARD_COLOR = (255, 40, 40)      
        self.CARD_SELECTED = (255, 80, 80) 
        self.TEXT_COLOR = (0, 0, 0)
        self.TEXT_SET = (0, 0, 0)
        self.DOTS = (220, 20, 20) 
        self.BACKGROUND = (255, 145, 145)
        self.FONT_NAME = "arial"
        self.FONT_TITLE_SIZE = 28
        self.FONT_MENU_SIZE = 15
        self.FONT_HOME_TITLE_SIZE = 28
        self.CARD_WIDTH = 100
        self.CARD_HEIGHT = 140
        self.CARD_SPACING = 20
        

# Helper function to create fonts
    def create_font(self, size, bold=False):
        return pygame.font.SysFont(self.FONT_NAME, size, bold)


# Shared styles instance for app-wide theming
styles = AppStyles()

