import pygame
import random
import json
import os

from core.scene import Scene
from settings import base_surface, BASE_WIDTH, BASE_HEIGHT
from core.input_manager import InputHandler

# --- CONFIGURATIE ---
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
FPS = 60
GRID_W, GRID_H = 5, 3  # 5 kolommen, 3 rijen

# Kleuren
BLACK = (10, 10, 10)
DARK_GRAY = (30, 30, 30)
GOLD = (212, 175, 55)
RED = (180, 0, 0)
WHITE = (220, 220, 220)
GREEN = (50, 180, 50)
BLUE = (0, 120, 255)

# Symbolen & Hun Basiswaarde — afgestemd op de foto (Φ-waarden en kansen)
# Gewichten zijn proportioneel met de percentages op de foto:
#   Citroen 19.4%, Kers 19.4%, Klaver 14.9%, Pruim 14.9%,
#   Diamant 11.9%, Bar 11.9%, Zeven 7.5%
SYMBOLS = {
    "Citroen":  {"color": (255, 230,  40), "value": 2,  "weight": 0.194, "icon": "🍋"},
    "Kers":     {"color": (220,  40,  40), "value": 2,  "weight": 0.194, "icon": "🍒"},
    "Klaver":   {"color": ( 30, 200,  80), "value": 3,  "weight": 0.149, "icon": "🍀"},
    "Pruim":    {"color": (180,  60, 200), "value": 3,  "weight": 0.149, "icon": "🍇"},
    "Diamant":  {"color": ( 80, 210, 255), "value": 5,  "weight": 0.119, "icon": "💎"},
    "Bar":      {"color": (200, 160,  40), "value": 5,  "weight": 0.119, "icon": "🎰"},
    "Zeven":    {"color": (255,  20,  20), "value": 7,  "weight": 0.075, "icon": "7"},
}

# Runtime gewichten — worden aangepast door shop-upgrades
# zodat het spel de weights uit SYMBOLS kan verhogen/verlagen zonder de originele te wijzigen
_symbol_weight_bonus = {name: 0.0 for name in SYMBOLS}
_symbol_value_bonus  = {name: 0   for name in SYMBOLS}

def get_effective_weight(sym_name):
    base = SYMBOLS[sym_name]["weight"]
    return max(0.01, base + _symbol_weight_bonus[sym_name])

def get_effective_value(sym_name):
    base = SYMBOLS[sym_name]["value"]
    return base + _symbol_value_bonus[sym_name]

