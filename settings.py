import pygame

pygame.init()

BASE_WIDTH = 480
BASE_HEIGHT = 270
FPS = 60

info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)

base_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))

clock = pygame.time.Clock()
pygame.display.set_caption("WinMan")
