import pygame
import random
import math
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT

class WinMan(Scene):
    def __init__(self, manager):
        super().__init__(manager)


        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 255, 0)
        self.ORANGE = (255, 128, 0)

        self.font_main = pygame.font.SysFont("couriernew", 14, bold=True)
        self.font_ui = pygame.font.SysFont("couriernew", 12, bold=True)
        self.font_boss = pygame.font.SysFont("couriernew", 14, italic=True)

        self.state = "MENU"
        self.selected_btn = 0
        self.sub_selected = 0
        self.message_text = "WinMan PRIME blokkeert de weg."

        self.hp = 20
        self.max_hp = 20
        self.inventory = [
            {"name": "Snoepje", "hp": 5},
            {"name": "Havermout", "hp": 10}
        ]

        self.enemy_name = "WinMan PRIME"
        self.enemy_hp = 100
        self.mercy_meter = 0
        self.is_spareable = False
        self.act_options = ["Check", "Compliment", "Hack", "Dansen"]
        self.boss_quotes = ["Systeemfout!", "01001001", "Oververhitting!", "Exit(0)"]
        self.current_quote = "Bereid je voor..."

        self.boss_y = 15
        self.box_rect = pygame.Rect(BASE_WIDTH // 2 - 140, 95, 280, 85)
        self.hp_bar_y = 195
        self.btn_y = 220
        self.btn_width = 65
        self.btn_height = 28

        self.soul_pos = [self.box_rect.centerx, self.box_rect.centery]
        self.soul_speed = 4

        self.timing_bar_x = self.box_rect.left + 10
        self.timing_speed = 7
        self.timing_dir = 1

        self.bullets = []
        self.attack_timer = 0
        self.attack_type = None


    def start_enemy_attack(self):
        self.state = "ENEMY_ATTACK"
        self.attack_timer = 140
        self.bullets = []
        self.soul_pos = [self.box_rect.centerx, self.box_rect.centery]
        self.current_quote = random.choice(self.boss_quotes)

        if self.enemy_hp < 50:
            self.attack_type = random.choice(["circle", "laser", "sides"])
        else:
            self.attack_type = random.choice(["rain", "sides"])


    def handle_selection(self):
        if self.selected_btn == 0:
            self.state = "FIGHT_TIMING"

        elif self.selected_btn == 1:
            self.state = "ACT_MENU"
            self.sub_selected = 0

        elif self.selected_btn == 2:
            if self.inventory:
                self.state = "ITEM_MENU"
                self.sub_selected = 0
            else:
                self.message_text = "Geen items meer!"
                self.state = "MESSAGE"

        elif self.selected_btn == 3:
            if self.is_spareable:
                self.message_text = "JE WINT! De robot laat je passeren."
            else:
                self.message_text = "De robot is nog niet overtuigd."
            self.state = "MESSAGE"

    def handle_events(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))

        if self.state == "MENU":
            if event.key == pygame.K_LEFT:
                self.selected_btn = (self.selected_btn - 1) % 4
            if event.key == pygame.K_RIGHT:
                self.selected_btn = (self.selected_btn + 1) % 4
            if event.key == pygame.K_RETURN:
                self.handle_selection()

        elif self.state in ["ACT_MENU", "ITEM_MENU"]:
            options = self.act_options if self.state == "ACT_MENU" else self.inventory
            limit = len(options)

            if event.key == pygame.K_DOWN:
                self.sub_selected = (self.sub_selected + 1) % limit
            if event.key == pygame.K_UP:
                self.sub_selected = (self.sub_selected - 1) % limit

            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"

            if event.key == pygame.K_RETURN:
                if self.state == "ACT_MENU":
                    opt = self.act_options[self.sub_selected]

                    if opt == "Check":
                        self.message_text = f"{self.enemy_name}: ATK 3 DEF 5. Een AI."

                    elif opt == "Compliment":
                        self.message_text = "Je prijst zijn code. Mercy +50%!"
                        self.mercy_meter += 50

                    elif opt == "Hack":
                        self.message_text = "Je typt 'sudo stop'."
                        self.mercy_meter += 20

                    elif opt == "Dansen":
                        self.message_text = "Je doet de robot-dans."
                        self.mercy_meter += 40

                    if self.mercy_meter >= 100:
                        self.is_spareable = True

                else:
                    item = self.inventory.pop(self.sub_selected)
                    self.hp = min(self.max_hp, self.hp + item["hp"])
                    self.message_text = f"+{item['hp']} HP!"

                self.state = "MESSAGE"

        elif self.state == "FIGHT_TIMING":
            if event.key == pygame.K_RETURN:
                dist = abs(self.timing_bar_x - self.box_rect.centerx)
                dmg = max(0, 20 - (dist // 8))
                self.enemy_hp -= int(dmg)
                self.message_text = f"KRAK! Je deed {int(dmg)} schade!"
                self.state = "MESSAGE"

        elif self.state == "MESSAGE":
            if event.key == pygame.K_RETURN:
                if "WINT" in self.message_text or self.enemy_hp <= 0:
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
                else:
                    self.start_enemy_attack()


    def update(self, dt):
        if self.state == "FIGHT_TIMING":
            self.timing_bar_x += self.timing_speed * self.timing_dir
            if self.timing_bar_x > self.box_rect.right or self.timing_bar_x < self.box_rect.left:
                self.timing_dir *= -1

        elif self.state == "ENEMY_ATTACK":

            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]: self.soul_pos[1] -= self.soul_speed
            if keys[pygame.K_DOWN]: self.soul_pos[1] += self.soul_speed
            if keys[pygame.K_LEFT]: self.soul_pos[0] -= self.soul_speed
            if keys[pygame.K_RIGHT]: self.soul_pos[0] += self.soul_speed

            # --- Attack patterns ---

            if self.attack_type == "rain":
                if random.random() < 0.12:
                    self.bullets.append({
                        "pos": [random.randint(self.box_rect.left, self.box_rect.right), self.box_rect.top],
                        "speed": random.randint(4, 7)
                    })

            elif self.attack_type == "sides":
                if random.random() < 0.08:
                    y = random.randint(self.box_rect.top, self.box_rect.bottom)
                    side = random.choice(["left", "right"])

                    if side == "left":
                        self.bullets.append({"pos": [self.box_rect.left, y], "vel": [5, 0]})
                    else:
                        self.bullets.append({"pos": [self.box_rect.right, y], "vel": [-5, 0]})

            elif self.attack_type == "circle":
                if self.attack_timer % 30 == 0:
                    cx = random.randint(self.box_rect.left, self.box_rect.right)
                    cy = random.randint(self.box_rect.top, self.box_rect.bottom)

                    for angle in range(0, 360, 30):
                        rad = math.radians(angle)
                        self.bullets.append({
                            "pos": [cx, cy],
                            "vel": [3 * math.cos(rad), 3 * math.sin(rad)]
                        })

            elif self.attack_type == "laser":
                if self.attack_timer % 50 == 0:
                    x = random.randint(self.box_rect.left, self.box_rect.right)
                    self.bullets.append({"laser": True, "x": x, "timer": 30})

            # --- Bullet update ---
            player_rect = pygame.Rect(self.soul_pos[0]-4, self.soul_pos[1]-4, 8, 8)

            for b in self.bullets[:]:
                if "laser" in b:
                    b["timer"] -= 1
                    if player_rect.colliderect(pygame.Rect(b["x"], self.box_rect.top, 3, self.box_rect.height)):
                        self.hp -= 1
                    if b["timer"] <= 0:
                        self.bullets.remove(b)
                    continue

                if "vel" in b:
                    b["pos"][0] += b["vel"][0]
                    b["pos"][1] += b["vel"][1]
                else:
                    b["pos"][1] += b.get("speed", 4)

                if player_rect.colliderect(pygame.Rect(b["pos"][0]-3, b["pos"][1]-3, 6, 6)):
                    self.hp -= 1
                    self.bullets.remove(b)

                elif not self.box_rect.collidepoint(b["pos"]):
                    self.bullets.remove(b)

            self.attack_timer -= 1
            if self.attack_timer <= 0 or self.hp <= 0:
                self.state = "MENU"



    def draw_soul(self, surface, x, y, size=3):
        pygame.draw.polygon(surface, self.RED,
            [(x, y-size), (x+size, y), (x, y+size), (x-size, y)])

    def draw(self, surface):
        surface.fill(self.BLACK)

        boss_color = self.YELLOW if self.is_spareable else self.WHITE
        pygame.draw.rect(surface, boss_color, (BASE_WIDTH//2 - 25, self.boss_y, 50, 50), 2)
        pygame.draw.circle(surface, self.RED, (BASE_WIDTH//2 - 8, self.boss_y + 15), 2)
        pygame.draw.circle(surface, self.RED, (BASE_WIDTH//2 + 8, self.boss_y + 15), 2)

        if self.state != "ENEMY_ATTACK":
            quote = self.font_boss.render(f"'{self.current_quote}'", True, self.WHITE)
            surface.blit(quote, (BASE_WIDTH//2 + 35, self.boss_y + 5))

        pygame.draw.rect(surface, self.WHITE, self.box_rect, 3)

        if self.state in ["MENU", "MESSAGE"]:
            txt = self.font_main.render(f"* {self.message_text}", True, self.WHITE)
            surface.blit(txt, (self.box_rect.left + 10, self.box_rect.top + 15))

        elif self.state in ["ACT_MENU", "ITEM_MENU"]:
            opts = self.act_options if self.state == "ACT_MENU" else [i["name"] for i in self.inventory]

            for i, opt in enumerate(opts):
                c = self.YELLOW if i == self.sub_selected else self.WHITE
                lbl = self.font_main.render(f"* {opt}", True, c)
                surface.blit(lbl, (self.box_rect.left + 35, self.box_rect.top + 10 + (i * 18)))

            self.draw_soul(surface,
                self.box_rect.left + 15,
                self.box_rect.top + 19 + (self.sub_selected * 18), 4)

        elif self.state == "FIGHT_TIMING":
            pygame.draw.rect(surface, (40, 40, 40),
                             (self.box_rect.centerx - 10, self.box_rect.top + 5, 20, 75))
            pygame.draw.rect(surface, self.WHITE,
                             (self.timing_bar_x, self.box_rect.top + 2, 4, 81))

        elif self.state == "ENEMY_ATTACK":
            self.draw_soul(surface, self.soul_pos[0], self.soul_pos[1], 5)

            for b in self.bullets:
                if "laser" in b:
                    pygame.draw.line(surface, self.RED,
                                     (b["x"], self.box_rect.top),
                                     (b["x"], self.box_rect.bottom), 3)
                else:
                    pygame.draw.circle(surface, self.WHITE,
                                       (int(b["pos"][0]), int(b["pos"][1])), 4)

        pygame.draw.rect(surface, self.RED, (BASE_WIDTH//2 - 50, self.hp_bar_y, 100, 10))
        pygame.draw.rect(surface, self.YELLOW,
                         (BASE_WIDTH//2 - 50, self.hp_bar_y,
                          (max(0, self.hp)/self.max_hp)*100, 10))

        hp_lbl = self.font_ui.render(f"HP {self.hp}/{self.max_hp}", True, self.WHITE)
        surface.blit(hp_lbl, (BASE_WIDTH//2 + 55, self.hp_bar_y - 2))

        btns = ["FIGHT", "ACT", "ITEM", "MERCY"]

        for i, b in enumerate(btns):
            x_pos = (BASE_WIDTH // 4) * i + 10
            active = (self.state == "MENU" and i == self.selected_btn)

            c = self.ORANGE if active else self.WHITE

            pygame.draw.rect(surface, c,
                             (x_pos, self.btn_y, self.btn_width, self.btn_height), 2)

            lbl = self.font_ui.render(b, True, self.YELLOW if active else c)
            surface.blit(lbl, (x_pos + 12, self.btn_y + 8))

            if active:
                self.draw_soul(surface, x_pos + 6, self.btn_y + 14, 3)