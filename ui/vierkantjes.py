import pygame
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import styles


class vierkantjes:
    def __init__(self):
        self.styles = styles
    def vierkantjes(self):
        #vierkantjes rechtsboven
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (470, 0, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (470, 0, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (461, 0, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (461, 0, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (470, 9, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (470, 9, 10, 10), width=1)

        #vierkantjes rechtsonder
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (470, 260, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (470, 260, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (461, 260, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (461, 260, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (461, 251, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (461, 251, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (360, 70, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (360, 70, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (360, 61, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (360, 61, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (369, 70, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (369, 70, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (70, 0, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (70, 0, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (79, 9, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (79, 9, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (60, 260, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (60, 260, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (69, 260, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (69, 260, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (69, 250, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (69, 250, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (0, 210, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (0, 210, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (9, 210, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (9, 210, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (0, 219, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (0, 219, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (0, 40, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (0, 40, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (70, 140, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (70, 140, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (79, 149, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (79, 149, 10, 10), width=1)

        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (330, 130, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (330, 130, 10, 10), width=1)
        pygame.draw.rect(base_surface, (self.styles.CARD_COLOR), (339, 139, 10, 10))
        pygame.draw.rect(base_surface, (0,0,0), (339, 139, 10, 10), width=1)