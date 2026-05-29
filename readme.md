# WinMan 🎮

WinMan is een Python-gebaseerd gamemenu-systeem voor de Raspberry Pi, speciaal ontworpen voor een handheld gameconsole. Het systeem biedt een overzichtelijk menu met 10 ingebouwde games, een highscore-systeem per game en aanpasbare gebruikersinstellingen.

## 📑 Inhoud
* [Features](#-features)
* [Games](#-games)
* [Installatie & Setup](#-installatie--setup)
* [Een game toevoegen](#-een-game-toevoegen)
* [Licentie](#-licentie)

---

## ✨ Features
* **Menu met drie secties:** Games, Highscores en Settings.
* **Highscores per game:** Lokaal opgeslagen op het apparaat.
* **Aanpasbare instellingen:** Zoals tekstgrootte, thema en wachtwoordbeheer.
* **Uitbreidbaar:** Nieuwe games zijn eenvoudig toe te voegen via de `SceneManager`.

---

## 🕹️ Games
WinMan wordt geleverd met de volgende 10 ingebouwde games:

| # | Game | # | Game |
|---|---|---|---|
| **1** | Monkey Stacker | **6** | Tower Defense |
| **2** | Pengu Slider | **7** | Pixel Spin |
| **3** | Dungeon | **8** | Farm Nation |
| **4** | Puzzle | **9** | System Purge |
| **5** | Space | **10**| Speed Racer |

---

## ⚙️ Installatie & Setup

### Vereisten
* Raspberry Pi / Raspberry Pi OS
* Python 3.x
* Git

### Stappen

1. **Clone de repository:**
   ```bash
   git clone [https://github.com/WytzedeJong/Main.git](https://github.com/WytzedeJong/Main.git)
   cd WinMan
Installeer Pygame:

Bash
pip install pygame
Start het systeem:

Bash
python main.py
🛠️ Een game toevoegen
Games worden toegevoegd door de SceneManager over te erven en er een game omheen te bouwen. Hieronder een minimaal voorbeeld van hoe je een nieuwe scene opzet:

```python
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
```
Let op: Vergeet niet om de game vervolgens te registreren in gamesmenu.py, zodat deze daadwerkelijk zichtbaar wordt en geselecteerd kan worden in de gamelijst.

📄 Licentie
Dit project is gelicenseerd onder de GNU General Public License v3.0. Je mag de software vrij gebruiken, aanpassen en verspreiden, mits je de broncode beschikbaar stelt onder dezelfde licentie.
