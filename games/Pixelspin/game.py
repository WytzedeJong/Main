import pygame
import random
import json
import os
import copy

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

MODIFIER_COLORS = {
    "golden": GOLD,
    "repetition": (170, 120, 255),
    "chain": (80, 210, 255),
    "token": (255, 140, 40),
    "ticket": (255, 200, 100),
    "battery": (80, 255, 120),
}
MODIFIER_LABELS = {
    "golden": "GOLD",
    "repetition": "REP",
    "chain": "CHAIN",
    "token": "TOKEN",
    "ticket": "TICKET",
    "battery": "BATT",
}
MODIFIER_DRAW_PRIORITY = ("golden", "ticket", "token", "battery", "chain", "repetition")

# Symbolen & Hun Basiswaarde — afgestemd op de foto (Φ-waarden en kansen)
SYMBOLS = {
    "Citroen":  {"color": (255, 230,  40), "value": 2,  "weight": 0.2153, "icon": "🍋"},
    "Kers":     {"color": (220,  40,  40), "value": 2,  "weight": 0.2153, "icon": "🍒"},
    "Klaver":   {"color": ( 30, 200,  80), "value": 3,  "weight": 0.1654, "icon": "🍀"},
    "Diamant":  {"color": ( 80, 210, 255), "value": 5,  "weight": 0.1321, "icon": "💎"},
    "Bell":     {"color": (240, 190,  40), "value": 5,  "weight": 0.0999, "icon": "🔔"},
    "Chest":    {"color": (170, 110,  45), "value": 5,  "weight": 0.0888, "icon": "🧰"},
    "Zeven":    {"color": (255,  20,  20), "value": 7,  "weight": 0.0832, "icon": "7"},
}

# Runtime gewichten — worden aangepast door shop-upgrades
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

BASE_PATTERNS = load_patterns()
PATTERNS = copy.deepcopy(BASE_PATTERNS)

# Load shop items from JSON
def load_shop_items():
    shop_path = os.path.join(os.path.dirname(__file__), "shop_items.json")
    try:
        with open(shop_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"charms": {}, "powerups": {}, "upgrades": {}}

SHOP_ITEMS = load_shop_items()
SHOP_ROLL_SIZE = 4            
SHOP_REFRESH_COST = 5         
REPEATABLE_SHOP_ITEMS = {"Coin Doubler", "Extra Spins"}

