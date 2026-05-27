import pygame
import random
import math
import os
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT


def game_name():
    return f"WinMan", WinMan


# ---------------------------------------------------------------------------
# Small helper: floating damage numbers
# ---------------------------------------------------------------------------
class DamageNumber:
    def __init__(self, x, y, text, color, font):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.font = font
        self.life = 52          # frames alive
        self.max_life = 52
        self.vy = -1.4          # floats upward

    def update(self):
        self.y += self.vy
        self.vy *= 0.92         # decelerates
        self.life -= 1

    def draw(self, surface):
        alpha = max(0, int(255 * (self.life / self.max_life)))
        surf = self.font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x - surf.get_width() // 2), int(self.y)))

    @property
    def alive(self):
        return self.life > 0


# ---------------------------------------------------------------------------
# Screen-shake helper
# ---------------------------------------------------------------------------
class ScreenShake:
    def __init__(self):
        self.timer = 0
        self.intensity = 0

    def trigger(self, intensity=4, duration=10):
        self.intensity = intensity
        self.timer = duration

    def get_offset(self):
        if self.timer <= 0:
            return (0, 0)
        self.timer -= 1
        t = self.timer / max(1, self.timer + 1)
        ox = random.randint(-self.intensity, self.intensity) * t
        oy = random.randint(-self.intensity, self.intensity) * t
        return (int(ox), int(oy))


