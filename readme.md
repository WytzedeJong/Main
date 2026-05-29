WinMan
WinMan is een Python-gebaseerd gamemenu-systeem voor de Raspberry Pi, speciaal ontworpen voor een handheld gameconsole. Het systeem biedt een overzichtelijk menu met 10 ingebouwde games, een highscore-systeem per game en aanpasbare gebruikersinstellingen.

Inhoud

Features
Games
Installatie & Setup
Een game toevoegen
Licentie


Features

Menu met drie secties: Games, Highscores en Settings
Highscores per game, lokaal opgeslagen op het apparaat
Aanpasbare instellingen zoals tekstgrootte, thema en wachtwoordbeheer
Uitbreidbaar — nieuwe games zijn eenvoudig toe te voegen via de SceneManager


Games
WinMan wordt geleverd met de volgende 10 ingebouwde games:
#Game1Monkey Stacker2Pengu Slider3Dungeon4Puzzle5Space6Tower Defense7Pixel Spin8Farm Nation9System Purge10Speed Racer

Installatie & Setup
Vereisten

Raspberry Pi / Raspberry Pi
Python 3.x
Git

Stappen

Clone de repository

bash   git clone https://github.com/WytzedeJong/Main.git
   cd WinMan

Installeer pygame

bash   pip install -r pygame

Start het systeem

bash   python main.py


Een game toevoegen
Games worden toegevoegd door de SceneManager over te erven en er een game omheen te bouwen. Hieronder een minimaal voorbeeld:

import pygame
from core.scene import Scene

class TestGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.SysFont("arial", 60)

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((50, 80, 120))

        text = self.font.render("Test Game", True, (255, 255, 255))
        text_rect = text.get_rect(center=(surface.get_width() // 2,
                                          surface.get_height() // 2))

        surface.blit(text, text_rect)

Registreer de game vervolgens in het hoofdmenu zodat hij zichtbaar wordt in de gamelijst.

Licentie
Dit project is gelicenseerd onder de GNU General Public License v3.0.
Je mag de software vrij gebruiken, aanpassen en verspreiden, mits je de broncode beschikbaar stelt onder dezelfde licentie.