# Load patterns from JSON
def load_patterns():
    patterns_path = os.path.join(os.path.dirname(__file__), "patterns.json")
    try:
        with open(patterns_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("patterns", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

PATTERNS = load_patterns()

# Load shop items from JSON
def load_shop_items():
    shop_path = os.path.join(os.path.dirname(__file__), "shop_items.json")
    try:
        with open(shop_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"charms": {}, "powerups": {}, "upgrades": {}}

SHOP_ITEMS = load_shop_items()

class PixelspinGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        pygame.init()

        self.font = pygame.font.SysFont("monospace", 18, bold=True)
        self.large_font = pygame.font.SysFont("monospace", 32, bold=True)

        self.button_cooldown = 0
        self.selected_button = 0
        self.buttons = []
        self.input = InputHandler()
        self.reset_game()

    def reset_game(self):
        self.coins = 50
        self.atm = 0
        self.luck = 0
        self.spin_count = 0
        self.atm_interest_rate = 0.05
        self.has_666_protection = False

        # Deadline / ronde systeem
        self.deadline_number = 1
        self.round_in_deadline = 1
        self.spins_left = 0
        self.chosen_spins = 0

        # Fase: "spin_choice", "spinning_phase", "between_rounds", "atm_phase"
        self.phase = "spin_choice"

        self.grid = self.generate_grid()
        self.spinning = False
        self.spin_timer = 0
        self.last_wins = []
        self.total_win_anim = 0
        self.button_cooldown = 0

        self.current_screen = "game"
        self.selected_button = 0
        self.buttons = []

        self.winning_coords = []
        self.winning_patterns = []
        self.flash_counter = 0
        self.purchased_items = {
            "charms": set(),
            "powerups": set(),
            "upgrades": set()
        }

        self.purchased_items = {
            "charms": set(),
            "powerups": set(),
            "upgrades": set()
        }

    def _deadline_cost_for(self, deadline_num):
        """Bereken de ATM-doelwaarde voor een bepaalde deadline"""
        return int(150 * (1.4 ** (deadline_num - 1)))
        
    def generate_grid(self):
        """Genereert het grid.
        Bij luck >= 15: alle cellen krijgen hetzelfde symbool → jackpot gegarandeerd.
        Anders: puur random gewogen per symbool.
        Luck bepaalt verder hoeveel patronen actief worden (zie _pattern_activation_chance)."""
        grid = []
        if self.luck >= 15:
            # Forceer één symbool zodat jackpot geometrisch klopt
            jackpot_sym = self.weighted_choice(SYMBOLS)
            for c in range(GRID_W):
                col = [jackpot_sym] * GRID_H
                grid.append(col)
        else:
            for c in range(GRID_W):
                col = []
                for r in range(GRID_H):
                    col.append(self.weighted_choice(SYMBOLS))
                grid.append(col)
        return grid

    def get_pattern_activation_count(self):
        """Bepaal hoeveel patronen deze spin geactiveerd worden op basis van luck.
        
        Luck bepaalt het AANTAL patronen, niet de kans per patroon:
          luck=0  → 0 patronen
          luck=1  → 1 patroon
          luck=5  → 5 patronen
          luck=10 → 10 patronen
          luck=15+ → alle patronen
        """
        if self.luck >= 15:
            return 999  # Alle patronen
        return max(0, self.luck)
    
    def weighted_choice(self, symbols):
        """Selecteert een symbool op basis van effectieve weight (inclusief bonussen)"""
        total_weight = sum(get_effective_weight(sym) for sym in symbols)
        choice = random.uniform(0, total_weight)
        current = 0
        for sym in symbols:
            current += get_effective_weight(sym)
            if choice <= current:
                return sym
        return list(symbols.keys())[-1]

    def choose_spins(self, amount):
        """Speler kiest 3 of 7 spins voor deze ronde"""
        self.chosen_spins = amount
        self.spins_left = amount
        self.phase = "spinning_phase"
        self.last_wins = []
        self.total_win_anim = 0
        self.winning_coords = []
        self.winning_patterns = []
        self.grid = self.generate_grid()  # Nieuw grid per ronde

    def spin(self):
        if self.phase != "spinning_phase":
            return
        if self.coins >= 5 and not self.spinning and self.spins_left > 0:
            self.coins -= 5
            self.spins_left -= 1
            self.spin_count += 1
            self.spinning = True
            self.spin_timer = 13
            self.last_wins = []
            self.total_win_anim = 0
            self.winning_coords = []  # Reset winnings per spin
            self.winning_patterns = []  # Reset winnings per spin
            
            # Reset luck en laad shop-bonuses in
            self.luck = 0
            self._apply_all_luck_bonuses()

    def find_pattern_coordinates(self, sym_name, pattern_type):
        """Vind alle coördinaten die matchen met een pattern type"""
        coords = []
        found_positions = set()  # Voorkom overlappende detectie
        
        if pattern_type == "horizontal":
            # Check elke rij voor horizontale matches
            for r in range(GRID_H):
                c = 0
                while c < GRID_W:
                    # Kijk hoeveel gelijk achter elkaar
                    length = 0
                    temp_c = c
                    while temp_c < GRID_W and self.grid[temp_c][r] == sym_name:
                        length += 1
                        temp_c += 1
                    
                    if length >= 3:
                        match = tuple([(c + i, r) for i in range(length)])
                        if match not in found_positions:
                            coords.append(list(match))
                            found_positions.add(match)
                        c = temp_c  # Skip voorbij deze match
                    else:
                        c += 1
        
        elif pattern_type == "vertical":
            # Check elke kolom voor verticale matches
            for c in range(GRID_W):
                r = 0
                while r < GRID_H:
                    length = 0
                    temp_r = r
                    while temp_r < GRID_H and self.grid[c][temp_r] == sym_name:
                        length += 1
                        temp_r += 1
                    
                    if length >= 3:
                        match = tuple([(c, r + i) for i in range(length)])
                        if match not in found_positions:
                            coords.append(list(match))
                            found_positions.add(match)
                        r = temp_r  # Skip voorbij deze match
                    else:
                        r += 1
        
        elif pattern_type == "diagonal":
            # Diagonale match van (0,0) naar (2,2)
            for c in range(GRID_W - 2):
                for r in range(GRID_H - 2):
                    if (self.grid[c][r] == sym_name and 
                        self.grid[c+1][r+1] == sym_name and 
                        self.grid[c+2][r+2] == sym_name):
                        coords.append([(c, r), (c+1, r+1), (c+2, r+2)])
        
        elif pattern_type == "bottom_row":
            # Onderste rij vol
            if all(self.grid[c][GRID_H-1] == sym_name for c in range(GRID_W)):
                coords.append([(c, GRID_H-1) for c in range(GRID_W)])
        
        elif pattern_type == "top_row":
            # Bovenste rij vol
            if all(self.grid[c][0] == sym_name for c in range(GRID_W)):
                coords.append([(c, 0) for c in range(GRID_W)])
        
        elif pattern_type == "eye":
            # O-vorm
            eye_coords = [(1,0), (2,0), (3,0), (1,2), (2,2), (3,2), (1,1), (3,1)]
            if all(self.grid[c][r] == sym_name for c, r in eye_coords):
                coords.append(eye_coords)
        
        elif pattern_type == "zigzag":
            # Z-patroon van links-boven naar rechts-onder
            for c in range(GRID_W - 2):
                # Laag-Midden-Hoog patroon (zigzag)
                if (self.grid[c][GRID_H-1] == sym_name and
                    self.grid[c+1][GRID_H-2] == sym_name and
                    self.grid[c+2][GRID_H-3] == sym_name):
                    coords.append([(c, GRID_H-1), (c+1, GRID_H-2), (c+2, GRID_H-3)])
        
        elif pattern_type == "zagzag":
            # Omgekeerde Z-patroon van links-onder naar rechts-boven
            for c in range(GRID_W - 2):
                # Hoog-Midden-Laag patroon (zagzag)
                if (self.grid[c][0] == sym_name and
                    self.grid[c+1][1] == sym_name and
                    self.grid[c+2][2] == sym_name):
                    coords.append([(c, 0), (c+1, 1), (c+2, 2)])
        
        elif pattern_type == "jackpot":
            # Alle cellen gelijk
            if all(self.grid[c][r] == sym_name for c in range(GRID_W) for r in range(GRID_H)):
                coords.append([(c, r) for c in range(GRID_W) for r in range(GRID_H)])
        
        # Safety: Ongedefinieerde pattern types returnen lege list
        # (geen crash, gewoon skip)
        
        return coords

    def check_all_patterns(self):
        """Pattern-checking met Luck-bepaalde activatie.
        
        Luck bepaalt hoeveel patronen geactiveerd worden.
        Eerst alle GOEDE patronen activeren (per luck count).
        Daarna random goede/slechte patronen vullen tot einde.
        """
        total_payout = 0
        found_any = []
        self.winning_coords = []
        self.winning_patterns = []

        # ── Stap 1: verzamel ALLE geometrisch-geldige treffers ─────────────
        candidate_hits = []   # lijst van (pattern_def, sym_name, match_coords)

        for sym_name in SYMBOLS.keys():
            for p in PATTERNS:
                pattern_coords_list = self.find_pattern_coordinates(sym_name, p["type"])
                for match_coords in pattern_coords_list:
                    candidate_hits.append((p, sym_name, match_coords))

        # Sorteer op multiplier (groot → klein) zodat jackpot/complex eerst komen
        candidate_hits.sort(key=lambda x: x[0]["multiplier"], reverse=True)

        # ── Stap 2: Luck bepaalt hoeveel patronen geactiveerd worden ───────
        # Activeer de BESTE patronen tot het luck-limit
        activated_count = self.get_pattern_activation_count()
        seen_pattern_coords = set()
        patterns_to_payout = []  # Patronen die uitbetaald worden

        for p, sym_name, match_coords in candidate_hits:
            if len(patterns_to_payout) >= activated_count:
                break  # Genoeg patronen geactiveerd

            key = (p["name"], sym_name, frozenset(match_coords))
            if key in seen_pattern_coords:
                continue

            seen_pattern_coords.add(key)
            patterns_to_payout.append((p, sym_name, match_coords))

        # ── Stap 3: Bereken uitbetalingen voor geactiveerde patronen ───────
        for p, sym_name, match_coords in patterns_to_payout:
            symbol_base = get_effective_value(sym_name)
            symbol_multiplier = 1.0
            pattern_multiplier = p["multiplier"]

            # Big Mushroom: x2 symboolwaarde (geen combo-check meer)
            if "Big Mushroom" in self.purchased_items["charms"]:
                symbol_multiplier *= 2.0

            # Pentacle: x1.5 pattern multiplier (geen combo-check meer)
            if "Pentacle" in self.purchased_items["charms"]:
                pattern_multiplier *= 1.5

            win = int((symbol_base * symbol_multiplier) * (10 * pattern_multiplier))
            total_payout += win
            found_any.append(f"{p['name']} ({sym_name}): +{win}")

            # Winning-coördinaten opslaan (voor highlight/flash)
            for coord in match_coords:
                if coord not in self.winning_coords:
                    self.winning_coords.append(coord)
            self.winning_patterns.append({
                "coords": match_coords,
                "symbol": sym_name,
                "pattern": p["name"]
            })

        # ── Stap 4: Lucky Cat ATM-rente (gebaseerd op activated patterns) ───
        if "Lucky Cat" in self.purchased_items["charms"] and len(patterns_to_payout) > 0:
            interest = max(1, int(self.atm * self.atm_interest_rate))
            total_payout += interest
            found_any.append(f"💰 Lucky Cat rente: +{interest}")

        if not found_any:
            found_any.append("Geen patronen deze spin...")

        self.coins += total_payout
        self.total_win_anim = total_payout
        self.last_wins = found_any
    
    # 666 pattern removed - no more evil patterns!

    def update(self, dt):
        self.input.update()
        self._handle_input_actions()
        self.button_cooldown -= 1
        self.flash_counter += 1

        if self.spinning:
            self.spin_timer -= 1
            for c in range(GRID_W):
                for r in range(GRID_H):
                    if random.random() > 0.1:
                        self.grid[c][r] = self.weighted_choice(SYMBOLS)
            if self.spin_timer <= 0:
                self.spinning = False
                self.flash_counter = 0
                self.check_all_patterns()
                # Als spins op zijn na deze spin → ronde klaar
                if self.spins_left == 0:
                    self._end_round()

    def _end_round(self):
        """Ronde is afgelopen: altijd eerst ATM-storting, dan volgende ronde of deadline-betaling"""
        # Ga altijd naar atm_phase na een ronde zodat speler kan storten
        self.phase = "atm_phase"
        self.current_screen = "game"

    def _is_final_round(self):
        return self.round_in_deadline >= 3

    def _atm_deposit_chunk(self):
        """Stort 20% van de deadline-doelwaarde (of alles als minder)"""
        if self.phase != "atm_phase":
            return
        target = self._deadline_cost_for(self.deadline_number)
        chunk = max(1, int(target * 0.20))
        amount = min(chunk, self.coins)
        if amount > 0:
            self.coins -= amount
            self.atm += amount

    def _atm_deposit_all(self):
        """Stort munten totdat ATM het deadline-doel bereikt (niet meer)"""
        if self.phase != "atm_phase":
            return
        target = self._deadline_cost_for(self.deadline_number)
        needed = max(0, target - self.atm)
        amount = min(needed, self.coins)
        if amount > 0:
            self.coins -= amount
            self.atm += amount

    def _try_next_deadline(self):
        """Na betaal-knop: door naar volgende ronde of deadline"""
        if not self._is_final_round():
            self.round_in_deadline += 1
            self.phase = "spin_choice"
            self.grid = self.generate_grid()  # Nieuw grid per ronde
        else:
            target = self._deadline_cost_for(self.deadline_number)
            if self.atm >= target:
                # Betaal exact het doel, behoud de rest in ATM
                self.atm -= target
                self.deadline_number += 1
                self.round_in_deadline = 1
                self.phase = "spin_choice"
                self.consecutive_misses = 0
                self.last_wins = []
                self.grid = self.generate_grid()  # Nieuw grid per deadline
            else:
                self.last_wins = [
                    "GAME OVER! Deadline niet gehaald!",
                    f"Nodig: {target}, ATM: {self.atm}"
                ]
                self.phase = "game_over"

    def _buy_item(self, item_name, cost, item_type):
        if self.coins >= cost and item_name not in self.purchased_items[item_type]:
            self.coins -= cost
            self.purchased_items[item_type].add(item_name)
            # Pas effecten toe voor symbool-upgrades
            self._apply_item_effect(item_name, item_type)
        else:
            # Je hebt dit item al of niet genoeg munten
            return

    def _apply_item_effect(self, item_name, item_type):
        """Verwerk gekochte item-effecten op goud/kansen"""
        # Kans-verhogingen per symbool
        chance_boosts = {
            "Diamant Boost":  ("Diamant", +0.05),
            "Zeven Boost":    ("Zeven",   +0.04),
            "Klaver Boost":   ("Klaver",  +0.04),
        }
        # Waarde-verhogingen per symbool
        value_boosts = {
            "Goud Diamant":   ("Diamant", +3),
            "Goud Zeven":     ("Zeven",   +5),
            "Goud Citroen":   ("Citroen", +1),
        }
        if item_name in chance_boosts:
            sym, delta = chance_boosts[item_name]
            _symbol_weight_bonus[sym] += delta
        if item_name in value_boosts:
            sym, delta = value_boosts[item_name]
            _symbol_value_bonus[sym] += delta
    
    def _apply_all_luck_bonuses(self):
        """Pas alle gekochte luck-items toe aan de huidige luck stat"""
        luck_items = {
            "Luck Potion": 10,
            "Golden Horseshoe": 0,  # Handled separately as multiplier
        }
        
        for item_name, luck_boost in luck_items.items():
            if item_name in self.purchased_items["powerups"] or item_name in self.purchased_items["charms"]:
                self.luck += luck_boost
        
        # Golden Horseshoe: verdubbel andere luck items
        if "Golden Horseshoe" in self.purchased_items["charms"]:
            other_luck = 0
            for item_name, luck_boost in luck_items.items():
                if item_name != "Golden Horseshoe" and item_name in self.purchased_items["powerups"]:
                    other_luck += luck_boost
            self.luck += other_luck

    def deposit(self):
        if self.phase == "atm_phase":
            self.current_screen = "atm"

    def shop(self):
        if self.phase in ("spin_choice", "atm_phase"):
            self.current_screen = "shop"

    def back_to_game(self):
        self.current_screen = "game"

    def handle_events(self, event):
        return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))
            elif event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                self._navigate_buttons(event.key)
            elif event.key == pygame.K_l:
                self._press_selected_button()
            elif event.key == pygame.K_b:
                self._handle_back_button()

    def _handle_input_actions(self):
        if self.input.just_pressed("ESCAPE"):
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))
            return

        direction = self._just_pressed_direction()
        if direction:
            self._navigate_buttons(direction)
        elif self.input.just_pressed("L"):
            self._press_selected_button()
        elif self.input.just_pressed("B"):
            self._handle_back_button()

    def _just_pressed_direction(self):
        for button, key in (
            ("LEFT", pygame.K_LEFT),
            ("RIGHT", pygame.K_RIGHT),
            ("UP", pygame.K_UP),
            ("DOWN", pygame.K_DOWN),
        ):
            if self.input.just_pressed(button):
                return key
        return None

    def _navigate_buttons(self, key):
        if self.button_cooldown > 0:
            return
        if len(self.buttons) == 0:
            return

        in_shop = self.current_screen == "shop"
        in_atm_phase = self.phase == "atm_phase" and self.current_screen == "game"
        in_atm_screen = self.current_screen == "atm"

        if in_atm_phase:
            # ATM phase knop-layout (indices):
            #   Rij 0: [0]=20%   [1]=ALLES
            #   Rij 1: [2]=VOLGENDE RONDE / BETAAL
            #   Rij 2: [3]=ATM   [4]=SHOP
            grid = [[0, 1], [2], [3, 4]]
            # Vind huidige rij en kolom
            cur = self.selected_button
            cur_row, cur_col = 0, 0
            for ri, row in enumerate(grid):
                if cur in row:
                    cur_row = ri
                    cur_col = row.index(cur)
                    break

            if key == pygame.K_LEFT:
                new_col = (cur_col - 1) % len(grid[cur_row])
                self.selected_button = grid[cur_row][new_col]
            elif key == pygame.K_RIGHT:
                new_col = (cur_col + 1) % len(grid[cur_row])
                self.selected_button = grid[cur_row][new_col]
            elif key == pygame.K_DOWN:
                new_row = (cur_row + 1) % len(grid)
                new_col = min(cur_col, len(grid[new_row]) - 1)
                self.selected_button = grid[new_row][new_col]
            elif key == pygame.K_UP:
                new_row = (cur_row - 1) % len(grid)
                new_col = min(cur_col, len(grid[new_row]) - 1)
                self.selected_button = grid[new_row][new_col]

        elif in_shop or in_atm_screen:
            if key == pygame.K_UP:
                self.selected_button = (self.selected_button - 1) % len(self.buttons)
            elif key == pygame.K_DOWN:
                self.selected_button = (self.selected_button + 1) % len(self.buttons)
            if key == pygame.K_LEFT:
                self.selected_button = (self.selected_button - 1) % len(self.buttons)
            elif key == pygame.K_RIGHT:
                self.selected_button = (self.selected_button + 1) % len(self.buttons)

        else:
            if key == pygame.K_LEFT:
                self.selected_button = (self.selected_button - 1) % len(self.buttons)
            elif key == pygame.K_RIGHT:
                self.selected_button = (self.selected_button + 1) % len(self.buttons)

        self.button_cooldown = 5

    def _press_selected_button(self):
        if self.button_cooldown > 0 or len(self.buttons) == 0:
            return
        action = self.buttons[self.selected_button]
        self.button_cooldown = 10
        if action is not None:
            action()

    def _handle_back_button(self):
        if self.button_cooldown > 0:
            return
        if self.current_screen != "game":
            self.back_to_game()
            self.button_cooldown = 10

    def draw(self, surface):
        """Toon het juiste scherm op basis van fase"""
        self.buttons = []
        if self.current_screen == "atm":
            self._draw_atm_screen(surface)
        elif self.current_screen == "shop":
            self._draw_shop_screen(surface)
        elif self.phase == "spin_choice":
            self._draw_spin_choice_screen(surface)
        elif self.phase == "spinning_phase":
            self._draw_spinning_screen(surface)
        elif self.phase == "atm_phase":
            self._draw_atm_phase_screen(surface)
        elif self.phase == "game_over":
            self._draw_game_over_screen(surface)
        self.selected_button = min(self.selected_button, max(0, len(self.buttons) - 1))

    # ── SPIN CHOICE ──────────────────────────────────────────────────────────
    def _draw_spin_choice_screen(self, surface):
        surface.fill(BLACK)
        sf = pygame.font.SysFont("monospace", 14, bold=True)
        lf = pygame.font.SysFont("monospace", 20, bold=True)
        target = self._deadline_cost_for(self.deadline_number)

        dl_txt = lf.render(f"DEADLINE {self.deadline_number}  —  Ronde {self.round_in_deadline}/3", True, GOLD)
        surface.blit(dl_txt, (WIDTH//2 - dl_txt.get_width()//2, 8))

        cost_txt = sf.render(f"Doel ATM: {target}  |  ATM: {self.atm}", True, WHITE)
        surface.blit(cost_txt, (WIDTH//2 - cost_txt.get_width()//2, 34))

        coins_txt = sf.render(f"Munten: {self.coins}  |  Luck: {self.luck}", True, GOLD)
        surface.blit(coins_txt, (WIDTH//2 - coins_txt.get_width()//2, 52))

        info = sf.render("Kies hoeveel spins:", True, WHITE)
        surface.blit(info, (WIDTH//2 - info.get_width()//2, 82))

        c3 = sf.render("3 spins = 15 munten", True, (180, 180, 180))
        surface.blit(c3, (WIDTH//2 - c3.get_width()//2, 100))
        c7 = sf.render("7 spins = 35 munten", True, (180, 180, 180))
        surface.blit(c7, (WIDTH//2 - c7.get_width()//2, 116))

        can_3 = self.coins >= 15
        can_7 = self.coins >= 35
        col_3 = BLUE if can_3 else (60, 60, 60)
        col_7 = GREEN if can_7 else (60, 60, 60)
        self._draw_btn(surface, "3 SPINS", WIDTH//2 - 80, HEIGHT - 100, 70, 40, col_3, (lambda: self.choose_spins(3)) if can_3 else (lambda: None))
        self._draw_btn(surface, "7 SPINS", WIDTH//2 + 10, HEIGHT - 100, 70, 40, col_7, (lambda: self.choose_spins(7)) if can_7 else (lambda: None))
        if not can_3:
            warn = sf.render("Te weinig munten!", True, RED)
            surface.blit(warn, (WIDTH//2 - warn.get_width()//2, HEIGHT - 55))
        self._draw_btn(surface, "SHOP", WIDTH - 55, HEIGHT - 45, 50, 35, GOLD, self.shop)

    # ── SPINNING PHASE ───────────────────────────────────────────────────────
    def _draw_spinning_screen(self, surface):
        surface.fill(BLACK)
        sf = pygame.font.SysFont("monospace", 13, bold=True)
        target = self._deadline_cost_for(self.deadline_number)

        hdr = sf.render(
            f"DL {self.deadline_number}  R{self.round_in_deadline}/3  "
            f"Spins: {self.spins_left}/{self.chosen_spins}  Doel: {target}",
            True, GOLD
        )
        surface.blit(hdr, (5, 5))

        stats_line = sf.render(f"MUNTEN: {self.coins}   ATM: {self.atm}   LUCK: {self.luck}", True, WHITE)
        surface.blit(stats_line, (5, 22))

        grid_margin = 8
        cell_w, cell_h = 50, 50
        start_x = (WIDTH - (GRID_W * (cell_w + grid_margin))) // 2
        start_y = 42

        for c in range(GRID_W):
            for r in range(GRID_H):
                self._draw_cell(surface, self.grid[c][r],
                               start_x + c * (cell_w + grid_margin),
                               start_y + r * (cell_h + grid_margin),
                               cell_w, cell_h, c, r)

        if self.winning_patterns:
            self._draw_winning_lines(surface, start_x, start_y, cell_w, cell_h, grid_margin)

        btn_y = HEIGHT - 45
        spin_color = GREEN if (self.coins >= 5 and self.spins_left > 0 and not self.spinning) else DARK_GRAY
        self._draw_btn(surface, "SPIN", WIDTH//2 - 25, btn_y, 50, 40, spin_color, self.spin)

        if self.total_win_anim > 0:
            win_txt = sf.render(f"WINST: +{self.total_win_anim}", True, GREEN)
            surface.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, btn_y - 36))
            for i, log in enumerate(self.last_wins[-2:]):
                lt = pygame.font.SysFont("monospace", 11, bold=True).render(log[:28], True, WHITE)
                surface.blit(lt, (5, btn_y - 36 + 16 + i * 14))

        if self.spins_left == 0 and not self.spinning:
            done_txt = sf.render("Ronde klaar! Laden...", True, GOLD)
            surface.blit(done_txt, (WIDTH//2 - done_txt.get_width()//2, btn_y - 20))

    # ── ATM PHASE (na 3 rondes) ──────────────────────────────────────────────
    def _draw_atm_phase_screen(self, surface):
        surface.fill(BLACK)
        target = self._deadline_cost_for(self.deadline_number)
        chunk = max(1, int(target * 0.20))
        is_final = self._is_final_round()
        sf  = pygame.font.SysFont("monospace", 13, bold=True)
        mf  = pygame.font.SysFont("monospace", 16, bold=True)

        # ── Header ──
        header_color = RED if is_final else GOLD
        header_txt = f"DEADLINE {self.deadline_number}  —  Ronde {self.round_in_deadline}/3"
        h = mf.render(header_txt, True, header_color)
        surface.blit(h, (WIDTH//2 - h.get_width()//2, 6))

        sub = sf.render("Stort in ATM voor de deadline" if not is_final else "Laatste ronde — betaal nu!", True, WHITE)
        surface.blit(sub, (WIDTH//2 - sub.get_width()//2, 26))

        # ── Progress bar ──
        bar_x, bar_y, bar_w, bar_h = 10, 46, WIDTH - 20, 18
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill = min(1.0, self.atm / target) if target > 0 else 1.0
        fill_color = GREEN if fill >= 1.0 else BLUE
        if fill > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * fill), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        pct_txt = sf.render(f"{int(fill*100)}%  {self.atm}/{target}", True, WHITE)
        surface.blit(pct_txt, (bar_x + bar_w//2 - pct_txt.get_width()//2, bar_y + 2))

        # ── Stat boxes ──
        box_y = 74
        boxes = [
            ("IN HAND",   str(self.coins), GOLD),
            ("IN ATM",    str(self.atm),   BLUE),
            ("NOG NODIG", str(max(0, target - self.atm)), RED if self.atm < target else GREEN),
        ]
        box_w = (WIDTH - 20) // 3
        for i, (label, val, col) in enumerate(boxes):
            bx = 10 + i * (box_w + 0)
            pygame.draw.rect(surface, (25, 25, 35), (bx, box_y, box_w - 4, 44), border_radius=5)
            pygame.draw.rect(surface, col, (bx, box_y, box_w - 4, 44), 1, border_radius=5)
            lbl = pygame.font.SysFont("monospace", 10, bold=True).render(label, True, (160,160,160))
            surface.blit(lbl, (bx + (box_w-4)//2 - lbl.get_width()//2, box_y + 4))
            vt = mf.render(val, True, col)
            surface.blit(vt, (bx + (box_w-4)//2 - vt.get_width()//2, box_y + 20))

        # ── Deposit buttons ──
        btn_y = 130
        chunk_label = f"+{chunk} (20%)"
        self._draw_btn(surface, chunk_label, 10,        btn_y, (WIDTH-24)//2, 40, GREEN, self._atm_deposit_chunk)
        self._draw_btn(surface, "ALLES",    10 + (WIDTH-24)//2 + 4, btn_y, (WIDTH-24)//2, 40, (0,140,80), self._atm_deposit_all)

        # ── Continue / Pay button ──
        if is_final:
            can_pay = self.atm >= target
            pay_col = GREEN if can_pay else (70, 70, 70)
            self._draw_btn(surface, "BETAAL DEADLINE", WIDTH//2 - 100, HEIGHT - 95, 200, 40, pay_col, self._try_next_deadline)
        else:
            # Toon "SKIP RONDE" als het ATM-doel al gehaald is, anders "VOLGENDE RONDE"
            can_skip = self.atm >= target
            skip_label = "⏩ SKIP RONDE" if can_skip else "VOLGENDE RONDE >"
            skip_col   = (180, 120, 0) if can_skip else BLUE
            self._draw_btn(surface, skip_label, WIDTH//2 - 100, HEIGHT - 95, 200, 40, skip_col, self._try_next_deadline)
            if can_skip:
                skip_hint = sf.render("Doel gehaald — sla ronde over!", True, GOLD)
                surface.blit(skip_hint, (WIDTH//2 - skip_hint.get_width()//2, HEIGHT - 130))

        # ── Bottom nav ──
        self._draw_btn(surface, "ATM",  5,          HEIGHT - 46, 60, 36, (0, 80, 160), self.deposit)
        self._draw_btn(surface, "SHOP", WIDTH - 68, HEIGHT - 46, 62, 36, (140,100,0),  self.shop)

    # ── ATM SCREEN (storten sub-scherm) ─────────────────────────────────────
    def _draw_atm_screen(self, surface):
        surface.fill(BLACK)
        target = self._deadline_cost_for(self.deadline_number)
        chunk = max(1, int(target * 0.20))
        sf  = pygame.font.SysFont("monospace", 13, bold=True)
        mf  = pygame.font.SysFont("monospace", 16, bold=True)

        title = mf.render("ATM", True, BLUE)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 8))

        # Progress bar
        bar_x, bar_y, bar_w, bar_h = 10, 30, WIDTH - 20, 16
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill = min(1.0, self.atm / target) if target > 0 else 1.0
        fill_color = GREEN if fill >= 1.0 else BLUE
        if fill > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * fill), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        pt = sf.render(f"{self.atm}/{target}", True, WHITE)
        surface.blit(pt, (bar_x + bar_w//2 - pt.get_width()//2, bar_y + 1))

        # Stat rows
        rows = [
            ("IN HAND",   self.coins,  GOLD),
            ("IN ATM",    self.atm,    BLUE),
            ("DOEL",      target,      RED if self.atm < target else GREEN),
            ("RENTE",     int(self.atm * self.atm_interest_rate), WHITE),
        ]
        for i, (label, val, col) in enumerate(rows):
            row_y = 56 + i * 26
            lbl = sf.render(label, True, (160,160,160))
            surface.blit(lbl, (14, row_y))
            vt = sf.render(str(val), True, col)
            surface.blit(vt, (WIDTH - 14 - vt.get_width(), row_y))
            pygame.draw.line(surface, (40,40,40), (14, row_y+18), (WIDTH-14, row_y+18))

        chunk_label = f"+{chunk} (20%)"
        self._draw_btn(surface, chunk_label, 10,        162, (WIDTH-24)//2, 32, GREEN, self._atm_deposit_chunk)
        self._draw_btn(surface, "ALLES",    10+(WIDTH-24)//2+4, 162, (WIDTH-24)//2, 32, (0,140,80), self._atm_deposit_all)
        self._draw_btn(surface, "BACK", WIDTH//2 - 28, HEIGHT - 46, 56, 36, WHITE, self.back_to_game)

    # ── SHOP SCREEN ──────────────────────────────────────────────────────────
    def _draw_shop_screen(self, surface):
        surface.fill(BLACK)
        small_font = pygame.font.SysFont("monospace", 12, bold=True)

        title = pygame.font.SysFont("monospace", 18, bold=True).render("SHOP", True, GOLD)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 5))

        coins_txt = small_font.render(f"MUNTEN: {self.coins}", True, GOLD)
        surface.blit(coins_txt, (5, 25))

        total_owned = sum(len(items) for items in self.purchased_items.values())
        owned_txt = small_font.render(f"Items: {total_owned}", True, GREEN)
        surface.blit(owned_txt, (WIDTH - 80, 25))

        y_offset = 45
        item_count = 0
        max_items = 10

        for category, items_dict in SHOP_ITEMS.items():
            for item_name, item_data in items_dict.items():
                if item_count >= max_items:
                    break
                purchased = item_name in self.purchased_items.get(category, set())
                cost = item_data["cost"]
                status = "✓" if purchased else f"{cost}g"
                label = f"{item_name[:12]} ({status})"
                btn_color = GREEN if purchased else (60, 60, 60)
                _name, _cost, _cat = item_name, cost, category
                action = (lambda n, c, t: lambda: self._buy_item(n, c, t))(_name, _cost, _cat)
                self._draw_btn(surface, label, 5, y_offset, WIDTH - 10, 28, btn_color, action)
                y_offset += 32
                item_count += 1
            if item_count >= max_items:
                break

        self._draw_btn(surface, "BACK", WIDTH//2 - 25, HEIGHT - 45, 50, 40, WHITE, self.back_to_game)

    # ── GAME OVER ────────────────────────────────────────────────────────────
    def _draw_game_over_screen(self, surface):
        surface.fill(BLACK)
        lf = pygame.font.SysFont("monospace", 22, bold=True)
        sf = pygame.font.SysFont("monospace", 14, bold=True)

        go = lf.render("GAME OVER", True, RED)
        surface.blit(go, (WIDTH//2 - go.get_width()//2, HEIGHT//2 - 60))

        for i, msg in enumerate(self.last_wins):
            t = sf.render(msg[:28], True, WHITE)
            surface.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 20 + i * 22))

        self._draw_btn(surface, "OPNIEUW", WIDTH//2 - 40, HEIGHT - 60, 80, 40, GREEN, self.reset_game)

    def _draw_cell(self, surface, name, x, y, w, h, c, r):
        color = SYMBOLS[name]["color"]
        icon  = SYMBOLS[name].get("icon", name[:2].upper())
        
        # Check of deze cell wint
        is_winning = (c, r) in self.winning_coords
        
        # Knippereffect
        if is_winning and (self.flash_counter // 5) % 2 == 0:
            pygame.draw.rect(surface, (100, 100, 100), (x, y, w, h), border_radius=3)
            pygame.draw.rect(surface, WHITE, (x, y, w, h), 2, border_radius=3)
        else:
            pygame.draw.rect(surface, DARK_GRAY, (x, y, w, h), border_radius=3)
            pygame.draw.rect(surface, color, (x, y, w, h), 1, border_radius=3)
        
        # Teken icoon — probeer emoji, val terug op tekst
        cell_font = pygame.font.SysFont("monospace", max(8, w // 6), bold=True)
        try:
            emoji_font = pygame.font.SysFont("segoeuiemoji", max(10, w // 4))
            txt = emoji_font.render(icon, True, color)
        except Exception:
            txt = cell_font.render(icon, True, color)
        surface.blit(txt, (x + (w - txt.get_width())//2, y + (h - txt.get_height())//2))
    
    def _draw_winning_lines(self, surface, start_x, start_y, cell_w, cell_h, grid_margin):
        """Teken lijnen door winning patterns"""
        for pattern in self.winning_patterns:
            coords = pattern["coords"]
            if len(coords) < 2:
                continue
            
            # Calculate centers van elke winning cell
            centers = []
            for c, r in coords:
                center_x = start_x + c * (cell_w + grid_margin) + cell_w // 2
                center_y = start_y + r * (cell_h + grid_margin) + cell_h // 2
                centers.append((center_x, center_y))
            
            # Teken lijn door alle centers
            for i in range(len(centers) - 1):
                pygame.draw.line(surface, WHITE, centers[i], centers[i+1], 3)
    
    def _draw_btn(self, surface, text, x, y, w, h, color, action):
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        rect = pygame.Rect(x, y, w, h)

        btn_idx = len(self.buttons)
        self.buttons.append(action)

        is_selected = btn_idx == self.selected_button
        is_hover = rect.collidepoint(mouse)

        if is_selected:
            bg = WHITE
            txt_color = BLACK
        elif is_hover:
            bg = WHITE
            txt_color = BLACK
        else:
            bg = color
            txt_color = WHITE

        pygame.draw.rect(surface, bg, rect, border_radius=5)

        btn_font = pygame.font.SysFont("monospace", 11, bold=True) if w < 80 else self.font
        t = btn_font.render(text, True, txt_color)

        text_rect = t.get_rect(center=(x + w // 2, y + h // 2))
        surface.blit(t, text_rect)

        if is_selected and is_hover:
            pygame.draw.rect(surface, (100, 200, 100), rect, 3, border_radius=5)
        elif is_selected:
            pygame.draw.rect(surface, GOLD, rect, 3, border_radius=5)

        if is_hover and click[0] and self.button_cooldown <= 0:
            self.button_cooldown = 10
            if action is not None:
                action()