class WinMan(Scene):
    def __init__(self, manager):
        super().__init__(manager)

        # --- Colours ---
        self.BLACK   = (0,   0,   0)
        self.WHITE   = (255, 255, 255)
        self.RED     = (255, 0,   0)
        self.BLUE    = (0,   120, 255)
        self.YELLOW  = (255, 255, 0)
        self.ORANGE  = (255, 128, 0)
        self.CYAN    = (0,   230, 255)
        self.GREEN   = (80,  255, 80)

        # --- Fonts ---
        self.font_main  = pygame.font.SysFont("couriernew", 14, bold=True)
        self.font_ui    = pygame.font.SysFont("couriernew", 12, bold=True)
        self.font_boss  = pygame.font.SysFont("couriernew", 14, italic=True)
        self.font_title = pygame.font.SysFont("couriernew", 28, bold=True)
        self.font_big   = pygame.font.SysFont("couriernew", 32, bold=True)
        self.font_huge  = pygame.font.SysFont("couriernew", 48, bold=True)
        self.font_dmg   = pygame.font.SysFont("couriernew", 13, bold=True)

        # --- Sprite loading ---
        script_dir = os.path.dirname(__file__)

        def load_img(name, scale=2.5):
            full_path = os.path.join(script_dir, name)
            try:
                img = pygame.image.load(full_path).convert_alpha()
                w, h = img.get_size()
                return pygame.transform.scale(img, (int(w * scale), int(h * scale)))
            except pygame.error:
                print(f"FOUT: Kan {full_path} niet vinden!")
                surf = pygame.Surface((100, 100))
                surf.fill(self.RED)
                return surf

        self.spr_f1_0 = load_img("f1_0.png")
        self.spr_f1_1 = load_img("f1_1.png")
        self.spr_f2_0 = load_img("f2_0.png", scale=2.8)
        self.spr_dog  = load_img(os.path.join("images", "dog.png"), scale=0.075)

        self.current_sprite = self.spr_f1_0

        # --- Polish helpers ---
        self.screen_shake   = ScreenShake()
        self.damage_numbers = []            # floating numbers
        self.enemy_flash    = 0             # frames of white-flash remaining
        self.hp_display     = 20.0          # smooth HP bar value

        # --- Game States ---
        self.state        = "MAIN_MENU"
        self.selected_btn = 0
        self.sub_selected = 0

        # --- Main Menu ---
        self.menu_options = ["START BATTLE", "TUTORIAL", "QUIT"]

        # --- Monologue ---
        self.monologue_index = 0
        self.monologue_text  = [
            "WinMan Prime: Welcome gamer! I can help u scan the entire system looking for bugs.",
            "WinMan Prime: I dont really like bugs to be honest.",
            "WinMan Prime: Everything looks... very stable, almost perfect :)",
            "WinMan Prime: No malware, no corrupt files, no unnecessary garbo that slows down the system.",
            "WinMan Prime: Except...",
            "WinMan Prime: YOU!!! >:(",
            "WinMan Prime: You are the worst thing that has every used this system.",
            "WinMan Prime: Time for a system purge! I am going to delete you!"
        ]
        self.message_text = self.monologue_text[0]

        # --- Player Stats ---
        self.hp     = 20
        self.max_hp = 20
        self.inventory = [
            {"name": "Cheese and ham sandwitch", "hp": 3},
            {"name": "Pancakes",                 "hp": 6}
        ]

        # --- Enemy Stats ---
        self.phase        = 1
        self.enemy_name   = "WinMan Prime"
        self.enemy_hp     = 150
        self.mercy_meter  = 0
        self.is_spareable = False
        self.act_options  = ["Check", "Compliment", "Hack", "Robot Dance"]

        self.boss_quotes_phase1 = ["System ERROR!", "01001001", "Overheating!", "Exit(0)", "FATAL ERROR"]
        self.boss_quotes_phase2 = ["...bad time.", "It's over buddy.", "OVERCLOCK MODE", "REBOOTING...", "ACCESS DENIED"]
        self.current_quote = "Loading..."

        # --- Layout ---
        self.boss_y          = 5
        self.battle_box_rect = pygame.Rect(BASE_WIDTH // 2 - 140, 95, 280, 85)
        self.tutorial_box_rect = pygame.Rect(BASE_WIDTH // 2 - 140, 45, 280, 75)
        self.box_rect        = self.battle_box_rect.copy()
        self.hp_bar_y        = 195
        self.btn_y           = 220
        self.btn_width       = 65
        self.btn_height      = 28

        # --- Mechanics ---
        self.soul_pos       = [self.box_rect.centerx, self.box_rect.centery]
        self.soul_speed     = 4.8
        self.timing_bar_x   = self.box_rect.left + 10
        self.timing_speed   = 7
        self.timing_dir     = 1
        self.bullets        = []
        self.attack_timer   = 0
        self.attack_type    = None
        self.invuln_timer   = 0
        self.invuln_duration = 14
        self.menu_exit_choice = 0

        # --- Tutorial ---
        self.tutorial_step         = 0
        self.tutorial_timer        = 0
        self.tutorial_demo_bullets = []
        self.demo_mercy            = 0

        self.tutorial_texts = [
            "Welcom to the tutorial human!\n\n"
            "This RED thing is your SOUL.\n"
            "Use ↑↓←→ to move it around.\n\n"
            "Press ENTER to continue.",

            "Avoid attacks!\n\n"
            "Enemies will try to hurt you.\n"
            "Move your SOUL to avoid them.\n"
            "Press ENTER to continue.",

            "FIGHT:\n\n"
            "Time your hit to get more damage.\n"
            "The better your timing the higher your damage!\n\n"
            "Press ENTER to swing.",

            "ACT:\n\n"
            "Use ACT to interact with the enemy.\n"
            "Choose 'Compliment' to fill the mercy meter.\n\n"
            "Press ENTER to give a compliment in this demo.",

            "MERCY:\n\n"
            "If the mercy meter is full the enemy name turns yellow.\n"
            "Spare them and they will go away!\n\n"
            "Press ENTER to continue.",

            "ITEM:\n\n"
            "Use items to heal your SOUL.\n\n"
            "You now know all mechanics!\n"
            "Press ENTER to continue."
        ]
        self.dog_easter_egg_used = False

        # --- Dev mode (Konami: ↑ ↑ ↓ ↓ ← → ← → at main menu) ---
        self._konami_sequence = [
            pygame.K_UP, pygame.K_UP, pygame.K_DOWN, pygame.K_DOWN,
            pygame.K_LEFT, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RIGHT
        ]
        self._konami_buffer  = []

        self._frame = 0

        self.dev_phase          = 1
        self.dev_selected       = 0
        self.dev_god_mode       = False
        self.dev_pressure_lock  = None
        self._dev_attacks_p1    = ["laser", "bouncing_balls", "rain", "spear_drop", "orb_burst"]
        self._dev_attacks_p2    = ["bone_wall", "circle_strike", "horizontal_laser",
                                   "cross_laser", "homing_orbs", "trident_rain", "chaos",
                                   "bouncing_balls_hard", "dog_joke"]


    def _pressure(self):
        """0.0 = first attempt  →  1.0 = fully ramped (after ~8 survived attacks)."""
        if getattr(self, "dev_pressure_lock", None) is not None:
            return self.dev_pressure_lock
        return min(1.0, getattr(self, "attacks_survived", 0) / 8.0)

    def start_enemy_attack(self):
        self.state      = "ENEMY_ATTACK"
        self.bullets    = []
        self.soul_pos   = [self.box_rect.centerx, self.box_rect.centery]
        self.current_quote = random.choice(
            self.boss_quotes_phase2 if self.phase == 2 else self.boss_quotes_phase1
        )

        p = self._pressure()

        if self.phase == 1:
            self.attack_timer = int(280 + 80 * p)
            self.attack_type = random.choice(["laser", "bouncing_balls", "rain", "spear_drop", "orb_burst"])
        else:
            self.attack_timer = int(360 + 60 * p)
            if not self.dog_easter_egg_used and random.randint(1, 50) == 1:
                self.attack_type = "dog_joke"
                self.attack_timer = 140
                self.dog_easter_egg_used = True
            else:
                self.attack_type = random.choice(
                    ["bone_wall", "circle_strike", "horizontal_laser",
                     "cross_laser", "homing_orbs", "trident_rain", "chaos",
                     "bouncing_balls_hard"]
                )

    def reset_battle(self):
        self.box_rect        = self.battle_box_rect.copy()
        self.hp              = 20
        self.hp_display      = 20.0
        self.enemy_hp        = 150
        self.phase           = 1
        self.mercy_meter     = 0
        self.is_spareable    = False
        self.current_sprite  = self.spr_f1_0
        self.monologue_index = 0
        self.message_text    = self.monologue_text[0]
        self.selected_btn    = 0
        self.sub_selected    = 0
        self.inventory = [
            {"name": "Cheese and ham sandwitch", "hp": 3},
            {"name": "Pancakes",                 "hp": 6}
        ]
        self.bullets          = []
        self.attack_timer     = 0
        self.attack_type      = None
        self.invuln_timer     = 0
        self.menu_exit_choice = 0
        self.timing_bar_x     = self.box_rect.left + 10
        self.timing_dir       = 1
        self.soul_pos         = [self.box_rect.centerx, self.box_rect.centery]
        self.damage_numbers   = []
        self.enemy_flash      = 0
        self.attacks_survived = 0

    def take_damage(self, amount):
        if self.invuln_timer > 0:
            return
        if getattr(self, "dev_god_mode", False):
            return
        self.hp          -= amount
        self.invuln_timer = self.invuln_duration
        # Screen shake — heavier hits shake harder
        shake_strength = 3 if amount < 1 else 5
        self.screen_shake.trigger(shake_strength, 8)

    def _deal_enemy_damage(self, dmg):
        """Apply damage to the enemy with flash + floating number."""
        self.enemy_hp -= int(dmg)
        self.enemy_flash = 6
        self.screen_shake.trigger(2, 5)
        x = BASE_WIDTH // 2 + random.randint(-20, 20)
        y = self.boss_y + 10 + random.randint(-5, 5)
        self.damage_numbers.append(
            DamageNumber(x, y, f"-{int(dmg)}", self.ORANGE, self.font_dmg)
        )

    def handle_selection(self):
        if self.selected_btn == 0:
            self.state        = "TARGET_SELECT"
            self.sub_selected = 0
        elif self.selected_btn == 1:
            self.state        = "ACT_MENU"
            self.sub_selected = 0
        elif self.selected_btn == 2:
            if self.inventory:
                self.state        = "ITEM_MENU"
                self.sub_selected = 0
            else:
                self.message_text = "You have nothing left!"
                self.state        = "MESSAGE"
        elif self.selected_btn == 3:
            self.state        = "MERCY_MENU"
            self.sub_selected = 0

    def _enter_dev_menu(self):
        """Set up the dev menu state."""
        self.reset_battle()
        self.state              = "DEV_MENU"
        self.dev_phase          = 1
        self.dev_selected       = 0
        self.dev_god_mode       = True     # god mode on by default in dev
        self.dev_pressure_lock  = None
        self.current_sprite     = self.spr_f1_0
        self.attacks_survived   = 0

    def _dev_launch(self, attack_name):
        """Launch a specific attack from the dev screen."""
        self.bullets        = []
        self.soul_pos       = [self.box_rect.centerx, self.box_rect.centery]
        self.attack_type    = attack_name
        self.current_quote  = f"[DEV] {attack_name}"
        # Reset per-attack state so restarts are always clean
        self._spear_pending   = []
        self._spear_safe_flash = 0
        self._bone_wave_index  = 0
        if self.dev_phase == 1:
            self.attack_timer = 400
        else:
            self.attack_timer = 500 if attack_name != "dog_joke" else 140
        self.state = "DEV_ATTACK"

    # -----------------------------------------------------------------------
    # EVENT HANDLING
    # -----------------------------------------------------------------------
    def handle_events(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.state == "MAIN_MENU":
            # --- Konami code detector ---
            self._konami_buffer.append(event.key)
            if len(self._konami_buffer) > len(self._konami_sequence):
                self._konami_buffer.pop(0)
            if self._konami_buffer == self._konami_sequence:
                self._konami_buffer = []
                self._enter_dev_menu()
                return

            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT):
                self.selected_btn = (self.selected_btn - 1) % 3
            if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT):
                self.selected_btn = (self.selected_btn + 1) % 3
            if event.key == pygame.K_RETURN:
                if self.selected_btn == 0:
                    self.reset_battle()
                    self.state = "MONOLOGUE"
                elif self.selected_btn == 1:
                    self.state              = "TUTORIAL"
                    self.box_rect           = self.tutorial_box_rect.copy()
                    self.tutorial_step      = 0
                    self.tutorial_timer     = 0
                    self.tutorial_demo_bullets = []
                    self.demo_mercy         = 0
                    self.timing_bar_x       = self.box_rect.left + 10
                    self.timing_dir         = 1
                    self.soul_pos           = [self.box_rect.centerx, self.box_rect.centery]
                elif self.selected_btn == 2:
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
            return

        if self.state == "TUTORIAL":
            if event.key == pygame.K_RETURN:
                if self.tutorial_step == 2:
                    dist  = abs(self.timing_bar_x - self.box_rect.centerx)
                    score = max(0, 25 - (dist // 6))
                    self.message_text = f"Timing score: {score}/25!"
                elif self.tutorial_step == 3:
                    self.demo_mercy   = min(100, self.demo_mercy + 50)
                    self.message_text = f"Compliment! Mercy +50% → {self.demo_mercy}%"
                elif self.tutorial_step == 4:
                    self.message_text = "SPARE succeeded! (demo)"
                if self.tutorial_step < len(self.tutorial_texts) - 1:
                    self.tutorial_step += 1
                else:
                    self.state    = "MAIN_MENU"
                    self.box_rect = self.battle_box_rect.copy()
                self.tutorial_demo_bullets = []
                self.timing_bar_x = self.box_rect.left + 10
                self.timing_dir   = 1
            return

        if self.state == "DEV_MENU":
            attacks = self._dev_attacks_p1 if self.dev_phase == 1 else self._dev_attacks_p2
            if event.key in (pygame.K_UP, pygame.K_w):
                self.dev_selected = (self.dev_selected - 1) % len(attacks)
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.dev_selected = (self.dev_selected + 1) % len(attacks)
            if event.key == pygame.K_RETURN:
                self._dev_launch(attacks[self.dev_selected])
                return
            if event.key == pygame.K_TAB:
                self.dev_phase      = 2 if self.dev_phase == 1 else 1
                self.dev_selected   = 0
                self.current_sprite = self.spr_f2_0 if self.dev_phase == 2 else self.spr_f1_0
            if event.key == pygame.K_g:
                self.dev_god_mode = not self.dev_god_mode
            if event.key == pygame.K_p:
                cycle = [None, 0.0, 0.5, 1.0]
                idx   = cycle.index(self.dev_pressure_lock)
                self.dev_pressure_lock = cycle[(idx + 1) % len(cycle)]
            if event.key == pygame.K_ESCAPE:
                self.state          = "MAIN_MENU"
                self.current_sprite = self.spr_f1_0
            return

        if self.state == "DEV_ATTACK":
            if event.key == pygame.K_ESCAPE:
                self.bullets      = []
                self.attack_timer = 0
                self.state        = "DEV_MENU"
            if event.key == pygame.K_r:
                self._dev_launch(self.attack_type)
            if event.key == pygame.K_g:
                self.dev_god_mode = not self.dev_god_mode
            return

        if self.state == "MERCY_MENU":
            if event.key == pygame.K_RETURN:
                if self.is_spareable and self.phase == 1:
                    self.message_text = "YOU WIN! WinMan lets you go."
                    self.state        = "WIN"
                else:
                    self.message_text = (
                        "WinMan ignores your pleads."
                        if self.phase == 1
                        else "PHASE 2: Mercy no longer exists."
                    )
                    self.state = "MESSAGE"
                return
            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"
            return

        if event.key == pygame.K_ESCAPE and self.state == "MAIN_MENU":
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))
            return

        if self.state == "MONOLOGUE":
            if event.key == pygame.K_RETURN:
                self.monologue_index += 1
                if self.monologue_index < len(self.monologue_text):
                    self.message_text = self.monologue_text[self.monologue_index]
                    if self.monologue_index >= 5:
                        self.current_sprite = self.spr_f1_1
                else:
                    self.state        = "MENU"
                    self.message_text = f"{self.enemy_name} blocks the way."

        elif self.state == "MENU":
            if event.key == pygame.K_LEFT:   self.selected_btn = (self.selected_btn - 1) % 4
            if event.key == pygame.K_RIGHT:  self.selected_btn = (self.selected_btn + 1) % 4
            if event.key == pygame.K_RETURN: self.handle_selection()
            if event.key == pygame.K_ESCAPE:
                self.menu_exit_choice = 0
                self.state            = "MENU_EXIT_POPUP"
                return

        elif self.state == "MENU_EXIT_POPUP":
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.menu_exit_choice = (self.menu_exit_choice - 1) % 3
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.menu_exit_choice = (self.menu_exit_choice + 1) % 3
            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"
                return
            if event.key == pygame.K_RETURN:
                if self.menu_exit_choice == 0:
                    self.reset_battle()
                    self.state = "MONOLOGUE"
                elif self.menu_exit_choice == 1:
                    self.state        = "MAIN_MENU"
                    self.selected_btn = 0
                else:
                    self.state = "MENU"
                return

        elif self.state == "TARGET_SELECT":
            if event.key in (pygame.K_UP, pygame.K_w):   self.sub_selected = 0
            if event.key in (pygame.K_DOWN, pygame.K_s): self.sub_selected = 0
            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"
                return
            if event.key == pygame.K_RETURN:
                self.state = "FIGHT_TIMING"
                return

        elif self.state in ["ACT_MENU", "ITEM_MENU"]:
            options = self.act_options if self.state == "ACT_MENU" else self.inventory
            limit   = len(options)
            if event.key == pygame.K_DOWN: self.sub_selected = (self.sub_selected + 1) % limit
            if event.key == pygame.K_UP:   self.sub_selected = (self.sub_selected - 1) % limit
            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"
                return
            if event.key == pygame.K_RETURN:
                if self.state == "ACT_MENU":
                    opt = self.act_options[self.sub_selected]
                    if opt == "Check":
                        self.message_text = (
                            f"{self.enemy_name}: ATK 3 DEF 5."
                            if self.phase == 1
                            else "ATK 9 DEF 9. OVERCLOCKED."
                        )
                    elif opt == "Compliment":
                        self.message_text = (
                            "You call him a good OS.  Mercy +50%!"
                            if self.phase == 1
                            else "Compliments are useless."
                        )
                        if self.phase == 1:
                            self.mercy_meter += 50
                    elif opt == "Hack":
                        self.message_text = (
                            "You try to bypass his firewall."
                            if self.phase == 1
                            else "Hack failed: 403 Forbidden."
                        )
                        if self.phase == 1:
                            self.mercy_meter += 20
                    elif opt == "Robot Dance":
                        self.message_text = (
                            "You do the robot dance. He looks confused."
                            if self.phase == 1
                            else "Too late for dancing."
                        )
                        if self.phase == 1:
                            self.mercy_meter += 40
                    if self.mercy_meter >= 100 and self.phase == 1:
                        self.is_spareable = True
                else:
                    item = self.inventory.pop(self.sub_selected)
                    self.hp          = min(self.max_hp, self.hp + item["hp"])
                    self.message_text = f"You use {item['name']}.  +{item['hp']} HP!"
                self.state = "MESSAGE"

        elif self.state == "FIGHT_TIMING":
            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"
                return
            if event.key == pygame.K_RETURN:
                dist = abs(self.timing_bar_x - self.box_rect.centerx)
                dmg  = max(0, 20 - (dist // 8))
                self._deal_enemy_damage(dmg)
                self.message_text = f"BOOM!  You dealt {int(dmg)} damage!"
                self.state        = "MESSAGE"
                return

        elif self.state == "MESSAGE":
            if event.key == pygame.K_RETURN:
                if self.enemy_hp <= 0 and self.phase == 2:
                    self.state = "WIN"
                elif self.enemy_hp <= 0 and self.phase == 1:
                    self.phase        = 2
                    self.enemy_hp     = 300
                    self.mercy_meter  = 0
                    self.is_spareable = False
                    self.current_sprite = self.spr_f2_0
                    self.message_text = "WinMan Prime forces an UPDATE to PHASE 2!"
                    self.state        = "MESSAGE"
                else:
                    self.attacks_survived = getattr(self, "attacks_survived", 0) + 1
                    self.start_enemy_attack()

        elif self.state == "GAME_OVER":
            if event.key == pygame.K_RETURN:
                self.reset_battle()
                self.state = "MONOLOGUE"
            elif event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

        elif self.state == "WIN":
            if event.key == pygame.K_RETURN:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    # -----------------------------------------------------------------------
    # UPDATE
    # -----------------------------------------------------------------------
    def update(self, dt):
        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        if self.enemy_flash > 0:
            self.enemy_flash -= 1
        self._frame += 1

        # Smooth HP bar
        self.hp_display += (self.hp - self.hp_display) * 0.12

        # Update floating numbers
        for dn in self.damage_numbers:
            dn.update()
        self.damage_numbers = [dn for dn in self.damage_numbers if dn.alive]

        # Ensure attacks_survived exists (in case reset was skipped)
        if not hasattr(self, "attacks_survived"):
            self.attacks_survived = 0

        p = self._pressure()   # learnable pressure scalar

        # ===== TUTORIAL =====
        if self.state == "TUTORIAL":
            self.tutorial_timer += 1
            if self.tutorial_step == 1:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]    or keys[pygame.K_w]: self.soul_pos[1] -= self.soul_speed
                if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.soul_pos[1] += self.soul_speed
                if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.soul_pos[0] -= self.soul_speed
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.soul_pos[0] += self.soul_speed
                self.soul_pos[0] = max(self.box_rect.left + 6,   min(self.box_rect.right - 6,  self.soul_pos[0]))
                self.soul_pos[1] = max(self.box_rect.top  + 6,   min(self.box_rect.bottom - 6, self.soul_pos[1]))
                if self.tutorial_timer % 12 == 0:
                    self.tutorial_demo_bullets.append({
                        "pos": [float(random.randint(self.box_rect.left + 20, self.box_rect.right - 20)),
                                float(self.box_rect.top - 10)],
                        "vel": [0, 4.0]
                    })
                for i in range(len(self.tutorial_demo_bullets) - 1, -1, -1):
                    b = self.tutorial_demo_bullets[i]
                    b["pos"][0] += b["vel"][0]
                    b["pos"][1] += b["vel"][1]
                    if b["pos"][1] > self.box_rect.bottom + 20:
                        del self.tutorial_demo_bullets[i]
            if self.tutorial_step == 2:
                self.timing_bar_x += self.timing_speed * self.timing_dir
                if self.timing_bar_x > self.box_rect.right or self.timing_bar_x < self.box_rect.left:
                    self.timing_dir *= -1
            return

        # ===== FIGHT TIMING =====
        if self.state == "FIGHT_TIMING":
            self.timing_bar_x += self.timing_speed * self.timing_dir
            if self.timing_bar_x > self.box_rect.right or self.timing_bar_x < self.box_rect.left:
                self.timing_dir *= -1

        # ===== ENEMY ATTACK / DEV ATTACK =====
        elif self.state in ("ENEMY_ATTACK", "DEV_ATTACK"):
            # In dev mode, use dev_phase instead of self.phase for spawning
            if self.state == "DEV_ATTACK":
                self.phase = self.dev_phase
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:    self.soul_pos[1] -= self.soul_speed
            if keys[pygame.K_DOWN]:  self.soul_pos[1] += self.soul_speed
            if keys[pygame.K_LEFT]:  self.soul_pos[0] -= self.soul_speed
            if keys[pygame.K_RIGHT]: self.soul_pos[0] += self.soul_speed
            self.soul_pos[0] = max(self.box_rect.left + 6,   min(self.box_rect.right - 6,  self.soul_pos[0]))
            self.soul_pos[1] = max(self.box_rect.top  + 6,   min(self.box_rect.bottom - 6, self.soul_pos[1]))

            # ---- Spawn logic (pressure-aware) ----

            if self.phase == 1:
                # ---- LASER (vertical) ----
                # Telegraph is long and visible: blue → yellow → fires RED
                # Spawn rate slows early on so player can read the pattern
                laser_interval = int(55 - 15 * p)   # 55f → 40f  as pressure rises
                if self.attack_type == "laser" and self.attack_timer % laser_interval == 0:
                    # 50% player-aimed, 50% random — same ratio always so it's learnable
                    if random.random() < 0.5:
                        target_x = int(self.soul_pos[0] + random.randint(-12, 12))
                        laser_x  = max(self.box_rect.left + 20, min(self.box_rect.right - 20, target_x))
                    else:
                        laser_x = random.randint(self.box_rect.left + 20, self.box_rect.right - 20)
                    # telegraph_warn: blue phase; telegraph_ready: yellow phase (dodge NOW)
                    self.bullets.append({
                        "type": "laser",
                        "x": laser_x,
                        "timer": 28,
                        "telegraph": 30,        # yellow "ready" phase
                        "telegraph_warn": 20,   # extra blue "incoming" phase
                    })

                # ---- BOUNCING BALLS ----
                # Early: slower balls from one edge.  Later: multiple edges.
                ball_interval = int(55 - 13 * p)
                max_balls     = int(2 + 3 * p)          # 2 → 5
                ball_speed_x  = 2.6 + 0.6 * p
                ball_speed_y  = 1.6 + 0.6 * p
                if self.attack_type == "bouncing_balls" and self.attack_timer % ball_interval == 0 and len(self.bullets) < max_balls:
                    edges = ["left", "right"] if p < 0.4 else ["left", "right", "top", "bottom"]
                    spawn_edge = random.choice(edges)
                    if spawn_edge == "left":
                        pos = [float(self.box_rect.left + 10),
                               float(random.randint(self.box_rect.top + 12, self.box_rect.bottom - 12))]
                        vel = [ball_speed_x, random.choice([-ball_speed_y, ball_speed_y])]
                    elif spawn_edge == "right":
                        pos = [float(self.box_rect.right - 10),
                               float(random.randint(self.box_rect.top + 12, self.box_rect.bottom - 12))]
                        vel = [-ball_speed_x, random.choice([-ball_speed_y, ball_speed_y])]
                    elif spawn_edge == "top":
                        pos = [float(random.randint(self.box_rect.left + 12, self.box_rect.right - 12)),
                               float(self.box_rect.top + 10)]
                        vel = [random.choice([-ball_speed_y, ball_speed_y]), ball_speed_x]
                    else:
                        pos = [float(random.randint(self.box_rect.left + 12, self.box_rect.right - 12)),
                               float(self.box_rect.bottom - 10)]
                        vel = [random.choice([-ball_speed_y, ball_speed_y]), -ball_speed_x]
                    # Never spawn on top of player
                    if math.hypot(pos[0] - self.soul_pos[0], pos[1] - self.soul_pos[1]) > 18:
                        self.bullets.append({"type": "bounce", "pos": pos, "vel": vel})

                # ---- RAIN ----
                rain_interval = int(16 - 6 * p)        # 16f → 10f
                if self.attack_type == "rain" and self.attack_timer % rain_interval == 0:
                    self.bullets.append({
                        "type": "normal",
                        "pos": [float(random.randint(self.box_rect.left, self.box_rect.right)),
                                float(self.box_rect.top - 10)],
                        "vel": [0, 3.5 + 0.5 * p]
                    })

                # ---- SPEAR DROP ----
                # Phase 1: mark the safe lane FIRST, then drop spears after a delay.
                # We use a pending-spear system: on the trigger frame we store the
                # wave and a countdown; when the countdown hits 0 the spears actually spawn.
                spear_interval = int(56 - 12 * p)
                if self.attack_type == "spear_drop":
                    # Initialise the pending list if needed
                    if not hasattr(self, "_spear_pending"):
                        self._spear_pending = []

                    # Trigger a new wave
                    if self.attack_timer % spear_interval == 0:
                        lane_count = 6
                        safe_lane  = random.randint(0, lane_count - 1)
                        lane_width = self.box_rect.width / lane_count
                        self._spear_safe_lane  = safe_lane
                        self._spear_lane_w     = lane_width
                        self._spear_safe_flash = 36          # show hint for 36 frames
                        # Queue up the actual spears with a 30-frame delay
                        wave = []
                        for lane in range(lane_count):
                            if lane == safe_lane:
                                continue
                            x = int(self.box_rect.left + lane * lane_width + lane_width / 2)
                            wave.append({
                                "type": "spear",
                                "pos": [float(x), float(self.box_rect.top - 10)],
                                "vel": [0, 3.8 + 0.4 * p]
                            })
                        self._spear_pending.append({"delay": 30, "wave": wave})

                    # Tick pending waves and release when delay expires
                    for pw in list(self._spear_pending):
                        pw["delay"] -= 1
                        if pw["delay"] <= 0:
                            self.bullets.extend(pw["wave"])
                            self._spear_pending.remove(pw)

                # ---- ORB BURST ----
                if self.attack_type == "orb_burst" and self.attack_timer % 55 == 0:
                    spread = 0.7 + 0.4 * p      # angles spread more over time
                    for spawn_pos in (
                        (float(self.box_rect.left  + 8), float(self.box_rect.centery)),
                        (float(self.box_rect.right - 8), float(self.box_rect.centery))
                    ):
                        dx   = self.soul_pos[0] - spawn_pos[0]
                        dy   = self.soul_pos[1] - spawn_pos[1]
                        dist = math.hypot(dx, dy) + 0.0001
                        bvx  = (dx / dist) * 2.5
                        bvy  = (dy / dist) * 2.5
                        for offset in (-spread, 0.0, spread):
                            self.bullets.append({
                                "type": "normal",
                                "pos": [spawn_pos[0], spawn_pos[1]],
                                "vel": [bvx + offset * (-0.4 if spawn_pos[0] > self.box_rect.centerx else 0.4),
                                        bvy + offset * 0.3]
                            })

            else:   # Phase 2 — same learnable approach
                if self.attack_type in ("horizontal_laser", "cross_laser"):
                    self.bullets = [b for b in self.bullets if b["type"] in ("laser", "h_laser")]

                # ---- BONE WALL ----
                # Sans-style: bones slide in one lane at a time, strictly alternating
                # top → bottom → top → bottom so the player can weave between them.
                # A bone_wave_index (0=top, 1=bottom) tracks which row fires next.
                # Speed scales with pressure but is always slow enough to be readable.
                bone_interval = int(23 - 10 * p)   # 44f → 34f  (faster at full pressure)
                bone_speed    = 2.8 + 0.8 * p       # 2.8 → 3.6
                if self.attack_type == "bone_wall":
                    if not hasattr(self, "_bone_wave_index"):
                        self._bone_wave_index = 0
                    if self.attack_timer % bone_interval == 0:
                        if self._bone_wave_index == 0:
                            # Top lane: bone enters from the left
                            y = float(self.box_rect.top + self.box_rect.height // 4)
                            self.bullets.append({"type": "bone", "pos": [float(self.box_rect.left - 8), y],
                                                 "vel": [bone_speed, 0]})
                        else:
                            # Bottom lane: bone enters from the right
                            y = float(self.box_rect.bottom - self.box_rect.height // 4)
                            self.bullets.append({"type": "bone", "pos": [float(self.box_rect.right + 8), y],
                                                 "vel": [-bone_speed, 0]})
                        self._bone_wave_index = 1 - self._bone_wave_index

                # ---- BOUNCING BALLS HARD (Phase 2) ----
                # More balls, faster, all 4 edges, small gap enforced so it stays fair.
                p2_ball_interval = int(28 - 8 * p)     # 28f → 20f
                p2_ball_max      = int(5 + 3 * p)       # 5 → 8 balls max
                p2_ball_spd      = 3.4 + 0.8 * p        # 3.4 → 4.2
                if self.attack_type == "bouncing_balls_hard" and self.attack_timer % p2_ball_interval == 0 and len(self.bullets) < p2_ball_max:
                    spawn_edge = random.choice(["left", "right", "top", "bottom"])
                    sx_var = p2_ball_spd * random.choice([-1, 1]) * (0.4 + 0.4 * random.random())
                    if spawn_edge == "left":
                        pos = [float(self.box_rect.left  + 10),
                               float(random.randint(self.box_rect.top + 10, self.box_rect.bottom - 10))]
                        vel = [p2_ball_spd, sx_var]
                    elif spawn_edge == "right":
                        pos = [float(self.box_rect.right - 10),
                               float(random.randint(self.box_rect.top + 10, self.box_rect.bottom - 10))]
                        vel = [-p2_ball_spd, sx_var]
                    elif spawn_edge == "top":
                        pos = [float(random.randint(self.box_rect.left + 10, self.box_rect.right - 10)),
                               float(self.box_rect.top + 10)]
                        vel = [sx_var, p2_ball_spd]
                    else:
                        pos = [float(random.randint(self.box_rect.left + 10, self.box_rect.right - 10)),
                               float(self.box_rect.bottom - 10)]
                        vel = [sx_var, -p2_ball_spd]
                    # Don't spawn right on the player
                    if math.hypot(pos[0] - self.soul_pos[0], pos[1] - self.soul_pos[1]) > 16:
                        self.bullets.append({"type": "bounce", "pos": pos, "vel": vel})

                # ---- CIRCLE STRIKE ----
                if self.attack_type == "circle_strike" and self.attack_timer % 70 == 0:
                    bullet_count = 10
                    ring_count   = int(1 + p)   # 1 ring early, 2 rings at full pressure
                    radius       = min(self.box_rect.width, self.box_rect.height) // 2 + 20
                    for _ in range(ring_count):
                        cx = random.randint(self.box_rect.left + 45, self.box_rect.right - 45)
                        cy = random.randint(self.box_rect.top  + 20, self.box_rect.bottom - 20)
                        gap_start   = random.randint(0, bullet_count - 1)
                        gap_indices = {gap_start, (gap_start + 1) % bullet_count}   # 2-bullet gap (always safe)
                        for i in range(bullet_count):
                            if i in gap_indices:
                                continue
                            angle = (math.pi * 2 / bullet_count) * i
                            self.bullets.append({
                                "type": "normal",
                                "pos": [cx + math.cos(angle) * radius,
                                        cy + math.sin(angle) * radius],
                                "vel": [-math.cos(angle) * 2.2,
                                        -math.sin(angle) * 2.2]
                            })

                # ---- HORIZONTAL LASER ----
                h_laser_interval = int(32 - 8 * p)   # was 45-10 — much faster now
                if self.attack_type == "horizontal_laser" and self.attack_timer % h_laser_interval == 0:
                    if not any(b["type"] == "h_laser" for b in self.bullets):
                        lane_center = random.choice([
                            self.box_rect.top    + self.box_rect.height // 6,
                            self.box_rect.centery,
                            self.box_rect.bottom - self.box_rect.height // 6
                        ])
                        beam_height = self.box_rect.height // 3
                        y_top = max(self.box_rect.top, int(lane_center - beam_height // 2))
                        y_top = min(y_top, self.box_rect.bottom - beam_height)
                        self.bullets.append({
                            "type": "h_laser",
                            "y": y_top,
                            "height": beam_height,
                            "timer": 20,           # was 26 — active shorter but faster overall
                            "telegraph": 14,        # was 20
                            "telegraph_warn": 14,   # was 18
                        })

                # ---- CROSS LASER ----
                if self.attack_type == "cross_laser" and self.attack_timer % 40 == 0:  # was 55
                    target_x    = random.randint(self.box_rect.left + 20, self.box_rect.right - 20)
                    lane_center = random.choice([
                        self.box_rect.top    + self.box_rect.height // 6,
                        self.box_rect.centery,
                        self.box_rect.bottom - self.box_rect.height // 6
                    ])
                    beam_height = self.box_rect.height // 3
                    y_top = max(self.box_rect.top, int(lane_center - beam_height // 2))
                    y_top = min(y_top, self.box_rect.bottom - beam_height)
                    self.bullets.append({"type": "laser",   "x": target_x, "timer": 20, "telegraph": 18, "telegraph_warn": 12})
                    self.bullets.append({"type": "h_laser", "y": y_top, "height": beam_height, "timer": 16, "telegraph": 16, "telegraph_warn": 10})

                # ---- HOMING ORBS ----
                homing_interval = int(65 - 15 * p)
                if self.attack_type == "homing_orbs" and self.attack_timer % homing_interval == 0:
                    if not any(b["type"] == "h_laser" for b in self.bullets):
                        orb_count = int(2 + p)   # 2 → 3
                        for _ in range(orb_count):
                            spawn_side = random.choice(["top", "left", "right"])
                            if spawn_side == "top":
                                sx = float(random.randint(self.box_rect.left + 8, self.box_rect.right - 8))
                                sy = float(self.box_rect.top - 12)
                            elif spawn_side == "left":
                                sx = float(self.box_rect.left  - 12)
                                sy = float(random.randint(self.box_rect.top + 8, self.box_rect.bottom - 8))
                            else:
                                sx = float(self.box_rect.right + 12)
                                sy = float(random.randint(self.box_rect.top + 8, self.box_rect.bottom - 8))
                            self.bullets.append({"type": "homing", "pos": [sx, sy], "vel": [0.0, 0.0]})

                # ---- TRIDENT RAIN ----
                # Always 3 spears with a clear gap on one side the player can slide into.
                # Spawn interval: 70f early → 55f at full pressure.
                # Speed: 2.8 early → 3.4 at full pressure (was 4.0-4.2, way too fast).
                trident_interval = int(70 - 15 * p)
                trident_speed    = 2.8 + 0.6 * p
                if self.attack_type == "trident_rain" and self.attack_timer % trident_interval == 0:
                    # Centre always at least 55px from each wall so a side gap exists
                    margin = 55
                    cx = random.randint(self.box_rect.left + margin, self.box_rect.right - margin)
                    # Wider offsets (±36 vs old ±24) = bigger readable gaps
                    offsets = (-36, 0, 36)
                    pattern = random.choice(["straight", "left_sweep", "right_sweep"])
                    for idx, offset in enumerate(offsets):
                        if pattern == "straight":
                            vx = 0.0
                        elif pattern == "left_sweep":
                            vx = -0.8 + idx * 0.4   # -0.8, -0.4, 0.0
                        else:
                            vx =  0.0 + idx * 0.4   #  0.0,  0.4, 0.8
                        self.bullets.append({
                            "type": "spear",
                            "pos": [float(cx + offset), float(self.box_rect.top - 10)],
                            "vel": [vx, trident_speed]
                        })

                # ---- CHAOS ----
                if self.attack_type == "chaos":
                    if self.attack_timer % 55 == 0:
                        lane_center = random.choice([
                            self.box_rect.top    + self.box_rect.height // 6,
                            self.box_rect.centery,
                            self.box_rect.bottom - self.box_rect.height // 6
                        ])
                        beam_height = self.box_rect.height // 3
                        y_top = max(self.box_rect.top, int(lane_center - beam_height // 2))
                        y_top = min(y_top, self.box_rect.bottom - beam_height)
                        self.bullets.append({
                            "type": "h_laser",
                            "y": y_top, "height": beam_height,
                            "timer": 22, "telegraph": 28, "telegraph_warn": 16
                        })
                    if self.attack_timer % 90 == 0:
                        self.bullets.append({
                            "type": "normal",
                            "pos": [float(random.randint(self.box_rect.left + 8, self.box_rect.right - 8)),
                                    float(self.box_rect.top - 12)],
                            "vel": [0, 3.2 + 0.4 * p]
                        })

            # ---- Bullet movement & collision ----
            player_rect = pygame.Rect(int(self.soul_pos[0] - 4), int(self.soul_pos[1] - 4), 8, 8)
            for i in range(len(self.bullets) - 1, -1, -1):
                b = self.bullets[i]

                # Delayed bones wait before moving
                if b.get("delay", 0) > 0:
                    b["delay"] -= 1
                    continue

                # ---------- LASER (vertical) ----------
                if b["type"] == "laser":
                    if b.get("telegraph_warn", 0) > 0:
                        b["telegraph_warn"] -= 1
                    elif b["telegraph"] > 0:
                        b["telegraph"] -= 1
                    else:
                        b["timer"] -= 1
                        if player_rect.colliderect(pygame.Rect(b["x"] - 6, self.box_rect.top, 12, self.box_rect.height)):
                            self.take_damage(0.9)
                        if b["timer"] <= 0:
                            del self.bullets[i]
                    continue

                # ---------- H_LASER (horizontal) ----------
                if b["type"] == "h_laser":
                    if b.get("telegraph_warn", 0) > 0:
                        b["telegraph_warn"] -= 1
                    elif b["telegraph"] > 0:
                        b["telegraph"] -= 1
                    else:
                        b["timer"] -= 1
                        if player_rect.colliderect(
                            pygame.Rect(self.box_rect.left, b["y"], self.box_rect.width, b["height"])
                        ):
                            self.take_damage(0.9)
                        if b["timer"] <= 0:
                            del self.bullets[i]
                    continue

                # ---------- SPEAR ----------
                if b["type"] == "spear":
                    b["pos"][0] += b["vel"][0]
                    b["pos"][1] += b["vel"][1]
                    spear_hitbox = pygame.Rect(int(b["pos"][0] - 3), int(b["pos"][1] - 14), 6, 28)
                    if player_rect.colliderect(spear_hitbox):
                        self.take_damage(1.0)
                        del self.bullets[i]
                        continue
                    if not self.box_rect.inflate(30, 40).collidepoint(b["pos"][0], b["pos"][1]):
                        del self.bullets[i]
                    continue

                # ---------- HOMING ----------
                if b["type"] == "homing":
                    dx   = self.soul_pos[0] - b["pos"][0]
                    dy   = self.soul_pos[1] - b["pos"][1]
                    dist = math.hypot(dx, dy) + 0.0001
                    # Turn speed is gentle early, snappier at full pressure
                    turn = 0.04 + 0.04 * p
                    target_vx = (dx / dist) * 2.0
                    target_vy = (dy / dist) * 2.0
                    b["vel"][0] += (target_vx - b["vel"][0]) * turn
                    b["vel"][1] += (target_vy - b["vel"][1]) * turn
                    b["pos"][0] += b["vel"][0]
                    b["pos"][1] += b["vel"][1]
                    bullet_hitbox = pygame.Rect(int(b["pos"][0] - 4), int(b["pos"][1] - 4), 8, 8)
                    if player_rect.colliderect(bullet_hitbox):
                        self.take_damage(0.9)
                        del self.bullets[i]
                        continue
                    if not self.box_rect.inflate(80, 80).collidepoint(b["pos"][0], b["pos"][1]):
                        del self.bullets[i]
                    continue

                # ---------- Everything else ----------
                b["pos"][0] += b["vel"][0]
                b["pos"][1] += b["vel"][1]

                if b["type"] == "bounce":
                    if b["pos"][0] <= self.box_rect.left  or b["pos"][0] >= self.box_rect.right:
                        b["vel"][0] *= -1
                    if b["pos"][1] <= self.box_rect.top   or b["pos"][1] >= self.box_rect.bottom:
                        b["vel"][1] *= -1

                if b["type"] == "bone":
                    bullet_hitbox = pygame.Rect(int(b["pos"][0] - 4), int(b["pos"][1] - 30), 8, 60)
                else:
                    size = 6
                    bullet_hitbox = pygame.Rect(int(b["pos"][0] - size // 2), int(b["pos"][1] - size // 2), size, size)

                if player_rect.colliderect(bullet_hitbox):
                    dmg = 0.9 if b["type"] == "bone" else 1
                    self.take_damage(dmg)
                    if b["type"] not in ("bone", "bounce"):
                        del self.bullets[i]
                elif b["type"] not in ("bounce",) and not self.box_rect.inflate(60, 60).collidepoint(b["pos"][0], b["pos"][1]):
                    del self.bullets[i]

            # Tick down safe-lane flash timer
            if hasattr(self, "_spear_safe_flash") and self._spear_safe_flash > 0:
                self._spear_safe_flash -= 1

            self.attack_timer -= 1
            if self.hp <= 0 and self.state != "DEV_ATTACK":
                self.state = "GAME_OVER"
            elif self.attack_timer <= 0:
                if self.state == "DEV_ATTACK":
                    self.bullets  = []
                    self.state    = "DEV_MENU"
                else:
                    self.attacks_survived += 1
                    self.state = "MENU"

    # -----------------------------------------------------------------------
    # DRAW HELPERS
    # -----------------------------------------------------------------------
    def draw_soul(self, surface, x, y, size=3):
        # Flash white during invulnerability
        color = self.WHITE if (self.invuln_timer > 0 and self.invuln_timer % 4 < 2) else self.RED
        pygame.draw.polygon(surface, color, [(x, y - size), (x + size, y), (x, y + size), (x - size, y)])

    def draw_text_wrapped(self, surface, text, rect, font, color, top_padding=15, line_height=18):
        paragraphs = text.split('\n')
        y = rect.top + top_padding
        for para in paragraphs:
            if not para.strip():
                y += line_height
                continue
            words        = para.split(' ')
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if font.size(test_line)[0] < rect.width - 20:
                    current_line = test_line
                else:
                    if current_line:
                        surface.blit(font.render(current_line.strip(), True, color), (rect.left + 10, y))
                        y += line_height
                    current_line = word + " "
            if current_line:
                surface.blit(font.render(current_line.strip(), True, color), (rect.left + 10, y))
                y += line_height

    def _draw_laser_telegraph(self, surface, b):
        """Render a vertical laser with a 3-stage colour cue: blue → yellow → red beam."""
        warn_active  = b.get("telegraph_warn", 0) > 0
        ready_active = b["telegraph"] > 0 and not warn_active

        if warn_active:
            # Stage 1: thin blue line — "something is coming"
            pygame.draw.line(surface, self.BLUE,
                             (b["x"], self.box_rect.top), (b["x"], self.box_rect.bottom), 2)
        elif ready_active:
            # Stage 2: yellow line — "dodge NOW"
            # Pulse using telegraph counter
            alpha_frac = b["telegraph"] / 30   # fades in
            r = int(255 * alpha_frac)
            g = int(255 * alpha_frac)
            col = (min(255, r), min(255, g), 0)
            pygame.draw.line(surface, col,
                             (b["x"], self.box_rect.top), (b["x"], self.box_rect.bottom), 3)
        else:
            pygame.draw.line(surface, self.RED,
                             (b["x"], self.box_rect.top), (b["x"], self.box_rect.bottom), 10)

    def _draw_h_laser_telegraph(self, surface, b):
        warn_active  = b.get("telegraph_warn", 0) > 0
        ready_active = b["telegraph"] > 0 and not warn_active
        y_mid        = b["y"] + b["height"] // 2

        if warn_active:
            pygame.draw.line(surface, self.BLUE,
                             (self.box_rect.left, y_mid), (self.box_rect.right, y_mid), 2)
        elif ready_active:
            alpha_frac = b["telegraph"] / 22
            col = (min(255, int(255 * alpha_frac)), min(255, int(255 * alpha_frac)), 0)
            pygame.draw.line(surface, col,
                             (self.box_rect.left, y_mid), (self.box_rect.right, y_mid), 3)
        else:
            pygame.draw.rect(surface, self.RED,
                             (self.box_rect.left, b["y"], self.box_rect.width, b["height"]))

    # DRAW

    def draw(self, surface):
        # screen shake
        ox, oy = self.screen_shake.get_offset()

        if ox != 0 or oy != 0:
            temp = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
            self._draw_scene(temp)
            surface.blit(temp, (ox, oy))
        else:
            self._draw_scene(surface)

        for dn in self.damage_numbers:
            dn.draw(surface)

    def _draw_button(self, surface, rect, label, font, active, frame=0):
        border_col = self.YELLOW if active else (80, 80, 80)
        fill_col   = (30, 30, 0)  if active else (10, 10, 10)
        pygame.draw.rect(surface, fill_col,   rect)
        pygame.draw.rect(surface, border_col, rect, 2)
        clen = 5
        for cx, cy, dx, dy in [
            (rect.left,       rect.top,    1,  1),
            (rect.right - 1,  rect.top,   -1,  1),
            (rect.left,       rect.bottom,-1, -1),
            (rect.right - 1,  rect.bottom,-1, -1),
        ]:
            pygame.draw.line(surface, self.WHITE,
                             (cx, cy), (cx + dx * clen, cy), 1)
            pygame.draw.line(surface, self.WHITE,
                             (cx, cy), (cx, cy + dy * clen), 1)
        txt_col = self.YELLOW if active else self.WHITE
        txt = font.render(label, True, txt_col)
        surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                           rect.centery - txt.get_height() // 2))
        if active and (frame // 8) % 2 == 0:
            self.draw_soul(surface, rect.left - 10, rect.centery, 4)

    def _draw_scanlines(self, surface, alpha=18):
        scan = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        for y in range(0, BASE_HEIGHT, 2):
            pygame.draw.line(scan, (0, 0, 0, alpha), (0, y), (BASE_WIDTH, y))
        surface.blit(scan, (0, 0))

    def _draw_scene(self, surface):
        surface.fill(self.BLACK)

        # MAIN MENU
        if self.state == "MAIN_MENU":
            f = self._frame
            for i in range(18):
                seed = i * 137
                x = (seed * 31 + f * (1 + i % 3)) % BASE_WIDTH
                y = (seed * 17 + f * (1 + i % 2)) % BASE_HEIGHT
                r = 1 + (i % 3)
                alpha_dot = 60 + (i % 3) * 30
                dot_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(dot_surf, (255, 255, 0, alpha_dot), (r, r), r)
                surface.blit(dot_surf, (x, y))

            # Title
            for offset, alpha in [(2, 60), (0, 255)]:
                col = (255, 220, 0) if offset == 0 else (120, 80, 0)
                t1 = self.font_huge.render("WINMAN", True, col)
                t2 = self.font_huge.render("PRIME",  True, col)
                surface.blit(t1, (BASE_WIDTH // 2 - t1.get_width() // 2 + offset,  52 + offset))
                surface.blit(t2, (BASE_WIDTH // 2 - t2.get_width() // 2 + offset, 100 + offset))

            pulse = int(180 + 75 * math.sin(f * 0.06))
            line_col = (pulse, pulse, 0)
            pygame.draw.line(surface, line_col, (60, 150), (BASE_WIDTH - 60, 150), 2)

            # Subtitle
            sub = self.font_main.render("~ SYSTEM PURGE BATTLE ~", True, self.ORANGE)
            surface.blit(sub, (BASE_WIDTH // 2 - sub.get_width() // 2, 158))

            pygame.draw.line(surface, (50, 50, 50), (60, 175), (BASE_WIDTH - 60, 175), 1)

            # Menu buttons
            btn_w, btn_h = 160, 26
            btn_x = BASE_WIDTH // 2 - btn_w // 2
            btn_labels = ["START BATTLE", "TUTORIAL", "QUIT"]
            for i, label in enumerate(btn_labels):
                r = pygame.Rect(btn_x, 184 + i * 34, btn_w, btn_h)
                self._draw_button(surface, r, label, self.font_main,
                                  i == self.selected_btn, f)

            hint_alpha = int(140 + 115 * math.sin(f * 0.05))
            hint_surf  = self.font_ui.render("", True, self.WHITE)
            hint_surf.set_alpha(hint_alpha)
            surface.blit(hint_surf, (BASE_WIDTH // 2 - hint_surf.get_width() // 2, BASE_HEIGHT - 28))

            self._draw_scanlines(surface)
            return

        #  DEV MENU
        if self.state == "DEV_MENU":
            hdr = self.font_title.render("// DEV MODE //", True, self.GREEN)
            surface.blit(hdr, (BASE_WIDTH // 2 - hdr.get_width() // 2, 8))
            pygame.draw.line(surface, self.GREEN, (20, 36), (BASE_WIDTH - 20, 36), 1)

            phase_col = self.ORANGE if self.dev_phase == 2 else self.CYAN
            ph_txt = self.font_main.render(
                f"PHASE {self.dev_phase}  ({'OVERCLOCK' if self.dev_phase == 2 else 'NORMAL'})",
                True, phase_col
            )
            surface.blit(ph_txt, (BASE_WIDTH // 2 - ph_txt.get_width() // 2, 42))

            p_label = (
                f"PRESSURE: {self.dev_pressure_lock:.1f} (locked)"
                if self.dev_pressure_lock is not None
                else f"PRESSURE: live ({self._pressure():.2f})"
            )
            god_label = "GOD: ON " if self.dev_god_mode else "GOD: OFF"
            status = self.font_ui.render(
                f"{god_label}   {p_label}", True,
                self.GREEN if self.dev_god_mode else self.RED
            )
            surface.blit(status, (BASE_WIDTH // 2 - status.get_width() // 2, 58))
            pygame.draw.line(surface, (60, 60, 60), (20, 74), (BASE_WIDTH - 20, 74), 1)

            # Attack list
            attacks = self._dev_attacks_p1 if self.dev_phase == 1 else self._dev_attacks_p2
            list_top = 80
            for i, atk in enumerate(attacks):
                is_sel = (i == self.dev_selected)
                col    = self.YELLOW if is_sel else self.WHITE
                prefix = "> " if is_sel else "  "
                txt    = self.font_main.render(f"{prefix}{atk}", True, col)
                surface.blit(txt, (BASE_WIDTH // 2 - 80, list_top + i * 20))
                if is_sel:
                    # small cursor soul
                    self.draw_soul(surface, BASE_WIDTH // 2 - 90, list_top + i * 20 + 7, 4)

            # keybinds (dev)
            kb_y = list_top + len(attacks) * 20 + 8
            pygame.draw.line(surface, (60, 60, 60), (20, kb_y), (BASE_WIDTH - 20, kb_y), 1)
            keys_info = [
                "ENTER = launch attack",
                "TAB   = toggle phase",
                "G     = toggle god mode",
                "P     = cycle pressure (0 / 0.5 / 1.0 / live)",
                "ESC   = back to main menu",
            ]
            for j, k in enumerate(keys_info):
                ks = self.font_ui.render(k, True, (160, 160, 160))
                surface.blit(ks, (BASE_WIDTH // 2 - ks.get_width() // 2, kb_y + 8 + j * 14))

            sprite_rect = self.current_sprite.get_rect(
                centerx=BASE_WIDTH - 40,
                centery=BASE_HEIGHT // 2
            )
            surface.blit(self.current_sprite, sprite_rect)
            return

        if self.state == "DEV_ATTACK":
            pass

        # TUTORIAL
        if self.state == "TUTORIAL":
            title = self.font_main.render(f"TUTORIAL - Step {self.tutorial_step + 1}/6", True, self.BLUE)
            surface.blit(title, (BASE_WIDTH // 2 - title.get_width() // 2, 20))
            pygame.draw.rect(surface, self.WHITE, self.box_rect, 2)

            if self.tutorial_step == 1:
                self.draw_soul(surface, self.soul_pos[0], self.soul_pos[1], 5)
                for b in self.tutorial_demo_bullets:
                    pygame.draw.circle(surface, self.ORANGE, (int(b["pos"][0]), int(b["pos"][1])), 4)
            elif self.tutorial_step == 2:
                pygame.draw.rect(surface, (40, 40, 40), (self.box_rect.centerx - 10, self.box_rect.top + 5, 20, 75))
                pygame.draw.rect(surface, self.ORANGE, (self.timing_bar_x, self.box_rect.top + 2, 4, 81))
            elif self.tutorial_step == 3:
                fake_opts = ["Check", "Compliment", "Hack", "Robot Dance"]
                for i, opt in enumerate(fake_opts):
                    c = self.YELLOW if i == 1 else self.WHITE
                    surface.blit(self.font_main.render(f"* {opt}", True, c),
                                 (self.box_rect.left + 35, self.box_rect.top + 10 + (i * 18)))
                self.draw_soul(surface, self.box_rect.left + 15, self.box_rect.top + 19 + 18, 4)
            elif self.tutorial_step == 4:
                mercy_bar = pygame.Rect(BASE_WIDTH // 2 - 120, self.box_rect.bottom + 10, 240, 18)
                pygame.draw.rect(surface, self.WHITE, mercy_bar, 3)
                fill = int((self.demo_mercy / 100) * 234)
                pygame.draw.rect(surface, self.YELLOW, (mercy_bar.x + 3, mercy_bar.y + 3, fill, 12))
                m_txt = self.font_main.render(f"MERCY {int(self.demo_mercy)}%", True, self.YELLOW)
                surface.blit(m_txt, (BASE_WIDTH // 2 - m_txt.get_width() // 2, mercy_bar.bottom + 8))

            instr_y      = self.box_rect.bottom + 12
            instr_height = BASE_HEIGHT - instr_y - 45
            instr_rect   = pygame.Rect(30, instr_y, BASE_WIDTH - 60, instr_height)
            pygame.draw.rect(surface, self.WHITE, instr_rect, 3)
            self.draw_text_wrapped(surface, self.tutorial_texts[self.tutorial_step],
                                   instr_rect, self.font_main, self.WHITE, top_padding=8, line_height=14)

            if self.message_text and self.message_text not in self.monologue_text:
                msg = self.font_ui.render(self.message_text, True, self.YELLOW)
                surface.blit(msg, (BASE_WIDTH // 2 - msg.get_width() // 2, instr_rect.bottom + 8))
            hint = self.font_ui.render("", True, self.YELLOW)
            surface.blit(hint, (BASE_WIDTH // 2 - hint.get_width() // 2, BASE_HEIGHT - 35))
            return

        # MERCY MENU
        if self.state == "MERCY_MENU":
            sprite_rect = self.current_sprite.get_rect(center=(BASE_WIDTH // 2, self.boss_y + 45))
            surface.blit(self.current_sprite, sprite_rect)
            pygame.draw.rect(surface, self.WHITE, self.box_rect, 3)
            name_color = self.YELLOW if (self.is_spareable and self.phase == 1) else self.WHITE
            surface.blit(self.font_main.render(f"* {self.enemy_name}", True, name_color),
                         (self.box_rect.left + 35, self.box_rect.top + 25))
            self.draw_soul(surface, self.box_rect.left + 15, self.box_rect.top + 30, 4)
            return

        # status GAME OVER
        if self.state == "GAME_OVER":
            f = self._frame
            vign = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
            for r in range(80, 0, -10):
                a = int(60 * (1 - r / 80))
                pygame.draw.rect(vign, (180, 0, 0, a),
                                 (BASE_WIDTH // 2 - r * 3, BASE_HEIGHT // 2 - r * 2,
                                  r * 6, r * 4), 12)
            surface.blit(vign, (0, 0))

            if (f % 40) < 3:
                dim = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 80))
                surface.blit(dim, (0, 0))

            # game over box
            hbox = pygame.Rect(40, 44, BASE_WIDTH - 80, 52)
            pygame.draw.rect(surface, (15, 0, 0), hbox)
            pygame.draw.rect(surface, self.RED, hbox, 2)
            go = self.font_title.render("GAME  OVER", True, self.RED)
            shake_x = random.randint(-1, 1) if (f % 6) == 0 else 0
            surface.blit(go, (BASE_WIDTH // 2 - go.get_width() // 2 + shake_x,
                               hbox.centery - go.get_height() // 2))

            pygame.draw.line(surface, (60, 0, 0), (40, 102), (BASE_WIDTH - 40, 102), 1)

            lines = ["Your data has been purged.", "But the soul never dies..."]
            for j, line in enumerate(lines):
                s = self.font_main.render(line, True, (200, 200, 200))
                surface.blit(s, (BASE_WIDTH // 2 - s.get_width() // 2, 118 + j * 20))

            pygame.draw.line(surface, (40, 40, 40), (40, 164), (BASE_WIDTH - 40, 164), 1)

            btn_w, btn_h = 180, 26
            bx = BASE_WIDTH // 2 - btn_w // 2
            self._draw_button(surface,
                              pygame.Rect(bx, 175, btn_w, btn_h),
                              "RETRY", self.font_main, True, f)
            esc_col = (160, 160, 160)
            esc_txt = self.font_ui.render("ESC  →  main menu", True, esc_col)
            surface.blit(esc_txt, (BASE_WIDTH // 2 - esc_txt.get_width() // 2, 210))

            self._draw_scanlines(surface, 30)
            return

        if self.state == "WIN":
            f = self._frame
            for i in range(28):
                seed  = i * 73
                angle = (seed % 360) * math.pi / 180
                dist  = 30 + (seed % 60) + (f * (1 + i % 3)) % 80
                px    = BASE_WIDTH  // 2 + int(math.cos(angle) * dist)
                py    = BASE_HEIGHT // 2 - 30 + int(math.sin(angle) * dist * 0.5)
                r     = 1 + (i % 3)
                a     = max(0, 200 - (f % 90) * 2)
                ps    = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
                pygame.draw.circle(ps, (255, 220, 0, a), (r, r), r)
                surface.blit(ps, (px - r, py - r))

            hbox = pygame.Rect(40, 44, BASE_WIDTH - 80, 52)
            pygame.draw.rect(surface, (20, 18, 0), hbox)
            pygame.draw.rect(surface, self.YELLOW, hbox, 2)

            pulse_scale = 1.0 + 0.03 * math.sin(f * 0.1)
            win_base    = self.font_title.render("YOU  WIN!", True, self.YELLOW)
            scaled_w    = int(win_base.get_width()  * pulse_scale)
            scaled_h    = int(win_base.get_height() * pulse_scale)
            win_scaled  = pygame.transform.scale(win_base, (scaled_w, scaled_h))
            surface.blit(win_scaled,
                         (BASE_WIDTH // 2 - scaled_w // 2,
                          hbox.centery - scaled_h // 2))

            pygame.draw.line(surface, (80, 70, 0), (40, 102), (BASE_WIDTH - 40, 102), 1)

            lines = ["The system is safe.", "WinMan has been purged."]
            for j, line in enumerate(lines):
                s = self.font_main.render(line, True, (220, 220, 180))
                surface.blit(s, (BASE_WIDTH // 2 - s.get_width() // 2, 118 + j * 20))

            pygame.draw.line(surface, (40, 40, 40), (40, 164), (BASE_WIDTH - 40, 164), 1)

            btn_w, btn_h = 200, 26
            bx = BASE_WIDTH // 2 - btn_w // 2
            self._draw_button(surface,
                              pygame.Rect(bx, 175, btn_w, btn_h),
                              "BACK TO MENU", self.font_main, True, f)

            self._draw_scanlines(surface, 14)
            return


        sprite = self.current_sprite
        if self.enemy_flash > 0:
            flash_surf = sprite.copy()
            flash_surf.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGBA_MAX)
            sprite = flash_surf
        sprite_rect = sprite.get_rect(center=(BASE_WIDTH // 2, self.boss_y + 45))
        surface.blit(sprite, sprite_rect)

        if self.state not in ["ENEMY_ATTACK", "GAME_OVER", "MONOLOGUE"]:
            quote = self.font_boss.render(f"'{self.current_quote}'", True, self.WHITE)
            surface.blit(quote, (BASE_WIDTH // 2 + 60, self.boss_y + 20))

        pygame.draw.rect(surface, self.WHITE, self.box_rect, 3)

        if self.state in ["MENU", "MENU_EXIT_POPUP", "MESSAGE", "MONOLOGUE"]:
            self.draw_text_wrapped(surface, f"* {self.message_text}", self.box_rect, self.font_main, self.WHITE)
            if self.state == "MONOLOGUE":
                prompt = self.font_ui.render("[ENTER]", True, self.YELLOW)
                surface.blit(prompt, (self.box_rect.right - 55, self.box_rect.bottom - 20))

            if self.state == "MENU_EXIT_POPUP":
                overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 170))
                surface.blit(overlay, (0, 0))
                pop = pygame.Rect(60, 70, BASE_WIDTH - 120, 130)
                pygame.draw.rect(surface, self.BLACK, pop)
                pygame.draw.rect(surface, self.WHITE, pop, 3)
                title_surf = self.font_main.render("Do you want to quit?", True, self.YELLOW)
                surface.blit(title_surf, (pop.centerx - title_surf.get_width() // 2, pop.y + 12))
                sub_surf = self.font_ui.render("Choose an option:", True, self.WHITE)
                surface.blit(sub_surf, (pop.centerx - sub_surf.get_width() // 2, pop.y + 35))
                options = ["RESTART", "MAIN MENU", "CANCEL"]
                for i, opt in enumerate(options):
                    col = self.ORANGE if i == self.menu_exit_choice else self.WHITE
                    txt = self.font_ui.render(opt, True, col)
                    x   = pop.x + 18 + i * ((pop.width - 36) // 3)
                    surface.blit(txt, (x + (((pop.width - 36) // 3) - txt.get_width()) // 2, pop.y + 75))
                hint = self.font_ui.render("←/→ select   ENTER confirm   ESC back", True, self.YELLOW)
                surface.blit(hint, (BASE_WIDTH // 2 - hint.get_width() // 2, pop.bottom - 22))

        elif self.state == "TARGET_SELECT":
            surface.blit(self.font_main.render("* Choose your target:", True, self.WHITE),
                         (self.box_rect.left + 20, self.box_rect.top + 12))
            surface.blit(self.font_main.render(f"> {self.enemy_name}", True, self.YELLOW),
                         (self.box_rect.left + 40, self.box_rect.top + 35))

        elif self.state in ["ACT_MENU", "ITEM_MENU"]:
            opts = self.act_options if self.state == "ACT_MENU" else [i["name"] for i in self.inventory]
            for i, opt in enumerate(opts):
                c = self.YELLOW if i == self.sub_selected else self.WHITE
                surface.blit(self.font_main.render(f"* {opt}", True, c),
                             (self.box_rect.left + 35, self.box_rect.top + 10 + (i * 18)))
            self.draw_soul(surface, self.box_rect.left + 15,
                           self.box_rect.top + 19 + (self.sub_selected * 18), 4)

        elif self.state == "FIGHT_TIMING":
            sweet_w = 20
            pygame.draw.rect(surface, (0, 80, 0),
                             (self.box_rect.centerx - sweet_w // 2, self.box_rect.top + 5,
                              sweet_w, 75))
            pygame.draw.rect(surface, (40, 40, 40),
                             (self.box_rect.centerx - 10, self.box_rect.top + 5, 20, 75))
            dist  = abs(self.timing_bar_x - self.box_rect.centerx)
            ratio = min(1.0, dist / (self.box_rect.width / 2))
            bar_r = min(255, max(0, int(ratio * 510)))
            bar_g = min(255, max(0, int((1 - ratio) * 510)))
            bar_c = (bar_r, bar_g, 0)
            pygame.draw.rect(surface, bar_c, (self.timing_bar_x, self.box_rect.top + 2, 4, 81))

        elif self.state in ("ENEMY_ATTACK", "DEV_ATTACK"):
            if (self.attack_type == "spear_drop"
                    and hasattr(self, "_spear_safe_flash")
                    and self._spear_safe_flash > 0):
                alpha = int(200 * (self._spear_safe_flash / 36))
                hint_surf = pygame.Surface((int(self._spear_lane_w), self.box_rect.height), pygame.SRCALPHA)
                hint_surf.fill((0, 255, 0, alpha))
                sx = self.box_rect.left + int(self._spear_safe_lane * self._spear_lane_w)
                surface.blit(hint_surf, (sx, self.box_rect.top))

            for b in self.bullets:
                if b.get("delay", 0) > 0:
                    continue
                if b["type"] == "laser":
                    self._draw_laser_telegraph(surface, b)
                elif b["type"] == "h_laser":
                    self._draw_h_laser_telegraph(surface, b)
                elif b["type"] == "homing":
                    pygame.draw.circle(surface, self.BLUE,  (int(b["pos"][0]), int(b["pos"][1])), 5)
                    pygame.draw.circle(surface, self.WHITE, (int(b["pos"][0]), int(b["pos"][1])), 2)
                elif b["type"] == "spear":
                    pygame.draw.rect(surface, self.ORANGE,
                                     (int(b["pos"][0] - 3), int(b["pos"][1] - 14), 6, 28))
                    pygame.draw.rect(surface, self.WHITE,
                                     (int(b["pos"][0] - 1), int(b["pos"][1] - 14), 2, 5))
                elif b["type"] == "bone":
                    pygame.draw.rect(surface, self.WHITE,
                                     (int(b["pos"][0] - 4), int(b["pos"][1] - 30), 8, 60))
                    # End caps
                    pygame.draw.ellipse(surface, self.WHITE,
                                        (int(b["pos"][0] - 6), int(b["pos"][1] - 34), 12, 8))
                    pygame.draw.ellipse(surface, self.WHITE,
                                        (int(b["pos"][0] - 6), int(b["pos"][1] + 26), 12, 8))
                else:
                    color = self.ORANGE if b["type"] == "bounce" else self.WHITE
                    pygame.draw.circle(surface, color, (int(b["pos"][0]), int(b["pos"][1])), 4)
                    pygame.draw.circle(surface, self.WHITE, (int(b["pos"][0]), int(b["pos"][1])), 2)

            if self.attack_type == "dog_joke":
                dog_rect = self.spr_dog.get_rect(center=(self.box_rect.centerx, self.box_rect.centery))
                surface.blit(self.spr_dog, dog_rect)

            #Soul
            self.draw_soul(surface, self.soul_pos[0], self.soul_pos[1], 5)

            if self.state == "DEV_ATTACK":
                bar = pygame.Surface((BASE_WIDTH, 16), pygame.SRCALPHA)
                bar.fill((0, 0, 0, 180))
                surface.blit(bar, (0, 0))
                atk_lbl = self.font_ui.render(
                    f"[DEV]  {self.attack_type}  |  phase {self.dev_phase}  |  "
                    f"pressure {self._pressure():.2f}  |  "
                    f"GOD {'ON' if self.dev_god_mode else 'OFF'}  |  "
                    f"timer {self.attack_timer}",
                    True, self.GREEN
                )
                surface.blit(atk_lbl, (4, 2))
                hint_bar = pygame.Surface((BASE_WIDTH, 14), pygame.SRCALPHA)
                hint_bar.fill((0, 0, 0, 160))
                surface.blit(hint_bar, (0, BASE_HEIGHT - 14))
                hint = self.font_ui.render(
                    "ESC = back to dev menu   R = restart this attack   G = toggle god",
                    True, (160, 160, 160)
                )
                surface.blit(hint, (BASE_WIDTH // 2 - hint.get_width() // 2, BASE_HEIGHT - 13))

        #HP bar
        if self.state not in ("MONOLOGUE", "DEV_MENU", "DEV_ATTACK"):
            pygame.draw.rect(surface, self.RED, (BASE_WIDTH // 2 - 50, self.hp_bar_y, 100, 10))
            fill_w = int((max(0.0, self.hp_display) / self.max_hp) * 100)
            pygame.draw.rect(surface, self.YELLOW, (BASE_WIDTH // 2 - 50, self.hp_bar_y, fill_w, 10))
            hp_lbl = self.font_ui.render(f"HP {int(self.hp)}/{self.max_hp}", True, self.WHITE)
            surface.blit(hp_lbl, (BASE_WIDTH // 2 + 55, self.hp_bar_y - 2))

            #Mercy bar
            if self.phase == 1 and self.state in ("MENU", "MESSAGE", "MONOLOGUE",
                                                   "ACT_MENU", "ITEM_MENU",
                                                   "TARGET_SELECT", "FIGHT_TIMING"):
                mercy_x = BASE_WIDTH // 2 - 50
                mercy_y = self.hp_bar_y + 13
                pygame.draw.rect(surface, (80, 80, 0), (mercy_x, mercy_y, 100, 5))
                m_fill = int((min(100, self.mercy_meter) / 100) * 100)
                mercy_col = self.YELLOW if self.is_spareable else (180, 180, 0)
                pygame.draw.rect(surface, mercy_col, (mercy_x, mercy_y, m_fill, 5))


            btns = ["FIGHT", "ACT", "ITEM", "MERCY"]
            btn_w  = (BASE_WIDTH - 20) // 4 - 4
            btn_h  = self.btn_height
            for i, b in enumerate(btns):
                bx = 10 + i * (btn_w + 4)
                r  = pygame.Rect(bx, self.btn_y, btn_w, btn_h)
                self._draw_button(surface, r, b, self.font_ui,
                                  self.state in ("MENU", "MENU_EXIT_POPUP") and i == self.selected_btn,
                                  self._frame)