# --- PHONE CALL MECHANIC DATA ---
PHONE_CALLS = {
    "Normal": [
        {"name": "Please don't throw my stuff away!", "desc": "Max Charms +1 permanent.", "type": "charm_space"},
        {"name": "I can't quit now!", "desc": "Jackpot waarde x2.", "type": "double_jackpot"},
        {"name": "Can I borrow some green?", "desc": "+5 Tickets.", "type": "plus_5_tickets"},
        {"name": "Can I eat something?", "desc": "Charms in shop -2 Munten korting (1x).", "type": "discount_charms"},
        {"name": "Can you give me some Energy Drinks?", "desc": "Red Button charms zijn opnieuw bruikbaar.", "type": "restore_charges"},
        {"name": "Fruit market: {symbol}!", "desc": "+1 kans-gewicht voor {symbol}.", "type": "plus_weight_symbol", "symbols": ["Kers", "Citroen", "Klaver"]},
        {"name": "Treasure market: {symbol}!", "desc": "+1 kans-gewicht voor {symbol}.", "type": "plus_weight_symbol", "symbols": ["Chest", "Bell", "Diamant"]},
        {"name": "Lucky market!", "desc": "+1 kans-gewicht voor Zeven.", "type": "plus_weight_seven"},
        {"name": "Fruit supplements!", "desc": "Verdubbel Kers, Citroen en Klaver.", "type": "double_fruit_clover"},
        {"name": "Heavy supplements!", "desc": "Verdubbel Chest, Bell en Diamant.", "type": "double_chest_bell_diamond"},
        {"name": "Lucky number!", "desc": "Zeven krijgt 3x zijn basiswaarde.", "type": "triple_seven"},
        {"name": "I'm thinking of some strategies!", "desc": "Verhoog de waarde van kleine patronen.", "type": "buff_small_patterns"}
    ],
    "Evil": [
        {"name": "I like Cryptic values!", "desc": "Verdubbel Tickets. Munten naar 0.", "type": "evil_cryptic"},
        {"name": "I don't care about the price!", "desc": "Shop deels gratis, maar Tickets naar 0.", "type": "evil_free_charms"},
        {"name": "My head hurts!", "desc": "Verdubbel Kers/Citroen/Klaver en Chest/Bell/Diamant.", "type": "evil_head_hurts"},
        {"name": "Give me back my money!", "desc": "Verdubbel munten. Tickets naar 0.", "type": "evil_money"},
        {"name": "Mouldy fruit...", "desc": "Halveer spawnkans van Kers, Citroen en Klaver.", "type": "evil_mould_fruit_clover"},
        {"name": "Rusty treasure...", "desc": "Halveer spawnkans van Chest, Bell en Diamant.", "type": "evil_mould_chest_bell_diamond"},
        {"name": "Broken seven...", "desc": "Halveer spawnkans van Zeven.", "type": "evil_mould_seven"}
    ]
}

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
        global PATTERNS
        PATTERNS = copy.deepcopy(BASE_PATTERNS)
        for sym in SYMBOLS:
            _symbol_weight_bonus[sym] = 0.0
            _symbol_value_bonus[sym] = 0

        self.show_info_for = None
        self.coins = 50
        self.tickets = 5
        self.atm = 0
        self.luck = 0
        self.spin_count = 0
        self.atm_interest_rate = 0.05
        self.pattern_chance_bonus = 0.0
        self.coin_doubler_spins_left = 0
        self.extra_spins_pending = 0
        self.free_restock_count = 0
        self.shop_refresh_cost = SHOP_REFRESH_COST
        self.phone_rerolls = 0
        self.phone_skips = 0
        self.consecutive_misses = 0
        self.next_spin_luck_bonus = 0
        self.charm_trigger_counts = {}
        self.pending_charm_activations = {}
        self.round_symbol_multiplier_bonus = 0.0
        self.round_pattern_multiplier_bonus = 0.0
        self.round_repetition_bonus_by_symbol = {}

        # Deadline / ronde systeem
        self.deadline_number = 1
        self.round_in_deadline = 1
        self.spins_left = 0
        self.chosen_spins = 0

        # Actieve variabelen voor Shop & Phone Call mechanics
        self.max_charms = 7
        self.charm_discount_active = False
        self.free_charms_active = False
        self.active_phone_options = []
        
        # Actieve Usables en Buffs (Red Button systeem)
        self.active_round_buffs = set()
        self.used_usables_this_round = set()

        # Fase: "spin_choice", "spinning_phase", "between_rounds", "atm_phase", "phone_call"
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
        self.shop_scroll_y = 0
        self.shop_items_for_phase = []
        self.repeatable_items_bought_this_round = set()

        self.winning_coords = []
        self.winning_patterns = []
        self.modifier_coords = {}
        self.flash_counter = 0
        self.purchased_items = {
            "charms": set(),
            "powerups": set(),
            "upgrades": set()
        }

        self._roll_shop_items()

    # Deadline kosten tabel
    DEADLINE_COSTS = {
        1: 75, 2: 200, 3: 666, 4: 2222, 5: 12500,
        6: 33333, 7: 66666, 8: 200000, 9: 1000000, 10: 6000000,
        11: 144000000, 12: 13824000000, 13: 21234000000000,
        14: 203840000000000000, 15: 10821000000000000000000,
        16: 2956000000000000000000000000,
        17: 1559400000000000000000000000000000000000,
        18: 25028000000000000000000000000000000000000000000000000000,
        19: 1193000000000000000000000000000000000000000000000000000000000000000000000,
        20: 16585000000000000000000000000000000000000000000000000000000000000000000000000000000000000,
    }

    def _deadline_cost_for(self, deadline_num):
        if deadline_num in self.DEADLINE_COSTS:
            return self.DEADLINE_COSTS[deadline_num]
        return self.DEADLINE_COSTS[20]
        
    def generate_grid(self):
        grid = []
        if self.luck >= 15:
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
            self._apply_luck_patterns(grid)
        return grid

    def _luck_pattern_count(self):
        if self.luck <= 0:
            return 1 if random.random() < self.pattern_chance_bonus else 0

        pattern_count = min(3, self.luck // 5)
        if random.random() < (self.luck % 5) / 5:
            pattern_count += 1
        if random.random() < self.pattern_chance_bonus:
            pattern_count += 1
        return max(1, min(3, pattern_count))

    def _luck_symbol_choice(self):
        symbols = list(SYMBOLS.keys())
        weights = []
        for sym in symbols:
            value_bias = max(1, get_effective_value(sym)) ** (1 + self.luck / 10)
            weights.append(get_effective_weight(sym) * value_bias)
        return random.choices(symbols, weights=weights, k=1)[0]

    def _coords_for_pattern(self, pattern):
        pattern_type = pattern["type"]
        length = pattern.get("length", 3)

        if pattern_type == "horizontal":
            row = random.randrange(GRID_H)
            start_col = random.randrange(0, GRID_W - length + 1)
            return [(start_col + i, row) for i in range(length)]
        if pattern_type == "vertical":
            col = random.randrange(GRID_W)
            return [(col, row) for row in range(GRID_H)]
        if pattern_type == "diagonal":
            start_col = random.randrange(0, GRID_W - 2)
            return [(start_col + i, i) for i in range(3)]
        if pattern_type == "zigzag":
            start_col = random.randrange(0, GRID_W - 2)
            return [(start_col, GRID_H - 1), (start_col + 1, GRID_H - 2), (start_col + 2, GRID_H - 3)]
        if pattern_type == "zagzag":
            start_col = random.randrange(0, GRID_W - 2)
            return [(start_col, 0), (start_col + 1, 1), (start_col + 2, 2)]
        if pattern_type == "top_row":
            return [(col, 0) for col in range(GRID_W)]
        if pattern_type == "bottom_row":
            return [(col, GRID_H - 1) for col in range(GRID_W)]
        if pattern_type == "eye":
            return [(1, 0), (2, 0), (3, 0), (1, 2), (2, 2), (3, 2), (1, 1), (3, 1)]
        return []

    def _apply_luck_patterns(self, grid):
        pattern_count = self._luck_pattern_count()
        if pattern_count == 0:
            return

        max_multiplier = 1 + self.luck * 0.6
        eligible_patterns = [
            p for p in PATTERNS
            if p["type"] != "jackpot" and p["multiplier"] <= max_multiplier
        ]
        if not eligible_patterns:
            return

        weights = [p["multiplier"] ** (1 + self.luck / 10) for p in eligible_patterns]
        for pattern in random.choices(eligible_patterns, weights=weights, k=pattern_count):
            symbol = self._luck_symbol_choice()
            for c, r in self._coords_for_pattern(pattern):
                grid[c][r] = symbol
    
    def weighted_choice(self, symbols):
        total_weight = sum(get_effective_weight(sym) for sym in symbols)
        choice = random.uniform(0, total_weight)
        current = 0
        for sym in symbols:
            current += get_effective_weight(sym)
            if choice <= current:
                return sym
        return list(symbols.keys())[-1]

    def _award_tickets(self, spins_chosen):
        if spins_chosen == 3:
            self.tickets += 2
        elif spins_chosen == 7:
            self.tickets += 1

    def _spin_cost_for(self, amount):
        deadline_target = self._deadline_cost_for(self.deadline_number)
        if amount == 1:
            return 0
        if amount == 3:
            return int(deadline_target * 0.05)
        if amount == 7:
            return int(deadline_target * 0.10)
        return 0

    def _can_take_emergency_spin(self):
        return self.coins < min(self._spin_cost_for(3), self._spin_cost_for(7))

    def choose_spins(self, amount):
        spin_cost = self._spin_cost_for(amount)
        if self.coins < spin_cost:
            self.last_wins = [f"Niet genoeg munten: {spin_cost} nodig."]
            return

        bonus_spins = self.extra_spins_pending
        if "Cat Food" in self.purchased_items.get("charms", set()):
            bonus_spins += SHOP_ITEMS["charms"]["Cat Food"].get("extra_spins_per_round", 0)

        total_spins = amount + bonus_spins
        self.extra_spins_pending = 0
        self.chosen_spins = total_spins
        self.spins_left = total_spins

        self.coins -= spin_cost
        
        self.phase = "spinning_phase"
        self.selected_button = 0
        self.last_wins = []
        self.total_win_anim = 0
        self.winning_coords = []
        self.winning_patterns = []
        self.modifier_coords = {}
        self.grid = self.generate_grid()
        self._award_tickets(amount)

    def spin(self):
        if self.phase != "spinning_phase":
            return
        if not self.spinning and self.spins_left > 0:
            is_last_spin = self.spins_left == 1
            self.spins_left -= 1
            self.spin_count += 1
            self.spinning = True
            self.spin_timer = 13
            self.last_wins = []
            self.total_win_anim = 0
            self.winning_coords = [] 
            self.winning_patterns = [] 
            self.modifier_coords = {}
            
            self.luck = 0
            self._apply_all_luck_bonuses()
            self.luck += self.next_spin_luck_bonus
            self.next_spin_luck_bonus = 0
            self._apply_event_luck_bonuses(is_last_spin)
            
            # Pas random_trigger Usables / Charms toe vóór de spin
            self._apply_random_trigger_charms()

    def _owned_charms(self):
        return self.purchased_items.get("charms", set())

    def _charm_data(self, charm_name):
        return SHOP_ITEMS.get("charms", {}).get(charm_name, {})

    def _record_charm_activation(self, charm_name, count=1):
        if count <= 0:
            return
        if not hasattr(self, "pending_charm_activations"):
            self.pending_charm_activations = {}
        self.pending_charm_activations[charm_name] = (
            self.pending_charm_activations.get(charm_name, 0) + count
        )

    def _format_charm_activation(self, charm_name, count):
        return f"{charm_name} x{count} geactiveerd"

    def _charm_activation_messages(self, activations):
        return [
            self._format_charm_activation(charm_name, count)
            for charm_name, count in activations.items()
            if count > 0
        ]

    def _consume_charm_activation_messages(self):
        messages = self._charm_activation_messages(
            getattr(self, "pending_charm_activations", {})
        )
        self.pending_charm_activations = {}
        return messages

    def _collect_patterns_to_payout(self):
        candidate_hits = []

        for sym_name in SYMBOLS.keys():
            for p in PATTERNS:
                pattern_coords_list = self.find_pattern_coordinates(sym_name, p["type"])
                for match_coords in pattern_coords_list:
                    required_length = p.get("length")
                    if required_length is not None and len(match_coords) < required_length:
                        continue
                    candidate_hits.append((p, sym_name, match_coords))

        candidate_hits.sort(key=lambda x: x[0]["multiplier"], reverse=True)

        seen_pattern_coords = set()
        patterns_to_payout = []

        for p, sym_name, match_coords in candidate_hits:
            key = (p["name"], sym_name, frozenset(match_coords))
            if key in seen_pattern_coords:
                continue

            seen_pattern_coords.add(key)
            patterns_to_payout.append((p, sym_name, match_coords))

        return patterns_to_payout

    def _apply_event_luck_bonuses(self, is_last_spin):
        for charm in self._owned_charms():
            charm_data = self._charm_data(charm)
            if charm_data.get("category") != "event_trigger":
                continue
            trigger = charm_data.get("trigger")
            if trigger == "on_last_spin" and is_last_spin:
                self.luck += charm_data.get("luck_bonus", 0)
                self._record_charm_activation(charm)
            elif trigger == "every_x_spins":
                interval = charm_data.get("spin_interval", 0)
                if interval > 0 and self.spin_count % interval == 0:
                    self.luck += charm_data.get("luck_bonus", 0)
                    self._record_charm_activation(charm)

    def _apply_random_trigger_charms(self):
        for charm in list(self._owned_charms()):
            charm_data = self._charm_data(charm)
            if charm_data.get("category") != "random_trigger":
                continue
            if random.random() > charm_data.get("trigger_chance", 0):
                continue

            self._record_charm_activation(charm)
            self.luck += charm_data.get("luck_bonus", 0)
            bonus_spins = charm_data.get("extra_spins", 0)
            if bonus_spins:
                self.spins_left += bonus_spins
                self.chosen_spins += bonus_spins

            max_uses = charm_data.get("max_uses")
            if max_uses is not None:
                self.charm_trigger_counts[charm] = self.charm_trigger_counts.get(charm, 0) + 1
                if self.charm_trigger_counts[charm] >= max_uses:
                    self.purchased_items["charms"].discard(charm)
                    self._remove_item_effect(charm, "charms")

    def _grid_has_666(self):
        for r in range(GRID_H):
            run = 0
            for c in range(GRID_W):
                run = run + 1 if self.grid[c][r] == "Zeven" else 0
                if run >= 3:
                    return True
        return False

    def _maybe_force_666(self):
        chance = 0.0
        for charm in self._owned_charms():
            chance += self._charm_data(charm).get("666_chance_bonus", 0.0)
        if chance <= 0 or random.random() >= min(1.0, chance):
            return
        row = random.randrange(GRID_H)
        start_col = random.randrange(0, GRID_W - 2)
        for offset in range(3):
            self.grid[start_col + offset][row] = "Zeven"

    def _modifier_chances_for_symbol(self, sym_name):
        chances = {
            "repetition": 0.0,
            "battery": 0.0,
            "chain": 0.0,
            "golden": 0.0,
            "token": 0.0,
            "ticket": 0.0,
        }

        def add_chance(key, targets, chance):
            if isinstance(targets, str):
                targets = [targets]
            if "ALL" in targets or sym_name in targets:
                chances[key] += chance

        simple_keys = {
            "repetition_chance": "repetition",
            "battery_chance": "battery",
            "chain_chance": "chain",
            "golden_chance": "golden",
            "token_chance": "token",
            "ticket_chance": "ticket",
        }
        for charm in self._owned_charms():
            charm_data = self._charm_data(charm)
            category = charm_data.get("category")
            if category == "modifier_chance":
                targets = charm_data.get("target_symbol", [])
                for json_key, chance_key in simple_keys.items():
                    if json_key in charm_data:
                        add_chance(chance_key, targets, charm_data[json_key])
            elif category == "modifier_chance_complex":
                for chance_key in chances:
                    target_data = charm_data.get(f"{chance_key}_targets")
                    if target_data:
                        add_chance(chance_key, target_data.get("symbols", []), target_data.get("chance", 0))
        return chances

    def _roll_modifier_hits(self, sym_name):
        hits = {}
        for key, chance in self._modifier_chances_for_symbol(sym_name).items():
            hits[key] = random.random() < min(1.0, chance)
        return hits

    def _recharge_usables(self, target="all"):
        used = list(self.used_usables_this_round)
        if not used:
            return 0
        if target == "random":
            used = [random.choice(used)]
        for charm in used:
            self.used_usables_this_round.discard(charm)
        return len(used)

    def _apply_pattern_event_charms(self, patterns_to_payout, total_payout, found_any):
        payout = total_payout
        pattern_count = len(patterns_to_payout)
        max_length = max((len(coords) for _, _, coords in patterns_to_payout), default=0)
        symbols_scored = {sym for _, sym, _ in patterns_to_payout}
        saw_666 = self._grid_has_666()

        if saw_666:
            found_any.append("666 gezien!")

        for charm in list(self._owned_charms()):
            charm_data = self._charm_data(charm)
            if charm_data.get("category") != "event_trigger":
                continue

            trigger = charm_data.get("trigger")
            targets = charm_data.get("target_symbol", [])
            if isinstance(targets, str):
                targets = [targets]

            should_trigger = False
            if trigger == "on_pattern_match":
                should_trigger = all(target in symbols_scored for target in targets)
            elif trigger == "on_patterns_count":
                should_trigger = pattern_count >= charm_data.get("condition_count", 0)
            elif trigger == "on_pattern_length":
                should_trigger = max_length >= charm_data.get("condition_length", 0)
            elif trigger == "on_single_pattern":
                should_trigger = pattern_count == 1 and (not targets or patterns_to_payout[0][1] in targets)
            elif trigger == "on_consecutive_losses":
                should_trigger = self.consecutive_misses >= charm_data.get("condition_losses", 0)
            elif trigger == "on_666":
                should_trigger = saw_666

            if not should_trigger:
                continue

            activated = False
            if "restock_bonus" in charm_data:
                self.free_restock_count += charm_data["restock_bonus"]
                activated = True
                found_any.append(f"{charm}: +{charm_data['restock_bonus']} restocks")
            if "luck_bonus" in charm_data:
                self.next_spin_luck_bonus += charm_data["luck_bonus"]
                activated = True
                found_any.append(f"{charm}: +{charm_data['luck_bonus']} Luck volgende spin")
            if "pattern_multiplier_temp" in charm_data:
                self.round_pattern_multiplier_bonus += charm_data["pattern_multiplier_temp"]
                activated = True
                found_any.append(f"{charm}: patronen sterker deze ronde")
            if "symbol_multiplier_temp" in charm_data:
                self.round_symbol_multiplier_bonus += charm_data["symbol_multiplier_temp"]
                activated = True
                found_any.append(f"{charm}: symbolen sterker deze ronde")
            if "repetition_temp_bonus" in charm_data:
                affected = targets if targets and "ALL" not in targets else list(SYMBOLS.keys())
                for sym in affected:
                    self.round_repetition_bonus_by_symbol[sym] = (
                        self.round_repetition_bonus_by_symbol.get(sym, 0)
                        + charm_data["repetition_temp_bonus"]
                    )
                activated = True
                found_any.append(f"{charm}: extra triggers deze ronde")
            if "payout_interest_multiplier" in charm_data:
                bonus = int(self.atm * self.atm_interest_rate * charm_data["payout_interest_multiplier"])
                payout += bonus
                activated = True
                found_any.append(f"{charm}: rente bonus +{bonus}")
            if charm_data.get("permanent_value_increase_by_base"):
                affected = targets if targets and "ALL" not in targets else list(SYMBOLS.keys())
                for sym in affected:
                    if sym in SYMBOLS:
                        _symbol_value_bonus[sym] += SYMBOLS[sym]["value"]
                activated = True
                found_any.append(f"{charm}: symboolwaardes permanent omhoog")
            if "recharge_amount" in charm_data:
                recharged = self._recharge_usables(charm_data.get("recharge_target", "all"))
                if recharged:
                    activated = True
                    found_any.append(f"{charm}: {recharged} Red Button charm(s) herladen")

            if trigger == "on_single_pattern" and charm == "Necklace":
                p, sym_name, coords = patterns_to_payout[0]
                base_win = int(round(get_effective_value(sym_name) * len(coords) * p["multiplier"]))
                extra = base_win + int(base_win * charm_data.get("final_trigger_multiplier", 1.0))
                payout += extra
                activated = True
                found_any.append(f"Necklace extra triggers: +{extra}")

            if activated:
                self._record_charm_activation(charm)

        self._event_adjusted_payout = payout

    def _apply_miss_event_charms(self, found_any):
        for charm in list(self._owned_charms()):
            charm_data = self._charm_data(charm)
            if (
                charm_data.get("category") != "event_trigger"
                or charm_data.get("trigger") != "on_consecutive_losses"
                or self.consecutive_misses < charm_data.get("condition_losses", 0)
            ):
                continue

            self._record_charm_activation(charm)
            targets = charm_data.get("target_symbol", [])
            if isinstance(targets, str):
                targets = [targets]

            if charm_data.get("permanent_value_increase_by_base"):
                affected = targets if targets and "ALL" not in targets else list(SYMBOLS.keys())
                for sym in affected:
                    if sym in SYMBOLS:
                        _symbol_value_bonus[sym] += SYMBOLS[sym]["value"]
                found_any.append(f"{charm}: symboolwaardes permanent omhoog")

            if "recharge_amount" in charm_data:
                recharged = self._recharge_usables(charm_data.get("recharge_target", "all"))
                if recharged:
                    found_any.append(f"{charm}: {recharged} Red Button charm(s) herladen")

    def find_pattern_coordinates(self, sym_name, pattern_type):
        coords = []
        found_positions = set()
        
        if pattern_type == "horizontal":
            for r in range(GRID_H):
                c = 0
                while c < GRID_W:
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
                        c = temp_c
                    else:
                        c += 1
        
        elif pattern_type == "vertical":
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
                        r = temp_r
                    else:
                        r += 1
        
        elif pattern_type == "diagonal":
            for c in range(GRID_W - 2):
                for r in range(GRID_H - 2):
                    if (self.grid[c][r] == sym_name and 
                        self.grid[c+1][r+1] == sym_name and 
                        self.grid[c+2][r+2] == sym_name):
                        coords.append([(c, r), (c+1, r+1), (c+2, r+2)])
        
        elif pattern_type == "bottom_row":
            if all(self.grid[c][GRID_H-1] == sym_name for c in range(GRID_W)):
                coords.append([(c, GRID_H-1) for c in range(GRID_W)])
        
        elif pattern_type == "top_row":
            if all(self.grid[c][0] == sym_name for c in range(GRID_W)):
                coords.append([(c, 0) for c in range(GRID_W)])
        
        elif pattern_type == "eye":
            eye_coords = [(1,0), (2,0), (3,0), (1,2), (2,2), (3,2), (1,1), (3,1)]
            if all(self.grid[c][r] == sym_name for c, r in eye_coords):
                coords.append(eye_coords)
        
        elif pattern_type == "zigzag":
            for c in range(GRID_W - 2):
                if (self.grid[c][GRID_H-1] == sym_name and
                    self.grid[c+1][GRID_H-2] == sym_name and
                    self.grid[c+2][GRID_H-3] == sym_name):
                    coords.append([(c, GRID_H-1), (c+1, GRID_H-2), (c+2, GRID_H-3)])
        
        elif pattern_type == "zagzag":
            for c in range(GRID_W - 2):
                if (self.grid[c][0] == sym_name and
                    self.grid[c+1][1] == sym_name and
                    self.grid[c+2][2] == sym_name):
                    coords.append([(c, 0), (c+1, 1), (c+2, 2)])
        
        elif pattern_type == "jackpot":
            if all(self.grid[c][r] == sym_name for c in range(GRID_W) for r in range(GRID_H)):
                coords.append([(c, r) for c in range(GRID_W) for r in range(GRID_H)])
        
        return coords

    def check_all_patterns(self):
        total_payout = 0
        found_any = []
        self.winning_coords = []
        self.winning_patterns = []
        self.modifier_coords = {}

        patterns_to_payout = self._collect_patterns_to_payout()

        # --- SINGLE PATTERN MECHANICS ---
        if len(patterns_to_payout) == 1:
            sp_sym_name = patterns_to_payout[0][1]
            if "Pain Killers" in self.purchased_items.get("charms", set()):
                # Zoek symbool met hoogste base value
                highest_val_sym = max(SYMBOLS.keys(), key=lambda s: get_effective_value(s))
                # Vervang het gewonnen symbool intern voor deze berekening
                patterns_to_payout[0] = (patterns_to_payout[0][0], highest_val_sym, patterns_to_payout[0][2])
                self._record_charm_activation("Pain Killers")

            if "Halo" in self.purchased_items.get("charms", set()):
                self._record_charm_activation("Halo")
                found_any.append("Halo transformeert omliggende vakjes!")
                for c, r in patterns_to_payout[0][2]:
                    for dc in (-1, 0, 1):
                        for dr in (-1, 0, 1):
                            nc, nr = c + dc, r + dr
                            if 0 <= nc < GRID_W and 0 <= nr < GRID_H:
                                self.grid[nc][nr] = sp_sym_name
                patterns_to_payout = self._collect_patterns_to_payout()

        # --- DYNAMIC SCALING MECHANICS (TICKETS/RESTOCKS/PHONE) ---
        extra_pattern_mult = self.round_pattern_multiplier_bonus
        extra_symbol_mult = self.round_symbol_multiplier_bonus
        for charm in self.purchased_items.get("charms", set()):
            charm_data = SHOP_ITEMS.get("charms", {}).get(charm, {})
            if charm_data.get("category") == "passive_boost":
                extra_pattern_mult += charm_data.get("pattern_multiplier_bonus", 0.0)
                extra_symbol_mult += charm_data.get("symbol_multiplier_bonus", 0.0)
            if charm_data.get("category") == "dynamic_scaling":
                if charm_data.get("scale_type") == "tickets":
                    stacks = self.tickets // charm_data.get("scale_ratio", 1)
                elif charm_data.get("scale_type") == "restocks":
                    stacks = self.free_restock_count // charm_data.get("scale_ratio", 1)
                elif charm_data.get("scale_type") == "phone_rerolls":
                    stacks = self.phone_rerolls // charm_data.get("scale_ratio", 1)
                elif charm_data.get("scale_type") == "phone_skips":
                    stacks = self.phone_skips // charm_data.get("scale_ratio", 1)
                else:
                    stacks = 0

                if "pattern_multiplier_bonus" in charm_data:
                    extra_pattern_mult += stacks * charm_data["pattern_multiplier_bonus"]
                if "symbol_multiplier_bonus" in charm_data:
                    extra_symbol_mult += stacks * charm_data["symbol_multiplier_bonus"]

        # Loop over geldige patronen
        for p, sym_name, match_coords in patterns_to_payout:
            symbol_base = get_effective_value(sym_name)
            symbol_multiplier = 1.0 + extra_symbol_mult
            pattern_multiplier = p["multiplier"] + extra_pattern_mult
            symbol_count = len(match_coords)
            repetitions = 1
            modifier_hits = self._roll_modifier_hits(sym_name)

            if "Big Mushroom" in self.purchased_items.get("charms", set()) and len(patterns_to_payout) >= 3:
                symbol_multiplier *= 2.0
                self._record_charm_activation("Big Mushroom")

            if "Pentacle" in self.purchased_items.get("charms", set()) and len(patterns_to_payout) >= 5:
                pattern_multiplier *= 1.5
                self._record_charm_activation("Pentacle")

            for charm in self._owned_charms():
                charm_data = self._charm_data(charm)
                targets = charm_data.get("target_symbol", [])
                if isinstance(targets, str):
                    targets = [targets]
                target_matches = "ALL" in targets or sym_name in targets
                if charm_data.get("category") == "pattern_modifier" and target_matches:
                    repetition_bonus = charm_data.get("repetition_bonus", 0)
                    repetitions += repetition_bonus
                    self._record_charm_activation(charm, repetition_bonus)

            repetitions += self.round_repetition_bonus_by_symbol.get(sym_name, 0)

            if modifier_hits["repetition"]:
                repetitions += 1
                found_any.append("Repetition modifier: +1 trigger")
            if modifier_hits["chain"]:
                repetitions += 1
                found_any.append("Chain modifier: +1 trigger")
            if modifier_hits["golden"]:
                value_bonus = SYMBOLS[sym_name]["value"]
                _symbol_value_bonus[sym_name] += value_bonus
                symbol_base += value_bonus
                found_any.append(f"Golden modifier: {sym_name} waarde +{value_bonus}")

            effective_symbol_value = symbol_base * symbol_multiplier
            win = int(round(effective_symbol_value * symbol_count * pattern_multiplier)) * repetitions
            total_payout += win
            if modifier_hits["token"]:
                token_bonus = symbol_count
                total_payout += token_bonus
                found_any.append(f"Token bonus: +{token_bonus}")
            if modifier_hits["ticket"]:
                self.tickets += 1
                found_any.append("Ticket modifier: +1 Ticket")
            if modifier_hits["battery"]:
                self.next_spin_luck_bonus += 1
                found_any.append("Battery modifier: +1 Luck volgende spin")
            found_any.append(
                f"{p['name']} ({sym_name} x{symbol_count}): "
                f"{effective_symbol_value:g}x{pattern_multiplier:g}x{repetitions}=+{win}"
            )

            # --- RED BUTTON / USABLE BUFFS ---
            if "midas_touch" in self.active_round_buffs:
                _symbol_value_bonus[sym_name] += SYMBOLS[sym_name]["value"]
                self._record_charm_activation("Midas Touch")
                found_any.append(f"Midas Touch: {sym_name} krijgt permanente bonus!")
                
            for coord in match_coords:
                if coord not in self.winning_coords:
                    self.winning_coords.append(coord)
                for modifier, hit in modifier_hits.items():
                    if hit:
                        self.modifier_coords.setdefault(coord, set()).add(modifier)
            self.winning_patterns.append({
                "coords": match_coords,
                "symbol": sym_name,
                "pattern": p["name"],
                "modifiers": [modifier for modifier, hit in modifier_hits.items() if hit],
            })

        if patterns_to_payout:
            self._apply_pattern_event_charms(patterns_to_payout, total_payout, found_any)
            total_payout = self._event_adjusted_payout
            del self._event_adjusted_payout

        lucky_cat_groups = len(patterns_to_payout) // 3
        if "Lucky Cat" in self.purchased_items.get("charms", set()) and lucky_cat_groups > 0:
            interest = max(1, int(self.atm * self.atm_interest_rate)) * lucky_cat_groups
            total_payout += interest
            self._record_charm_activation("Lucky Cat", lucky_cat_groups)
            found_any.append(f"💰 Lucky Cat rente: +{interest}")

        if not found_any:
            found_any.append("Geen patronen deze spin...")
            self.consecutive_misses += 1
            self._apply_miss_event_charms(found_any)
        else:
            self.consecutive_misses = 0

        if self.coin_doubler_spins_left > 0:
            total_payout *= 2
            self.coin_doubler_spins_left -= 1
            found_any.append(f"Coin Doubler x2 ({self.coin_doubler_spins_left} over)")

        activation_messages = self._consume_charm_activation_messages()
        if activation_messages:
            found_any.extend(activation_messages)

        self.coins += total_payout
        self.total_win_anim = total_payout
        self.last_wins = found_any

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
                self.grid = self.generate_grid()
                self.modifier_coords = {}
                self._maybe_force_666()
                self.check_all_patterns()

    def _end_round(self):
        self._apply_round_end_charm_effects()
        self._clear_round_buffs()
        self.phase = "atm_phase"
        self.current_screen = "game"
        if "D6" in self.purchased_items.get("charms", set()):
            self.free_restock_count += SHOP_ITEMS["charms"]["D6"].get("restock_bonus", 1)
        self._roll_shop_items()

    def _clear_round_buffs(self):
        self.active_round_buffs.clear()
        self.used_usables_this_round.clear()
        self.round_symbol_multiplier_bonus = 0.0
        self.round_pattern_multiplier_bonus = 0.0
        self.round_repetition_bonus_by_symbol.clear()

    def _apply_round_end_charm_effects(self):
        for charm in list(self._owned_charms()):
            charm_data = self._charm_data(charm)
            if charm_data.get("category") != "decaying_boost":
                continue
            decay = charm_data.get("decay_per_round", 0)
            if decay <= 0:
                continue
            self.atm_interest_rate = max(0.0, self.atm_interest_rate - decay)
            current_bonus = charm_data.get("_runtime_bonus", charm_data.get("interest_rate_bonus", 0))
            current_bonus = max(0.0, current_bonus - decay)
            charm_data["_runtime_bonus"] = current_bonus
            if current_bonus <= 0:
                self.purchased_items["charms"].discard(charm)

    def _is_final_round(self):
        return self.round_in_deadline >= 3

    def _atm_deposit_chunk(self):
        if self.phase != "atm_phase":
            return
        target = self._deadline_cost_for(self.deadline_number)
        chunk = max(1, int(target * 0.20))
        amount = min(chunk, self.coins)
        if amount > 0:
            self.coins -= amount
            self.atm += amount

    def _atm_deposit_all(self):
        if self.phase != "atm_phase":
            return
        target = self._deadline_cost_for(self.deadline_number)
        needed = max(0, target - self.atm)
        amount = min(needed, self.coins)
        if amount > 0:
            self.coins -= amount
            self.atm += amount

    def _try_next_deadline(self):
        if not self._is_final_round():
            self._continue_to_spin_choice()
        else:
            target = self._deadline_cost_for(self.deadline_number)
            if self.atm >= target:
                self.atm -= target
                self.deadline_number += 1
                self.round_in_deadline = 1
                
                # --- START PHONE CALL MECHANIC ---
                self._generate_phone_calls()
                
                self.consecutive_misses = 0
                self.last_wins = []
                self.repeatable_items_bought_this_round.clear()
                self._clear_round_buffs()
                if "Shopping Cart" in self.purchased_items.get("charms", set()):
                    self.free_restock_count += SHOP_ITEMS["charms"]["Shopping Cart"].get("deadline_bonus_restock", 1)
                self.selected_button = 0
                self.grid = self.generate_grid()
                self._roll_shop_items()
            else:
                # --- ANKH MECHANIC ---
                if "Ankh" in self.purchased_items.get("charms", set()):
                    self.purchased_items["charms"].remove("Ankh")
                    self.round_in_deadline -= 2
                    self.last_wins = ["Ankh heeft je gered! Je krijgt 2 extra rondes."]
                    self._continue_to_spin_choice()
                else:
                    self.last_wins = [
                        "GAME OVER! Deadline niet gehaald!",
                        f"Nodig: {target}, ATM: {self.atm}"
                    ]
                    self.phase = "game_over"

    def _continue_to_spin_choice(self):
        if self._is_final_round():
            return
        self.round_in_deadline += 1
        self.phase = "spin_choice"
        self.current_screen = "game"
        self.repeatable_items_bought_this_round.clear()
        self._clear_round_buffs()
        self.selected_button = 0
        self.grid = self.generate_grid()

    def _skip_spin_phase(self):
        if self._is_final_round():
            return
        if self.round_in_deadline == 1:
            self.tickets += 8
        elif self.round_in_deadline == 2:
            self.tickets += 4
        self.round_in_deadline += 1
        self.phase = "atm_phase"
        self.current_screen = "game"
        self.repeatable_items_bought_this_round.clear()
        self._clear_round_buffs()
        self.selected_button = 0
        self._roll_shop_items()

    def _buy_item(self, item_name, cost, item_type):
        repeatable = item_name in REPEATABLE_SHOP_ITEMS
        already_bought_this_round = item_name in self.repeatable_items_bought_this_round
        
        # Controleer maximum charms
        if item_type == "charms" and len(self.purchased_items.get("charms", set())) >= self.max_charms and not repeatable:
            # Tenzij het een consumable is die geen ruimte inneemt!
            item_data = SHOP_ITEMS.get(item_type, {}).get(item_name, {})
            if item_data.get("takes_space") is not False:
                return

        can_buy = (
            (repeatable and not already_bought_this_round)
            or item_name not in self.purchased_items.get(item_type, set())
        )

        actual_cost = cost
        if item_type == "charms" and self.charm_discount_active:
            actual_cost = max(0, actual_cost - 2)
        if item_type == "charms" and getattr(self, "free_charms_active", False):
            actual_cost = 0
            
        # Fidelity Card korting
        if "Fidelity Card" in self.purchased_items.get("charms", set()):
            actual_cost = max(0, actual_cost - 1)

        if self.tickets >= actual_cost and can_buy:
            self.tickets -= actual_cost
            if item_type == "charms" and self.charm_discount_active:
                self.charm_discount_active = False # One time use
            if item_type == "charms" and getattr(self, "free_charms_active", False):
                self.free_charms_active = False
            
            item_data = SHOP_ITEMS.get(item_type, {}).get(item_name, {})
            
            # Check of het een consumable is die niet in inventory moet (zoals Cardboard House of Cigarettes)
            if item_data.get("takes_space") is False:
                self._apply_item_effect(item_name, item_type)
            elif repeatable:
                self.repeatable_items_bought_this_round.add(item_name)
                self._apply_item_effect(item_name, item_type)
            else:
                self.purchased_items[item_type].add(item_name)
                self._apply_item_effect(item_name, item_type)
                
            # Verwijder item uit huidige shop lijst
            self.shop_items_for_phase = [
                entry for entry in self.shop_items_for_phase
                if not (entry[0] == item_type and entry[1] == item_name)
            ]
            self.selected_button = min(self.selected_button, max(0, len(self.shop_items_for_phase) * 2 - 1))

    def _apply_item_effect(self, item_name, item_type):
        item_data = SHOP_ITEMS.get(item_type, {}).get(item_name, {})
        
        # --- DYNAMIC JSON HOOKS ---
        
        # 1. Dynamic Weight Boosts
        if "weight_bonus" in item_data and "target_symbol" in item_data:
            targets = item_data["target_symbol"]
            if isinstance(targets, str): targets = [targets]
            for sym in targets:
                if sym in _symbol_weight_bonus:
                    _symbol_weight_bonus[sym] += item_data["weight_bonus"]
                    
        # 2. Dynamic Value Boosts
        if "value_bonus" in item_data and "target_symbol" in item_data:
            targets = item_data["target_symbol"]
            if isinstance(targets, str): targets = [targets]
            for sym in targets:
                if sym in _symbol_value_bonus:
                    _symbol_value_bonus[sym] += item_data["value_bonus"]
                    
        # 3. Consumable Max Charms Bonus
        if "max_charms_bonus" in item_data:
            self.max_charms += item_data["max_charms_bonus"]

        # 4. Generic passive/consumable hooks from shop_items.json
        if "interest_rate_bonus" in item_data:
            self.atm_interest_rate += item_data["interest_rate_bonus"]

        if "restock_bonus" in item_data:
            self.free_restock_count += item_data["restock_bonus"]

        if item_data.get("permanent_value_increase_by_base"):
            targets = item_data.get("target_symbol", [])
            if isinstance(targets, str):
                targets = [targets]
            if "ALL" in targets:
                targets = list(SYMBOLS.keys())
            for sym in targets:
                if sym in SYMBOLS:
                    _symbol_value_bonus[sym] += SYMBOLS[sym]["value"]

        # --- HARDCODED SPECIAL CASES ---
        if item_name == "Coin Doubler":
            self.coin_doubler_spins_left += 3
        elif item_name == "Extra Spins":
            if self.phase == "spinning_phase":
                self.spins_left += 5
                self.chosen_spins += 5
            else:
                self.extra_spins_pending += 5
        elif item_name == "Better Odds":
            self.pattern_chance_bonus += 0.15
        elif item_name == "Interest Boost":
            self.atm_interest_rate += 0.02

    def _remove_item_effect(self, item_name, item_type):
        item_data = SHOP_ITEMS.get(item_type, {}).get(item_name, {})

        if "weight_bonus" in item_data and "target_symbol" in item_data:
            targets = item_data["target_symbol"]
            if isinstance(targets, str):
                targets = [targets]
            for sym in targets:
                if sym in _symbol_weight_bonus:
                    _symbol_weight_bonus[sym] -= item_data["weight_bonus"]

        if "value_bonus" in item_data and "target_symbol" in item_data:
            targets = item_data["target_symbol"]
            if isinstance(targets, str):
                targets = [targets]
            for sym in targets:
                if sym in _symbol_value_bonus:
                    _symbol_value_bonus[sym] -= item_data["value_bonus"]

        if "max_charms_bonus" in item_data:
            self.max_charms = max(0, self.max_charms - item_data["max_charms_bonus"])

        if "interest_rate_bonus" in item_data:
            self.atm_interest_rate = max(0.0, self.atm_interest_rate - item_data["interest_rate_bonus"])
    
    def _apply_all_luck_bonuses(self):
        luck_items = {
            "Luck Potion": 10,
            "Golden Horseshoe": 0,
        }
        
        for item_name, luck_boost in luck_items.items():
            if item_name in self.purchased_items.get("powerups", set()) or item_name in self.purchased_items.get("charms", set()):
                self.luck += luck_boost
        
        if "Golden Horseshoe" in self.purchased_items.get("charms", set()):
            other_luck = 0
            for item_name, luck_boost in luck_items.items():
                if item_name != "Golden Horseshoe" and item_name in self.purchased_items.get("powerups", set()):
                    other_luck += luck_boost
            self.luck += other_luck

    def deposit(self):
        if self.phase == "atm_phase":
            self.current_screen = "atm"

    def shop(self):
        if self.phase in ("spin_choice", "atm_phase"):
            self.current_screen = "shop"
            self.selected_button = 0
            self.shop_scroll_y = 0

    def values_menu(self):
        if self.phase in ("spin_choice", "atm_phase"):
            self.current_screen = "values"
            self.selected_button = 0

    def back_to_game(self):
        self.current_screen = "game"
    
    def charms_menu(self):
        if self.phase in ("spin_choice", "atm_phase"):
            self.current_screen = "charms_menu"
            self.selected_button = 0
            self.shop_scroll_y = 0

    def _get_eligible_shop_items(self):
        eligible_items = []
        for category, items_dict in SHOP_ITEMS.items():
            for item_name, item_data in items_dict.items():
                already_bought = item_name in self.purchased_items.get(category, set())
                if already_bought and item_name not in REPEATABLE_SHOP_ITEMS:
                    continue
                if item_name in self.repeatable_items_bought_this_round:
                    continue
                eligible_items.append((category, item_name, item_data))
        return eligible_items

    def _roll_shop_items(self):
        eligible_items = self._get_eligible_shop_items()
        roll_size = min(SHOP_ROLL_SIZE, len(eligible_items))
        self.shop_items_for_phase = random.sample(eligible_items, roll_size)
        self.shop_scroll_y = 0
        self.selected_button = 0

    def _refresh_shop(self):
        if self.free_restock_count > 0:
            self.free_restock_count -= 1
            self._roll_shop_items()
            self._apply_restock_event_charms()
        elif self.coins >= self.shop_refresh_cost:
            self.coins -= self.shop_refresh_cost
            self.shop_refresh_cost = (self.shop_refresh_cost * 3 + 1) // 2
            self._roll_shop_items()
            self._apply_restock_event_charms()

    def _apply_restock_event_charms(self):
        for charm in self._owned_charms():
            charm_data = self._charm_data(charm)
            if charm_data.get("category") == "event_trigger" and charm_data.get("trigger") == "on_shop_restock":
                self._recharge_usables(charm_data.get("recharge_target", "random"))

    def _get_shop_item_count(self):
        return len(self.shop_items_for_phase)

    def _sync_shop_scroll(self):
        if self.current_screen == "shop":
            item_count = self._get_shop_item_count()
        else:  # charms_menu
            item_count = len(self.purchased_items.get("charms", set()))
            
        # Scroll niet als het infoscherm open is of de lijst leeg is
        if item_count == 0 or getattr(self, "show_info_for", None) is not None:
            self.shop_scroll_y = 0
            return

        list_top = 45
        list_bottom = HEIGHT - 55
        item_step = 32
        item_height = 28
        max_scroll = max(0, item_count * item_step - (list_bottom - list_top))

        # Omdat er nu 2 knoppen per item zijn (koop/verkoop & info), is de index gedeeld door 2
        item_idx = self.selected_button // 2

        if item_idx >= item_count:
            self.shop_scroll_y = max_scroll
            return

        item_top = list_top + item_idx * item_step
        item_bottom = item_top + item_height

        if item_top - self.shop_scroll_y < list_top:
            self.shop_scroll_y = item_top - list_top
        elif item_bottom - self.shop_scroll_y > list_bottom:
            self.shop_scroll_y = item_bottom - list_bottom

        self.shop_scroll_y = max(0, min(self.shop_scroll_y, max_scroll))

    def handle_events(self, event):
        return

    def _trigger_usables(self):
        if self.phase not in ["spin_choice", "spinning_phase"]:
            return

        has_nuclear = "Nuclear Button" in self.purchased_items.get("charms", set())
        has_sacred_heart = "Sacred Heart" in self.purchased_items.get("charms", set())
        
        activations = 2 if has_nuclear else 1
        usables_triggered = {}

        for charm in list(self.purchased_items.get("charms", set())):
            charm_data = SHOP_ITEMS.get("charms", {}).get(charm, {})
            
            if charm_data.get("category") == "usable":
                if charm in self.used_usables_this_round:
                    continue
                
                for _ in range(activations):
                    luck_bonus = charm_data.get("luck_bonus", 0)
                    if luck_bonus:
                        self.next_spin_luck_bonus += luck_bonus
                    bonus_spins = charm_data.get("extra_spins", 0)
                    if bonus_spins:
                        if self.phase == "spinning_phase":
                            self.spins_left += bonus_spins
                            self.chosen_spins += bonus_spins
                        else:
                            self.extra_spins_pending += bonus_spins
                    if charm == "Midas Touch":
                        self.active_round_buffs.add("midas_touch")
                    elif charm == "Number 1":
                        self.active_round_buffs.add("number_1")
                        self.round_repetition_bonus_by_symbol["Citroen"] = (
                            self.round_repetition_bonus_by_symbol.get("Citroen", 0) + 1
                        )
                    elif charm == "Number 2":
                        self.active_round_buffs.add("number_2")
                        for sym in SYMBOLS:
                            if sym != "Citroen":
                                self.round_repetition_bonus_by_symbol[sym] = (
                                    self.round_repetition_bonus_by_symbol.get(sym, 0) + 1
                                )
                
                self._record_charm_activation(charm, activations)
                usables_triggered[charm] = usables_triggered.get(charm, 0) + activations
                
                save_chance = self._charm_data("Sacred Heart").get("red_button_save_charge_chance", 0)
                if has_sacred_heart and random.random() < save_chance:
                    self._record_charm_activation("Sacred Heart")
                    usables_triggered["Sacred Heart"] = usables_triggered.get("Sacred Heart", 0) + 1
                else:
                    self.used_usables_this_round.add(charm)

        if usables_triggered:
            self.last_wins.extend(self._charm_activation_messages(usables_triggered))

    def _handle_input_actions(self):
        if self.input.just_pressed("ESCAPE"):
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))
            return
            
        if self.input.just_pressed("SPACE"):
            self._trigger_usables()

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
        in_phone_call = self.phase == "phone_call"
        in_spin_choice = self.phase == "spin_choice" and self.current_screen == "game"

        def move_in_grid(grid):
            if not grid:
                return
            cur = self.selected_button
            cur_row, cur_col = 0, 0
            for ri, row in enumerate(grid):
                if cur in row:
                    cur_row = ri
                    cur_col = row.index(cur)
                    break

            if key == pygame.K_LEFT:
                new_col = max(0, cur_col - 1)
                self.selected_button = grid[cur_row][new_col]
            elif key == pygame.K_RIGHT:
                new_col = min(len(grid[cur_row]) - 1, cur_col + 1)
                self.selected_button = grid[cur_row][new_col]
            elif key == pygame.K_DOWN:
                new_row = min(len(grid) - 1, cur_row + 1)
                new_col = min(cur_col, len(grid[new_row]) - 1)
                self.selected_button = grid[new_row][new_col]
            elif key == pygame.K_UP:
                new_row = max(0, cur_row - 1)
                new_col = min(cur_col, len(grid[new_row]) - 1)
                self.selected_button = grid[new_row][new_col]

        if in_phone_call:
            if key == pygame.K_UP or key == pygame.K_LEFT:
                self.selected_button = (self.selected_button - 1) % len(self.buttons)
            elif key == pygame.K_DOWN or key == pygame.K_RIGHT:
                self.selected_button = (self.selected_button + 1) % len(self.buttons)

        elif in_spin_choice:
            if self._can_take_emergency_spin():
                grid = [[0, 1], [2], [3], [4, 5, 6]]
            else:
                grid = [[0, 1], [2], [3, 4, 5]]
            move_in_grid([row for row in grid if all(idx < len(self.buttons) for idx in row)])

        elif in_atm_phase:
            can_skip = self.atm >= self._deadline_cost_for(self.deadline_number) and not self._is_final_round()
            middle_row = [2, 3] if can_skip else [2]
            nav_start = 4 if can_skip else 3
            bottom_row = [idx for idx in range(nav_start, len(self.buttons))]
            grid = [[0, 1], middle_row, bottom_row]
            move_in_grid(grid)

        elif in_shop or self.current_screen == "charms_menu":
            if getattr(self, "show_info_for", None) is not None:
                self.selected_button = 0
            else:
                if self.current_screen == "shop":
                    item_count = self._get_shop_item_count()
                else:  # charms_menu
                    item_count = len(self.purchased_items.get("charms", set()))
                
                grid = []
                # Rij opbouwen: [Koop/Verkoop Knop, Info Knop]
                for i in range(item_count):
                    grid.append([i * 2, i * 2 + 1])
                
                # Onderste knoppen toevoegen (Back & Reroll)
                bottom_row = []
                if len(self.buttons) > item_count * 2:
                    bottom_row.append(item_count * 2)
                if self.current_screen == "shop" and len(self.buttons) > item_count * 2 + 1:
                    bottom_row.append(item_count * 2 + 1)
                if bottom_row:
                    grid.append(bottom_row)

                move_in_grid(grid)
                self._sync_shop_scroll()

        elif in_atm_screen:
            if key == pygame.K_UP or key == pygame.K_LEFT:
                self.selected_button = (self.selected_button - 1) % len(self.buttons)
            elif key == pygame.K_DOWN or key == pygame.K_RIGHT:
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
            if getattr(self, "show_info_for", None) is not None:
                self._close_info()
            else:
                self.back_to_game()
            self.button_cooldown = 10
    
    def _sell_charm(self, charm_name):
        """Verkoop een charm en krijg 50% terug van de kosten"""
        charm_data = SHOP_ITEMS.get("charms", {}).get(charm_name, {})
        cost = charm_data.get("cost", 0)
        refund = max(1, cost // 2)  # 50% terug
        
        self._remove_item_effect(charm_name, "charms")
        self.purchased_items["charms"].discard(charm_name)
        self.tickets += refund
        
        # Verwijder uit shop lijst
        self.shop_items_for_phase = [
            entry for entry in self.shop_items_for_phase
            if not (entry[0] == "charms" and entry[1] == charm_name)
        ]
        self.selected_button = min(self.selected_button, max(0, len(self.purchased_items.get("charms", set())) * 2 - 1))

    def draw(self, surface):
        self.buttons = []
        if self.current_screen == "atm":
            self._draw_atm_screen(surface)
        elif self.current_screen == "shop":
            self._draw_shop_screen(surface)
        elif self.current_screen == "charms_menu":
            self._draw_charms_menu_screen(surface)
        elif self.current_screen == "values":
            self._draw_values_screen(surface)
        elif self.phase == "phone_call":
            self._draw_phone_call_screen(surface)
        elif self.phase == "spin_choice":
            self._draw_spin_choice_screen(surface)
        elif self.phase == "spinning_phase":
            self._draw_spinning_screen(surface)
        elif self.phase == "atm_phase":
            self._draw_atm_phase_screen(surface)
        elif self.phase == "game_over":
            self._draw_game_over_screen(surface)
        self.selected_button = min(self.selected_button, max(0, len(self.buttons) - 1))

    # ── PHONE CALL MECHANIC ──────────────────────────────────────────────────
    def _generate_phone_calls(self):
        self.phase = "phone_call"
        self.current_screen = "game"
        self.selected_button = 0
        
        amount_of_options = 3
        if "Dear Diary" in self.purchased_items.get("charms", set()):
            amount_of_options += 1
            
        options = []
        for _ in range(amount_of_options):
            if random.random() < 0.25:
                option = dict(random.choice(PHONE_CALLS["Evil"]))
            else:
                option = dict(random.choice(PHONE_CALLS["Normal"]))
            if option.get("type") == "plus_weight_symbol" and "symbol" not in option:
                symbol = random.choice(option.get("symbols", []))
                option["symbol"] = symbol
                option["name"] = option["name"].format(symbol=symbol)
                option["desc"] = option["desc"].format(symbol=symbol)
            options.append(option)
                
        self.active_phone_options = options

    def _draw_phone_call_screen(self, surface):
        surface.fill(BLACK)
        lf = pygame.font.SysFont("monospace", 18, bold=True)
        mf = pygame.font.SysFont("monospace", 11, bold=True)
        sf = pygame.font.SysFont("monospace", 9)

        title = lf.render("📞 THE PHONE IS RINGING...", True, RED)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 10))

        sub = mf.render("Kies een van de volgende opties:", True, WHITE)
        surface.blit(sub, (WIDTH//2 - sub.get_width()//2, 30))

        box_w = WIDTH - 20
        box_h = 38
        start_y = 52
        spacing = 6

        for i, option in enumerate(self.active_phone_options):
            y_pos = start_y + i * (box_h + spacing)
            
            is_evil = option in PHONE_CALLS["Evil"]
            bg_color = (80, 0, 0) if is_evil else (0, 60, 100)
            rect = pygame.Rect(10, y_pos, box_w, box_h)
            is_hover = rect.collidepoint(pygame.mouse.get_pos())
            is_selected = len(self.buttons) == self.selected_button
            
            btn_label = "" 
            action = (lambda o=option: self._apply_phone_call(o))
            self._draw_btn(surface, btn_label, 10, y_pos, box_w, box_h, bg_color, action)
            
            if is_selected or is_hover:
                name_color = BLACK
                desc_color = (40, 40, 40)
            else:
                name_color = GOLD if is_evil else WHITE
                desc_color = (200, 200, 200)

            name_txt = mf.render(option["name"], True, name_color)
            desc_txt = sf.render(option["desc"], True, desc_color)
            
            surface.blit(name_txt, (20, y_pos + 6))
            surface.blit(desc_txt, (20, y_pos + 20))

        self._draw_btn(surface, "REROLL", 35, HEIGHT - 42, 80, 34, BLUE, self._reroll_phone_calls)
        self._draw_btn(surface, "SKIP", WIDTH - 115, HEIGHT - 42, 80, 34, DARK_GRAY, self._skip_phone_call)

    def _reroll_phone_calls(self):
        self.phone_rerolls += 1
        self._generate_phone_calls()

    def _skip_phone_call(self):
        self.phone_skips += 1
        self.phase = "spin_choice"
        self.selected_button = 0

    def _apply_phone_call(self, option):
        opt_type = option["type"]
        repeat_count = 1
        if "Megaphone" in self.purchased_items.get("charms", set()):
            repeat_count = SHOP_ITEMS["charms"]["Megaphone"].get("phone_trigger_multiplier", 2)
        
        for _ in range(repeat_count):
            # --- NORMAL CALLS ---
            if opt_type == "charm_space":
                self.max_charms += 1
            elif opt_type == "double_jackpot":
                for p in PATTERNS:
                    if p["type"] == "jackpot":
                        p["multiplier"] *= 2.0
            elif opt_type == "plus_5_tickets":
                self.tickets += 5
            elif opt_type == "discount_charms":
                self.charm_discount_active = True
            elif opt_type == "restore_charges":
                self._recharge_usables("all")
            elif opt_type == "plus_weight_symbol":
                self._increase_symbol_weights([option.get("symbol")], 1.0)
            elif opt_type in ("plus_weight", "plus_weight_fruit_clover"):
                self._increase_symbol_weights(["Kers", "Citroen", "Klaver"], 1.0)
            elif opt_type == "plus_weight_chest_bell_diamond":
                self._increase_symbol_weights(["Chest", "Bell", "Diamant"], 1.0)
            elif opt_type == "plus_weight_seven":
                self._increase_symbol_weights(["Zeven"], 1.0)
            elif opt_type in ("double_pair", "double_fruit_clover"):
                self._increase_symbol_values(["Kers", "Citroen", "Klaver"], 2)
            elif opt_type == "double_chest_bell_diamond":
                self._increase_symbol_values(["Chest", "Bell", "Diamant"], 2)
            elif opt_type == "triple_seven":
                self._increase_symbol_values(["Zeven"], 3)
            elif opt_type == "buff_small_patterns":
                for p in PATTERNS:
                    if p.get("length", 4) <= 3:
                        p["multiplier"] += 0.5

            # --- EVIL CALLS ---
            elif opt_type == "evil_cryptic":
                self.tickets *= 2
                self.coins = 0
            elif opt_type == "evil_free_charms":
                self.free_charms_active = True
                self.tickets = 0
            elif opt_type == "evil_head_hurts":
                self._increase_symbol_values(["Kers", "Citroen", "Klaver"], 2)
                self._increase_symbol_values(["Chest", "Bell", "Diamant"], 2)
            elif opt_type == "evil_money":
                self.coins *= 2
                self.tickets = 0
            elif opt_type == "evil_mould_fruit_clover":
                self._halve_symbol_weights(["Kers", "Citroen", "Klaver"])
            elif opt_type == "evil_mould_chest_bell_diamond":
                self._halve_symbol_weights(["Chest", "Bell", "Diamant"])
            elif opt_type == "evil_mould_seven":
                self._halve_symbol_weights(["Zeven"])

        self.phase = "spin_choice"
        self.selected_button = 0

    def _increase_symbol_values(self, symbols, multiplier):
        for sym in symbols:
            if sym in SYMBOLS:
                current_value = get_effective_value(sym)
                _symbol_value_bonus[sym] += current_value * (multiplier - 1)

    def _increase_symbol_weights(self, symbols, amount):
        for sym in symbols:
            if sym in SYMBOLS:
                _symbol_weight_bonus[sym] += amount

    def _halve_symbol_weights(self, symbols):
        for sym in symbols:
            if sym in SYMBOLS:
                _symbol_weight_bonus[sym] -= SYMBOLS[sym]["weight"] / 2

    def _apply_phone_effect_once(self, opt_type):
        saved_phase = self.phase
        saved_selected = self.selected_button
        self.phase = "phone_call"
        self._apply_phone_call({"type": opt_type})
        self.phase = saved_phase
        self.selected_button = saved_selected

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

        coins_txt = sf.render(f"Munten: {self.coins}  |  Tickets: {self.tickets}  |  Luck: {self.luck}", True, GOLD)
        surface.blit(coins_txt, (WIDTH//2 - coins_txt.get_width()//2, 52))

        info = sf.render("Kies hoeveel spins:", True, WHITE)
        surface.blit(info, (WIDTH//2 - info.get_width()//2, 82))

        cost_3 = int(target * 0.05)
        cost_7 = int(target * 0.10)
        c3 = sf.render(f"3 spins = +2 tickets (Kost: {cost_3})", True, (180, 180, 180))
        surface.blit(c3, (WIDTH//2 - c3.get_width()//2, 100))
        c7 = sf.render(f"7 spins = +1 ticket (Kost: {cost_7})", True, (180, 180, 180))
        surface.blit(c7, (WIDTH//2 - c7.get_width()//2, 116))

        col_3 = BLUE if self.coins >= cost_3 else DARK_GRAY
        col_7 = GREEN if self.coins >= cost_7 else DARK_GRAY
        emergency_spin = self._can_take_emergency_spin()
        choice_y = HEIGHT - 158 if emergency_spin else HEIGHT - 126
        choice_h = 36 if emergency_spin else 40
        skip_y = HEIGHT - 82 if emergency_spin else HEIGHT - 78
        skip_h = 30 if emergency_spin else 35
        self._draw_btn(surface, "3 SPINS", WIDTH//2 - 80, choice_y, 70, choice_h, col_3, (lambda: self.choose_spins(3)))
        self._draw_btn(surface, "7 SPINS", WIDTH//2 + 10, choice_y, 70, choice_h, col_7, (lambda: self.choose_spins(7)))
        if emergency_spin:
            self._draw_btn(surface, "1 SPIN 0M", WIDTH//2 - 45, HEIGHT - 116, 90, 30, GOLD, (lambda: self.choose_spins(1)))
        skip_btn = GREEN if self.round_in_deadline < 3 else (100, 100, 100)
        self._draw_btn(surface, "SKIP", WIDTH//2 - 25, skip_y, 50, skip_h, skip_btn, self._skip_spin_phase if self.round_in_deadline < 3 else (lambda: None))
        self._draw_btn(surface, "WAARDES", 5, HEIGHT - 45, 70, 35, (0, 110, 120), self.values_menu)
        self._draw_btn(surface, "CHARMS", WIDTH - 110, HEIGHT - 45, 60, 35, (180, 100, 200), self.charms_menu)
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
        round_done = self.spins_left == 0 and not self.spinning
        if round_done:
            self._draw_btn(surface, "NAAR ATM", WIDTH//2 - 45, btn_y, 90, 40, BLUE, self._end_round)
        else:
            spin_color = GREEN if (self.spins_left > 0 and not self.spinning) else DARK_GRAY
            red_ready = any(
                self._charm_data(charm).get("category") == "usable"
                and charm not in self.used_usables_this_round
                for charm in self._owned_charms()
            )
            red_color = RED if red_ready else DARK_GRAY
            self._draw_btn(surface, "RED", WIDTH//2 - 58, btn_y, 50, 40, red_color, self._trigger_usables)
            self._draw_btn(surface, "SPIN", WIDTH//2 + 8, btn_y, 50, 40, spin_color, self.spin)

        if self.total_win_anim > 0:
            win_txt = sf.render(f"WINST: +{self.total_win_anim}", True, GREEN)
            surface.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, btn_y - 36))
            for i, log in enumerate(self.last_wins[-2:]):
                lt = pygame.font.SysFont("monospace", 11, bold=True).render(log[:28], True, WHITE)
                surface.blit(lt, (5, btn_y - 36 + 16 + i * 14))

        if round_done:
            done_txt = sf.render("Laatste spin klaar", True, GOLD)
            surface.blit(done_txt, (WIDTH//2 - done_txt.get_width()//2, btn_y - 20))

    # ── ATM PHASE ────────────────────────────────────────────────────────────
    def _draw_atm_phase_screen(self, surface):
        surface.fill(BLACK)
        target = self._deadline_cost_for(self.deadline_number)
        chunk = max(1, int(target * 0.20))
        is_final = self._is_final_round()
        sf  = pygame.font.SysFont("monospace", 13, bold=True)
        mf  = pygame.font.SysFont("monospace", 16, bold=True)

        header_color = RED if is_final else GOLD
        header_txt = f"DEADLINE {self.deadline_number}  —  Ronde {self.round_in_deadline}/3"
        h = mf.render(header_txt, True, header_color)
        surface.blit(h, (WIDTH//2 - h.get_width()//2, 6))

        tickets_info = ""
        if not is_final:
            if self.round_in_deadline == 1:
                tickets_info = "SKIP → +8 tickets"
            elif self.round_in_deadline == 2:
                tickets_info = "SKIP → +4 tickets"
            else:
                tickets_info = "SKIP → +0 tickets"
        
        sub_text = "Stort in ATM voor de deadline" if not is_final else "Laatste ronde — betaal nu!"
        if tickets_info:
            sub_text += f"  |  {tickets_info}"
        sub = sf.render(sub_text, True, WHITE)
        surface.blit(sub, (WIDTH//2 - sub.get_width()//2, 26))

        bar_x, bar_y, bar_w, bar_h = 10, 46, WIDTH - 20, 18
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill = min(1.0, self.atm / target) if target > 0 else 1.0
        fill_color = GREEN if fill >= 1.0 else BLUE
        if fill > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * fill), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        pct_txt = sf.render(f"{int(fill*100)}%  {self.atm}/{target}", True, WHITE)
        surface.blit(pct_txt, (bar_x + bar_w//2 - pct_txt.get_width()//2, bar_y + 2))

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
        
        tickets_txt = sf.render(f"TICKETS: {self.tickets}", True, (255, 200, 100))
        surface.blit(tickets_txt, (10, 120))

        btn_y = 130
        chunk_label = f"+{chunk} (20%)"
        self._draw_btn(surface, chunk_label, 10,        btn_y, (WIDTH-24)//2, 40, GREEN, self._atm_deposit_chunk)
        self._draw_btn(surface, "ALLES",    10 + (WIDTH-24)//2 + 4, btn_y, (WIDTH-24)//2, 40, (0,140,80), self._atm_deposit_all)

        if is_final:
            can_pay = self.atm >= target
            pay_col = GREEN if can_pay else (70, 70, 70)
            self._draw_btn(surface, "BETAAL DEADLINE", WIDTH//2 - 100, HEIGHT - 95, 200, 40, pay_col, self._try_next_deadline)
        else:
            can_skip = self.atm >= target
            if can_skip:
                btn_w = 96
                gap = 8
                left_x = WIDTH//2 - btn_w - gap//2
                right_x = WIDTH//2 + gap//2
                self._draw_btn(surface, "SPIN", left_x, HEIGHT - 95, btn_w, 40, BLUE, self._continue_to_spin_choice)
                self._draw_btn(surface, "SKIP", right_x, HEIGHT - 95, btn_w, 40, (180, 120, 0), self._skip_spin_phase)
                skip_hint = sf.render("Doel gehaald — sla ronde over!", True, GOLD)
                surface.blit(skip_hint, (WIDTH//2 - skip_hint.get_width()//2, HEIGHT - 130))
            else:
                self._draw_btn(surface, "VOLGENDE RONDE >", WIDTH//2 - 100, HEIGHT - 95, 200, 40, BLUE, self._continue_to_spin_choice)

        self._draw_btn(surface, "WAARDE", 5,         HEIGHT - 46, 64, 36, (0, 110, 120), self.values_menu)
        self._draw_btn(surface, "CHARMS", 72,        HEIGHT - 46, 64, 36, (180, 100, 200), self.charms_menu)
        self._draw_btn(surface, "SHOP",  WIDTH - 62, HEIGHT - 46, 56, 36, (140,100,0),  self.shop)

    # ── ATM SCREEN ──────────────────────────────────────────────────────────
    def _draw_atm_screen(self, surface):
        surface.fill(BLACK)
        target = self._deadline_cost_for(self.deadline_number)
        chunk = max(1, int(target * 0.20))
        sf  = pygame.font.SysFont("monospace", 13, bold=True)
        mf  = pygame.font.SysFont("monospace", 16, bold=True)

        title = mf.render("ATM", True, BLUE)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 8))

        bar_x, bar_y, bar_w, bar_h = 10, 30, WIDTH - 20, 16
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill = min(1.0, self.atm / target) if target > 0 else 1.0
        fill_color = GREEN if fill >= 1.0 else BLUE
        if fill > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * fill), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        pt = sf.render(f"{self.atm}/{target}", True, WHITE)
        surface.blit(pt, (bar_x + bar_w//2 - pt.get_width()//2, bar_y + 1))

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

    # ── CHARMS INVENTORY SCREEN ───────────────────────────────────────────────
    # --- VALUES SCREEN ---
    def _draw_values_screen(self, surface):
        surface.fill(BLACK)
        title_font = pygame.font.SysFont("monospace", 18, bold=True)
        header_font = pygame.font.SysFont("monospace", 12, bold=True)
        row_font = pygame.font.SysFont("monospace", 10, bold=True)
        tiny_font = pygame.font.SysFont("monospace", 9)

        title = title_font.render("WAARDES", True, GOLD)
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 5))

        symbol_header = header_font.render("SYMBOLEN", True, BLUE)
        pattern_header = header_font.render("PATRONEN", True, BLUE)
        surface.blit(symbol_header, (10, 28))
        surface.blit(pattern_header, (166, 28))

        y = 44
        for name, data in SYMBOLS.items():
            color = data["color"]
            icon = data.get("icon", name[:1])
            value = get_effective_value(name)
            weight = get_effective_weight(name)
            label = f"{icon} {name[:7]:<7} V:{value:g} K:{weight:.2f}"
            text = row_font.render(label, True, color)
            surface.blit(text, (10, y))
            y += 15

        y = 44
        for pattern in PATTERNS:
            length = pattern.get("length", "-")
            label = f"{pattern['name'][:8]:<8} x{pattern['multiplier']:g} L:{length}"
            text = row_font.render(label, True, WHITE)
            surface.blit(text, (166, y))
            y += 13

        formula = tiny_font.render("Winst = symboolwaarde x aantal x patroon", True, (170, 170, 170))
        surface.blit(formula, (10, HEIGHT - 66))
        self._draw_btn(surface, "BACK", WIDTH // 2 - 35, HEIGHT - 45, 70, 36, BLUE, self.back_to_game)

    # --- CHARMS INVENTORY SCREEN ---
    def _draw_charms_menu_screen(self, surface):
        if getattr(self, "show_info_for", None) is not None:
            self._draw_info_popup(surface)
            return

        surface.fill(BLACK)
        small_font = pygame.font.SysFont("monospace", 12, bold=True)
        self._sync_shop_scroll()

        title = pygame.font.SysFont("monospace", 18, bold=True).render("GEKOCHTE CHARMS", True, GOLD)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 5))

        stats_txt = small_font.render(f"Tickets: {self.tickets}", True, GOLD)
        surface.blit(stats_txt, (5, 25))

        total_owned = len(self.purchased_items.get("charms", set()))
        owned_txt = small_font.render(f"Totaal: {total_owned}/{self.max_charms}", True, GREEN)
        surface.blit(owned_txt, (WIDTH - 110, 25))

        list_top = 45
        list_bottom = HEIGHT - 55
        list_clip = pygame.Rect(0, list_top, WIDTH, list_bottom - list_top)
        y_offset = list_top - self.shop_scroll_y
        item_count = 0
        old_clip = surface.get_clip()
        surface.set_clip(list_clip)

        charm_list = list(self.purchased_items.get("charms", set()))
        charm_list.sort()

        for charm_name in charm_list:
            charm_data = SHOP_ITEMS.get("charms", {}).get(charm_name, {})
            cost = charm_data.get("cost", 0)
            refund = max(1, cost // 2)  # 50% terug voor verkoop
            
            label = f"{charm_name[:12]} (Refund: +{refund}T)"
            
            _name = charm_name
            
            # Knoppen afmetingen
            sell_btn_w = WIDTH - 45
            info_btn_w = 30

            # Verkoop knop
            sell_action = (lambda n=_name: lambda: self._sell_charm(n))
            self._draw_btn(surface, label, 5, y_offset, sell_btn_w, 28, (200, 80, 80), sell_action, clip_rect=list_clip)
            
            # Info knop
            info_action = (lambda n=_name, d=charm_data: self._open_info(n, d))
            self._draw_btn(surface, "?", 5 + sell_btn_w + 5, y_offset, info_btn_w, 28, BLUE, info_action, clip_rect=list_clip)
            
            y_offset += 32
            item_count += 1
        
        if item_count == 0:
            empty_txt = small_font.render("Geen charms gekocht", True, (100, 100, 100))
            surface.blit(empty_txt, (WIDTH//2 - empty_txt.get_width()//2, list_top + 50))
            
        surface.set_clip(old_clip)

        self._draw_btn(surface, "BACK", WIDTH//2 - 70, HEIGHT - 45, 50, 40, BLUE, self.back_to_game)

    # ── SHOP SCREEN ──────────────────────────────────────────────────────────
    def _draw_shop_screen(self, surface):
        if getattr(self, "show_info_for", None) is not None:
            self._draw_info_popup(surface)
            return

        surface.fill(BLACK)
        small_font = pygame.font.SysFont("monospace", 12, bold=True)
        self._sync_shop_scroll()

        title = pygame.font.SysFont("monospace", 18, bold=True).render("SHOP", True, GOLD)
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 5))

        stats_txt = small_font.render(f"T: {self.tickets} | M: {self.coins} | R: {self.free_restock_count}", True, GOLD)
        surface.blit(stats_txt, (5, 25))

        total_owned = len(self.purchased_items.get("charms", set()))
        owned_txt = small_font.render(f"Charms: {total_owned}/{self.max_charms}", True, GREEN)
        surface.blit(owned_txt, (WIDTH - 110, 25))

        list_top = 45
        list_bottom = HEIGHT - 55
        list_clip = pygame.Rect(0, list_top, WIDTH, list_bottom - list_top)
        y_offset = list_top - self.shop_scroll_y
        item_count = 0
        old_clip = surface.get_clip()
        surface.set_clip(list_clip)

        for category, item_name, item_data in self.shop_items_for_phase:
            purchased = (
                item_name in self.purchased_items.get(category, set())
                and item_name not in REPEATABLE_SHOP_ITEMS
            )
            cost = item_data.get("cost", 0)
            
            actual_cost = cost
            if category == "charms" and self.charm_discount_active:
                actual_cost = max(0, actual_cost - 2)
            if category == "charms" and getattr(self, "free_charms_active", False):
                actual_cost = 0
            if "Fidelity Card" in self.purchased_items.get("charms", set()):
                actual_cost = max(0, actual_cost - 1)

            status = "✓" if purchased else f"{actual_cost}T"
            label = f"{item_name[:12]} ({status})"
            btn_color = GREEN if purchased else (60, 60, 60)
            
            _name, _cost, _cat = item_name, cost, category
            
            # Knoppen afmetingen
            buy_btn_w = WIDTH - 45
            info_btn_w = 30

            # Koop knop
            buy_action = (lambda n, c, t: lambda: self._buy_item(n, c, t))(_name, _cost, _cat)
            self._draw_btn(surface, label, 5, y_offset, buy_btn_w, 28, btn_color, buy_action, clip_rect=list_clip)
            
            # Info knop
            info_action = (lambda n=_name, d=item_data: self._open_info(n, d))
            self._draw_btn(surface, "?", 5 + buy_btn_w + 5, y_offset, info_btn_w, 28, BLUE, info_action, clip_rect=list_clip)
            
            y_offset += 32
            item_count += 1
            
        surface.set_clip(old_clip)

        self._draw_btn(surface, "BACK", WIDTH//2 - 70, HEIGHT - 45, 50, 40, BLUE, self.back_to_game)
        
        refresh_label = "REROLL (FREE)" if self.free_restock_count > 0 else f"REROLL ({self.shop_refresh_cost}M)"
        refresh_color = GOLD if self.free_restock_count > 0 or self.coins >= self.shop_refresh_cost else DARK_GRAY
        self._draw_btn(surface, refresh_label, WIDTH//2 - 10, HEIGHT - 45, 90, 40, refresh_color, self._refresh_shop)

    # --- INFO SCHERM METHODES ---
    def _open_info(self, name, data):
        self.show_info_for = {
            "name": name,
            "desc": data.get("effect", "Geen extra informatie beschikbaar.")
        }
        self.selected_button = 0  # Zet de selectie terug voor het infoscherm

    def _close_info(self):
        self.show_info_for = None
        self.selected_button = 0  # Zet de selectie terug naar de eerste shop item
        self._sync_shop_scroll()

    def _draw_text_wrapped(self, surface, text, font, color, rect):
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= rect.width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        y = rect.y
        for line in lines:
            surface.blit(font.render(line, True, color), (rect.x, y))
            y += font.get_linesize()

    def _draw_info_popup(self, surface):
        surface.fill(BLACK)
        mf = pygame.font.SysFont("monospace", 16, bold=True)
        sf = pygame.font.SysFont("monospace", 12)
        
        # Titel (Naam van Charm)
        title = mf.render(self.show_info_for["name"], True, GOLD)
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))
        
        # Subtitel / Decoratie lijn
        pygame.draw.line(surface, DARK_GRAY, (20, 55), (WIDTH - 20, 55), 2)
        
        # Text (De Effect beschrijving - Word Wrapped)
        text_rect = pygame.Rect(20, 70, WIDTH - 40, HEIGHT - 140)
        self._draw_text_wrapped(surface, self.show_info_for["desc"], sf, WHITE, text_rect)
        
        # Terug knop
        self._draw_btn(surface, "TERUG", WIDTH // 2 - 40, HEIGHT - 50, 80, 36, RED, self._close_info)

    # ── GAME OVER ────────────────────────────────────────────────────────────
    def _draw_game_over_screen(self, surface):
        surface.fill(BLACK)
        lf = pygame.font.SysFont("monospace", 22, bold=True)
        sf = pygame.font.SysFont("monospace", 14, bold=True)

        go = lf.render("GAME OVER", True, RED)
        surface.blit(go, (WIDTH//2 - go.get_width()//2, HEIGHT//2 - 60))

        for i, msg in enumerate(self.last_wins):
            t = sf.render(msg, True, WHITE)
            surface.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 20 + i * 22))

        self._draw_btn(surface, "OPNIEUW", WIDTH//2 - 40, HEIGHT - 60, 80, 40, GREEN, self.reset_game)

    def _draw_cell(self, surface, name, x, y, w, h, c, r):
        color = SYMBOLS[name]["color"]
        icon  = SYMBOLS[name].get("icon", name[:2].upper())
        
        is_winning = (c, r) in self.winning_coords
        cell_modifiers = getattr(self, "modifier_coords", {}).get((c, r), set())
        modifier_color = self._modifier_display_color(cell_modifiers)
        
        if is_winning and (self.flash_counter // 5) % 2 == 0:
            flash_fill = (100, 85, 20) if "golden" in cell_modifiers else (100, 100, 100)
            pygame.draw.rect(surface, flash_fill, (x, y, w, h), border_radius=3)
            pygame.draw.rect(surface, modifier_color, (x, y, w, h), 2, border_radius=3)
        else:
            pygame.draw.rect(surface, DARK_GRAY, (x, y, w, h), border_radius=3)
            pygame.draw.rect(surface, modifier_color if cell_modifiers else color, (x, y, w, h), 1, border_radius=3)
        
        cell_font = pygame.font.SysFont("monospace", max(8, w // 6), bold=True)
        try:
            emoji_font = pygame.font.SysFont("segoeuiemoji", max(10, w // 4))
            txt = emoji_font.render(icon, True, color)
        except Exception:
            txt = cell_font.render(icon, True, color)
        surface.blit(txt, (x + (w - txt.get_width())//2, y + (h - txt.get_height())//2))

        if cell_modifiers:
            label = self._modifier_display_label(cell_modifiers)
            label_font = pygame.font.SysFont("monospace", 8, bold=True)
            label_txt = label_font.render(label, True, modifier_color)
            label_bg = pygame.Rect(x + 2, y + 2, min(w - 4, label_txt.get_width() + 4), label_txt.get_height() + 2)
            pygame.draw.rect(surface, BLACK, label_bg, border_radius=2)
            surface.blit(label_txt, (label_bg.x + 2, label_bg.y + 1))

    def _modifier_display_color(self, modifiers):
        for modifier in MODIFIER_DRAW_PRIORITY:
            if modifier in modifiers:
                return MODIFIER_COLORS[modifier]
        return WHITE

    def _modifier_display_label(self, modifiers):
        for modifier in MODIFIER_DRAW_PRIORITY:
            if modifier in modifiers:
                return MODIFIER_LABELS[modifier]
        return ""
    
    def _draw_winning_lines(self, surface, start_x, start_y, cell_w, cell_h, grid_margin):
        for pattern in self.winning_patterns:
            coords = pattern["coords"]
            if len(coords) < 2:
                continue
            line_color = self._modifier_display_color(pattern.get("modifiers", []))
            
            centers = []
            for c, r in coords:
                center_x = start_x + c * (cell_w + grid_margin) + cell_w // 2
                center_y = start_y + r * (cell_h + grid_margin) + cell_h // 2
                centers.append((center_x, center_y))
            
            for i in range(len(centers) - 1):
                pygame.draw.line(surface, line_color, centers[i], centers[i+1], 3)
    
    def _draw_btn(self, surface, text, x, y, w, h, color, action, clip_rect=None):
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        rect = pygame.Rect(x, y, w, h)
        can_interact = clip_rect is None or clip_rect.colliderect(rect)

        btn_idx = len(self.buttons)
        self.buttons.append(action)

        is_selected = btn_idx == self.selected_button
        is_hover = can_interact and rect.collidepoint(mouse)
        if is_hover and clip_rect is not None:
            is_hover = clip_rect.collidepoint(mouse)

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
